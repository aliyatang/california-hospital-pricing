from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ucla_price_fact"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bigquery"
    / "fact_ucla_negotiated_price"
)


def main():

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName(
            "ExportUCLAFactForBigQuery"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    df = (
        spark.read
        .parquet(
            str(INPUT_PATH)
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

    row_count = df.count()

    facility_count = (
        df.select(
            "facility_id"
        )
        .distinct()
        .count()
    )

    print(
        "\n=== BIGQUERY EXPORT ==="
    )

    print(
        "Rows:",
        f"{row_count:,}",
    )

    print(
        "Facilities:",
        facility_count,
    )

    if row_count != 2_700_721:
        raise RuntimeError(
            "Unexpected UCLA row count."
        )

    if facility_count != 3:
        raise RuntimeError(
            "Unexpected facility count."
        )

    (
        df
        .coalesce(1)
        .write
        .mode("overwrite")
        .option(
            "compression",
            "snappy",
        )
        .parquet(
            str(OUTPUT_PATH)
        )
    )

    print(
        "\nSaved:"
    )

    print(
        OUTPUT_PATH
    )

    spark.stop()


if __name__ == "__main__":
    main()