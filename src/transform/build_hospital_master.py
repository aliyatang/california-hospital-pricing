from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CROSSWALK_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cms_hcai_crosswalk.parquet"
)

HCAI_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "hcai_hospitals_ca.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospital_master_ca.parquet"
)


def load_data():
    """Load CMS-HCAI crosswalk and cleaned HCAI hospitals."""

    crosswalk = pd.read_parquet(CROSSWALK_PATH)
    hcai = pd.read_parquet(HCAI_PATH)

    return crosswalk, hcai


def prepare_hcai(hcai):
    """Select and rename HCAI attributes for the master table."""

    hcai = hcai[
        [
            "hcai_id",
            "facility_name",
            "address",
            "city",
            "zip_code",
            "longitude",
            "latitude",
            "license_category",
            "facility_level",
            "er_service_level",
            "licensed_beds",
            "facility_status",
        ]
    ].copy()

    hcai = hcai.rename(
        columns={
            "facility_name": "hcai_facility_name",
            "address": "hcai_address",
            "city": "hcai_city",
            "zip_code": "hcai_zip_code",
        }
    )

    return hcai


def build_master(crosswalk, hcai):
    """Join CMS hospitals to HCAI attributes."""

    master = crosswalk.merge(
        hcai,
        on="hcai_id",
        how="left",
        validate="many_to_one",
    )

    # valid HCAI ID doesn't necessarily mean that the facility
    # appears in curent Facility Profile Attributes extract
    master["hcai_profile_available"] = (
        master["hcai_facility_name"].notna()
    )

    return master


def validate_master(master):
    """Run basic integrity checks on the merged hospital table."""

    if not master["facility_id"].is_unique:
        raise ValueError(
            "CMS facility IDs are no longer unique after the join."
        )

    eligible = master[
        master["analysis_eligible"]
    ]

    missing_hcai = eligible[
        eligible["hcai_id"].isna()
    ]

    print("Total CMS hospitals:", len(master))
    print("Analysis cohort:", len(eligible))
    print("Matched to HCAI:", eligible["hcai_id"].notna().sum())
    print("Missing HCAI IDs:", len(missing_hcai))

    missing_attributes = eligible[
        eligible["hcai_facility_name"].isna()
    ]

    print(
        "Matched IDs missing current HCAI attributes:",
        len(missing_attributes),
    )

    if len(missing_attributes) > 0:
        print("\nHospitals missing HCAI attributes:")
        print(
            missing_attributes[
                [
                    "facility_id",
                    "facility_name",
                    "hcai_id",
                    "match_method",
                ]
            ].to_string(index=False)
        )


def save_master(master):
    """Save the unified hospital master table."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    master.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\nSaved hospital master table to:")
    print(OUTPUT_PATH)


def main():

    print("Building California hospital master table...\n")

    crosswalk, hcai = load_data()

    hcai = prepare_hcai(hcai)

    master = build_master(
        crosswalk,
        hcai,
    )

    validate_master(master)

    save_master(master)


if __name__ == "__main__":
    main()