from pathlib import Path
import time

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOCATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_location_dimension.parquet"
)

ACS_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "acs5_2024_zcta.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "kaiser_location_dimension.parquet"
)

TIGERWEB_URL = (
    "https://tigerweb.geo.census.gov/"
    "arcgis/rest/services/TIGERweb/"
    "tigerWMS_ACS2024/MapServer/2/query"
)


def get_zcta(latitude, longitude):

    params = {
        "geometry":
            f"{longitude},{latitude}",

        "geometryType":
            "esriGeometryPoint",

        "inSR":
            "4326",

        "spatialRel":
            "esriSpatialRelIntersects",

        "outFields":
            "ZCTA5",

        "returnGeometry":
            "false",

        "f":
            "json",
    }

    response = requests.get(
        TIGERWEB_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    features = data.get(
        "features",
        [],
    )

    if not features:
        return None

    return (
        features[0]
        ["attributes"]
        ["ZCTA5"]
    )


def main():

    locations = pd.read_parquet(
        LOCATION_PATH
    )

    old_zcta = locations[
        "zcta"
    ].copy()

    coordinate_zctas = []

    for index, row in locations.iterrows():

        print(
            f"[{index + 1}/{len(locations)}] "
            f"{row['mrf_location_name']}"
        )

        zcta = get_zcta(
            row["latitude"],
            row["longitude"],
        )

        coordinate_zctas.append(
            zcta
        )

        time.sleep(0.1)

    locations[
        "coordinate_zcta"
    ] = coordinate_zctas

    print(
        "\n=== ZIP VS COORDINATE ZCTA ==="
    )

    comparison = pd.DataFrame({
        "facility_id":
            locations["facility_id"],

        "mrf_location_name":
            locations["mrf_location_name"],

        "hcai_zip":
            locations["hcai_zip"],

        "old_zcta":
            old_zcta,

        "coordinate_zcta":
            locations["coordinate_zcta"],
    })

    differences = comparison[
        comparison[
            "old_zcta"
        ]
        != comparison[
            "coordinate_zcta"
        ]
    ]

    if differences.empty:

        print(
            "All 37 ZIP-based ZCTAs agree "
            "with coordinate-based ZCTAs."
        )

    else:

        print(
            differences.to_string(
                index=False
            )
        )

    missing = (
        locations[
            "coordinate_zcta"
        ]
        .isna()
        .sum()
    )

    print(
        "\nMissing coordinate ZCTAs:",
        missing,
    )

    if missing:
        raise RuntimeError(
            "Some campus coordinates "
            "could not be assigned to a ZCTA."
        )

    # ----------------------------------------
    # Replace previous ACS fields
    # ----------------------------------------

    acs_columns = [
        "population",
        "median_household_income",
        "poverty_rate",
        "uninsured_rate",
        "unemployment_rate",
        "bachelors_or_higher_rate",
    ]

    locations = locations.drop(
        columns=acs_columns,
        errors="ignore",
    )

    locations["zcta"] = (
        locations[
            "coordinate_zcta"
        ]
    )

    locations = locations.drop(
        columns=[
            "coordinate_zcta"
        ]
    )

    acs = pd.read_parquet(
        ACS_PATH
    )

    acs["zcta"] = (
        acs["zcta"]
        .astype(str)
        .str.zfill(5)
    )

    locations = locations.merge(
        acs,
        on="zcta",
        how="left",
        validate="many_to_one",
    )

    missing_acs = (
        locations[
            "population"
        ]
        .isna()
        .sum()
    )

    print(
        "Locations missing ACS record:",
        missing_acs,
    )

    if missing_acs:
        raise RuntimeError(
            "Some coordinate ZCTAs "
            "did not match ACS."
        )

    locations.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\nSaved updated location dimension:"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()