from pathlib import Path
import re

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_manifest_ca.parquet"
)

HOSPITAL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospital_features_ca.parquet"
)

PRICE_ROOT = (
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
    / "kaiser_price_fact"
)

SUMMARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_location_summary"
)


def slugify(value):
    """Convert location name to the filename format used by the pipeline."""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def main():

    print("Building combined Kaiser pricing dataset...\n")

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("BuildKaiserPricingDataset")
        .config(
            "spark.sql.shuffle.partitions",
            "16",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    # --------------------------------------------------
    # 1. Load Kaiser MRF manifest
    # --------------------------------------------------

    manifest = spark.read.parquet(
        str(MANIFEST_PATH)
    )

    manifest = (
        manifest
        .withColumn(
            "facility_id",
            F.lpad(
                F.col("facility_id").cast("string"),
                6,
                "0",
            )
        )
    )

    expected_locations = manifest.count()

    print(
        "Expected Kaiser MRF locations:",
        expected_locations,
    )

    # --------------------------------------------------
    # 2. Build exact list of price-fact directories
    # --------------------------------------------------

    manifest_rows = (
        manifest
        .select(
            "facility_id",
            "location_name",
        )
        .collect()
    )

    price_paths = []

    missing_paths = []

    for row in manifest_rows:

        facility_id = row["facility_id"]
        location_name = row["location_name"]

        slug = slugify(
            location_name
        )

        path = (
            PRICE_ROOT
            / f"{facility_id}_{slug}"
        )

        if path.exists():
            price_paths.append(
                str(path)
            )
        else:
            missing_paths.append(
                (
                    facility_id,
                    location_name,
                    str(path),
                )
            )

    if missing_paths:

        print("\nMissing price-fact outputs:")

        for (
            facility_id,
            location_name,
            path,
        ) in missing_paths:

            print(
                facility_id,
                location_name,
                "->",
                path,
            )

        raise RuntimeError(
            f"{len(missing_paths)} Kaiser "
            "price-fact outputs are missing."
        )

    print(
        "Price-fact directories found:",
        len(price_paths),
    )

    # --------------------------------------------------
    # 3. Read all 37 price-fact datasets together
    # --------------------------------------------------

    prices = spark.read.parquet(
        *price_paths
    )

    prices = (
        prices
        .withColumn(
            "facility_id",
            F.lpad(
                F.col("facility_id").cast("string"),
                6,
                "0",
            )
        )
    )

    total_price_rows = prices.count()

    print(
        "Combined negotiated-price rows:",
        f"{total_price_rows:,}",
    )

    # --------------------------------------------------
    # 4. Add manifest provenance
    # --------------------------------------------------

    manifest_lookup = (
        manifest
        .select(
            "facility_id",
            F.col(
                "location_name"
            ).alias(
                "mrf_location_name"
            ),
            "system_name",
            "mrf_url",
            "source_page_url",
        )
    )

    prices = prices.join(
        manifest_lookup,
        on=[
            "facility_id",
            "mrf_location_name",
        ],
        how="left",
    )

    # --------------------------------------------------
    # 5. Attach SAFE CMS-level hospital features
    # --------------------------------------------------

    hospitals = spark.read.parquet(
        str(HOSPITAL_PATH)
    )

    hospitals = (
        hospitals
        .withColumn(
            "facility_id",
            F.lpad(
                F.col("facility_id").cast("string"),
                6,
                "0",
            )
        )
    )

    cms_features = (
        hospitals
        .select(
            "facility_id",
            F.col(
                "facility_name"
            ).alias(
                "cms_facility_name"
            ),
            "hospital_type",
            "hospital_ownership",
            "emergency_services",
            "overall_rating",
        )
    )

    # Make sure CMS side really is one row per ID.
    duplicate_cms_ids = (
        cms_features
        .groupBy("facility_id")
        .count()
        .filter(
            F.col("count") > 1
        )
        .count()
    )

    if duplicate_cms_ids:
        raise RuntimeError(
            "CMS feature table contains duplicate facility IDs."
        )

    enriched = prices.join(
        cms_features,
        on="facility_id",
        how="left",
    )

    # --------------------------------------------------
    # 6. Validation
    # --------------------------------------------------

    enriched_count = enriched.count()

    if enriched_count != total_price_rows:
        raise RuntimeError(
            "Hospital-feature join changed the pricing row count."
        )

    location_count = (
        enriched
        .select(
            "facility_id",
            "mrf_location_name",
        )
        .distinct()
        .count()
    )

    print(
        "Distinct MRF locations:",
        location_count,
    )

    missing_cms = (
        enriched
        .filter(
            F.col(
                "cms_facility_name"
            ).isNull()
        )
        .select(
            "facility_id",
            "mrf_location_name",
        )
        .distinct()
        .count()
    )

    print(
        "Locations missing CMS features:",
        missing_cms,
    )

    print("\nPrice representations:")

    (
        enriched
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

    # Check our fundamental row key again.
    duplicate_keys = (
        enriched
        .groupBy(
            "facility_id",
            "mrf_location_name",
            "source_row_number",
            "payer",
            "plan",
        )
        .count()
        .filter(
            F.col("count") > 1
        )
        .count()
    )

    print(
        "Duplicate source-row/payer keys:",
        duplicate_keys,
    )

    # --------------------------------------------------
    # 7. Location-level audit summary
    # --------------------------------------------------

    location_summary = (
        enriched
        .groupBy(
            "facility_id",
            "mrf_location_name",
            "cms_facility_name",
        )
        .agg(

            F.count("*").alias(
                "negotiated_price_rows"
            ),

            F.sum(
                F.when(
                    F.col(
                        "price_representation"
                    ) == "dollar",
                    1,
                ).otherwise(0)
            ).alias(
                "negotiated_dollar_rows"
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

            F.countDistinct(
                "code_1"
            ).alias(
                "unique_primary_codes"
            ),
        )
        .orderBy(
            "facility_id",
            "mrf_location_name",
        )
    )

    print("\n=== LOCATION SUMMARY ===")

    location_summary.show(
        50,
        truncate=50,
    )

    # --------------------------------------------------
    # 8. Save
    # --------------------------------------------------

    print("\nWriting combined pricing table...")

    (
        enriched.write
        .mode("overwrite")
        .option(
            "compression",
            "snappy",
        )
        .partitionBy(
            "facility_id"
        )
        .parquet(
            str(OUTPUT_PATH)
        )
    )

    (
        location_summary.write
        .mode("overwrite")
        .option(
            "compression",
            "snappy",
        )
        .parquet(
            str(SUMMARY_PATH)
        )
    )

    print("\nSaved combined price fact:")
    print(OUTPUT_PATH)

    print("\nSaved location summary:")
    print(SUMMARY_PATH)

    spark.stop()


if __name__ == "__main__":
    main()