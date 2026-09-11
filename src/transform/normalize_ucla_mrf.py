from pathlib import Path
from collections import Counter
from decimal import Decimal
import json

import ijson
import pyarrow as pa
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "ucla"
    / "ronald_reagan_ucla.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "mrf"
    / "normalized"
    / "ucla"
    / "050262_ronald_reagan_ucla_medical_center.parquet"
)

FACILITY_ID = "050262"

BATCH_SIZE = 50_000


SCHEMA = pa.schema([
    ("system_name", pa.string()),
    ("facility_id", pa.string()),

    ("mrf_location_name", pa.string()),
    ("mrf_hospital_name", pa.string()),
    ("mrf_address", pa.string()),
    ("mrf_license_number", pa.string()),
    ("mrf_type_2_npi", pa.string()),
    ("mrf_last_updated_on", pa.string()),
    ("mrf_as_of_date", pa.string()),
    ("mrf_version", pa.string()),

    ("source_service_number", pa.int64()),
    ("source_charge_number", pa.int64()),
    ("source_payer_number", pa.int64()),
    ("source_record_id", pa.string()),

    ("description", pa.string()),

    ("code_1", pa.string()),
    ("code_1_type", pa.string()),
    ("code_2", pa.string()),
    ("code_2_type", pa.string()),
    ("all_codes_json", pa.string()),

    ("modifier", pa.string()),
    ("modifiers", pa.string()),

    ("drug_unit", pa.float64()),
    ("drug_type", pa.string()),

    ("setting", pa.string()),

    ("gross_charge", pa.float64()),
    ("discounted_cash_charge", pa.float64()),
    ("minimum_charge", pa.float64()),
    ("maximum_charge", pa.float64()),

    ("additional_generic_notes", pa.string()),

    ("payer", pa.string()),
    ("plan", pa.string()),

    ("negotiated_dollar", pa.float64()),
    ("negotiated_percentage", pa.float64()),
    ("negotiated_algorithm", pa.string()),

    ("median_amount", pa.float64()),
    ("p10_amount", pa.float64()),
    ("p90_amount", pa.float64()),

    ("negotiated_count", pa.string()),
    ("methodology", pa.string()),
    ("additional_payer_notes", pa.string()),

    ("has_negotiated_dollar", pa.bool_()),
    ("has_negotiated_percentage", pa.bool_()),
    ("has_negotiated_algorithm", pa.bool_()),
    ("has_negotiated_price", pa.bool_()),

    ("price_representation", pa.string()),
])


