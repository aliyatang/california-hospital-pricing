import os

from dotenv import load_dotenv
from google.cloud import bigquery


load_dotenv()

PROJECT_ID = os.getenv(
    "GOOGLE_CLOUD_PROJECT"
)

DATASET_NAME = os.getenv(
    "BIGQUERY_DATASET",
    "hospital_pricing",
)


def main():

    if not PROJECT_ID:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT is not set."
        )

    client = bigquery.Client(
        project=PROJECT_ID
    )

    dataset_id = (
        f"{PROJECT_ID}.{DATASET_NAME}"
    )

    dataset = bigquery.Dataset(
        dataset_id
    )

    dataset.location = "US"

    client.create_dataset(
        dataset,
        exists_ok=True,
    )

    print(
        "BigQuery dataset ready:"
    )
    print(dataset_id)


if __name__ == "__main__":
    main()