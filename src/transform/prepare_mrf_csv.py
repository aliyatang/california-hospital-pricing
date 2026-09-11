from pathlib import Path
import argparse
import csv
import re

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_manifest_ca.parquet"
)

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "kaiser"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "kaiser"
)


def slugify(value):
    """Convert a location name into a safe filename."""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def main():

    parser = argparse.ArgumentParser(
        description="Prepare one Kaiser MRF CSV for Spark."
    )

    parser.add_argument(
        "--location",
        required=True,
        help="MRF location name from the Kaiser manifest.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing prepared CSV.",
    )

    args = parser.parse_args()

    manifest = pd.read_parquet(
        MANIFEST_PATH
    )

    match = manifest[
        manifest["location_name"]
        == args.location
    ]

    if len(match) == 0:
        raise ValueError(
            f"No MRF found for location: {args.location}"
        )

    if len(match) > 1:
        raise ValueError(
            f"Multiple MRF records found for: {args.location}"
        )

    row = match.iloc[0]

    facility_id = str(
        row["facility_id"]
    ).zfill(6)

    location_slug = slugify(
        row["location_name"]
    )

    raw_path = (
        RAW_DIR
        / f"{facility_id}_{location_slug}.csv"
    )

    output_path = (
        OUTPUT_DIR
        / f"{facility_id}_{location_slug}_pricing.csv"
    )

    print("Preparing pricing CSV")
    print("---------------------")
    print("Location:", row["location_name"])
    print("CMS facility ID:", facility_id)
    print("Input:", raw_path)
    print("Output:", output_path)
    print()

    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw MRF does not exist:\n{raw_path}\n\n"
            "Run download_mrf.py first."
        )

    if output_path.exists() and not args.force:
        print("Prepared file already exists.")
        print("Use --force to recreate it.")
        return

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pricing_rows = 0

    with open(
        raw_path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as infile, open(
        output_path,
        "w",
        encoding="utf-8",
        newline="",
    ) as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # CMS CSV-wide format:
        #
        # record 1 = metadata column names
        # record 2 = metadata values
        # record 3 = pricing table header
        try:
            next(reader)
            next(reader)
            pricing_header = next(reader)
        except StopIteration:
            raise ValueError(
                "MRF does not contain the expected "
                "metadata + pricing header records."
            )

        writer.writerow(
            ["source_row_number"]
            + pricing_header
        )

        for source_row_number, record in enumerate(
            reader,
            start=1,
        ):

            if len(record) != len(pricing_header):
                raise ValueError(
                    f"Source row {source_row_number}: "
                    f"found {len(record)} fields, "
                    f"expected {len(pricing_header)}."
                )

            writer.writerow(
                [source_row_number]
                + record
            )

            pricing_rows += 1

    print(
        "Pricing records:",
        f"{pricing_rows:,}",
    )

    print("\nPreparation complete.")


if __name__ == "__main__":
    main()