from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_price_fact"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bigquery"
    / "fact_kaiser_negotiated_price"
)


def main():

    print("Preparing Kaiser price fact for BigQuery...\n")

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("ExportKaiserPriceFactBigQuery")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.parquet(
        str(INPUT_PATH)
    )

    # Spark may infer partition directory values such as
    # 050760 as integers, so explicitly restore 6-digit CMS IDs.
    df = df.withColumn(
        "facility_id",
        F.lpad(
            F.col("facility_id").cast("string"),
            6,
            "0",
        ),
    )

    row_count = df.count()

    print(
        "Rows:",
        f"{row_count:,}",
    )

    location_count = (
        df.select(
            "facility_id",
            "mrf_location_name",
        )
        .distinct()
        .count()
    )

    print(
        "MRF locations:",
        location_count,
    )

    # One Parquet part file is convenient for a local BigQuery load.
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
            str(OUTPUT_DIR)
        )
    )

    print("\nSaved BigQuery export:")
    print(OUTPUT_DIR)

    spark.stop()


if __name__ == "__main__":
    main()