from pathlib import Path
import re

import pandas as pd
from rapidfuzz import fuzz, utils


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MRF_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf_manifest_raw.csv"
)

HOSPITAL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospital_features_ca.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_match_candidates.csv"
)


def normalize(value):
    """Normalize facility names for comparison."""

    if pd.isna(value):
        return ""

    value = str(value).upper()
    value = value.replace("&", " AND ")
    value = re.sub(r"[^A-Z0-9 ]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def similarity(a, b):
    """Fuzzy string similarity from 0 to 100."""

    return fuzz.WRatio(
        str(a),
        str(b),
        processor=utils.default_process,
    )


def strip_common_words(name):
    """
    Remove generic Kaiser/hospital terminology so that
    geographic terms have more influence in matching.
    """

    value = normalize(name)

    remove_words = [
        "KAISER",
        "FOUNDATION",
        "HOSPITAL",
        "MEDICAL",
        "CENTER",
    ]

    words = [
        word
        for word in value.split()
        if word not in remove_words
    ]

    return " ".join(words)


def main():

    print("Generating Kaiser MRF match candidates...\n")

    mrf = pd.read_csv(MRF_PATH)

    hospitals = pd.read_parquet(HOSPITAL_PATH)

    kaiser = hospitals[
        hospitals["analysis_eligible"]
        & (
            hospitals["facility_name"].str.contains(
                "Kaiser",
                case=False,
                na=False,
            )
            |
            hospitals["hcai_facility_name"].str.contains(
                "Kaiser",
                case=False,
                na=False,
            )
        )
    ].copy()

    # Build comparison versions of names.
    mrf["location_match_name"] = (
        mrf["location_name"]
        .apply(strip_common_words)
    )

    kaiser["cms_match_name"] = (
        kaiser["facility_name"]
        .apply(strip_common_words)
    )

    kaiser["hcai_match_name"] = (
        kaiser["hcai_facility_name"]
        .apply(strip_common_words)
    )

    rows = []

    for _, mrf_row in mrf.iterrows():

        for _, hospital_row in kaiser.iterrows():

            cms_score = similarity(
                mrf_row["location_match_name"],
                hospital_row["cms_match_name"],
            )

            hcai_score = similarity(
                mrf_row["location_match_name"],
                hospital_row["hcai_match_name"],
            )

            # Use whichever hospital naming system
            # best matches the MRF location.
            name_score = max(
                cms_score,
                hcai_score,
            )

            rows.append(
                {
                    "location_name":
                        mrf_row["location_name"],

                    "mrf_url":
                        mrf_row["mrf_url"],

                    "facility_id":
                        hospital_row["facility_id"],

                    "cms_name":
                        hospital_row["facility_name"],

                    "hcai_name":
                        hospital_row["hcai_facility_name"],

                    "city":
                        hospital_row["city"],

                    "location_match_name":
                        mrf_row["location_match_name"],

                    "hospital_match_name":
                        hospital_row["hcai_match_name"],

                    "name_score":
                        round(name_score, 1),
                }
            )

    candidates = pd.DataFrame(rows)

    candidates = (
        candidates
        .sort_values(
            ["location_name", "name_score"],
            ascending=[True, False],
        )
    )

    candidates["rank"] = (
        candidates
        .groupby("location_name")
        .cumcount()
        + 1
    )

    # Keep top 3 CMS candidates for each MRF.
    candidates = candidates[
        candidates["rank"] <= 3
    ].copy()

    candidates.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("MRF locations:", mrf["location_name"].nunique())
    print("Kaiser CMS hospitals:", len(kaiser))
    print("Candidate rows:", len(candidates))

    print("\nSaved candidates to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()