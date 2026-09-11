from pathlib import Path
import re

import pandas as pd
from rapidfuzz import fuzz


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MRF_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_location_metadata.parquet"
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
    / "kaiser_mrf_hcai_crosswalk.parquet"
)

REVIEW_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "kaiser_mrf_hcai_review.csv"
)


STREET_REPLACEMENTS = {
    "STREET": "ST",
    "ST": "ST",
    "AVENUE": "AVE",
    "AVE": "AVE",
    "BOULEVARD": "BLVD",
    "BLVD": "BLVD",
    "ROAD": "RD",
    "RD": "RD",
    "DRIVE": "DR",
    "DR": "DR",
    "PARKWAY": "PKWY",
    "PKWY": "PKWY",
    "HIGHWAY": "HWY",
    "HWY": "HWY",
    "LANE": "LN",
    "LN": "LN",
    "COURT": "CT",
    "CT": "CT",
    "PLACE": "PL",
    "PL": "PL",
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
}


def clean_string(value):
    if pd.isna(value):
        return ""

    value = str(value).upper().strip()

    value = re.sub(
        r"[^A-Z0-9]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def normalize_street(value):
    text = clean_string(value)

    tokens = text.split()

    tokens = [
        STREET_REPLACEMENTS.get(
            token,
            token,
        )
        for token in tokens
    ]

    return " ".join(tokens)


def normalize_name(value):
    text = clean_string(value)

    # Remove generic Kaiser wording so the location
    # itself has more influence on fuzzy matching.
    generic_phrases = [
        "KAISER FOUNDATION HOSPITAL",
        "KAISER PERMANENTE",
        "MEDICAL CENTER",
        "MED CENTER",
        "HOSPITAL",
        "CAMPUS",
    ]

    for phrase in generic_phrases:
        text = text.replace(
            phrase,
            " ",
        )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def parse_mrf_address(value):
    """
    Example:
    4501 SAND CREEK ROAD, ANTIOCH, CA 94531
    """

    if pd.isna(value):
        return "", "", ""

    text = str(value).strip().strip('"')

    parts = [
        part.strip()
        for part in text.split(",")
    ]

    street = (
        parts[0]
        if len(parts) >= 1
        else ""
    )

    city = (
        parts[-2]
        if len(parts) >= 3
        else ""
    )

    zip_match = re.search(
        r"\b(\d{5})(?:-\d{4})?\b",
        text,
    )

    zip_code = (
        zip_match.group(1)
        if zip_match
        else ""
    )

    return (
        street,
        city,
        zip_code,
    )


def main():

    mrf = pd.read_parquet(
        MRF_PATH
    )

    hcai = pd.read_parquet(
        HCAI_PATH
    )

    # --------------------------------------------------
    # HCAI matching universe
    # --------------------------------------------------

    hcai = hcai[
        hcai["match_candidate"]
        .fillna(False)
    ].copy()

    hcai = hcai[
        hcai["facility_name"]
        .astype(str)
        .str.contains(
            "KAISER",
            case=False,
            na=False,
        )
    ].copy()

    hcai["hcai_id"] = (
        hcai["hcai_id"]
        .astype(str)
    )

    hcai["zip_code"] = (
        hcai["zip_code"]
        .astype(str)
        .str.extract(
            r"(\d{5})",
            expand=False,
        )
    )

    hcai["address_norm"] = (
        hcai["address"]
        .apply(normalize_street)
    )

    hcai["city_norm"] = (
        hcai["city"]
        .apply(clean_string)
    )

    hcai["name_norm"] = (
        hcai["facility_name"]
        .apply(normalize_name)
    )

    print(
        "Kaiser HCAI candidate facilities:",
        len(hcai),
    )

    # --------------------------------------------------
    # Parse MRF physical addresses
    # --------------------------------------------------

    parsed = (
        mrf[
            "mrf_meta__hospital_address"
        ]
        .apply(parse_mrf_address)
    )

    mrf[
        [
            "mrf_street",
            "mrf_city",
            "mrf_zip",
        ]
    ] = pd.DataFrame(
        parsed.tolist(),
        index=mrf.index,
    )

    mrf["street_norm"] = (
        mrf["mrf_street"]
        .apply(normalize_street)
    )

    mrf["city_norm"] = (
        mrf["mrf_city"]
        .apply(clean_string)
    )

    mrf["hospital_name_norm"] = (
        mrf[
            "mrf_meta__hospital_name"
        ]
        .apply(normalize_name)
    )

    mrf["location_name_norm"] = (
        mrf[
            "mrf_meta__location_name"
        ]
        .apply(normalize_name)
    )

    # --------------------------------------------------
    # Candidate matching
    # --------------------------------------------------

    candidate_rows = []
    crosswalk_rows = []

    for row in mrf.itertuples(
        index=False
    ):

        # First block by ZIP.
        candidates = hcai[
            hcai["zip_code"]
            == row.mrf_zip
        ].copy()

        block_method = "zip"

        # Fallback to city if necessary.
        if candidates.empty:

            candidates = hcai[
                hcai["city_norm"]
                == row.city_norm
            ].copy()

            block_method = "city"

        # Last-resort comparison to all Kaiser hospitals.
        if candidates.empty:

            candidates = hcai.copy()

            block_method = "all_kaiser"

        scored = []

        for candidate in candidates.itertuples(
            index=False
        ):

            address_score = fuzz.WRatio(
                row.street_norm,
                candidate.address_norm,
            )

            hospital_name_score = fuzz.WRatio(
                row.hospital_name_norm,
                candidate.name_norm,
            )

            location_name_score = fuzz.WRatio(
                row.location_name_norm,
                candidate.name_norm,
            )

            name_score = max(
                hospital_name_score,
                location_name_score,
            )

            combined_score = (
                0.75 * address_score
                + 0.25 * name_score
            )

            scored.append(
                {
                    "hcai_id":
                        candidate.hcai_id,

                    "hcai_facility_name":
                        candidate.facility_name,

                    "hcai_address":
                        candidate.address,

                    "hcai_city":
                        candidate.city,

                    "hcai_zip":
                        candidate.zip_code,

                    "address_score":
                        round(
                            address_score,
                            2,
                        ),

                    "name_score":
                        round(
                            name_score,
                            2,
                        ),

                    "combined_score":
                        round(
                            combined_score,
                            2,
                        ),
                }
            )

        scored = sorted(
            scored,
            key=lambda x: x[
                "combined_score"
            ],
            reverse=True,
        )

        best = scored[0]

        second_score = (
            scored[1]["combined_score"]
            if len(scored) > 1
            else None
        )

        score_gap = (
            best["combined_score"]
            - second_score
            if second_score is not None
            else None
        )

        # Exact normalized address + ZIP
        # is the strongest possible match.
        exact_address = (
            best["address_score"] == 100
            and block_method == "zip"
        )

        fuzzy_accept = (
            best["combined_score"] >= 85
            and best["address_score"] >= 80
            and best["name_score"] >= 55
            and (
                score_gap is None
                or score_gap >= 8
            )
        )

        if exact_address:

            status = "matched"
            match_method = (
                "exact_address_zip"
            )

        elif fuzzy_accept:

            status = "matched"
            match_method = (
                f"fuzzy_{block_method}"
            )

        else:

            status = "review"
            match_method = (
                f"review_{block_method}"
            )

        for rank, candidate in enumerate(
            scored[:3],
            start=1,
        ):

            candidate_rows.append(
                {
                    "facility_id":
                        str(
                            row.facility_id
                        ).zfill(6),

                    "mrf_location_name":
                        row.manifest_location_name,

                    "mrf_address":
                        row.mrf_meta__hospital_address,

                    "mrf_zip":
                        row.mrf_zip,

                    "candidate_rank":
                        rank,

                    **candidate,
                }
            )

        crosswalk_rows.append(
            {
                "facility_id":
                    str(
                        row.facility_id
                    ).zfill(6),

                "mrf_location_name":
                    row.manifest_location_name,

                "mrf_hospital_name":
                    row.mrf_meta__hospital_name,

                "mrf_address":
                    row.mrf_meta__hospital_address,

                "mrf_license_number":
                    row.mrf_meta__license_number_ca,

                "mrf_type_2_npi":
                    row.mrf_meta__type_2_npi,

                "mrf_zip":
                    row.mrf_zip,

                "hcai_id":
                    best["hcai_id"],

                "hcai_facility_name":
                    best[
                        "hcai_facility_name"
                    ],

                "hcai_address":
                    best["hcai_address"],

                "address_score":
                    best["address_score"],

                "name_score":
                    best["name_score"],

                "combined_score":
                    best["combined_score"],

                "score_gap":
                    (
                        round(
                            score_gap,
                            2,
                        )
                        if score_gap is not None
                        else None
                    ),

                "match_method":
                    match_method,

                "match_status":
                    status,
            }
        )

    # --------------------------------------------------
    # Save results
    # --------------------------------------------------

    crosswalk = pd.DataFrame(
        crosswalk_rows
    )

    candidates = pd.DataFrame(
        candidate_rows
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    crosswalk.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    candidates.to_csv(
        REVIEW_PATH,
        index=False,
    )

    print(
        "\n=== MATCH SUMMARY ==="
    )

    print(
        crosswalk[
            "match_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\n=== MATCH METHODS ==="
    )

    print(
        crosswalk[
            "match_method"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\n=== NEEDS REVIEW ==="
    )

    review = crosswalk[
        crosswalk[
            "match_status"
        ] == "review"
    ]

    if review.empty:

        print(
            "No locations require review."
        )

    else:

        print(
            review[
                [
                    "facility_id",
                    "mrf_location_name",
                    "mrf_address",
                    "hcai_facility_name",
                    "hcai_address",
                    "address_score",
                    "name_score",
                    "combined_score",
                    "score_gap",
                ]
            ].to_string(
                index=False
            )
        )

    print(
        "\nSaved crosswalk:"
    )
    print(OUTPUT_PATH)

    print(
        "\nSaved top-3 candidates:"
    )
    print(REVIEW_PATH)


if __name__ == "__main__":
    main()