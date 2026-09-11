from pathlib import Path
import hashlib
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

PREPARED_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "kaiser"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_mrf_hashes.parquet"
)


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def sha256_file(path):
    """Calculate SHA-256 without loading the whole file into memory."""

    hasher = hashlib.sha256()

    with open(path, "rb") as file:

        while True:

            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            hasher.update(chunk)

    return hasher.hexdigest()


def main():

    print("Checking Kaiser MRF content hashes...\n")

    manifest = pd.read_parquet(
        MANIFEST_PATH
    )

    rows = []

    for row in manifest.itertuples(
        index=False
    ):

        facility_id = str(
            row.facility_id
        ).zfill(6)

        slug = slugify(
            row.location_name
        )

        base_name = (
            f"{facility_id}_{slug}"
        )

        raw_path = (
            RAW_DIR
            / f"{base_name}.csv"
        )

        prepared_path = (
            PREPARED_DIR
            / f"{base_name}_pricing.csv"
        )

        if not raw_path.exists():
            continue

        print(
            f"Hashing {row.location_name}..."
        )

        raw_hash = sha256_file(
            raw_path
        )

        pricing_hash = (
            sha256_file(
                prepared_path
            )
            if prepared_path.exists()
            else None
        )

        rows.append(
            {
                "facility_id":
                    facility_id,

                "location_name":
                    row.location_name,

                "raw_sha256":
                    raw_hash,

                "pricing_sha256":
                    pricing_hash,
            }
        )

    hashes = pd.DataFrame(
        rows
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    hashes.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\n=== FILE HASHES ===")

    print(
        hashes[
            [
                "facility_id",
                "location_name",
                "raw_sha256",
                "pricing_sha256",
            ]
        ].to_string(
            index=False
        )
    )

    print("\n=== UNIQUE COUNTS ===")

    print(
        "Raw files:",
        len(hashes)
    )

    print(
        "Unique raw files:",
        hashes["raw_sha256"].nunique()
    )

    print(
        "Unique pricing tables:",
        hashes["pricing_sha256"].nunique()
    )

    print("\n=== SHARED PRICING TABLES ===")

    shared = (
        hashes
        .groupby(
            "pricing_sha256",
            dropna=False
        )
        .agg(
            locations=(
                "location_name",
                list
            ),
            location_count=(
                "location_name",
                "size"
            ),
        )
        .reset_index()
    )

    shared = shared[
        shared["location_count"] > 1
    ]

    if shared.empty:

        print(
            "No identical pricing tables detected."
        )

    else:

        for row in shared.itertuples(
            index=False
        ):

            print(
                f"\nIdentical pricing table "
                f"across {row.location_count} locations:"
            )

            for location in row.locations:
                print(
                    " -",
                    location
                )

    print("\nSaved:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()