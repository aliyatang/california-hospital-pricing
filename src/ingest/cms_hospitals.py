from pathlib import Path
import json

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "cms"
OUTPUT_PATH = OUTPUT_DIR / "hospital_general_information_ca.json"

STATE = "CA"
PAGE_SIZE = 500


def load_config():
    """Load project data-source configuration."""
    with open(CONFIG_PATH, "r") as file:
        return yaml.safe_load(file)


def fetch_california_hospitals(api_url):
    """Fetch all California hospitals from the CMS Provider Data API."""
    hospitals = []
    offset = 0

    while True:
        params = {
            "limit": PAGE_SIZE,
            "offset": offset,
            "conditions[0][property]": "state",
            "conditions[0][operator]": "=",
            "conditions[0][value]": STATE,
        }

        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        hospitals.extend(results)

        print(
            f"Fetched {len(results)} records "
            f"(total: {len(hospitals)})"
        )

        if len(results) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return hospitals


def save_raw_data(hospitals):
    """Save the CMS response records without transforming them."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w") as file:
        json.dump(hospitals, file, indent=2)

    print(f"Saved {len(hospitals)} hospitals to:")
    print(OUTPUT_PATH)


def main():
    config = load_config()

    api_url = config["cms"]["hospital_general_information"]["api_url"]

    print("Downloading CMS Hospital General Information")
    print(f"State: {STATE}")

    hospitals = fetch_california_hospitals(api_url)

    if not hospitals:
        raise RuntimeError("CMS returned no California hospital records")

    save_raw_data(hospitals)


if __name__ == "__main__":
    main()