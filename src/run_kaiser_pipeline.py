from pathlib import Path
import argparse
import re
import subprocess
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_manifest_ca.parquet"
)

PREPARED_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "kaiser"
)


def slugify(value):
    """Convert a location name into safe filename text."""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def run_command(command):
    """Run one pipeline stage and stop if it fails."""

    print("\n" + "=" * 70)
    print("Running:")
    print(" ".join(command))
    print("=" * 70 + "\n")

    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )


def get_prepared_path(location):
    """
    Find the prepared CSV path for one manifest location.
    """

    manifest = pd.read_parquet(
        MANIFEST_PATH
    )

    match = manifest[
        manifest["location_name"] == location
    ]

    if len(match) != 1:
        raise ValueError(
            f"Expected exactly one manifest row for "
            f"{location}, found {len(match)}."
        )

    row = match.iloc[0]

    facility_id = str(
        row["facility_id"]
    ).zfill(6)

    location_slug = slugify(
        row["location_name"]
    )

    return (
        PREPARED_DIR
        / f"{facility_id}_{location_slug}_pricing.csv"
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run the full Kaiser MRF pipeline "
            "for one hospital location."
        )
    )

    parser.add_argument(
        "--location",
        required=True,
        help="MRF location name from the Kaiser manifest.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Recreate prepared, normalized, "
            "and price-fact outputs."
        ),
    )

    parser.add_argument(
        "--force-download",
        action="store_true",
        help=(
            "Redownload the raw MRF even if "
            "it already exists."
        ),
    )

    parser.add_argument(
        "--keep-prepared",
        action="store_true",
        help=(
            "Keep the temporary prepared CSV "
            "after successful processing."
        ),
    )

    args = parser.parse_args()

    python = sys.executable

    print("\nKaiser MRF Pipeline")
    print("===================")
    print("Location:", args.location)

    # --------------------------------------------------
    # 1. Download raw MRF
    # --------------------------------------------------

    download_command = [
        python,
        "src/ingest/download_mrf.py",
        "--location",
        args.location,
    ]

    if args.force_download:
        download_command.append(
            "--force"
        )

    run_command(
        download_command
    )

    # --------------------------------------------------
    # 2. Prepare raw CMS CSV for Spark
    # --------------------------------------------------

    prepare_command = [
        python,
        "src/transform/prepare_mrf_csv.py",
        "--location",
        args.location,
    ]

    if args.force:
        prepare_command.append(
            "--force"
        )

    run_command(
        prepare_command
    )

    # --------------------------------------------------
    # 3. Normalize wide MRF with Spark
    # --------------------------------------------------

    normalize_command = [
        python,
        "src/transform/normalize_kaiser_mrf_spark.py",
        "--location",
        args.location,
    ]

    if args.force:
        normalize_command.append(
            "--force"
        )

    run_command(
        normalize_command
    )

    # --------------------------------------------------
    # 4. Build negotiated-price fact table
    # --------------------------------------------------

    fact_command = [
        python,
        "src/transform/build_price_fact_spark.py",
        "--location",
        args.location,
    ]

    if args.force:
        fact_command.append(
            "--force"
        )

    run_command(
        fact_command
    )

    # --------------------------------------------------
    # 5. Remove temporary prepared CSV
    # --------------------------------------------------

    if not args.keep_prepared:

        prepared_path = get_prepared_path(
            args.location
        )

        if prepared_path.exists():

            size_mb = (
                prepared_path.stat().st_size
                / (1024 ** 2)
            )

            prepared_path.unlink()

            print("\nTemporary prepared CSV removed:")
            print(prepared_path)

            print(
                "Freed:",
                f"{size_mb:.2f} MB"
            )

        else:

            print(
                "\nNo temporary prepared CSV "
                "to remove."
            )

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print("Location:", args.location)


if __name__ == "__main__":
    main()