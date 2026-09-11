from pathlib import Path
import argparse
import csv
import re

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCES_PATH = (
    PROJECT_ROOT
    / "config"
    / "ucla_mrf_sources.csv"
)

CROSSWALK_PATH = (
    PROJECT_ROOT
    / "config"
    / "ucla_mrf_crosswalk.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "ucla"
)


def slugify(value):
    value = value.lower()
    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )
    return value.strip("_")


def read_csv(path):
    with open(
        path,
        newline="",
        encoding="utf-8",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def get_location_record(location_name):

    sources = {
        row["location_name"]:
            row["mrf_url"]
        for row in read_csv(
            SOURCES_PATH
        )
    }

    crosswalk = {
        row["location_name"]:
            row
        for row in read_csv(
            CROSSWALK_PATH
        )
    }

    if location_name not in sources:
        raise ValueError(
            f"Location not found in "
            f"{SOURCES_PATH.name}: "
            f"{location_name}"
        )

    if location_name not in crosswalk:
        raise ValueError(
            f"Location not found in "
            f"{CROSSWALK_PATH.name}: "
            f"{location_name}"
        )

    row = crosswalk[
        location_name
    ]

    if row["status"] != "include":
        raise ValueError(
            f"{location_name} is marked "
            f"{row['status']}."
        )

    return {
        "location_name":
            location_name,
        "facility_id":
            row["facility_id"],
        "mrf_url":
            sources[
                location_name
            ],
    }


def download(
    location_name,
    force=False,
):

    record = get_location_record(
        location_name
    )

    facility_id = record[
        "facility_id"
    ]

    filename = (
        f"{facility_id}_"
        f"{slugify(location_name)}"
        ".json"
    )

    output_path = (
        OUTPUT_DIR
        / filename
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        output_path.exists()
        and not force
    ):
        print(
            "Already exists:"
        )
        print(
            output_path
        )
        return output_path

    temp_path = Path(
        str(output_path)
        + ".part"
    )

    print(
        "Downloading:"
    )
    print(
        location_name
    )

    print(
        "CMS facility ID:",
        facility_id,
    )

    with requests.get(
        record["mrf_url"],
        stream=True,
        timeout=120,
    ) as response:

        response.raise_for_status()

        total_bytes = 0

        with open(
            temp_path,
            "wb",
        ) as file:

            for chunk in (
                response.iter_content(
                    chunk_size=1024 * 1024
                )
            ):

                if not chunk:
                    continue

                file.write(
                    chunk
                )

                total_bytes += (
                    len(chunk)
                )

                if (
                    total_bytes
                    // (100 * 1024 * 1024)
                    !=
                    (
                        total_bytes
                        - len(chunk)
                    )
                    // (100 * 1024 * 1024)
                ):
                    print(
                        f"Downloaded "
                        f"{total_bytes / (1024 ** 2):,.0f} MB"
                    )

    temp_path.replace(
        output_path
    )

    print(
        "\nDownloaded:",
        f"{output_path.stat().st_size / (1024 ** 2):.2f} MB",
    )

    print(
        "Saved:"
    )
    print(
        output_path
    )

    return output_path


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--location",
        required=True,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    download(
        args.location,
        force=args.force,
    )


if __name__ == "__main__":
    main()