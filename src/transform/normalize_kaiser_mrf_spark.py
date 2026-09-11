from collections import defaultdict
from functools import reduce
from pathlib import Path
import argparse
import re

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_manifest_ca.parquet"
)

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "kaiser"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "normalized"
    / "kaiser"
)


PAYER_COLUMN_PATTERN = re.compile(
    r"^(standard_charge|median_amount|10th_percentile|"
    r"90th_percentile|count|additional_payer_notes)"
    r"\|\[(.*?)\]\|\[(.*?)\]"
    r"(?:\|(negotiated_dollar|negotiated_percentage|"
    r"negotiated_algorithm|methodology))?$"
)


def slugify(value):
    """Convert location name to safe filename text."""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def quoted_col(name):
    """Safely reference Spark columns with special characters."""

    escaped = name.replace("`", "``")

    return F.col(f"`{escaped}`")


def clean_string(expr):
    """Trim strings and convert blanks to null."""

    value = F.trim(expr)

    return F.when(
        (value == "") | value.isNull(),
        F.lit(None).cast("string"),
    ).otherwise(value)


def clean_double(expr):
    """Convert price-like text to Spark double."""

    value = clean_string(expr)

    value = F.regexp_replace(
        value,
        r"[$,%]",
        "",
    )

    return value.cast("double")


def get_string(column_name):
    """Return cleaned string or typed null."""

    if column_name is None:
        return F.lit(None).cast("string")

    return clean_string(
        quoted_col(column_name)
    )


def get_double(column_name):
    """Return numeric value or typed null."""

    if column_name is None:
        return F.lit(None).cast("double")

    return clean_double(
        quoted_col(column_name)
    )


def get_count(column_name):
    """
    Preserve CMS count as a string.

    Valid values can include:
    - 0
    - 1 through 10
    - exact counts 11+
    """

    if column_name is None:
        return F.lit(None).cast("string")

    return clean_string(
        quoted_col(column_name)
    )


def discover_payer_groups(columns):
    """
    Detect payer/plan groups dynamically from the wide CSV header.
    """

    groups = defaultdict(dict)

    for column in columns:

        match = PAYER_COLUMN_PATTERN.match(
            column
        )

        if not match:
            continue

        prefix, payer, plan, suffix = (
            match.groups()
        )

        if prefix == "standard_charge":
            metric = suffix
        else:
            metric = prefix

        key = (
            payer.strip(),
            plan.strip(),
        )

        if metric in groups[key]:
            raise ValueError(
                f"Duplicate metric {metric} "
                f"for payer/plan {key}"
            )

        groups[key][metric] = column

    return dict(groups)


def build_payer_structs(groups):
    """Build Spark structs for each detected payer/plan group."""

    structs = []

    for (payer, plan), fields in sorted(
        groups.items()
    ):

        structs.append(
            F.struct(

                F.lit(payer).alias(
                    "payer"
                ),

                F.lit(plan).alias(
                    "plan"
                ),

                get_double(
                    fields.get(
                        "negotiated_dollar"
                    )
                ).alias(
                    "negotiated_dollar"
                ),

                get_double(
                    fields.get(
                        "negotiated_percentage"
                    )
                ).alias(
                    "negotiated_percentage"
                ),

                get_string(
                    fields.get(
                        "negotiated_algorithm"
                    )
                ).alias(
                    "negotiated_algorithm"
                ),

                get_double(
                    fields.get(
                        "median_amount"
                    )
                ).alias(
                    "median_amount"
                ),

                get_double(
                    fields.get(
                        "10th_percentile"
                    )
                ).alias(
                    "p10_amount"
                ),

                get_double(
                    fields.get(
                        "90th_percentile"
                    )
                ).alias(
                    "p90_amount"
                ),

                get_count(
                    fields.get(
                        "count"
                    )
                ).alias(
                    "negotiated_count"
                ),

                get_string(
                    fields.get(
                        "methodology"
                    )
                ).alias(
                    "methodology"
                ),

                get_string(
                    fields.get(
                        "additional_payer_notes"
                    )
                ).alias(
                    "additional_payer_notes"
                ),
            )
        )

    return structs

