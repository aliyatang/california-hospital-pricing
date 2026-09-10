from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

HOSPITAL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospital_master_ca.parquet"
)

CENSUS_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "acs5_2024_zcta.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "hospital_zcta_crosswalk.parquet"
)


TIGERWEB_URL = (
    "https://tigerweb.geo.census.gov/"
    "arcgis/rest/services/TIGERweb/"
    "tigerWMS_ACS2024/MapServer/2/query"
)


def lookup_zcta(longitude, latitude):
    """Find the Census ZCTA containing a hospital coordinate."""

    if pd.isna(longitude) or pd.isna(latitude):
        return None

    params = {
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "ZCTA5",
        "returnGeometry": "false",
        "f": "json",
    }

    response = requests.get(
        TIGERWEB_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    features = data.get("features", [])

    if not features:
        return None

    return features[0]["attributes"]["ZCTA5"]


def main():
    print("Building hospital-ZCTA crosswalk...\n")

    hospitals = pd.read_parquet(HOSPITAL_PATH)
    census = pd.read_parquet(CENSUS_PATH)

    valid_zctas = set(
        census["zcta"].astype("string")
    )

    eligible = hospitals[
        hospitals["analysis_eligible"]
    ].copy()

    rows = []

    for _, row in eligible.iterrows():

        hospital_zip = str(row["zip_code"]).zfill(5)

        if hospital_zip in valid_zctas:
            rows.append(
                {
                    "facility_id": row["facility_id"],
                    "hospital_zip": hospital_zip,
                    "census_zcta": hospital_zip,
                    "zcta_match_method": "zip_exact",
                }
            )

            continue

        zcta = lookup_zcta(
            row["longitude"],
            row["latitude"],
        )

        rows.append(
            {
                "facility_id": row["facility_id"],
                "hospital_zip": hospital_zip,
                "census_zcta": zcta,
                "zcta_match_method": (
                    "coordinate_point"
                    if zcta
                    else "unresolved"
                ),
            }
        )

        print(
            f'{row["facility_id"]} '
            f'{row["facility_name"]}: '
            f'{hospital_zip} -> {zcta}'
        )

    crosswalk = pd.DataFrame(rows)

    print("\nMatch methods:")
    print(
        crosswalk["zcta_match_method"]
        .value_counts(dropna=False)
    )

    print(
        "\nUnresolved:",
        crosswalk["census_zcta"].isna().sum(),
    )

    crosswalk.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\nSaved crosswalk to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()