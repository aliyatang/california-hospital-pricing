from pathlib import Path
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

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_location_metadata.parquet"
)


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def normalize_header(value):
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def read_metadata(path):
    """
    Read the first two records of a CMS CSV-wide MRF.

    Record 1 = metadata field names
    Record 2 = metadata values
    """

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.reader(file)

        header = next(reader)
        values = next(reader)

    if len(header) != len(values):

        raise ValueError(
            f"Metadata header/value length mismatch "
            f"for {path.name}: "
            f"{len(header)} vs {len(values)}"
        )

    metadata = {}

    for key, value in zip(
        header,
        values,
    ):

        clean_key = normalize_header(
            key
        )

        if not clean_key:
            continue

        column_name = (
            f"mrf_meta__{clean_key}"
        )

        # Protect against any duplicate normalized headers.
        suffix = 2
        original_column_name = column_name

        while column_name in metadata:
            column_name = (
                f"{original_column_name}_{suffix}"
            )
            suffix += 1

        value = value.strip()

        metadata[column_name] = (
            value
            if value
            else None
        )

    return metadata


def main():

    manifest = pd.read_parquet(
        MANIFEST_PATH
    )

    records = []

    for row in manifest.itertuples(
        index=False
    ):

        facility_id = str(
            row.facility_id
        ).zfill(6)

        location_name = (
            row.location_name
        )

        slug = slugify(
            location_name
        )

        raw_path = (
            RAW_DIR
            / f"{facility_id}_{slug}.csv"
        )

        if not raw_path.exists():

            raise FileNotFoundError(
                f"Missing raw MRF: {raw_path}"
            )

        print(
            "Reading:",
            location_name,
        )

        metadata = read_metadata(
            raw_path
        )

        record = {
            "facility_id":
                facility_id,

            "manifest_location_name":
                location_name,

            "raw_filename":
                raw_path.name,
        }

        record.update(
            metadata
        )

        records.append(
            record
        )

    output = pd.DataFrame(
        records
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\nMRF locations:",
        len(output),
    )

    print(
        "Metadata columns:",
        len(output.columns) - 3,
    )

    print("\n=== METADATA FIELDS ===")

    for column in output.columns:

        if column.startswith(
            "mrf_meta__"
        ):
            print(column)

    interesting = [
        column
        for column in output.columns
        if (
            column
            in {
                "facility_id",
                "manifest_location_name",
            }
            or any(
                word in column
                for word in [
                    "hospital_name",
                    "location_name",
                    "address",
                    "license",
                    "npi",
                ]
            )
        )
    ]

    print(
        "\n=== LOCATION METADATA PREVIEW ==="
    )

    print(
        output[
            interesting
        ].head(10).to_string(
            index=False
        )
    )

    print("\nSaved:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()