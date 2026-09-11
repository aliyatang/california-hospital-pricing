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
    / "normalized"
    / "kaiser"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pricing"
    / "kaiser"
)


def slugify(value):
    """Convert a location name into safe filename text."""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Build negotiated-price fact table "
            "for one Kaiser hospital MRF."
        )
    )

    parser.add_argument(
        "--location",
        required=True,
        help="MRF location name from the Kaiser manifest.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the existing price fact table.",
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
        / f"{facility_id}_{location_slug}"
    )

    output_path = (
        OUTPUT_DIR
        / f"{facility_id}_{location_slug}"
    )

    print("Building negotiated-price fact table")
    print("------------------------------------")
    print("Location:", location_name)
    print("CMS facility ID:", facility_id)
    print("Input:", input_path)
    print("Output:", output_path)
    print()

    if not input_path.exists():
        raise FileNotFoundError(
            f"Normalized MRF does not exist:\n"
            f"{input_path}\n\n"
            "Run normalize_kaiser_mrf_spark.py first."
        )

    if output_path.exists() and not args.force:
        print("Price fact output already exists.")
        print("Use --force to recreate it.")
        return

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("BuildPriceFact")
        .config(
            "spark.sql.shuffle.partitions",
            "8",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    df = spark.read.parquet(
        str(input_path)
    )

    required_columns = [
        "has_negotiated_price",
        "has_negotiated_dollar",
        "has_negotiated_percentage",
        "has_negotiated_algorithm",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Normalized data is missing required columns: "
            + ", ".join(missing_columns)
        )

    price_df = (
        df
        .filter(
            F.col("has_negotiated_price")
        )
        .withColumn(
            "price_representation",
            F.when(
                F.col("has_negotiated_dollar"),
                F.lit("dollar"),
            )
            .when(
                F.col("has_negotiated_percentage")
                & F.col("has_negotiated_algorithm"),
                F.lit("percentage_algorithm"),
            )
            .when(
                F.col("has_negotiated_percentage"),
                F.lit("percentage"),
            )
            .when(
                F.col("has_negotiated_algorithm"),
                F.lit("algorithm"),
            )
            .otherwise(
                F.lit("unknown")
            )
        )
        .cache()
    )

    normalized_count = df.count()
    price_count = price_df.count()

    print(
        "Normalized payer rows:",
        f"{normalized_count:,}",
    )

    print(
        "Negotiated-price rows:",
        f"{price_count:,}",
    )

    if normalized_count:
        print(
            "Percent with negotiated price:",
            f"{100 * price_count / normalized_count:.2f}%",
        )

    print("\nPrice representations:")

    (
        price_df
        .groupBy(
            "price_representation"
        )
        .count()
        .orderBy(
            F.desc("count")
        )
        .show(
            truncate=False
        )
    )

    print("\nRows by plan:")

    (
        price_df
        .groupBy("plan")
        .count()
        .orderBy(
            F.desc("count")
        )
        .show(
            truncate=False
        )
    )

    (
        price_df.write
        .mode("overwrite")
        .option(
            "compression",
            "snappy",
        )
        .parquet(
            str(output_path)
        )
    )

    print("\nPrice fact complete.")
    print("Saved to:")
    print(output_path)

    price_df.unpersist()

    spark.stop()


if __name__ == "__main__":
    main()