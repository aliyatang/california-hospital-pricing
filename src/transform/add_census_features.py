from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

HOSPITAL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospital_master_ca.parquet"
)

ZCTA_CROSSWALK_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "hospital_zcta_crosswalk.parquet"
)

CENSUS_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "acs5_2024_zcta.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospital_features_ca.parquet"
)


CENSUS_COLUMNS = [
    "zcta",
    "zcta_name",
    "population",
    "median_household_income",
    "poverty_rate",
    "uninsured_rate",
    "unemployment_rate",
    "bachelors_or_higher_rate",
]


def load_data():
    """Load hospital, ZCTA crosswalk, and Census tables."""

    hospitals = pd.read_parquet(HOSPITAL_PATH)
    crosswalk = pd.read_parquet(ZCTA_CROSSWALK_PATH)
    census = pd.read_parquet(CENSUS_PATH)

    return hospitals, crosswalk, census


def prepare_census(census):
    """Select and rename Census socioeconomic variables."""

    census = census[CENSUS_COLUMNS].copy()

    census = census.rename(
        columns={
            "zcta": "census_zcta",
            "zcta_name": "census_zcta_name",
            "population": "zcta_population",
            "median_household_income": "zcta_median_household_income",
            "poverty_rate": "zcta_poverty_rate",
            "uninsured_rate": "zcta_uninsured_rate",
            "unemployment_rate": "zcta_unemployment_rate",
            "bachelors_or_higher_rate": "zcta_bachelors_or_higher_rate",
        }
    )

    return census


def add_census_features(hospitals, crosswalk, census):
    """Join hospitals to their resolved Census ZCTA and ACS features."""

    crosswalk = crosswalk[
        [
            "facility_id",
            "hospital_zip",
            "census_zcta",
            "zcta_match_method",
        ]
    ].copy()

    # Add the resolved Census geography to each hospital.
    enriched = hospitals.merge(
        crosswalk,
        on="facility_id",
        how="left",
        validate="one_to_one",
    )

    # Add socioeconomic characteristics for that ZCTA.
    enriched = enriched.merge(
        census,
        on="census_zcta",
        how="left",
        validate="many_to_one",
        indicator="_acs_merge",
    )

    enriched["census_acs_matched"] = (
        enriched["_acs_merge"] == "both"
    )

    enriched = enriched.drop(
        columns="_acs_merge"
    )

    return enriched


def validate_join(df):
    """Report Census coverage for the main analysis cohort."""

    eligible = df[
        df["analysis_eligible"]
    ].copy()

    print("Analysis cohort:", len(eligible))

    print(
        "Resolved Census ZCTA:",
        eligible["census_zcta"].notna().sum(),
    )

    print(
        "Matched to ACS record:",
        eligible["census_acs_matched"].sum(),
    )

    print(
        "Unresolved:",
        eligible["census_zcta"].isna().sum(),
    )

    print("\nZCTA match methods:")

    print(
        eligible["zcta_match_method"]
        .value_counts(dropna=False)
    )

    socioeconomic_columns = [
        "zcta_population",
        "zcta_median_household_income",
        "zcta_poverty_rate",
        "zcta_uninsured_rate",
        "zcta_unemployment_rate",
        "zcta_bachelors_or_higher_rate",
    ]

    print("\nMissing socioeconomic values:")

    print(
        eligible[
            socioeconomic_columns
        ].isna().sum()
    )


def save_data(df):
    """Save hospital-level feature table."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\nSaved hospital feature table to:")
    print(OUTPUT_PATH)


def main():

    print("Adding Census socioeconomic features...\n")

    hospitals, crosswalk, census = load_data()

    census = prepare_census(census)

    enriched = add_census_features(
        hospitals,
        crosswalk,
        census,
    )

    validate_join(enriched)

    save_data(enriched)


if __name__ == "__main__":
    main()