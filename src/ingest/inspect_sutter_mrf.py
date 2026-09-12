import csv
import requests
from io import StringIO


URL = (
    "https://edge.sitecorecloud.io/"
    "sutterhealt962c-sutterhealt8fce-production57cc-4860/"
    "media/Project/SutterHealth/SutterHealth/Files/"
    "billing-insurance/costs-and-charges/"
    "941156621-1811946734_"
    "sutter-medical-center-sacramento_standardcharges.csv"
)


def main():
    print("Downloading first portion of Sutter MRF...")

    response = requests.get(
        URL,
        timeout=120,
    )

    response.raise_for_status()

    text = response.text

    print("\nBytes:")
    print(len(response.content))

    reader = csv.reader(
        StringIO(text)
    )

    rows = []

    for i, row in enumerate(reader):
        rows.append(row)

        if i >= 5:
            break

    print("\n=== FIRST ROWS ===")

    for i, row in enumerate(rows):
        print(f"\nROW {i}")
        print(row)


if __name__ == "__main__":
    main()