def to_string(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def to_float(value):
    if value is None:
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return float(value)

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def get_single_value(prefix):
    """
    Read one small metadata value without loading the
    standard_charge_information array.
    """

    with open(
        INPUT_PATH,
        "rb",
    ) as file:

        items = ijson.items(
            file,
            prefix,
        )

        try:
            return next(items)
        except StopIteration:
            return None


def get_metadata():

    license_info = (
        get_single_value(
            "license_information"
        )
        or {}
    )

    return {
        "mrf_hospital_name":
            to_string(
                get_single_value(
                    "hospital_name"
                )
            ),

        "mrf_location_name":
            to_string(
                get_single_value(
                    "location_name.item"
                )
            ),

        "mrf_address":
            to_string(
                get_single_value(
                    "hospital_address.item"
                )
            ),

        "mrf_license_number":
            to_string(
                license_info.get(
                    "license_number"
                )
            ),

        "mrf_type_2_npi":
            to_string(
                get_single_value(
                    "type_2_npi.item"
                )
            ),

        "mrf_last_updated_on":
            to_string(
                get_single_value(
                    "last_updated_on"
                )
            ),

        "mrf_as_of_date":
            to_string(
                get_single_value(
                    "as_of_date"
                )
            ),

        "mrf_version":
            to_string(
                get_single_value(
                    "version"
                )
            ),
    }


def get_price_representation(
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
        return "none"

    return "_".join(parts)


def write_batch(
    writer,
    batch,
):

    if not batch:
        return

    table = pa.Table.from_pylist(
        batch,
        schema=SCHEMA,
    )

    writer.write_table(
        table
    )


def main():

    print(
        "Normalizing Ronald Reagan UCLA MRF...\n"
    )

    metadata = get_metadata()

    print(
        "Hospital:",
        metadata[
            "mrf_hospital_name"
        ],
    )

    print(
        "Location:",
        metadata[
            "mrf_location_name"
        ],
    )

    print(
        "CMS facility ID:",
        FACILITY_ID,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    writer = pq.ParquetWriter(
        OUTPUT_PATH,
        SCHEMA,
        compression="snappy",
    )

    batch = []

    service_count = 0
    charge_count = 0
    payer_count = 0
    no_price_count = 0

    representations = Counter()

    try:

        with open(
            INPUT_PATH,
            "rb",
        ) as file:

            services = ijson.items(
                file,
                "standard_charge_information.item",
            )

            for service_number, service in enumerate(
                services,
                start=1,
            ):

                service_count += 1

                description = to_string(
                    service.get(
                        "description"
                    )
                )

                # ---------------------------------
                # Preserve complete code array
                # ---------------------------------

                codes = (
                    service.get(
                        "code_information",
                        []
                    )
                    or []
                )

                code_1 = (
                    codes[0]
                    if len(codes) >= 1
                    else {}
                )

                code_2 = (
                    codes[1]
                    if len(codes) >= 2
                    else {}
                )

                all_codes_json = (
                    json.dumps(
                        codes,
                        default=str,
                        separators=(
                            ",",
                            ":",
                        ),
                    )
                    if codes
                    else None
                )

                # ---------------------------------
                # Drug information
                # ---------------------------------

                drug = (
                    service.get(
                        "drug_information"
                    )
                    or {}
                )

                drug_unit = to_float(
                    drug.get("unit")
                )

                drug_type = to_string(
                    drug.get("type")
                )

                # ---------------------------------
                # Charge objects
                # ---------------------------------

                charges = (
                    service.get(
                        "standard_charges",
                        []
                    )
                    or []
                )

                for charge_number, charge in enumerate(
                    charges,
                    start=1,
                ):

                    charge_count += 1

                    payers = (
                        charge.get(
                            "payers_information",
                            []
                        )
                        or []
                    )

                    for payer_number, payer in enumerate(
                        payers,
                        start=1,
                    ):

                        payer_count += 1

                        negotiated_dollar = (
                            to_float(
                                payer.get(
                                    "standard_charge_dollar"
                                )
                            )
                        )

                        negotiated_percentage = (
                            to_float(
                                payer.get(
                                    "standard_charge_percentage"
                                )
                            )
                        )

                        negotiated_algorithm = (
                            to_string(
                                payer.get(
                                    "standard_charge_algorithm"
                                )
                            )
                        )

                        has_dollar = (
                            negotiated_dollar
                            is not None
                        )

                        has_percentage = (
                            negotiated_percentage
                            is not None
                        )

                        has_algorithm = (
                            negotiated_algorithm
                            is not None
                        )

                        has_price = (
                            has_dollar
                            or has_percentage
                            or has_algorithm
                        )

                        representation = (
                            get_price_representation(
                                has_dollar,
                                has_percentage,
                                has_algorithm,
                            )
                        )

                        representations[
                            representation
                        ] += 1

                        if not has_price:
                            no_price_count += 1

                        record = {
                            "system_name":
                                "UCLA Health",

                            "facility_id":
                                FACILITY_ID,

                            **metadata,

                            "source_service_number":
                                service_number,

                            "source_charge_number":
                                charge_number,

                            "source_payer_number":
                                payer_number,

                            "source_record_id":
                                (
                                    f"{service_number}:"
                                    f"{charge_number}:"
                                    f"{payer_number}"
                                ),

                            "description":
                                description,

                            "code_1":
                                to_string(
                                    code_1.get(
                                        "code"
                                    )
                                ),

                            "code_1_type":
                                to_string(
                                    code_1.get(
                                        "type"
                                    )
                                ),

                            "code_2":
                                to_string(
                                    code_2.get(
                                        "code"
                                    )
                                ),

                            "code_2_type":
                                to_string(
                                    code_2.get(
                                        "type"
                                    )
                                ),

                            "all_codes_json":
                                all_codes_json,

                            # Modifier information is a
                            # separate UCLA reference table.
                            "modifier":
                                None,

                            "modifiers":
                                None,

                            "drug_unit":
                                drug_unit,

                            "drug_type":
                                drug_type,

                            "setting":
                                to_string(
                                    charge.get(
                                        "setting"
                                    )
                                ),

                            "gross_charge":
                                to_float(
                                    charge.get(
                                        "gross_charge"
                                    )
                                ),

                            "discounted_cash_charge":
                                to_float(
                                    charge.get(
                                        "discounted_cash"
                                    )
                                ),

                            "minimum_charge":
                                to_float(
                                    charge.get(
                                        "minimum"
                                    )
                                ),

                            "maximum_charge":
                                to_float(
                                    charge.get(
                                        "maximum"
                                    )
                                ),

                            "additional_generic_notes":
                                to_string(
                                    charge.get(
                                        "additional_generic_notes"
                                    )
                                ),

                            "payer":
                                to_string(
                                    payer.get(
                                        "payer_name"
                                    )
                                ),

                            "plan":
                                to_string(
                                    payer.get(
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
                                to_float(
                                    payer.get(
                                        "median_amount"
                                    )
                                ),

                            "p10_amount":
                                to_float(
                                    payer.get(
                                        "10th_percentile"
                                    )
                                ),

                            "p90_amount":
                                to_float(
                                    payer.get(
                                        "90th_percentile"
                                    )
                                ),

                            # Keep count as STRING.
                            "negotiated_count":
                                to_string(
                                    payer.get(
                                        "count"
                                    )
                                ),

                            "methodology":
                                to_string(
                                    payer.get(
                                        "methodology"
                                    )
                                ),

                            "additional_payer_notes":
                                to_string(
                                    payer.get(
                                        "additional_payer_notes"
                                    )
                                ),

                            "has_negotiated_dollar":
                                has_dollar,

                            "has_negotiated_percentage":
                                has_percentage,

                            "has_negotiated_algorithm":
                                has_algorithm,

                            "has_negotiated_price":
                                has_price,

                            "price_representation":
                                representation,
                        }

                        batch.append(
                            record
                        )

                        if (
                            len(batch)
                            >= BATCH_SIZE
                        ):

                            write_batch(
                                writer,
                                batch,
                            )

                            batch.clear()

                if (
                    service_number % 1000
                    == 0
                ):

                    print(
                        f"Processed "
                        f"{service_number:,} "
                        f"services | "
                        f"{payer_count:,} "
                        f"payer rows"
                    )

        write_batch(
            writer,
            batch,
        )

    finally:

        writer.close()

    print(
        "\n=== NORMALIZATION SUMMARY ==="
    )

    print(
        "Services:",
        f"{service_count:,}",
    )

    print(
        "Charge objects:",
        f"{charge_count:,}",
    )

    print(
        "Normalized payer rows:",
        f"{payer_count:,}",
    )

    print(
        "Rows without negotiated price:",
        f"{no_price_count:,}",
    )

    print(
        "\n=== PRICE REPRESENTATIONS ==="
    )

    for representation, count in (
        representations
        .most_common()
    ):

        print(
            representation,
            f"{count:,}",
        )

    print(
        "\nOutput size:",
        f"{OUTPUT_PATH.stat().st_size / (1024 ** 2):.2f} MB",
    )

    print(
        "\nSaved:"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()