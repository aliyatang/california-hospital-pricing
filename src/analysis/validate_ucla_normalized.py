from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "normalized"
    / "ucla"
    / "050262_ronald_reagan_ucla_medical_center.parquet"
)


def main():

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("ValidateUCLANormalizedMRF")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.parquet(
        str(INPUT_PATH)
    )

    row_count = df.count()

    distinct_record_ids = (
        df.select("source_record_id")
        .distinct()
        .count()
    )

    duplicate_keys = (
        df.groupBy("source_record_id")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )

    no_price_rows = (
        df.filter(
            ~F.col("has_negotiated_price")
        )
        .count()
    )

    missing_payer = (
        df.filter(
            F.col("payer").isNull()
        )
        .count()
    )

    missing_plan = (
        df.filter(
            F.col("plan").isNull()
        )
        .count()
    )

    print("\n=== VALIDATION SUMMARY ===")

    print(
        "Rows:",
        f"{row_count:,}",
    )

    print(
        "Distinct source record IDs:",
        f"{distinct_record_ids:,}",
    )

    print(
        "Duplicate source record IDs:",
        duplicate_keys,
    )

    print(
        "Rows without negotiated price:",
        no_price_rows,
    )

    print(
        "Rows missing payer:",
        missing_payer,
    )

    print(
        "Rows missing plan:",
        missing_plan,
    )

    print("\n=== PRICE REPRESENTATIONS ===")

    (
        df.groupBy(
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

    print("\n=== CODE TYPES ===")

    (
        df.groupBy(
            "code_1_type"
        )
        .count()
        .orderBy(
            F.desc("count")
        )
        .show(
            truncate=False
        )
    )

    print("\n=== SETTINGS ===")

    (
        df.groupBy(
            "setting"
        )
        .count()
        .orderBy(
            F.desc("count")
        )
        .show(
            truncate=False
        )
    )

    if row_count != 1_278_643:
        raise RuntimeError(
            "Unexpected normalized row count."
        )

    if distinct_record_ids != row_count:
        raise RuntimeError(
            "source_record_id is not unique."
        )

    if duplicate_keys != 0:
        raise RuntimeError(
            "Duplicate source records detected."
        )

    if no_price_rows != 0:
        raise RuntimeError(
            "Rows without negotiated prices detected."
        )

    print("\nUCLA normalization validation PASSED.")

    spark.stop()


if __name__ == "__main__":
    main()