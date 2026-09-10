from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MRF_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf_manifest_raw.csv"
)

CROSSWALK_PATH = (
    PROJECT_ROOT
    / "config"
    / "kaiser_mrf_crosswalk.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_manifest_ca.parquet"
)


def main():
    print("Building California Kaiser MRF manifest...\n")

    mrf = pd.read_csv(MRF_PATH)

    crosswalk = pd.read_csv(
        CROSSWALK_PATH,
        dtype={"facility_id": "string"},
    )

    # Every crosswalk location should be unique.
    if not crosswalk["location_name"].is_unique:
        raise ValueError(
            "Duplicate location names in Kaiser crosswalk."
        )

    merged = mrf.merge(
        crosswalk,
        on="location_name",
        how="left",
        validate="one_to_one",
    )

    missing_classification = merged["status"].isna()

    if missing_classification.any():
        print("Unclassified MRF locations:")
        print(
            merged.loc[
                missing_classification,
                "location_name"
            ].to_string(index=False)
        )

        raise ValueError(
            "Some Kaiser MRF locations are not in the crosswalk."
        )

    california = merged[
        merged["status"] == "include"
    ].copy()

    print("All Kaiser MRFs:", len(merged))
    print("California MRFs:", len(california))
    print(
        "Unique CMS hospitals:",
        california["facility_id"].nunique(),
    )

    print(
        "Missing MRF URLs:",
        california["mrf_url"].isna().sum(),
    )

    print("\nMRFs per CMS hospital:")
    print(
        california["facility_id"]
        .value_counts()
        .value_counts()
        .sort_index()
    )

    california.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\nSaved manifest to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()