from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_PATH = (
    PROJECT_ROOT
    / "config"
    / "mrf_sources.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf_manifest_raw.csv"
)


FIELDS = [
    "location-name",
    "source-page-url",
    "mrf-url",
    "contact-name",
    "contact-email",
]


def fetch_txt(url):
    """Download a hospital price-transparency TXT file."""

    response = requests.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def parse_txt(text):
    """
    Parse CMS hospital-price-transparency TXT entries.

    Each hospital entry consists of five key:value fields.
    """

    rows = []
    current = {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip()
        value = value.strip()

        if key not in FIELDS:
            continue

        # A new location-name means a new hospital entry.
        if key == "location-name" and current:
            rows.append(current)
            current = {}

        current[key] = value

    if current:
        rows.append(current)

    return rows


def main():

    print("Discovering hospital MRFs...\n")

    sources = pd.read_csv(SOURCE_PATH)

    all_rows = []

    for _, source in sources.iterrows():

        print(
            f'Fetching {source["system_name"]}...'
        )

        text = fetch_txt(
            source["txt_url"]
        )

        entries = parse_txt(text)

        print(
            f"Found {len(entries)} MRF entries"
        )

        for entry in entries:

            all_rows.append(
                {
                    "system_name":
                        source["system_name"],

                    "txt_url":
                        source["txt_url"],

                    "location_name":
                        entry.get("location-name"),

                    "source_page_url":
                        entry.get("source-page-url"),

                    "mrf_url":
                        entry.get("mrf-url"),

                    "contact_name":
                        entry.get("contact-name"),

                    "contact_email":
                        entry.get("contact-email"),
                }
            )

    manifest = pd.DataFrame(all_rows)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nTotal MRF entries:", len(manifest))

    print("\nSaved manifest to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()