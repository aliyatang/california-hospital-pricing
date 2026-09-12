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

OUTPUT_FACT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ucla_price_fact"
)

OUTPUT_SUMMARY = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ucla_location_summary"
)


EXPECTED_FACILITIES = {
    "050112",
    "050262",
    "050481",
}


def main():

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName(
            "BuildUCLAPricingDataset"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    df = spark.read.parquet(
        str(INPUT_DIR / "*.parquet")
    )

    # ---------------------------------
    # Keep only negotiated-price rows
    # ---------------------------------

    fact = (
        df
        .filter(
            F.col(
                "has_negotiated_price"
            )
        )
        .withColumn(
            "facility_id",
            F.lpad(
                F.col(
                    "facility_id"
                ).cast("string"),
                6,
                "0",
            ),
        )
    )

    row_count = fact.count()

    facility_count = (
        fact.select(
            "facility_id"
        )
        .distinct()
        .count()
    )

    facilities = {
        row["facility_id"]
        for row in (
            fact.select(
                "facility_id"
            )
            .distinct()
            .collect()
        )
    }

    duplicate_keys = (
        fact
        .groupBy(
            "facility_id",
            "source_record_id",
        )
        .count()
        .filter(
            F.col("count") > 1
        )
        .count()
    )

    # ---------------------------------
    # Location summary
    # ---------------------------------

    summary = (
        fact
        .groupBy(
            "system_name",
            "facility_id",
            "mrf_location_name",
        )
        .agg(
            F.count("*").alias(
                "negotiated_rows"
            ),

            F.countDistinct(
                "payer"
            ).alias(
                "unique_payers"
            ),

            F.countDistinct(
                "plan"
            ).alias(
                "unique_plans"
            ),

            F.countDistinct(
                F.struct(
                    "payer",
                    "plan",
                )
            ).alias(
                "unique_payer_plan_pairs"
            ),

            F.countDistinct(
                "code_1"
            ).alias(
                "unique_primary_codes"
            ),

            F.sum(
                F.col(
                    "has_negotiated_dollar"
                ).cast("long")
            ).alias(
                "rows_with_dollar"
            ),

            F.sum(
                F.col(
                    "has_negotiated_percentage"
                ).cast("long")
            ).alias(
                "rows_with_percentage"
            ),

            F.sum(
                F.col(
                    "has_negotiated_algorithm"
                ).cast("long")
            ).alias(
                "rows_with_algorithm"
            ),
        )
        .orderBy(
            "facility_id"
        )
    )

    # ---------------------------------
    # Validation
    # ---------------------------------

    print(
        "\n=== UCLA COMBINED FACT ==="
    )

    print(
        "Rows:",
        f"{row_count:,}",
    )

    print(
        "Facilities:",
        facility_count,
    )

    print(
        "Facility IDs:",
        sorted(facilities),
    )

    print(
        "Duplicate source keys:",
        duplicate_keys,
    )

    print(
        "\n=== PRICE REPRESENTATIONS ==="
    )

    (
        fact.groupBy(
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
        "\n=== LOCATION SUMMARY ==="
    )

    summary.show(
        truncate=False
    )

    if row_count != 2_700_721:

        raise RuntimeError(
            "Unexpected UCLA combined "
            "row count."
        )

    if facilities != EXPECTED_FACILITIES:

        raise RuntimeError(
            "Unexpected UCLA facilities."
        )

    if duplicate_keys != 0:

        raise RuntimeError(
            "Duplicate source keys "
            "detected."
        )

    # ---------------------------------
    # Write processed datasets
    # ---------------------------------

    (
        fact.write
        .mode("overwrite")
        .parquet(
            str(OUTPUT_FACT)
        )
    )

    (
        summary.write
        .mode("overwrite")
        .parquet(
            str(OUTPUT_SUMMARY)
        )
    )

    print(
        "\nSaved fact:"
    )

    print(
        OUTPUT_FACT
    )

    print(
        "\nSaved summary:"
    )

    print(
        OUTPUT_SUMMARY
    )

    spark.stop()


if __name__ == "__main__":
    main()