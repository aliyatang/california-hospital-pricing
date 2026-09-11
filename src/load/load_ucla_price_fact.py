from pathlib import Path
import os

from dotenv import load_dotenv
from google.cloud import bigquery


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / ".env"
)

PROJECT_ID = os.environ[
    "GOOGLE_CLOUD_PROJECT"
]

DATASET_ID = os.environ[
    "BIGQUERY_DATASET"
]

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bigquery"
    / "fact_ucla_negotiated_price"
)

TABLE_ID = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"fact_ucla_negotiated_price"
)


def main():

    parquet_files = list(
        INPUT_DIR.rglob(
            "*.parquet"
        )
    )

    if len(parquet_files) != 1:
        raise RuntimeError(
            f"Expected 1 Parquet part, "
            f"found {len(parquet_files)}."
        )

    parquet_path = (
        parquet_files[0]
    )

    client = bigquery.Client(
        project=PROJECT_ID
    )

    job_config = (
        bigquery.LoadJobConfig(
            source_format=(
                bigquery.SourceFormat
                .PARQUET
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
        "Loading:"
    )

    print(
        parquet_path
    )

    print(
        "\nDestination:"
    )

    print(
        TABLE_ID
    )

    with open(
        parquet_path,
        "rb",
    ) as file:

        job = (
            client.load_table_from_file(
                file,
                TABLE_ID,
                job_config=job_config,
            )
        )

        job.result()

    table = client.get_table(
        TABLE_ID
    )

    print(
        "\nRows:",
        f"{table.num_rows:,}",
    )

    print(
        "Columns:",
        len(table.schema),
    )


if __name__ == "__main__":
    main()