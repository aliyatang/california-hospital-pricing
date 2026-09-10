from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cms"
    / "hospital_general_information_ca.json"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "interim"
OUTPUT_PATH = OUTPUT_DIR / "cms_hospitals_ca.parquet"


KEEP_COLUMNS = [
    "facility_id",
    "facility_name",
    "address",
    "citytown",
    "state",
    "zip_code",
    "countyparish",
    "telephone_number",
    "hospital_type",
    "hospital_ownership",
    "emergency_services",
    "hospital_overall_rating",
]


def load_raw_data():
    """Load raw CMS hospital data."""
    return pd.read_json(INPUT_PATH, dtype=False)


def clean_hospitals(df):
    """Clean and standardize CMS hospital records."""
    df = df[KEEP_COLUMNS].copy()

    # Rename fields for consistency
    df = df.rename(
        columns={
            "citytown": "city",
            "countyparish": "county",
            "hospital_overall_rating": "overall_rating",
        }
    )

    # Remove leading/trailing whitespace
    string_columns = [
        "facility_id",
        "facility_name",
        "address",
        "city",
        "state",
        "zip_code",
        "county",
        "telephone_number",
        "hospital_type",
        "hospital_ownership",
        "emergency_services",
    ]

    for column in string_columns:
        df[column] = df[column].astype("string").str.strip()

    # Preserve identifiers as strings
    df["facility_id"] = df["facility_id"].str.zfill(6)
    df["zip_code"] = df["zip_code"].str.zfill(5)

    # Convert blank ratings to missing values, then numeric
    df["overall_rating"] = pd.to_numeric(
        df["overall_rating"],
        errors="coerce",
    )

    # Standardize text fields
    df["facility_name"] = df["facility_name"].str.title()
    df["city"] = df["city"].str.title()
    df["county"] = df["county"].str.title()

    # Remove exact duplicate hospitals if present
    df = df.drop_duplicates(subset=["facility_id"])

    main_hospital_types = [
        "Acute Care Hospitals",
        "Critical Access Hospitals",
    ]

    df["analysis_eligible"] = df["hospital_type"].isin(main_hospital_types)

    df["exclusion_reason"] = pd.NA

    df.loc[
        df["hospital_type"] == "Psychiatric",
        "exclusion_reason",
    ] = "Psychiatric hospital"

    df.loc[
        df["hospital_type"] == "Childrens",
        "exclusion_reason",
    ] = "Children's hospital"

    df.loc[
        df["hospital_type"] == "Acute Care - Veterans Administration",
        "exclusion_reason",
    ] = "Veterans Administration hospital"

    df.loc[
        df["hospital_type"] == "Acute Care - Department of Defense",
        "exclusion_reason",
    ] = "Department of Defense hospital"

    return df


def save_clean_data(df):
    """Save cleaned hospital master table."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(f"Saved {len(df)} cleaned hospitals to:")
    print(OUTPUT_PATH)


def main():
    print("Loading CMS hospital data...")

    df = load_raw_data()

    print(f"Raw hospitals: {len(df)}")

    df = clean_hospitals(df)

    print(f"Cleaned hospitals: {len(df)}")

    save_clean_data(df)


if __name__ == "__main__":
    main()