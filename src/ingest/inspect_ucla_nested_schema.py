from pathlib import Path
from pprint import pprint

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


def print_keys(label, value):
    print(f"\n=== {label} ===")

    if isinstance(value, dict):
        for key, item in value.items():
            print(
                f"{key}: {type(item).__name__}"
            )
    else:
        print(
            type(value).__name__
        )


def get_first_item(prefix):
    with open(
        INPUT_PATH,
        "rb",
    ) as file:

        items = ijson.items(
            file,
            prefix,
        )

        return next(items)


def main():

    # -----------------------------------
    # First service/procedure
    # -----------------------------------

    service = get_first_item(
        "standard_charge_information.item"
    )

    print_keys(
        "SERVICE KEYS",
        service,
    )

    print("\nDescription:")
    print(
        service.get("description")
    )

    print("\nCode information:")
    pprint(
        service.get(
            "code_information"
        )
    )

    print(
        "\nDrug information:"
    )
    pprint(
        service.get(
            "drug_information"
        )
    )

    # -----------------------------------
    # First standard-charge object
    # -----------------------------------

    charges = service.get(
        "standard_charges",
        [],
    )

    print(
        "\nStandard charge objects:",
        len(charges),
    )

    if charges:

        charge = charges[0]

        print_keys(
            "STANDARD CHARGE KEYS",
            charge,
        )

        # Print scalar fields only.
        print(
            "\n=== STANDARD CHARGE SCALARS ==="
        )

        for key, value in charge.items():

            if not isinstance(
                value,
                (list, dict),
            ):

                print(
                    f"{key}: {value}"
                )

        # Inspect nested lists/dicts.
        for key, value in charge.items():

            if isinstance(
                value,
                list,
            ):

                print(
                    f"\n=== NESTED LIST: {key} ==="
                )

                print(
                    "items:",
                    len(value),
                )

                if value:

                    print_keys(
                        f"FIRST {key} ITEM KEYS",
                        value[0],
                    )

                    print(
                        "\nFirst item:"
                    )

                    pprint(
                        value[0],
                        width=120,
                    )

            elif isinstance(
                value,
                dict,
            ):

                print(
                    f"\n=== NESTED DICT: {key} ==="
                )

                print_keys(
                    key,
                    value,
                )

                pprint(
                    value,
                    width=120,
                )

    # -----------------------------------
    # Modifier structure
    # -----------------------------------

    modifier = get_first_item(
        "modifier_information.item"
    )

    print_keys(
        "MODIFIER KEYS",
        modifier,
    )

    print(
        "\nModifier description:",
        modifier.get("description"),
    )

    print(
        "Modifier code:",
        modifier.get("code"),
    )

    modifier_payers = (
        modifier.get(
            "modifier_payer_information",
            [],
        )
    )

    print(
        "\nModifier payer records:",
        len(modifier_payers),
    )

    if modifier_payers:

        print_keys(
            "MODIFIER PAYER KEYS",
            modifier_payers[0],
        )

        print(
            "\nFirst modifier payer record:"
        )

        pprint(
            modifier_payers[0],
            width=120,
        )


if __name__ == "__main__":
    main()