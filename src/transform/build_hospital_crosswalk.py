from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MATCH_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cms_hcai_matches.parquet"
)

CANDIDATE_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cms_hcai_match_candidates.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cms_hcai_crosswalk.parquet"
)

REVIEW_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cms_hcai_manual_review.csv"
)

MANUAL_MATCH_PATH = (
    PROJECT_ROOT
    / "config"
    / "manual_hospital_matches.csv"
)

def load_candidates():
    """Load fuzzy-match candidates while preserving identifiers."""

    return pd.read_csv(
        CANDIDATE_PATH,
        dtype={
            "cms_id": "string",
            "hcai_id": "string",
            "cms_zip": "string",
            "hcai_zip": "string",
        },
    )


def summarize_candidates(candidates):
    """
    Get the best and second-best HCAI candidate
    for each CMS hospital.
    """

    candidates = candidates.sort_values(
        ["cms_id", "combined_score"],
        ascending=[True, False],
    ).copy()

    candidates["rank"] = (
        candidates
        .groupby("cms_id")
        .cumcount()
        + 1
    )

    top1 = (
        candidates[candidates["rank"] == 1]
        .copy()
    )

    second_scores = (
        candidates[candidates["rank"] == 2]
        [["cms_id", "combined_score"]]
        .rename(
            columns={
                "combined_score": "second_score"
            }
        )
    )

    top1 = top1.merge(
        second_scores,
        on="cms_id",
        how="left",
    )

    top1["score_gap"] = (
        top1["combined_score"]
        - top1["second_score"]
    )

    return top1


def classify_candidates(top):
    """Classify fuzzy candidates by matching confidence."""

    top = top.copy()

    strong_scores = (
        (top["combined_score"] >= 85)
        & (top["name_score"] >= 80)
        & (top["address_score"] >= 80)
    )

    clear_winner = (
        top["second_score"].isna()
        | (top["score_gap"] >= 10)
    )

    top["auto_accept"] = (
        strong_scores
        & clear_winner
    )

    return top


def build_crosswalk(matches, fuzzy):
    """Add high-confidence fuzzy matches to exact matches."""

    crosswalk = matches.copy()

    accepted = fuzzy[
        fuzzy["auto_accept"]
    ][
        [
            "cms_id",
            "hcai_id",
            "combined_score",
        ]
    ].rename(
        columns={
            "cms_id": "facility_id",
            "hcai_id": "fuzzy_hcai_id",
            "combined_score": "fuzzy_score",
        }
    )

    crosswalk = crosswalk.merge(
        accepted,
        on="facility_id",
        how="left",
    )

    use_fuzzy = (
        crosswalk["hcai_id"].isna()
        & crosswalk["fuzzy_hcai_id"].notna()
    )

    crosswalk.loc[
        use_fuzzy,
        "hcai_id"
    ] = crosswalk.loc[
        use_fuzzy,
        "fuzzy_hcai_id"
    ]

    crosswalk.loc[
        use_fuzzy,
        "match_method"
    ] = "high_confidence_fuzzy"

    crosswalk.loc[
        use_fuzzy,
        "match_score"
    ] = crosswalk.loc[
        use_fuzzy,
        "fuzzy_score"
    ]

    # Exact matches get a perfect deterministic match score
    crosswalk.loc[
        crosswalk["match_method"].isin(
            [
                "exact_name_zip",
                "exact_address_zip",
            ]
        ),
        "match_score",
    ] = 100.0

    crosswalk = crosswalk.drop(
        columns=[
            "fuzzy_hcai_id",
            "fuzzy_score",
        ]
    )

    return crosswalk

def apply_manual_matches(crosswalk):
    """Apply manually verified CMS-HCAI matches."""

    manual = pd.read_csv(
        MANUAL_MATCH_PATH,
        dtype={
            "cms_id": "string",
            "hcai_id": "string",
        },
    )

    manual = manual.rename(
        columns={
            "hcai_id": "manual_hcai_id",
            "reason": "manual_match_reason",
        }
    )

    crosswalk = crosswalk.merge(
        manual,
        left_on="facility_id",
        right_on="cms_id",
        how="left",
    )

    use_manual = (
        crosswalk["hcai_id"].isna()
        & crosswalk["manual_hcai_id"].notna()
    )

    crosswalk.loc[
        use_manual,
        "hcai_id"
    ] = crosswalk.loc[
        use_manual,
        "manual_hcai_id"
    ]

    crosswalk.loc[
        use_manual,
        "match_method"
    ] = "manual_verified"

    crosswalk = crosswalk.drop(
        columns=[
            "cms_id",
            "manual_hcai_id",
        ]
    )

    return crosswalk

def main():

    print("Loading match data...")

    matches = pd.read_parquet(MATCH_PATH)

    candidates = load_candidates()

    fuzzy = summarize_candidates(candidates)

    fuzzy = classify_candidates(fuzzy)

    print(
        "High-confidence fuzzy matches:",
        fuzzy["auto_accept"].sum(),
    )

    print(
        "Manual-review candidates:",
        (~fuzzy["auto_accept"]).sum(),
    )

    crosswalk = build_crosswalk(
        matches,
        fuzzy,
    )

    crosswalk = apply_manual_matches(crosswalk)

    eligible = crosswalk[
        crosswalk["analysis_eligible"]
    ]

    matched = (
        eligible["hcai_id"]
        .notna()
        .sum()
    )

    print("\nAnalysis cohort:", len(eligible))
    print("Matched:", matched)
    print("Unmatched:", len(eligible) - matched)

    print("\nMatch methods:")
    print(
        eligible["match_method"]
        .value_counts(dropna=False)
    )

    crosswalk.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    # Anything not auto accepted goes file for manual review
    review = fuzzy[
        ~fuzzy["auto_accept"]
    ].copy()

    review.to_csv(
        REVIEW_PATH,
        index=False,
    )

    print("\nSaved crosswalk to:")
    print(OUTPUT_PATH)

    print("\nSaved manual-review cases to:")
    print(REVIEW_PATH)


if __name__ == "__main__":
    main()