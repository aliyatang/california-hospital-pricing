from pathlib import Path
import argparse
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

SUMMARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_batch_status.csv"
)


def run_location(location, force=False, force_download=False):
    """Run the full MRF pipeline for one Kaiser location."""

    command = [
        sys.executable,
        "src/run_kaiser_pipeline.py",
        "--location",
        location,
    ]

    if force:
        command.append("--force")

    if force_download:
        command.append("--force-download")

    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )


def main():

    parser = argparse.ArgumentParser(
        description="Batch process California Kaiser MRFs."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N MRF locations.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild derived outputs.",
    )

    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Redownload raw MRFs.",
    )

    args = parser.parse_args()

    manifest = pd.read_parquet(
        MANIFEST_PATH
    ).copy()

    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be greater than 0.")

        manifest = manifest.head(
            args.limit
        )

    print("\nKaiser Batch Pipeline")
    print("=====================")
    print("Locations selected:", len(manifest))

    results = []

    for index, row in enumerate(
        manifest.itertuples(index=False),
        start=1,
    ):

        location = row.location_name

        print("\n" + "=" * 75)
        print(
            f"[{index}/{len(manifest)}] "
            f"{location}"
        )
        print("=" * 75)

        try:
            run_location(
                location,
                force=args.force,
                force_download=args.force_download,
            )

            status = "success"
            error = None

        except subprocess.CalledProcessError as exc:
            status = "failed"
            error = str(exc)

        results.append(
            {
                "facility_id": row.facility_id,
                "location_name": location,
                "status": status,
                "error": error,
            }
        )

    summary = pd.DataFrame(
        results
    )

    SUMMARY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_csv(
        SUMMARY_PATH,
        index=False,
    )

    print("\n" + "=" * 75)
    print("BATCH SUMMARY")
    print("=" * 75)

    print(
        summary["status"]
        .value_counts()
        .to_string()
    )

    print("\nSaved status table to:")
    print(SUMMARY_PATH)

    failed = summary[
        summary["status"] == "failed"
    ]

    if not failed.empty:
        print("\nFailed locations:")

        print(
            failed[
                [
                    "facility_id",
                    "location_name",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()