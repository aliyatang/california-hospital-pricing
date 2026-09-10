from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hcai"
    / "facility_profile_attributes.json"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "interim"

OUTPUT_PATH = (
    OUTPUT_DIR
    / "hcai_hospitals_ca.parquet"
)


KEEP_COLUMNS = [
    "oshpd_id",
    "facility_desc",
    "site_address1",
    "site_city",
    "site_zip",
    "site_x_coordinate",
    "site_y_coordinate",
    "license_type_desc",
    "license_category_desc",
    "facility_level_desc",
    "er_service_level_desc",
    "licensed_beds",
    "facility_status_desc",
]


def load_raw_data():
    """Load raw HCAI facility records."""
    return pd.read_json(
        INPUT_PATH,
        dtype=False,
    )


def clean_hospitals(df):
    """Create a clean HCAI hospital facility table."""

    # Keep hospital records only
    df = df[
        df["license_type_desc"] == "Hospital"
    ].copy()

    # Keep only columns relevant to hospital identification
    # and matching for now.
    df = df[KEEP_COLUMNS].copy()

    # Use consistent project-wide names
    df = df.rename(
        columns={
            "oshpd_id": "hcai_id",
            "facility_desc": "facility_name",
            "site_address1": "address",
            "site_city": "city",
            "site_zip": "zip_code",
            "site_x_coordinate": "longitude",
            "site_y_coordinate": "latitude",
            "license_type_desc": "license_type",
            "license_category_desc": "license_category",
            "facility_level_desc": "facility_level",
            "er_service_level_desc": "er_service_level",
            "facility_status_desc": "facility_status",
        }
    )

    # Clean strings
    string_columns = [
        "hcai_id",
        "facility_name",
        "address",
        "city",
        "zip_code",
        "license_type",
        "license_category",
        "facility_level",
        "er_service_level",
        "facility_status",
    ]

    for column in string_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Identifiers are labels, not quantities
    df["hcai_id"] = df["hcai_id"].str.zfill(9)
    df["zip_code"] = df["zip_code"].str[:5].str.zfill(5)

    # Convert numerical attributes
    numeric_columns = [
        "longitude",
        "latitude",
        "licensed_beds",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # Identify records that are appropriate candidates
    # for matching to the CMS hospital population.
    df["match_candidate"] = (
        (df["license_category"] == "General Acute Care Hospital")
        & (df["facility_status"] == "Open")
        & (
            df["facility_level"].isin(
                [
                    "Parent Facility",
                    "Consolidated Facility",
                ]
            )
        )
    )

    # HCAI ID should uniquely identify facility records
    if not df["hcai_id"].is_unique:
        raise ValueError("Duplicate HCAI IDs detected.")

    return df


def save_clean_data(df):
    """Save cleaned HCAI hospital table."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(f"Saved {len(df)} HCAI hospitals to:")
    print(OUTPUT_PATH)


def main():

    print("Loading HCAI facility data...")

    df = load_raw_data()

    print(f"Raw HCAI facilities: {len(df)}")

    df = clean_hospitals(df)

    print(f"HCAI hospitals: {len(df)}")
    print(
        "Matching candidates:",
        df["match_candidate"].sum(),
    )

    save_clean_data(df)


if __name__ == "__main__":
    main()