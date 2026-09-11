from pathlib import Path
import csv

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_manifest_ca.parquet"
)

TEST_LOCATION = "Antioch Medical Center"


def inspect_mrf(url):
    """Inspect metadata, pricing schema, and first data row."""

    print("\nOpening streamed connection...")

    with requests.get(
        url,
        stream=True,
        timeout=60,
    ) as response:

        response.raise_for_status()

        # Handles the UTF-8 BOM correctly.
        response.encoding = "utf-8-sig"

        print("\n=== HTTP INFO ===")
        print("Status:", response.status_code)
        print(
            "Content-Type:",
            response.headers.get("Content-Type"),
        )
        print(
            "Content-Length:",
            response.headers.get("Content-Length"),
        )
        print(
            "Accept-Ranges:",
            response.headers.get("Accept-Ranges"),
        )

        lines = []

        for line in response.iter_lines(
            decode_unicode=True,
        ):
            if line is None:
                continue

            lines.append(line)

            # Need rows 1–4:
            # metadata header
            # metadata values
            # pricing header
            # first pricing record
            if len(lines) == 4:
                break

    if len(lines) < 4:
        raise RuntimeError(
            "Expected at least four rows in CSV MRF."
        )

    metadata_header = next(
        csv.reader([lines[0]])
    )

    metadata_values = next(
        csv.reader([lines[1]])
    )

    pricing_header = next(
        csv.reader([lines[2]])
    )

    first_record = next(
        csv.reader([lines[3]])
    )

    print("\n=== FILE METADATA ===")

    for key, value in zip(
        metadata_header,
        metadata_values,
    ):
        if key:
            print(f"{key}: {value}")

    print("\n=== PRICING TABLE ===")
    print(
        "Pricing columns:",
        len(pricing_header),
    )

    print(
        "First data-row fields:",
        len(first_record),
    )

    print("\nPricing column names:")

    for i, column in enumerate(
        pricing_header,
        start=1,
    ):
        print(f"{i:>3}. {column}")

    print("\n=== FIRST PRICING RECORD ===")

    for column, value in zip(
        pricing_header,
        first_record,
    ):
        print(
            f"{column}: {value[:150]}"
        )


def main():

    manifest = pd.read_parquet(
        MANIFEST_PATH
    )

    row = manifest[
        manifest["location_name"]
        == TEST_LOCATION
    ]

    if row.empty:
        raise ValueError(
            f"{TEST_LOCATION} not found."
        )

    row = row.iloc[0]

    print("Inspecting hospital MRF")
    print("-----------------------")
    print("Location:", row["location_name"])
    print("CMS facility ID:", row["facility_id"])

    inspect_mrf(
        row["mrf_url"]
    )


if __name__ == "__main__":
    main()