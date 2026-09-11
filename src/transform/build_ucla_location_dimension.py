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
    / "ucla_location_dimension.parquet"
)

UCLA_FACILITIES = {
    "050112": "UCLA Santa Monica Medical Center",
    "050262": "Ronald Reagan UCLA Medical Center",
    "050481": "UCLA West Valley Medical Center",
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

    ucla = (
        df[
            df["facility_id"].isin(
                UCLA_FACILITIES
            )
        ]
        .copy()
    )

    ucla.insert(
        0,
        "system_name",
        "UCLA Health",
    )

    found = set(
        ucla["facility_id"]
    )

    expected = set(
        UCLA_FACILITIES
    )

    print(
        "\n=== UCLA LOCATION DIMENSION ==="
    )

    print(
        "Rows:",
        len(ucla),
    )

    print(
        "Facility IDs:",
        sorted(found),
    )

    print(
        "Columns:",
        len(ucla.columns),
    )

    if found != expected:
        raise RuntimeError(
            f"Expected {sorted(expected)}, "
            f"found {sorted(found)}"
        )

    if len(ucla) != 3:
        raise RuntimeError(
            "Expected exactly 3 UCLA facilities."
        )

    print(
        "\n=== FACILITIES ==="
    )

    print(
        ucla[
            [
                "facility_id",
                "facility_name",
            ]
        ].to_string(
            index=False
        )
    )

    ucla.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\nSaved:"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()