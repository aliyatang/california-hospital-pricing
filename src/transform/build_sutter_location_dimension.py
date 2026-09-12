from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospital_features_ca.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "sutter_location_dimension.parquet"
)


EXPECTED_FACILITY_IDS = {
    "050108",
    "050291",
    "050309",
}


def main():

    df = pd.read_parquet(
        INPUT_PATH
    )

    df["facility_id"] = (
        df["facility_id"]
        .astype(str)
        .str.zfill(6)
    )

    sutter = (
        df[
            df["facility_id"]
            .isin(
                EXPECTED_FACILITY_IDS
            )
        ]
        .copy()
    )

    found_ids = set(
        sutter[
            "facility_id"
        ].unique()
    )

    if found_ids != EXPECTED_FACILITY_IDS:
        raise RuntimeError(
            "Unexpected Sutter facility IDs.\n"
            f"Expected: "
            f"{sorted(EXPECTED_FACILITY_IDS)}\n"
            f"Found: "
            f"{sorted(found_ids)}"
        )

    if len(sutter) != 3:
        raise RuntimeError(
            f"Expected 3 Sutter hospitals, "
            f"found {len(sutter)}."
        )

    if (
        ~sutter[
            "analysis_eligible"
        ].fillna(False)
    ).any():
        raise RuntimeError(
            "Found Sutter hospital that is "
            "not analysis eligible."
        )

    if (
        sutter[
            "hcai_id"
        ]
        .isna()
        .any()
    ):
        raise RuntimeError(
            "Missing HCAI match."
        )

    if (
        sutter[
            "census_zcta"
        ]
        .isna()
        .any()
    ):
        raise RuntimeError(
            "Missing Census ZCTA match."
        )

    if (
        sutter[
            [
                "latitude",
                "longitude",
            ]
        ]
        .isna()
        .any()
        .any()
    ):
        raise RuntimeError(
            "Missing coordinates."
        )

    sutter.insert(
        0,
        "system_name",
        "Sutter Health",
    )

    sutter = (
        sutter
        .sort_values(
            "facility_id"
        )
        .reset_index(
            drop=True
        )
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sutter.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\n=== SUTTER LOCATION DIMENSION ==="
    )

    print(
        "Rows:",
        len(sutter),
    )

    print(
        "Facility IDs:",
        sutter[
            "facility_id"
        ].tolist(),
    )

    print(
        "Columns:",
        len(sutter.columns),
    )

    print(
        "\n=== FACILITIES ==="
    )

    print(
        sutter[
            [
                "facility_id",
                "facility_name",
                "city",
                "census_zcta",
                "hcai_id",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print(
        "\nSaved:"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()