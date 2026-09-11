from pathlib import Path
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

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "kaiser"
)

PREPARED_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "kaiser"
)

NORMALIZED_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "normalized"
    / "kaiser"
)

PRICE_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pricing"
    / "kaiser"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_pipeline_metrics.parquet"
)


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def directory_size(path):
    """Return total size of all files in a directory."""

    if not path.exists():
        return None

    return sum(
        file.stat().st_size
        for file in path.rglob("*")
        if file.is_file()
    )


def bytes_to_mb(num_bytes):
    if num_bytes is None:
        return None

    return round(
        num_bytes / (1024 ** 2),
        2,
    )


def main():

    print("Building Kaiser pipeline metrics...\n")

    manifest = pd.read_parquet(
        MANIFEST_PATH
    )

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("KaiserPipelineMetrics")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    results = []

    for index, row in enumerate(
        manifest.itertuples(index=False),
        start=1,
    ):

        facility_id = str(
            row.facility_id
        ).zfill(6)

        location_name = row.location_name

        slug = slugify(
            location_name
        )

        base_name = (
            f"{facility_id}_{slug}"
        )

        raw_path = (
            RAW_DIR
            / f"{base_name}.csv"
        )

        prepared_path = (
            PREPARED_DIR
            / f"{base_name}_pricing.csv"
        )

        normalized_path = (
            NORMALIZED_DIR
            / base_name
        )

        price_path = (
            PRICE_DIR
            / base_name
        )

        print(
            f"[{index}/{len(manifest)}] "
            f"{location_name}"
        )

        source_rows = None
        normalized_rows = None

        negotiated_rows = None
        dollar_rows = None
        percentage_algorithm_rows = None

        # -----------------------------
        # Normalized table metrics
        # -----------------------------

        if normalized_path.exists():

            normalized = spark.read.parquet(
                str(normalized_path)
            )

            stats = (
                normalized
                .agg(
                    F.count("*").alias(
                        "normalized_rows"
                    ),

                    F.max(
                        "source_row_number"
                    ).alias(
                        "source_rows"
                    ),
                )
                .first()
            )

            normalized_rows = (
                stats["normalized_rows"]
            )

            source_rows = (
                stats["source_rows"]
            )

        # -----------------------------
        # Price fact metrics
        # -----------------------------

        if price_path.exists():

            prices = spark.read.parquet(
                str(price_path)
            )

            stats = (
                prices
                .agg(
                    F.count("*").alias(
                        "negotiated_rows"
                    ),

                    F.sum(
                        F.when(
                            F.col(
                                "price_representation"
                            ) == "dollar",
                            1,
                        ).otherwise(0)
                    ).alias(
                        "dollar_rows"
                    ),

                    F.sum(
                        F.when(
                            F.col(
                                "price_representation"
                            )
                            == "percentage_algorithm",
                            1,
                        ).otherwise(0)
                    ).alias(
                        "percentage_algorithm_rows"
                    ),
                )
                .first()
            )

            negotiated_rows = (
                stats["negotiated_rows"]
            )

            dollar_rows = (
                stats["dollar_rows"]
            )

            percentage_algorithm_rows = (
                stats[
                    "percentage_algorithm_rows"
                ]
            )

        pipeline_complete = (
            raw_path.exists()
            and normalized_path.exists()
            and price_path.exists()
        )

        results.append(
            {
                "facility_id":
                    facility_id,

                "location_name":
                    location_name,

                "raw_exists":
                    raw_path.exists(),

                "raw_size_mb":
                    bytes_to_mb(
                        raw_path.stat().st_size
                        if raw_path.exists()
                        else None
                    ),

                # This is temporary staging data,
                # so False does NOT imply pipeline failure.
                "prepared_temp_exists":
                    prepared_path.exists(),

                "prepared_temp_size_mb":
                    bytes_to_mb(
                        prepared_path.stat().st_size
                        if prepared_path.exists()
                        else None
                    ),

                "normalized_exists":
                    normalized_path.exists(),

                "normalized_size_mb":
                    bytes_to_mb(
                        directory_size(
                            normalized_path
                        )
                    ),

                "price_fact_exists":
                    price_path.exists(),

                "price_fact_size_mb":
                    bytes_to_mb(
                        directory_size(
                            price_path
                        )
                    ),

                "pipeline_complete":
                    pipeline_complete,

                "source_rows":
                    source_rows,

                "normalized_rows":
                    normalized_rows,

                "negotiated_price_rows":
                    negotiated_rows,

                "negotiated_dollar_rows":
                    dollar_rows,

                "percentage_algorithm_rows":
                    percentage_algorithm_rows,
            }
        )

    metrics = pd.DataFrame(
        results
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metrics.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\n=== PIPELINE COVERAGE ===")

    print(
        "Manifest MRFs:",
        len(metrics)
    )

    print(
        "Raw downloaded:",
        metrics["raw_exists"].sum()
    )

    print(
        "Temporary prepared CSVs currently on disk:",
        metrics["prepared_temp_exists"].sum()
    )

    print(
        "Normalized:",
        metrics["normalized_exists"].sum()
    )

    print(
        "Price fact:",
        metrics["price_fact_exists"].sum()
    )

    print(
        "Pipeline complete:",
        metrics["pipeline_complete"].sum()
    )

    print("\n=== AVAILABLE HOSPITAL METRICS ===")

    available = metrics[
    metrics["pipeline_complete"]
    ]

    print(
        available[
            [
                "facility_id",
                "location_name",
                "raw_size_mb",
                "source_rows",
                "normalized_rows",
                "negotiated_price_rows",
                "negotiated_dollar_rows",
                "percentage_algorithm_rows",
            ]
        ].to_string(
            index=False
        )
    )

    print("\nSaved:")
    print(OUTPUT_PATH)

    spark.stop()


if __name__ == "__main__":
    main()