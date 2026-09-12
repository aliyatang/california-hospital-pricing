from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "sutter"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sutter_price_fact.parquet"
)

SUMMARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sutter_location_summary.parquet"
)


EXPECTED_FILES = [
    "sutter_medical_center_sacramento.parquet",
    "sutter_roseville_medical_center.parquet",
    "sutter_santa_rosa_regional_hospital.parquet",
]

EXPECTED_FACILITIES = {
    "050108",
    "050309",
    "050291",
}

EXPECTED_ROWS = 92_819


def main():

    frames = []

    for filename in EXPECTED_FILES:

        path = INPUT_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Missing normalized file: {path}"
            )

        df = pd.read_parquet(path)

        print(
            filename,
            f"{len(df):,}",
        )

        frames.append(df)

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    facility_ids = set(
        combined["facility_id"]
        .astype(str)
        .str.zfill(6)
        .unique()
    )

    duplicate_ids = (
        combined["source_record_id"]
        .duplicated()
        .sum()
    )

    if len(combined) != EXPECTED_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_ROWS:,} rows, "
            f"found {len(combined):,}."
        )

    if facility_ids != EXPECTED_FACILITIES:
        raise RuntimeError(
            f"Unexpected facility IDs: "
            f"{sorted(facility_ids)}"
        )

    if duplicate_ids != 0:
        raise RuntimeError(
            f"Found {duplicate_ids:,} duplicate "
            f"source_record_id values."
        )

    if (
        ~combined[
            "has_negotiated_price"
        ]
    ).sum() != 0:
        raise RuntimeError(
            "Found rows without negotiated prices."
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    summary = (
        combined
        .groupby(
            [
                "facility_id",
                "mrf_location_name",
            ],
            as_index=False,
        )
        .agg(
            row_count=(
                "source_record_id",
                "size",
            ),
            payer_count=(
                "payer",
                "nunique",
            ),
            plan_count=(
                "plan",
                "nunique",
            ),
            code_count=(
                "code_1",
                "nunique",
            ),
            dollar_rows=(
                "has_negotiated_dollar",
                "sum",
            ),
            percentage_rows=(
                "has_negotiated_percentage",
                "sum",
            ),
            algorithm_rows=(
                "has_negotiated_algorithm",
                "sum",
            ),
        )
    )

    summary.to_parquet(
        SUMMARY_PATH,
        index=False,
    )

    print(
        "\n=== SUTTER COMBINED FACT ==="
    )

    print(
        "Rows:",
        f"{len(combined):,}",
    )

    print(
        "Facilities:",
        combined[
            "facility_id"
        ].nunique(),
    )

    print(
        "Duplicate source IDs:",
        duplicate_ids,
    )

    print(
        "\nRepresentation:"
    )

    print(
        combined[
            "price_representation"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\n=== LOCATION SUMMARY ==="
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print(
        "\nSaved:"
    )

    print(OUTPUT_PATH)
    print(SUMMARY_PATH)


if __name__ == "__main__":
    main()