from pathlib import Path
import json

import requests


URL = (
    "https://www.uclahealth.org/sites/default/files/"
    "cms-hpt/956006143_ronald-reagan-ucla-medical-center_"
    "standardcharges.json?refresh=2026"
)


def describe(value, indent=0, max_items=5):
    prefix = " " * indent

    if isinstance(value, dict):
        print(
            f"{prefix}dict with {len(value)} keys:"
        )

        for key in list(value.keys())[:max_items]:
            item = value[key]

            print(
                f"{prefix}- {key}: "
                f"{type(item).__name__}"
            )

            if isinstance(
                item,
                (dict, list),
            ):
                describe(
                    item,
                    indent + 4,
                    max_items=3,
                )

    elif isinstance(value, list):
        print(
            f"{prefix}list with "
            f"{len(value)} items"
        )

        if value:
            print(
                f"{prefix}first item:"
            )

            describe(
                value[0],
                indent + 4,
                max_items=5,
            )


def main():

    print(
        "Fetching Ronald Reagan UCLA MRF..."
    )

    response = requests.get(
        URL,
        timeout=120,
    )

    response.raise_for_status()

    print(
        "Downloaded:",
        f"{len(response.content) / (1024 ** 2):.2f} MB",
    )

    data = response.json()

    print(
        "\n=== TOP-LEVEL STRUCTURE ==="
    )

    describe(
        data,
        max_items=20,
    )

    print(
        "\n=== TOP-LEVEL KEYS ==="
    )

    for key in data.keys():
        print(key)

    print(
        "\n=== METADATA VALUES ==="
    )

    for key, value in data.items():

        if not isinstance(
            value,
            (list, dict),
        ):
            print(
                f"{key}: {value}"
            )

    # Save raw source-of-truth file.
    output_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "raw"
        / "mrf"
        / "ucla"
        / "ronald_reagan_ucla.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
        )

    print(
        "\nSaved:"
    )

    print(
        output_path
    )


if __name__ == "__main__":
    main()