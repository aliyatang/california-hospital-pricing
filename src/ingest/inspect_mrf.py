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


def format_bytes(num_bytes):
    """Convert bytes to a readable file size."""

    if num_bytes is None:
        return "Unknown"

    size = float(num_bytes)

    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1000:
            return f"{size:.2f} {unit}"

        size /= 1000

    return f"{size:.2f} TB"


def inspect_mrf(url):
    """
    Inspect an MRF without downloading the entire file.
    """

    print("\nOpening streamed connection...")

    with requests.get(
        url,
        stream=True,
        timeout=60,
    ) as response:

        response.raise_for_status()

        print("\n=== HTTP INFO ===")
        print("Status:", response.status_code)
        print(
            "Content-Type:",
            response.headers.get("Content-Type"),
        )

        content_length = response.headers.get(
            "Content-Length"
        )

        if content_length:
            content_length = int(content_length)

        print(
            "File size:",
            format_bytes(content_length),
        )

        print(
            "Accept-Ranges:",
            response.headers.get("Accept-Ranges"),
        )

        print("\n=== FIRST LINES ===")

        lines = []

        for line in response.iter_lines(
            decode_unicode=True,
        ):

            if not line:
                continue

            lines.append(line)

            print(
                f"\nLine {len(lines)} "
                f"({len(line):,} characters)"
            )

            # Avoid flooding the terminal if a line is enormous.
            print(line[:2000])

            if len(line) >= 2000:
                print("\n... [line truncated]")

            if len(lines) == 3:
                break

        if not lines:
            raise RuntimeError(
                "MRF returned no readable lines."
            )

        # Interpret first row as CSV header.
        header = next(
            csv.reader([lines[0]])
        )

        print("\n=== CSV HEADER ===")
        print("Number of columns:", len(header))

        print("\nColumn names:")

        for i, column in enumerate(
            header,
            start=1,
        ):
            print(f"{i:>3}. {column}")


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
            f"Could not find {TEST_LOCATION} "
            "in the Kaiser manifest."
        )

    row = row.iloc[0]

    print("Inspecting hospital MRF")
    print("-----------------------")
    print("Location:", row["location_name"])
    print("CMS facility ID:", row["facility_id"])
    print("URL:", row["mrf_url"])

    inspect_mrf(
        row["mrf_url"]
    )


if __name__ == "__main__":
    main()