def normalize_base_column_variants(df):
    """
    Normalize small schema/header differences across Kaiser MRFs.

    Some Kaiser files use 'Modifiers ' in the position where
    other files use 'modifier'. Some also omit the separate
    generic 'modifiers' column entirely.
    """

    columns = df.columns

    # -------------------------------------------
    # Normalize the procedure-level modifier field
    # -------------------------------------------

    if "modifier" not in columns and "setting" in columns:

        setting_index = columns.index("setting")

        candidates = [
            col
            for col in columns
            if (
                col.strip().lower()
                in {"modifier", "modifiers"}
                and columns.index(col) < setting_index
            )
        ]

        if len(candidates) == 1:

            old_name = candidates[0]

            print(
                f"Normalizing column "
                f"{old_name!r} -> 'modifier'"
            )

            df = df.withColumnRenamed(
                old_name,
                "modifier",
            )

    # -------------------------------------------
    # Some Kaiser files omit this second field
    # -------------------------------------------

    if "modifiers" not in df.columns:

        print(
            "Column 'modifiers' not present; "
            "adding nullable field."
        )

        df = df.withColumn(
            "modifiers",
            F.lit(None).cast("string"),
        )

    return df


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Normalize one Kaiser CSV-wide MRF "
            "with PySpark."
        )
    )

    parser.add_argument(
        "--location",
        required=True,
        help="MRF location name from Kaiser manifest.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite normalized output if it exists.",
    )

    args = parser.parse_args()

    manifest = pd.read_parquet(
        MANIFEST_PATH
    )

    match = manifest[
        manifest["location_name"]
        == args.location
    ]

    if len(match) == 0:
        raise ValueError(
            f"No MRF found for location: {args.location}"
        )

    if len(match) > 1:
        raise ValueError(
            f"Multiple MRF records found for: {args.location}"
        )

    row = match.iloc[0]

    facility_id = str(
        row["facility_id"]
    ).zfill(6)

    location_name = row[
        "location_name"
    ]

    location_slug = slugify(
        location_name
    )

    input_path = (
        INPUT_DIR
        / f"{facility_id}_{location_slug}_pricing.csv"
    )

    output_path = (
        OUTPUT_DIR
        / f"{facility_id}_{location_slug}"
    )

    print("Starting Spark MRF normalization")
    print("--------------------------------")
    print("Location:", location_name)
    print("CMS facility ID:", facility_id)
    print("Input:", input_path)
    print("Output:", output_path)
    print()

    if not input_path.exists():
        raise FileNotFoundError(
            f"Prepared MRF does not exist:\n"
            f"{input_path}\n\n"
            "Run prepare_mrf_csv.py first."
        )

    if output_path.exists() and not args.force:
        print("Normalized output already exists.")
        print("Use --force to recreate it.")
        return

    spark = (
        SparkSession.builder
        .appName(
            "KaiserMRFNormalization"
        )
        .master("local[*]")
        .config(
            "spark.sql.shuffle.partitions",
            "8",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    print("Reading pricing CSV...")

    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", False)
        .option("multiLine", True)
        .option("quote", '"')
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .csv(str(input_path))
    )

    print(
        "Input columns:",
        len(df.columns),
    )

    df = normalize_base_column_variants(
        df
    )

    if "source_row_number" not in df.columns:
        raise ValueError(
            "Prepared CSV is missing source_row_number."
        )

    groups = discover_payer_groups(
        df.columns
    )

    if not groups:
        raise ValueError(
            "No payer-specific columns detected."
        )

    print(
        "\nDetected payer-plan groups:",
        len(groups),
    )

    for payer, plan in sorted(groups):
        print(
            f"  payer={payer} | plan={plan}"
        )

    payer_structs = build_payer_structs(
        groups
    )

    long_df = (
        df
        .withColumn(
            "_payer",
            F.explode(
                F.array(
                    *payer_structs
                )
            ),
        )
        .select(

            F.lit(
                facility_id
            ).alias(
                "facility_id"
            ),

            F.lit(
                location_name
            ).alias(
                "mrf_location_name"
            ),

            F.col(
                "source_row_number"
            ).cast(
                "long"
            ).alias(
                "source_row_number"
            ),

            clean_string(
                quoted_col("description")
            ).alias(
                "description"
            ),

            clean_string(
                quoted_col("code|1")
            ).alias(
                "code_1"
            ),

            clean_string(
                quoted_col("code|1|type")
            ).alias(
                "code_1_type"
            ),

            clean_string(
                quoted_col("code|2")
            ).alias(
                "code_2"
            ),

            clean_string(
                quoted_col("code|2|type")
            ).alias(
                "code_2_type"
            ),

            clean_string(
                quoted_col("modifier")
            ).alias(
                "modifier"
            ),

            clean_string(
                quoted_col("setting")
            ).alias(
                "setting"
            ),

            clean_string(
                quoted_col(
                    "drug_unit_of_measurement"
                )
            ).alias(
                "drug_unit_of_measurement"
            ),

            clean_string(
                quoted_col(
                    "drug_type_of_measurement"
                )
            ).alias(
                "drug_type_of_measurement"
            ),

            get_double(
                "standard_charge|gross"
            ).alias(
                "gross_charge"
            ),

            get_double(
                "standard_charge|discounted_cash"
            ).alias(
                "discounted_cash_charge"
            ),

            clean_string(
                quoted_col("modifiers")
            ).alias(
                "modifiers"
            ),

            get_double(
                "standard_charge|min"
            ).alias(
                "minimum_charge"
            ),

            get_double(
                "standard_charge|max"
            ).alias(
                "maximum_charge"
            ),

            clean_string(
                quoted_col(
                    "additional_generic_notes"
                )
            ).alias(
                "additional_generic_notes"
            ),

            F.col(
                "_payer.payer"
            ).alias(
                "payer"
            ),

            F.col(
                "_payer.plan"
            ).alias(
                "plan"
            ),

            F.col(
                "_payer.negotiated_dollar"
            ),

            F.col(
                "_payer.negotiated_percentage"
            ),

            F.col(
                "_payer.negotiated_algorithm"
            ),

            F.col(
                "_payer.median_amount"
            ),

            F.col(
                "_payer.p10_amount"
            ),

            F.col(
                "_payer.p90_amount"
            ),

            F.col(
                "_payer.negotiated_count"
            ),

            F.col(
                "_payer.methodology"
            ),

            F.col(
                "_payer.additional_payer_notes"
            ),
        )
    )

    # Flags describing what kind of negotiated-price
    # representation exists for this payer/service row.
    long_df = (
        long_df
        .withColumn(
            "has_negotiated_dollar",
            F.col(
                "negotiated_dollar"
            ).isNotNull(),
        )
        .withColumn(
            "has_negotiated_percentage",
            F.col(
                "negotiated_percentage"
            ).isNotNull(),
        )
        .withColumn(
            "has_negotiated_algorithm",
            F.col(
                "negotiated_algorithm"
            ).isNotNull(),
        )
        .withColumn(
            "has_negotiated_price",
            (
                F.col(
                    "negotiated_dollar"
                ).isNotNull()
                |
                F.col(
                    "negotiated_percentage"
                ).isNotNull()
                |
                F.col(
                    "negotiated_algorithm"
                ).isNotNull()
            ),
        )
    )

    meaningful_columns = [
        "negotiated_dollar",
        "negotiated_percentage",
        "negotiated_algorithm",
        "median_amount",
        "p10_amount",
        "p90_amount",
        "negotiated_count",
        "methodology",
        "additional_payer_notes",
    ]

    has_payer_data = reduce(
        lambda left, right: left | right,
        [
            F.col(column).isNotNull()
            for column
            in meaningful_columns
        ],
    )

    long_df = (
        long_df
        .filter(
            has_payer_data
        )
        .cache()
    )

    print("\nCounting rows...")

    service_rows = df.count()
    payer_rows = long_df.count()

    print(
        "Original service records:",
        f"{service_rows:,}",
    )

    print(
        "Normalized payer rows:",
        f"{payer_rows:,}",
    )

    if service_rows:
        print(
            "Average payer rows per service:",
            f"{payer_rows / service_rows:.2f}",
        )

    negotiated_rows = (
        long_df
        .filter(
            F.col(
                "has_negotiated_price"
            )
        )
        .count()
    )

    print(
        "Rows with negotiated price:",
        f"{negotiated_rows:,}",
    )

    print("\nWriting Parquet...")

    (
        long_df.write
        .mode("overwrite")
        .option(
            "compression",
            "snappy",
        )
        .parquet(
            str(output_path)
        )
    )

    print("\nNormalization complete.")
    print("Saved to:")
    print(output_path)

    long_df.unpersist()

    spark.stop()


if __name__ == "__main__":
    main()