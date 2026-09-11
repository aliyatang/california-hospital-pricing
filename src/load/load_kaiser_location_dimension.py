from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_location_dimension.parquet"
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
    "dim_kaiser_location"
)


def main():

    if not PROJECT_ID:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT is not set."
        )

    df = pd.read_parquet(
        INPUT_PATH
    )

    # -----------------------------
    # Preserve identifier types
    # -----------------------------

    string_columns = [
        "facility_id",
        "mrf_location_name",
        "mrf_hospital_name",
        "mrf_address",
        "mrf_license_number",
        "mrf_type_2_npi",
        "hcai_id",
        "hcai_facility_name_dim",
        "hcai_address_dim",
        "hcai_city",
        "hcai_zip",
        "license_type",
        "license_category",
        "facility_level",
        "er_service_level",
        "facility_status",
        "match_method",
        "zcta",
    ]

    for column in string_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .astype("string")
            )

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
            write_disposition=(
                bigquery.WriteDisposition
                .WRITE_TRUNCATE
            )
        )
    )

    print(
        "Loading:",
        INPUT_PATH
    )

    print(
        "Rows:",
        len(df)
    )

    print(
        "Destination:",
        table_id
    )

    job = (
        client.load_table_from_dataframe(
            df,
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
        table.num_rows
    )

    print(
        "Columns:",
        len(table.schema)
    )


if __name__ == "__main__":
    main()