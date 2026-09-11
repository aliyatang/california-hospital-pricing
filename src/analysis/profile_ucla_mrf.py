from pathlib import Path
from collections import Counter
import ijson


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "mrf"
    / "ucla"
    / "ronald_reagan_ucla.json"
)


def main():

    service_count = 0
    charge_count = 0
    payer_record_count = 0

    service_keys = Counter()
    charge_keys = Counter()
    payer_keys = Counter()

    charges_per_service = Counter()
    codes_per_service = Counter()
    payers_per_charge = Counter()

    code_types = Counter()
    settings = Counter()
    methodologies = Counter()

    dollar_present = 0
    percentage_present = 0
    algorithm_present = 0

    unique_payers = set()
    unique_plans = set()
    unique_payer_plan_pairs = set()

    modifier_related_keys = set()
    algorithm_related_keys = set()

    print("Profiling UCLA MRF...\n")

    with open(
        INPUT_PATH,
        "rb",
    ) as file:

        services = ijson.items(
            file,
            "standard_charge_information.item",
        )

        for service in services:

            service_count += 1

            service_keys.update(
                service.keys()
            )

            for key in service.keys():

                if "modifier" in key.lower():
                    modifier_related_keys.add(
                        f"service.{key}"
                    )

                if "algorithm" in key.lower():
                    algorithm_related_keys.add(
                        f"service.{key}"
                    )

            # --------------------------------
            # Procedure codes
            # --------------------------------

            codes = service.get(
                "code_information",
                [],
            ) or []

            codes_per_service[
                len(codes)
            ] += 1

            for code in codes:

                code_type = code.get(
                    "type"
                )

                if code_type:
                    code_types[
                        str(code_type)
                    ] += 1

            # --------------------------------
            # Standard charge objects
            # --------------------------------

            charges = service.get(
                "standard_charges",
                [],
            ) or []

            charges_per_service[
                len(charges)
            ] += 1

            for charge in charges:

                charge_count += 1

                charge_keys.update(
                    charge.keys()
                )

                for key in charge.keys():

                    if "modifier" in key.lower():
                        modifier_related_keys.add(
                            f"charge.{key}"
                        )

                    if "algorithm" in key.lower():
                        algorithm_related_keys.add(
                            f"charge.{key}"
                        )

                setting = charge.get(
                    "setting"
                )

                if setting:
                    settings[
                        str(setting)
                    ] += 1

                # --------------------------------
                # Payer records
                # --------------------------------

                payers = charge.get(
                    "payers_information",
                    [],
                ) or []

                payers_per_charge[
                    len(payers)
                ] += 1

                for payer in payers:

                    payer_record_count += 1

                    payer_keys.update(
                        payer.keys()
                    )

                    for key in payer.keys():

                        if "modifier" in key.lower():
                            modifier_related_keys.add(
                                f"payer.{key}"
                            )

                        if "algorithm" in key.lower():
                            algorithm_related_keys.add(
                                f"payer.{key}"
                            )

                    payer_name = payer.get(
                        "payer_name"
                    )

                    plan_name = payer.get(
                        "plan_name"
                    )

                    if payer_name:
                        unique_payers.add(
                            str(payer_name)
                        )

                    if plan_name:
                        unique_plans.add(
                            str(plan_name)
                        )

                    if payer_name or plan_name:
                        unique_payer_plan_pairs.add(
                            (
                                str(payer_name),
                                str(plan_name),
                            )
                        )

                    if payer.get(
                        "standard_charge_dollar"
                    ) is not None:
                        dollar_present += 1

                    if payer.get(
                        "standard_charge_percentage"
                    ) is not None:
                        percentage_present += 1

                    if payer.get(
                        "standard_charge_algorithm"
                    ) is not None:
                        algorithm_present += 1

                    methodology = payer.get(
                        "methodology"
                    )

                    if methodology:
                        methodologies[
                            str(methodology)
                        ] += 1

            if (
                service_count % 1000
                == 0
            ):
                print(
                    f"Processed "
                    f"{service_count:,} "
                    f"services..."
                )

    # --------------------------------
    # Results
    # --------------------------------

    print("\n=== COUNTS ===")
    print(
        "Services:",
        f"{service_count:,}",
    )
    print(
        "Standard charge objects:",
        f"{charge_count:,}",
    )
    print(
        "Payer records:",
        f"{payer_record_count:,}",
    )

    print("\n=== SERVICE KEYS ===")
    for key in sorted(
        service_keys
    ):
        print(
            key,
            service_keys[key],
        )

    print("\n=== STANDARD CHARGE KEYS ===")
    for key in sorted(
        charge_keys
    ):
        print(
            key,
            charge_keys[key],
        )

    print("\n=== PAYER KEYS ===")
    for key in sorted(
        payer_keys
    ):
        print(
            key,
            payer_keys[key],
        )

    print("\n=== CHARGES PER SERVICE ===")
    print(
        charges_per_service
    )

    print("\n=== CODES PER SERVICE ===")
    print(
        codes_per_service
    )

    print("\n=== PAYERS PER CHARGE ===")
    print(
        payers_per_charge
    )

    print("\n=== CODE TYPES ===")
    print(
        code_types
    )

    print("\n=== SETTINGS ===")
    print(
        settings
    )

    print("\n=== NEGOTIATED VALUE COVERAGE ===")
    print(
        "Dollar:",
        f"{dollar_present:,}",
    )
    print(
        "Percentage:",
        f"{percentage_present:,}",
    )
    print(
        "Algorithm:",
        f"{algorithm_present:,}",
    )

    print("\n=== UNIQUE PAYER STRUCTURE ===")
    print(
        "Unique payers:",
        len(unique_payers),
    )
    print(
        "Unique plans:",
        len(unique_plans),
    )
    print(
        "Unique payer-plan pairs:",
        len(
            unique_payer_plan_pairs
        ),
    )

    print("\n=== METHODOLOGIES ===")
    for value, count in (
        methodologies
        .most_common()
    ):
        print(
            value,
            count,
        )

    print("\n=== MODIFIER-RELATED KEYS ===")
    if modifier_related_keys:
        for key in sorted(
            modifier_related_keys
        ):
            print(key)
    else:
        print("None")

    print("\n=== ALGORITHM-RELATED KEYS ===")
    if algorithm_related_keys:
        for key in sorted(
            algorithm_related_keys
        ):
            print(key)
    else:
        print("None")


if __name__ == "__main__":
    main()