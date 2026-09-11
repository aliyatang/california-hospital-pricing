from pathlib import Path
import os

from dotenv import load_dotenv
from google.cloud import bigquery


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPORT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bigquery"
    / "fact_kaiser_negotiated_price"
)

load_dotenv(
    PROJECT_ROOT / ".env"
)

PROJECT_ID = os.getenv(
    "GOOGLE_CLOUD_PROJECT"
)

DATASET_NAME = os.getenv(
    "BIGQUERY_DATASET",
    "hospital_pricing",
)

TABLE_NAME = (
    "fact_kaiser_negotiated_price"
)


def main():

    if not PROJECT_ID:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT is not set."
        )

    parquet_files = list(
        EXPORT_DIR.glob(
            "part-*.parquet"
        )
    )

    if len(parquet_files) != 1:
        raise RuntimeError(
            f"Expected exactly one Parquet part file, "
            f"found {len(parquet_files)}."
        )

    input_path = parquet_files[0]

    table_id = (
        f"{PROJECT_ID}."
        f"{DATASET_NAME}."
        f"{TABLE_NAME}"
    )

    client = bigquery.Client(
        project=PROJECT_ID
    )

    job_config = (
        bigquery.LoadJobConfig(
            source_format=(
                bigquery.SourceFormat.PARQUET
            ),

            write_disposition=(
                bigquery.WriteDisposition
                .WRITE_TRUNCATE
            ),

            clustering_fields=[
                "facility_id",
                "code_1_type",
                "payer",
                "plan",
            ],
        )
    )

    print(
        "Loading:",
        input_path
    )

    print(
        "Destination:",
        table_id
    )

    print(
        "File size:",
        f"{input_path.stat().st_size / (1024 ** 2):.2f} MB"
    )

    with open(
        input_path,
        "rb",
    ) as file:

        job = (
            client.load_table_from_file(
                file,
                table_id,
                job_config=job_config,
            )
        )

        job.result()

    table = client.get_table(
        table_id
    )

    print(
        "\nBigQuery load complete."
    )

    print(
        "Rows in BigQuery:",
        f"{table.num_rows:,}",
    )

    print(
        "Columns:",
        len(table.schema),
    )

    print(
        "Clustering:",
        table.clustering_fields,
    )


if __name__ == "__main__":
    main()