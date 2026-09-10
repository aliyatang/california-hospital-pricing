from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, utils


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MATCH_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cms_hcai_matches.parquet"
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
    / "interim"
    / "cms_hcai_match_candidates.csv"
)


def similarity(a, b):
    """Return case- and punctuation-insensitive similarity from 0 to 100."""

    if pd.isna(a) or pd.isna(b):
        return 0

    return fuzz.WRatio(
        str(a),
        str(b),
        processor=utils.default_process,
    )


def generate_candidates(cms, hcai):
    """Generate likely HCAI matches for unmatched CMS hospitals."""

    rows = []

    for _, cms_row in cms.iterrows():

        # First block candidates to the same ZIP.
        candidates = hcai[
            hcai["zip_code"] == cms_row["zip_code"]
        ].copy()

        candidate_source = "same_zip"

        # If ZIP finds nothing, fall back to same city.
        if candidates.empty:
            candidates = hcai[
                hcai["city"].str.upper()
                == str(cms_row["city"]).upper()
            ].copy()

            candidate_source = "same_city"

        # No reasonable geographic candidates
        if candidates.empty:
            continue

        for _, hcai_row in candidates.iterrows():

            name_score = similarity(
                cms_row["facility_name"],
                hcai_row["facility_name"],
            )

            address_score = similarity(
                cms_row["address"],
                hcai_row["address"],
            )

            # Name matters more than address.
            combined_score = (
                0.70 * name_score
                + 0.30 * address_score
            )

            rows.append(
                {
                    "cms_id": cms_row["facility_id"],
                    "cms_name": cms_row["facility_name"],
                    "cms_address": cms_row["address"],
                    "cms_city": cms_row["city"],
                    "cms_zip": cms_row["zip_code"],

                    "hcai_id": hcai_row["hcai_id"],
                    "hcai_name": hcai_row["facility_name"],
                    "hcai_address": hcai_row["address"],
                    "hcai_city": hcai_row["city"],
                    "hcai_zip": hcai_row["zip_code"],

                    "candidate_source": candidate_source,
                    "name_score": round(name_score, 1),
                    "address_score": round(address_score, 1),
                    "combined_score": round(combined_score, 1),
                }
            )

    return pd.DataFrame(rows)


def keep_top_candidates(df, n=3):
    """Keep the top N HCAI candidates for each CMS hospital."""

    return (
        df.sort_values(
            ["cms_id", "combined_score"],
            ascending=[True, False],
        )
        .groupby("cms_id")
        .head(n)
        .reset_index(drop=True)
    )


def main():

    matches = pd.read_parquet(MATCH_PATH)
    hcai = pd.read_parquet(HCAI_PATH)

    # Only hospitals that matter for our primary analysis
    cms_unmatched = matches[
        matches["analysis_eligible"]
        & matches["hcai_id"].isna()
    ].copy()

    hcai_candidates = hcai[
        hcai["match_candidate"]
    ].copy()

    print(
        "Unmatched eligible CMS hospitals:",
        len(cms_unmatched),
    )

    candidates = generate_candidates(
        cms_unmatched,
        hcai_candidates,
    )

    candidates = keep_top_candidates(
        candidates,
        n=3,
    )

    candidates.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "CMS hospitals with candidates:",
        candidates["cms_id"].nunique(),
    )

    print(
        "Candidate rows saved:",
        len(candidates),
    )

    print("\nSaved to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()