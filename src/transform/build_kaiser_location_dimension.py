from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CROSSWALK_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_hcai_crosswalk.parquet"
)

HCAI_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "hcai_hospitals_ca.parquet"
)

ACS_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "acs5_2024_zcta.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_location_dimension.parquet"
)


def clean_id(value):
    if pd.isna(value):
        return None

    return str(value).strip()


def clean_zip(value):
    if pd.isna(value):
        return None

    value = str(value)

    digits = "".join(
        char for char in value
        if char.isdigit()
    )

    if len(digits) < 5:
        return None

    return digits[:5]


def main():

    print(
        "Building Kaiser location dimension...\n"
    )

    crosswalk = pd.read_parquet(
        CROSSWALK_PATH
    )

    hcai = pd.read_parquet(
        HCAI_PATH
    )

    acs = pd.read_parquet(
        ACS_PATH
    )

    # --------------------------------------------------
    # 1. Standardize IDs
    # --------------------------------------------------

    crosswalk["facility_id"] = (
        crosswalk["facility_id"]
        .astype(str)
        .str.zfill(6)
    )

    crosswalk["hcai_id"] = (
        crosswalk["hcai_id"]
        .apply(clean_id)
    )

    hcai["hcai_id"] = (
        hcai["hcai_id"]
        .apply(clean_id)
    )

    # --------------------------------------------------
    # 2. Select physical HCAI attributes
    # --------------------------------------------------

    hcai_features = (
        hcai[
            [
                "hcai_id",
                "facility_name",
                "address",
                "city",
                "zip_code",
                "longitude",
                "latitude",
                "license_type",
                "license_category",
                "facility_level",
                "er_service_level",
                "licensed_beds",
                "facility_status",
            ]
        ]
        .rename(
            columns={
                "facility_name":
                    "hcai_facility_name_dim",

                "address":
                    "hcai_address_dim",

                "city":
                    "hcai_city",

                "zip_code":
                    "hcai_zip",
            }
        )
        .copy()
    )

    hcai_features["hcai_zip"] = (
        hcai_features[
            "hcai_zip"
        ]
        .apply(clean_zip)
    )

    # --------------------------------------------------
    # 3. Join MRF campus → HCAI facility
    # --------------------------------------------------

    locations = crosswalk.merge(
        hcai_features,
        on="hcai_id",
        how="left",
        validate="many_to_one",
    )

    print(
        "MRF locations:",
        len(locations),
    )

    missing_hcai = (
        locations[
            "latitude"
        ]
        .isna()
        .sum()
    )

    print(
        "Locations missing HCAI coordinates:",
        missing_hcai,
    )

    # --------------------------------------------------
    # 4. Use physical facility ZIP as campus ZCTA
    # --------------------------------------------------

    locations["zcta"] = (
        locations[
            "hcai_zip"
        ]
        .apply(clean_zip)
    )

    acs["zcta"] = (
        acs["zcta"]
        .apply(clean_zip)
    )

    # Ensure ACS is unique by ZCTA.
    duplicate_zctas = (
        acs["zcta"]
        .duplicated()
        .sum()
    )

    if duplicate_zctas:
        raise RuntimeError(
            "ACS table contains duplicate ZCTAs."
        )

    # --------------------------------------------------
    # 5. Attach ACS socioeconomic features
    # --------------------------------------------------

    locations = locations.merge(
        acs,
        on="zcta",
        how="left",
        validate="many_to_one",
    )

    # --------------------------------------------------
    # 6. Validation
    # --------------------------------------------------

    if len(locations) != 37:

        raise RuntimeError(
            f"Expected 37 Kaiser locations, "
            f"found {len(locations)}."
        )

    duplicate_keys = (
        locations
        .duplicated(
            subset=[
                "facility_id",
                "mrf_location_name",
            ]
        )
        .sum()
    )

    print(
        "Duplicate campus keys:",
        duplicate_keys,
    )

    missing_acs = (
        locations[
            "population"
        ]
        .isna()
        .sum()
    )

    print(
        "Locations missing ACS record:",
        missing_acs,
    )

    # --------------------------------------------------
    # 7. Select final dimension columns
    # --------------------------------------------------

    final_columns = [
        "facility_id",
        "mrf_location_name",
        "mrf_hospital_name",
        "mrf_address",
        "mrf_license_number",
        "mrf_type_2_npi",

        "hcai_id",
        "hcai_facility_name_dim",
        "hcai_address_dim",
        "hcai_city",
        "hcai_zip",

        "longitude",
        "latitude",

        "license_type",
        "license_category",
        "facility_level",
        "er_service_level",
        "licensed_beds",
        "facility_status",

        "match_method",
        "address_score",
        "name_score",
        "combined_score",

        "zcta",

        "population",
        "median_household_income",
        "poverty_rate",
        "uninsured_rate",
        "unemployment_rate",
        "bachelors_or_higher_rate",
    ]

    dimension = locations[
        final_columns
    ].copy()

    # --------------------------------------------------
    # 8. Show fuzzy matches for final audit
    # --------------------------------------------------

    print(
        "\n=== FUZZY MATCH AUDIT ==="
    )

    fuzzy = dimension[
        dimension[
            "match_method"
        ].str.startswith(
            "fuzzy",
            na=False,
        )
    ]

    print(
        fuzzy[
            [
                "facility_id",
                "mrf_location_name",
                "hcai_facility_name_dim",
                "hcai_address_dim",
                "match_method",
                "address_score",
                "name_score",
                "combined_score",
            ]
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # 9. Campus examples where one CMS ID has >1 MRF
    # --------------------------------------------------

    campus_counts = (
        dimension
        .groupby(
            "facility_id"
        )
        .size()
    )

    shared_ids = (
        campus_counts[
            campus_counts > 1
        ]
        .index
    )

    print(
        "\n=== MULTI-CAMPUS CMS IDs ==="
    )

    print(
        dimension[
            dimension[
                "facility_id"
            ].isin(shared_ids)
        ][
            [
                "facility_id",
                "mrf_location_name",
                "hcai_city",
                "hcai_zip",
                "latitude",
                "longitude",
                "zcta",
            ]
        ]
        .sort_values(
            [
                "facility_id",
                "mrf_location_name",
            ]
        )
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # 10. Save
    # --------------------------------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dimension.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\nSaved location dimension:"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()