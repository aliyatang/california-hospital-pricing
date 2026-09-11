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
    / "kaiser"
    / "050760_antioch"
)


def main():

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("ValidateNormalizedMRF")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.parquet(
        str(INPUT_PATH)
    )

    print("\n=== BASIC COUNTS ===")

    print("Rows:", f"{df.count():,}")

    print("\nRows by plan:")

    (
        df.groupBy("plan")
        .count()
        .orderBy("plan")
        .show()
    )

    print("\n=== PRICE COVERAGE ===")

    df.select(
        F.count(
            F.when(
                F.col("negotiated_dollar").isNotNull(),
                1,
            )
        ).alias("negotiated_dollar"),

        F.count(
            F.when(
                F.col("negotiated_percentage").isNotNull(),
                1,
            )
        ).alias("negotiated_percentage"),

        F.count(
            F.when(
                F.col("negotiated_algorithm").isNotNull(),
                1,
            )
        ).alias("negotiated_algorithm"),

        F.count(
            F.when(
                F.col("median_amount").isNotNull(),
                1,
            )
        ).alias("median_amount"),
    ).show()

    print("\n=== SETTINGS ===")

    (
        df.groupBy("setting")
        .count()
        .orderBy(
            F.desc("count")
        )
        .show()
    )

    print("\n=== CODE TYPES ===")

    (
        df.groupBy("code_1_type")
        .count()
        .orderBy(
            F.desc("count")
        )
        .show(20)
    )

    print("\n=== METHODOLOGIES ===")

    (
        df.groupBy("methodology")
        .count()
        .orderBy(
            F.desc("count")
        )
        .show(20, truncate=False)
    )

    print("\n=== DUPLICATE NORMALIZED KEYS ===")

    duplicates = (
        df.groupBy(
            "facility_id",
            "source_row_number",
            "payer",
            "plan",
        )
        .count()
        .filter(
            F.col("count") > 1
        )
    )

    duplicate_count = duplicates.count()

    print(
        "Duplicate source-row/payer keys:",
        duplicate_count,
    )

    if duplicate_count:
        duplicates.show(
            20,
            truncate=False,
        )

    print("\n=== NEGOTIATED PRICE TYPES ===")

    (
        df.groupBy(
            "has_negotiated_dollar",
            "has_negotiated_percentage",
            "has_negotiated_algorithm",
        )
        .count()
        .orderBy(
            F.desc("count")
        )
        .show(
            truncate=False
        )
    )

    print("\nRows with any negotiated price representation:")

    print(
        f"{df.filter(F.col('has_negotiated_price')).count():,}"
    )

    print("\n=== ROWS WITHOUT NEGOTIATED PRICE ===")

    no_price = df.filter(
        ~F.col("has_negotiated_price")
    )

    print(
        "Rows without negotiated price:",
        f"{no_price.count():,}",
    )

    print("\nMethodologies:")

    (
        no_price
        .groupBy("methodology")
        .count()
        .orderBy(F.desc("count"))
        .show(20, truncate=False)
    )

    print("\nOther price/stat fields present:")

    no_price.select(
        F.count(
            F.when(
                F.col("median_amount").isNotNull(),
                1,
            )
        ).alias("median_amount"),

        F.count(
            F.when(
                F.col("p10_amount").isNotNull(),
                1,
            )
        ).alias("p10_amount"),

        F.count(
            F.when(
                F.col("p90_amount").isNotNull(),
                1,
            )
        ).alias("p90_amount"),

        F.count(
            F.when(
                F.col("negotiated_count").isNotNull(),
                1,
            )
        ).alias("negotiated_count"),

        F.count(
            F.when(
                F.col("additional_payer_notes").isNotNull(),
                1,
            )
        ).alias("payer_notes"),

    ).show()

    print("\n=== DRG 1 EXAMPLE ===")

    (
        df.filter(
            (F.col("code_1") == "1")
            & (F.col("code_1_type") == "MS-DRG")
        )
        .select(
            "source_row_number",
            "description",
            "setting",
            "modifier",
            "modifiers",
            "payer",
            "plan",
            "negotiated_dollar",
            "methodology",
            "additional_payer_notes",
        )
        .orderBy(
            "source_row_number",
            "plan",
        )
        .show(
            30,
            truncate=80,
        )
    )

    spark.stop()


if __name__ == "__main__":
    main()