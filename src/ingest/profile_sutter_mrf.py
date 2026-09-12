from collections import Counter
from pathlib import Path
import csv
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

URL = (
    "https://edge.sitecorecloud.io/"
    "sutterhealt962c-sutterhealt8fce-production57cc-4860/"
    "media/Project/SutterHealth/SutterHealth/Files/"
    "billing-insurance/costs-and-charges/"
    "941156621-1811946734_"
    "sutter-medical-center-sacramento_standardcharges.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "sutter"
    / "sutter_medical_center_sacramento.csv"
)


def nonempty(value):
    return (
        value is not None
        and str(value).strip() != ""
    )


def main():

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not OUTPUT_PATH.exists():

        print("Downloading Sutter Sacramento MRF...")

        response = requests.get(
            URL,
            timeout=180,
        )

        response.raise_for_status()

        OUTPUT_PATH.write_bytes(
            response.content
        )

        print(
            "Saved:",
            OUTPUT_PATH,
        )

    with open(
        OUTPUT_PATH,
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

        print("\n=== METADATA ===")

        for key, value in metadata.items():
            print(
                f"{key}: {value}"
            )

        total_rows = 0

        with_any_price = 0
        with_dollar = 0
        with_percentage = 0
        with_algorithm = 0
        without_price = 0

        representations = Counter()
        payers = Counter()
        plans = Counter()
        payer_plan_pairs = Counter()
        code_types = Counter()
        settings = Counter()
        billing_classes = Counter()
        methodologies = Counter()

        max_codes = 0

        for values in reader:

            if not values:
                continue

            row = dict(
                zip(
                    charge_header,
                    values,
                )
            )

            total_rows += 1

            has_dollar = nonempty(
                row.get(
                    "standard_charge|negotiated_dollar"
                )
            )

            has_percentage = nonempty(
                row.get(
                    "standard_charge|negotiated_percentage"
                )
            )

            has_algorithm = nonempty(
                row.get(
                    "standard_charge|negotiated_algorithm"
                )
            )

            flags = []

            if has_dollar:
                flags.append("dollar")
                with_dollar += 1

            if has_percentage:
                flags.append("percentage")
                with_percentage += 1

            if has_algorithm:
                flags.append("algorithm")
                with_algorithm += 1

            if flags:
                with_any_price += 1

                representations[
                    "_".join(flags)
                ] += 1
            else:
                without_price += 1
                representations[
                    "none"
                ] += 1

            payer = (
                row.get("payer_name")
                or ""
            ).strip()

            plan = (
                row.get("plan_name")
                or ""
            ).strip()

            if payer:
                payers[payer] += 1

            if plan:
                plans[plan] += 1

            if payer or plan:
                payer_plan_pairs[
                    (payer, plan)
                ] += 1

            code_count = 0

            for i in range(1, 5):

                code = (
                    row.get(
                        f"code|{i}"
                    )
                    or ""
                ).strip()

                code_type = (
                    row.get(
                        f"code|{i}|type"
                    )
                    or ""
                ).strip()

                if code:
                    code_count += 1

                if code_type:
                    code_types[
                        code_type
                    ] += 1

            max_codes = max(
                max_codes,
                code_count,
            )

            setting = (
                row.get("setting")
                or ""
            ).strip()

            if setting:
                settings[setting] += 1

            billing_class = (
                row.get(
                    "billing_class"
                )
                or ""
            ).strip()

            if billing_class:
                billing_classes[
                    billing_class
                ] += 1

            methodology = (
                row.get(
                    "standard_charge|methodology"
                )
                or ""
            ).strip()

            if methodology:
                methodologies[
                    methodology
                ] += 1

    print("\n=== ROW COUNTS ===")
    print(
        "Total rows:",
        f"{total_rows:,}",
    )
    print(
        "Rows with any negotiated price:",
        f"{with_any_price:,}",
    )
    print(
        "Rows without negotiated price:",
        f"{without_price:,}",
    )

    print("\n=== PRICE COVERAGE ===")
    print(
        "Dollar:",
        f"{with_dollar:,}",
    )
    print(
        "Percentage:",
        f"{with_percentage:,}",
    )
    print(
        "Algorithm:",
        f"{with_algorithm:,}",
    )

    print("\n=== REPRESENTATIONS ===")

    for key, value in (
        representations.most_common()
    ):
        print(
            key,
            f"{value:,}",
        )

    print("\n=== DIMENSIONS ===")
    print(
        "Unique payers:",
        len(payers),
    )
    print(
        "Unique plans:",
        len(plans),
    )
    print(
        "Unique payer-plan pairs:",
        len(payer_plan_pairs),
    )
    print(
        "Max codes on one row:",
        max_codes,
    )

    print("\nCode types:")
    print(code_types)

    print("\nSettings:")
    print(settings)

    print("\nBilling classes:")
    print(billing_classes)

    print("\nMethodologies:")
    print(methodologies)


if __name__ == "__main__":
    main()