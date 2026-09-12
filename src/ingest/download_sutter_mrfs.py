from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "sutter_mrf_sources.csv"
)

CROSSWALK_PATH = (
    PROJECT_ROOT
    / "config"
    / "sutter_mrf_crosswalk.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "sutter"
)


def main():

    sources = pd.read_csv(
        CONFIG_PATH,
        dtype=str,
    )

    crosswalk = pd.read_csv(
        CROSSWALK_PATH,
        dtype=str,
    )

    df = sources.merge(
        crosswalk[
            [
                "mrf_location_name",
                "source_file",
            ]
        ],
        left_on="facility_name",
        right_on="mrf_location_name",
        how="left",
        validate="one_to_one",
    )

    if df["source_file"].isna().any():
        missing = df.loc[
            df["source_file"].isna(),
            "facility_name",
        ].tolist()

        raise RuntimeError(
            f"Missing crosswalk rows: {missing}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for _, row in df.iterrows():

        output_path = (
            OUTPUT_DIR
            / row["source_file"]
        )

        if output_path.exists():
            print(
                "Already exists:",
                output_path.name,
            )
            continue

        print(
            "\nDownloading:",
            row["facility_name"],
        )

        response = requests.get(
            row["mrf_url"],
            timeout=180,
        )

        response.raise_for_status()

        output_path.write_bytes(
            response.content
        )

        print(
            "Saved:",
            output_path,
        )

        print(
            "Bytes:",
            f"{len(response.content):,}",
        )


if __name__ == "__main__":
    main()