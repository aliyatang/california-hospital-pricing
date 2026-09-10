from pathlib import Path
import json
import os

import requests
import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "census"
OUTPUT_PATH = OUTPUT_DIR / "acs5_2024_zcta.json"


def load_config():
    """Load project data-source configuration."""
    with open(CONFIG_PATH, "r") as file:
        return yaml.safe_load(file)


def get_api_key():
    """Load Census API key from the local .env file."""
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("CENSUS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "CENSUS_API_KEY is missing from .env"
        )

    return api_key


def fetch_census_data(
    api_url,
    variable_map,
    geography,
    api_key,
):
    """Fetch ACS variables for all U.S. ZCTAs."""

    variable_codes = list(variable_map.values())

    get_fields = ",".join(
        ["NAME"] + variable_codes
    )

    params = {
        "get": get_fields,
        "for": f"{geography}:*",
        "key": api_key,
    }

    print("Requesting ACS data...")

    response = requests.get(
        api_url,
        params=params,
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


def save_raw_data(data):
    """Save raw Census API response."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(OUTPUT_PATH, "w") as file:
        json.dump(
            data,
            file,
            indent=2,
        )

    print("Saved Census data to:")
    print(OUTPUT_PATH)


def main():
    config = load_config()

    census_config = (
        config["census"]
        ["acs5_profile_2024"]
    )

    api_key = get_api_key()

    print("Downloading 2024 ACS 5-Year ZCTA data...")

    data = fetch_census_data(
        api_url=census_config["api_url"],
        variable_map=census_config["variables"],
        geography=census_config["geography"],
        api_key=api_key,
    )

    record_count = len(data) - 1

    print(f"Received {record_count} ZCTA records")

    save_raw_data(data)


if __name__ == "__main__":
    main()