from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
DATASET_ID = os.environ["BIGQUERY_DATASET"]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sutter_location_dimension.parquet"
)

TABLE_ID = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"dim_sutter_location"
)


def main():

    df = pd.read_parquet(INPUT_PATH)

    client = bigquery.Client(
        project=PROJECT_ID
    )

    job_config = bigquery.LoadJobConfig(
        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE
        )
    )

    print("Loading:", TABLE_ID)

    job = client.load_table_from_dataframe(
        df,
        TABLE_ID,
        job_config=job_config,
    )

    job.result()

    table = client.get_table(TABLE_ID)

    print("Rows:", table.num_rows)
    print("Columns:", len(table.schema))


if __name__ == "__main__":
    main()