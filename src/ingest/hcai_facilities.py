from pathlib import Path
import json

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "hcai"
OUTPUT_PATH = OUTPUT_DIR / "facility_profile_attributes.json"

PAGE_SIZE = 1000


def load_config():
    """Load project data-source configuration."""
    with open(CONFIG_PATH, "r") as file:
        return yaml.safe_load(file)


def fetch_facilities(api_url, resource_id):
    """Fetch all HCAI facility records using the CKAN DataStore API."""

    facilities = []
    offset = 0

    while True:
        params = {
            "resource_id": resource_id,
            "limit": PAGE_SIZE,
            "offset": offset,
        }

        response = requests.get(
            api_url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        payload = response.json()

        if not payload.get("success"):
            raise RuntimeError("HCAI API returned an unsuccessful response.")

        result = payload["result"]
        records = result["records"]
        total = result["total"]

        if not records:
            break

        facilities.extend(records)

        print(
            f"Fetched {len(records)} records "
            f"(total: {len(facilities)} / {total})"
        )

        if len(facilities) >= total:
            break

        offset += PAGE_SIZE

    return facilities


def save_raw_data(facilities):
    """Save raw HCAI API records without transforming them."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(OUTPUT_PATH, "w") as file:
        json.dump(
            facilities,
            file,
            indent=2,
        )

    print(f"Saved {len(facilities)} facilities to:")
    print(OUTPUT_PATH)


def main():
    config = load_config()

    hcai_config = config["hcai"]["facility_profile_attributes"]

    api_url = hcai_config["api_url"]
    resource_id = hcai_config["resource_id"]

    print("Downloading HCAI Facility Profile Attributes...")

    facilities = fetch_facilities(
        api_url,
        resource_id,
    )

    if not facilities:
        raise RuntimeError("HCAI returned no facility records.")

    save_raw_data(facilities)


if __name__ == "__main__":
    main()