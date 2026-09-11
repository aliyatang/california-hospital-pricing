from pathlib import Path
import argparse
import re

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_manifest_ca.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "kaiser"
)


def format_bytes(num_bytes):
    size = float(num_bytes)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} PB"


def slugify(value):
    """
    Convert a hospital location name into a safe filename.

    Example:
    "South San Francisco Medical Center"
        ->
    "south_san_francisco_medical_center"
    """

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def download_file(url, output_path):
    """Stream the MRF directly to disk."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    downloaded = 0

    with requests.get(
        url,
        stream=True,
        timeout=120,
    ) as response:

        response.raise_for_status()

        with open(output_path, "wb") as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if not chunk:
                    continue

                file.write(chunk)

                downloaded += len(chunk)

                print(
                    f"\rDownloaded: "
                    f"{format_bytes(downloaded)}",
                    end="",
                    flush=True,
                )

    print()

    return downloaded


def main():

    parser = argparse.ArgumentParser(
        description="Download one Kaiser hospital MRF."
    )

    parser.add_argument(
        "--location",
        required=True,
        help="MRF location name from the Kaiser manifest.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload even if the raw file already exists.",
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

    filename = (
        f"{facility_id}_{location_slug}.csv"
    )

    output_path = (
        OUTPUT_DIR
        / filename
    )

    print("Downloading MRF")
    print("---------------")
    print("Location:", row["location_name"])
    print("CMS facility ID:", facility_id)
    print("Destination:", output_path)
    print()

    if output_path.exists() and not args.force:

        print("File already exists.")
        print(
            "Use --force to download it again."
        )

        return

    size = download_file(
        row["mrf_url"],
        output_path,
    )

    print("\nDownload complete.")
    print(
        "File size:",
        format_bytes(size)
    )


if __name__ == "__main__":
    main()