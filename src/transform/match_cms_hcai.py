from pathlib import Path
import re

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CMS_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cms_hospitals_ca.parquet"
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
    / "cms_hcai_matches.parquet"
)


def normalize_text(value):
    """
    Normalize text for record matching.

    Example:
        "ST. ROSE HOSPITAL" -> "ST ROSE HOSPITAL"
    """

    if pd.isna(value):
        return pd.NA

    value = str(value).upper()

    # Replace ampersand consistently
    value = value.replace("&", " AND ")

    # Remove punctuation
    value = re.sub(r"[^A-Z0-9 ]", " ", value)

    # Collapse repeated whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def prepare_cms(df):
    """Create normalized CMS matching fields."""

    df = df.copy()

    df["name_normalized"] = (
        df["facility_name"]
        .apply(normalize_text)
    )

    df["address_normalized"] = (
        df["address"]
        .apply(normalize_text)
    )

    return df


def prepare_hcai(df):
    """Create normalized HCAI matching fields."""

    df = df[
        df["match_candidate"]
    ].copy()

    df["name_normalized"] = (
        df["facility_name"]
        .apply(normalize_text)
    )

    df["address_normalized"] = (
        df["address"]
        .apply(normalize_text)
    )

    return df


def unique_lookup(df, columns):
    """
    Keep only matching keys that uniquely identify
    one HCAI facility.
    """

    counts = (
        df.groupby(columns, dropna=False)
        .size()
        .reset_index(name="count")
    )

    unique_keys = counts[
        counts["count"] == 1
    ][columns]

    return df.merge(
        unique_keys,
        on=columns,
        how="inner",
    )


def match_exact_name_zip(cms, hcai):
    """Match hospitals using normalized name + ZIP."""

    unique_hcai = unique_lookup(
        hcai,
        ["name_normalized", "zip_code"],
    )

    lookup = unique_hcai[
        [
            "hcai_id",
            "name_normalized",
            "zip_code",
        ]
    ]

    matches = cms.merge(
        lookup,
        on=[
            "name_normalized",
            "zip_code",
        ],
        how="left",
    )

    matches["match_method"] = pd.NA

    matches.loc[
        matches["hcai_id"].notna(),
        "match_method"
    ] = "exact_name_zip"

    return matches


def match_exact_address_zip(matches, hcai):
    """
    For still-unmatched CMS hospitals,
    try exact normalized address + ZIP.
    """

    unique_hcai = unique_lookup(
        hcai,
        ["address_normalized", "zip_code"],
    )

    lookup = unique_hcai[
        [
            "hcai_id",
            "address_normalized",
            "zip_code",
        ]
    ].rename(
        columns={
            "hcai_id": "hcai_id_address"
        }
    )

    matches = matches.merge(
        lookup,
        on=[
            "address_normalized",
            "zip_code",
        ],
        how="left",
    )

    unmatched = matches["hcai_id"].isna()
    has_address_match = (
        matches["hcai_id_address"].notna()
    )

    use_address_match = (
        unmatched & has_address_match
    )

    matches.loc[
        use_address_match,
        "hcai_id"
    ] = matches.loc[
        use_address_match,
        "hcai_id_address"
    ]

    matches.loc[
        use_address_match,
        "match_method"
    ] = "exact_address_zip"

    matches = matches.drop(
        columns=["hcai_id_address"]
    )

    return matches


def main():

    print("Loading CMS and HCAI hospital tables...")

    cms = pd.read_parquet(CMS_PATH)
    hcai = pd.read_parquet(HCAI_PATH)

    print(f"CMS hospitals: {len(cms)}")
    print(
        "HCAI matching candidates:",
        hcai["match_candidate"].sum()
    )

    cms = prepare_cms(cms)
    hcai = prepare_hcai(hcai)

    matches = match_exact_name_zip(
        cms,
        hcai,
    )

    matches = match_exact_address_zip(
        matches,
        hcai,
    )

    matched = matches["hcai_id"].notna().sum()
    unmatched = matches["hcai_id"].isna().sum()

    print(f"\nMatched: {matched}")
    print(f"Unmatched: {unmatched}")

    print("\nMatch methods:")
    print(
        matches["match_method"]
        .value_counts(dropna=False)
    )

    matches.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\nSaved match table to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()