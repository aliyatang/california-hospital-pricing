from pathlib import Path
import argparse
import csv
import json
import re

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "sutter"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "sutter"
)

CROSSWALK_PATH = (
    PROJECT_ROOT
    / "config"
    / "sutter_mrf_crosswalk.csv"
)


def slugify(value):
    value = value.lower()
    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )
    return value.strip("_")


def clean_string(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def parse_number(value):
    value = clean_string(value)

    if value is None:
        return None

    value = (
        value
        .replace("$", "")
        .replace(",", "")
        .replace("%", "")
    )

    try:
        return float(value)

    except ValueError:
        return None


def build_codes(row):
    codes = []

    for i in range(1, 5):

        code = clean_string(
            row.get(
                f"code|{i}"
            )
        )

        code_type = clean_string(
            row.get(
                f"code|{i}|type"
            )
        )

        if code is not None:

            codes.append(
                {
                    "code": code,
                    "type": code_type,
                }
            )

    return codes


def get_representation(
    has_dollar,
    has_percentage,
    has_algorithm,
):
    parts = []

    if has_dollar:
        parts.append("dollar")

    if has_percentage:
        parts.append("percentage")

    if has_algorithm:
        parts.append("algorithm")

    if not parts:
        return None

    return "_".join(parts)


def load_crosswalk(location):

    crosswalk = pd.read_csv(
        CROSSWALK_PATH,
        dtype=str,
    )

    match = crosswalk[
        crosswalk[
            "mrf_location_name"
        ] == location
    ]

    if len(match) != 1:
        raise RuntimeError(
            f"Expected exactly one crosswalk "
            f"match for {location!r}, "
            f"found {len(match)}."
        )

    return match.iloc[0]


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--location",
        required=True,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    crosswalk = load_crosswalk(
        args.location
    )

    facility_id = str(
        crosswalk["facility_id"]
    ).zfill(6)

    source_file = (
        RAW_DIR
        / crosswalk["source_file"]
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Raw MRF not found: "
            f"{source_file}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / (
            slugify(args.location)
            + ".parquet"
        )
    )

    if (
        output_path.exists()
        and not args.force
    ):
        print(
            "Already exists:",
            output_path,
        )
        return

    records = []

    source_rows = 0
    skipped_no_price = 0

    with source_file.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.reader(file)

        metadata_header = next(reader)
        metadata_values = next(reader)
        charge_header = next(reader)

        metadata = dict(
            zip(
                metadata_header,
                metadata_values,
            )
        )

        hospital_name = clean_string(
            metadata.get(
                "hospital_name"
            )
        )

        location_name = clean_string(
            metadata.get(
                "location_name"
            )
        )

        hospital_address = clean_string(
            metadata.get(
                "hospital_address"
            )
        )

        type_2_npi = clean_string(
            metadata.get(
                "type_2_npi"
            )
        )

        license_number = clean_string(
            metadata.get(
                "license_number|CA"
            )
        )

        last_updated_on = clean_string(
            metadata.get(
                "last_updated_on"
            )
        )

        version = clean_string(
            metadata.get(
                "version"
            )
        )

        for source_row_number, values in enumerate(
            reader,
            start=1,
        ):

            if not values:
                continue

            source_rows += 1

            row = dict(
                zip(
                    charge_header,
                    values,
                )
            )

            negotiated_dollar = parse_number(
                row.get(
                    "standard_charge|negotiated_dollar"
                )
            )

            negotiated_percentage = parse_number(
                row.get(
                    "standard_charge|negotiated_percentage"
                )
            )

            negotiated_algorithm = clean_string(
                row.get(
                    "standard_charge|negotiated_algorithm"
                )
            )

            has_dollar = (
                negotiated_dollar is not None
            )

            has_percentage = (
                negotiated_percentage is not None
            )

            has_algorithm = (
                negotiated_algorithm is not None
            )

            has_price = (
                has_dollar
                or has_percentage
                or has_algorithm
            )

            # Our negotiated-price fact excludes
            # gross/cash-only and informational rows.
            if not has_price:
                skipped_no_price += 1
                continue

            codes = build_codes(row)

            code_1 = (
                codes[0]["code"]
                if len(codes) >= 1
                else None
            )

            code_1_type = (
                codes[0]["type"]
                if len(codes) >= 1
                else None
            )

            code_2 = (
                codes[1]["code"]
                if len(codes) >= 2
                else None
            )

            code_2_type = (
                codes[1]["type"]
                if len(codes) >= 2
                else None
            )

            records.append(
                {
                    "system_name":
                        "Sutter Health",

                    "facility_id":
                        facility_id,

                    "mrf_location_name":
                        location_name,

                    "mrf_hospital_name":
                        hospital_name,

                    "mrf_address":
                        hospital_address,

                    "mrf_license_number":
                        license_number,

                    "mrf_type_2_npi":
                        type_2_npi,

                    "mrf_last_updated_on":
                        last_updated_on,

                    "mrf_version":
                        version,

                    "source_row_number":
                        source_row_number,

                    "source_record_id":
                        (
                            f"{facility_id}|"
                            f"{source_row_number}"
                        ),

                    "description":
                        clean_string(
                            row.get(
                                "description"
                            )
                        ),

                    "billing_class":
                        clean_string(
                            row.get(
                                "billing_class"
                            )
                        ),

                    "code_1":
                        code_1,

                    "code_1_type":
                        code_1_type,

                    "code_2":
                        code_2,

                    "code_2_type":
                        code_2_type,

                    "all_codes_json":
                        json.dumps(
                            codes,
                            separators=(
                                ",",
                                ":",
                            ),
                        ),

                    "modifier":
                        None,

                    "modifiers":
                        clean_string(
                            row.get(
                                "modifiers"
                            )
                        ),

                    "drug_unit":
                        clean_string(
                            row.get(
                                "drug_unit_of_measurement"
                            )
                        ),

                    "drug_type":
                        clean_string(
                            row.get(
                                "drug_type_of_measurement"
                            )
                        ),

                    "setting":
                        clean_string(
                            row.get(
                                "setting"
                            )
                        ),

                    "gross_charge":
                        parse_number(
                            row.get(
                                "standard_charge|gross"
                            )
                        ),

                    "discounted_cash_charge":
                        parse_number(
                            row.get(
                                "standard_charge|discounted_cash"
                            )
                        ),

                    "minimum_charge":
                        parse_number(
                            row.get(
                                "standard_charge|min"
                            )
                        ),

                    "maximum_charge":
                        parse_number(
                            row.get(
                                "standard_charge|max"
                            )
                        ),

                    "additional_generic_notes":
                        clean_string(
                            row.get(
                                "additional_generic_notes"
                            )
                        ),

                    "payer":
                        clean_string(
                            row.get(
                                "payer_name"
                            )
                        ),

                    "plan":
                        clean_string(
                            row.get(
                                "plan_name"
                            )
                        ),

                    "negotiated_dollar":
                        negotiated_dollar,

                    "negotiated_percentage":
                        negotiated_percentage,

                    "negotiated_algorithm":
                        negotiated_algorithm,

                    "median_amount":
                        parse_number(
                            row.get(
                                "median_amount"
                            )
                        ),

                    "p10_amount":
                        parse_number(
                            row.get(
                                "10th_percentile"
                            )
                        ),

                    "p90_amount":
                        parse_number(
                            row.get(
                                "90th_percentile"
                            )
                        ),

                    "negotiated_count":
                        clean_string(
                            row.get(
                                "count"
                            )
                        ),

                    "methodology":
                        clean_string(
                            row.get(
                                "standard_charge|methodology"
                            )
                        ),

                    "additional_payer_notes":
                        None,

                    "has_negotiated_dollar":
                        has_dollar,

                    "has_negotiated_percentage":
                        has_percentage,

                    "has_negotiated_algorithm":
                        has_algorithm,

                    "has_negotiated_price":
                        has_price,

                    "price_representation":
                        get_representation(
                            has_dollar,
                            has_percentage,
                            has_algorithm,
                        ),
                }
            )

    df = pd.DataFrame(
        records
    )

    df.to_parquet(
        output_path,
        index=False,
    )

    print(
        "\n=== SUTTER NORMALIZATION ==="
    )

    print(
        "Location:",
        args.location,
    )

    print(
        "Facility ID:",
        facility_id,
    )

    print(
        "Source rows:",
        f"{source_rows:,}",
    )

    print(
        "Negotiated-price rows:",
        f"{len(df):,}",
    )

    print(
        "Skipped no-price rows:",
        f"{skipped_no_price:,}",
    )

    print(
        "\nPrice representation:"
    )

    print(
        df[
            "price_representation"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\nUnique payers:",
        df["payer"].nunique()
    )

    print(
        "Unique payer-plan pairs:",
        df[
            [
                "payer",
                "plan",
            ]
        ]
        .drop_duplicates()
        .shape[0]
    )

    print(
        "\nSaved:"
    )

    print(
        output_path
    )


if __name__ == "__main__":
    main()