from pathlib import Path
import json

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "sources.yaml"
)

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "census"
    / "acs5_2024_zcta.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "acs5_2024_zcta.parquet"
)


def load_config():
    """Load project data-source configuration."""
    with open(CONFIG_PATH, "r") as file:
        return yaml.safe_load(file)


def load_raw_data():
    """
    Convert the Census API response into a DataFrame.

    Census format:
        first row = column names
        remaining rows = data
    """
    with open(INPUT_PATH) as file:
        data = json.load(file)

    columns = data[0]
    rows = data[1:]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def clean_census_data(df, variable_map, geography):
    """Clean and rename ACS ZCTA variables."""

    df = df.copy()

    # Config is friendly_name -> Census_code.
    # pandas rename needs Census_code -> friendly_name.
    rename_map = {
        code: name
        for name, code in variable_map.items()
    }

    rename_map["NAME"] = "zcta_name"
    rename_map[geography] = "zcta"

    df = df.rename(
        columns=rename_map
    )

    keep_columns = [
        "zcta",
        "zcta_name",
        *variable_map.keys(),
    ]

    df = df[keep_columns].copy()

    # ZIP/ZCTA is an identifier, not a number.
    df["zcta"] = (
        df["zcta"]
        .astype("string")
        .str.zfill(5)
    )

    numeric_columns = list(
        variable_map.keys()
    )

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # ACS uses negative sentinel values for some
    # unavailable/suppressed estimates.
    for column in numeric_columns:
        df.loc[
            df[column] < 0,
            column,
        ] = pd.NA

    # Percentage variables should be between 0 and 100.
    rate_columns = [
        "poverty_rate",
        "uninsured_rate",
        "unemployment_rate",
        "bachelors_or_higher_rate",
    ]

    for column in rate_columns:
        invalid = (
            (df[column] < 0)
            | (df[column] > 100)
        )

        df.loc[
            invalid,
            column,
        ] = pd.NA

    if not df["zcta"].is_unique:
        raise ValueError(
            "Duplicate ZCTAs detected."
        )

    return df


def save_clean_data(df):
    """Save cleaned Census table as Parquet."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("Saved cleaned Census data to:")
    print(OUTPUT_PATH)


def main():

    print("Cleaning 2024 ACS ZCTA data...\n")

    config = load_config()

    census_config = (
        config["census"]
        ["acs5_profile_2024"]
    )

    df = load_raw_data()

    print("Raw ZCTAs:", len(df))

    df = clean_census_data(
        df,
        variable_map=census_config["variables"],
        geography=census_config["geography"],
    )

    print("Cleaned ZCTAs:", len(df))

    print("\nMissing values:")
    print(
        df[
            census_config["variables"].keys()
        ].isna().sum()
    )

    save_clean_data(df)


if __name__ == "__main__":
    main()