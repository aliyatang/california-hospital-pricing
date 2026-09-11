from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "normalized"
    / "ucla"
)

EXPECTED_ROWS = {
    "050112": 1_148_815,
    "050262": 1_278_643,
    "050481": 273_263,
}

EXPECTED_TOTAL = sum(
    EXPECTED_ROWS.values()
)


def main():

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName(
            "ValidateAllUCLANormalizedMRFs"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    df = spark.read.parquet(
        str(INPUT_DIR / "*.parquet")
    )

    # -----------------------------
    # Core counts
    # -----------------------------

    row_count = df.count()

    facility_counts = {
        row["facility_id"]:
            row["count"]
        for row in (
            df.groupBy("facility_id")
            .count()
            .collect()
        )
    }

    distinct_keys = (
        df.select(
            "facility_id",
            "source_record_id",
        )
        .distinct()
        .count()
    )

    duplicate_keys = (
        df.groupBy(
            "facility_id",
            "source_record_id",
        )
        .count()
        .filter(
            F.col("count") > 1
        )
        .count()
    )

    no_price_rows = (
        df.filter(
            ~F.col(
                "has_negotiated_price"
            )
        )
        .count()
    )

    missing_facility = (
        df.filter(
            F.col(
                "facility_id"
            ).isNull()
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

    # -----------------------------
    # Summary
    # -----------------------------

    print(
        "\n=== UCLA VALIDATION SUMMARY ==="
    )

    print(
        "Total rows:",
        f"{row_count:,}",
    )

    print(
        "Distinct facility/source keys:",
        f"{distinct_keys:,}",
    )

    print(
        "Duplicate facility/source keys:",
        duplicate_keys,
    )

    print(
        "Rows without negotiated price:",
        no_price_rows,
    )

    print(
        "Rows missing facility ID:",
        missing_facility,
    )

    print(
        "Rows missing payer:",
        missing_payer,
    )

    print(
        "Rows missing plan:",
        missing_plan,
    )

    print(
        "\n=== ROWS BY FACILITY ==="
    )

    for facility_id in sorted(
        facility_counts
    ):

        print(
            facility_id,
            f"{facility_counts[facility_id]:,}",
        )

    print(
        "\n=== PRICE REPRESENTATIONS ==="
    )

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

    print(
        "\n=== PAYER STRUCTURE ==="
    )

    print(
        "Unique payers:",
        df.select("payer")
        .distinct()
        .count(),
    )

    print(
        "Unique payer-plan pairs:",
        df.select(
            "payer",
            "plan",
        )
        .distinct()
        .count(),
    )

    # -----------------------------
    # Assertions
    # -----------------------------

    if row_count != EXPECTED_TOTAL:
        raise RuntimeError(
            f"Expected "
            f"{EXPECTED_TOTAL:,} rows, "
            f"found {row_count:,}."
        )

    if facility_counts != EXPECTED_ROWS:
        raise RuntimeError(
            "Facility row counts "
            "do not match expected counts."
        )

    if distinct_keys != row_count:
        raise RuntimeError(
            "Composite source key "
            "is not unique."
        )

    if duplicate_keys != 0:
        raise RuntimeError(
            "Duplicate source rows detected."
        )

    if no_price_rows != 0:
        raise RuntimeError(
            "Rows without negotiated "
            "prices detected."
        )

    if missing_facility != 0:
        raise RuntimeError(
            "Missing facility IDs detected."
        )

    print(
        "\nAll UCLA normalized MRFs PASSED."
    )

    spark.stop()


if __name__ == "__main__":
    main()