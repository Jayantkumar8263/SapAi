from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "samples"
REPORT_DIR = PROJECT_ROOT / "data" / "reports"


JULY_FILE = (
    DATA_DIR / "Inventory Previous 07(month).xlsx"
)

AUGUST_FILE = (
    DATA_DIR / "Inventory Previous 25.08.xlsx"
)

REFERENCE_FILE = (
    DATA_DIR / "Final output file.xlsx"
)


def normalize(value):
    if pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
    )


def inspect_raw_sheet(
    label,
    sap_file,
    reference_sheet,
):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    # --------------------------------------------------------
    # Read SAP Sheet1
    # --------------------------------------------------------

    raw = pd.read_excel(
        sap_file,
        sheet_name="Sheet1",
    )

    raw.columns = [
        str(column).strip()
        for column in raw.columns
    ]

    print(
        f"\nSAP Sheet1 rows: {len(raw)}"
    )

    print("\nSAP Sheet1 columns:")

    for column in raw.columns:
        print(f"  {column}")

    # --------------------------------------------------------
    # Read manual report
    # --------------------------------------------------------

    manual = pd.read_excel(
        REFERENCE_FILE,
        sheet_name=reference_sheet,
    )

    manual.columns = [
        str(column).strip()
        for column in manual.columns
    ]

    print(
        f"\nManual rows: {len(manual)}"
    )

    # --------------------------------------------------------
    # Build manual key
    # --------------------------------------------------------

    manual["__key"] = (
        manual["Concatenate"]
        .apply(normalize)
    )

    # --------------------------------------------------------
    # Build key from raw Sheet1
    #
    # Plant is 1000 in the BSP data.
    #
    # Key structure:
    #
    # Plant + Material + Storage Location
    # --------------------------------------------------------

    raw["__material"] = (
        raw["Material"]
        .apply(normalize)
    )

    raw["__storage"] = (
        raw["Storage Location"]
        .apply(normalize)
    )

    raw["__key"] = (
        "1000"
        + raw["__material"]
        + raw["__storage"]
    )

    # --------------------------------------------------------
    # Compare keys
    # --------------------------------------------------------

    raw_keys = set(
        raw["__key"]
    )

    manual_keys = set(
        manual["__key"]
    )

    manual_only = (
        manual_keys - raw_keys
    )

    raw_only = (
        raw_keys - manual_keys
    )

    common = (
        manual_keys & raw_keys
    )

    print("\nKEY ANALYSIS")
    print("-" * 70)

    print(
        f"Manual unique keys : "
        f"{len(manual_keys)}"
    )

    print(
        f"Raw Sheet1 unique keys : "
        f"{len(raw_keys)}"
    )

    print(
        f"Common keys : "
        f"{len(common)}"
    )

    print(
        f"Manual keys NOT found in Sheet1 : "
        f"{len(manual_only)}"
    )

    print(
        f"Sheet1 keys NOT found in manual : "
        f"{len(raw_only)}"
    )

    # --------------------------------------------------------
    # Inspect manual-only records
    # --------------------------------------------------------

    if manual_only:

        print(
            "\nFirst 20 manual records "
            "NOT found in Sheet1:"
        )

        manual_only_df = manual[
            manual["__key"].isin(
                manual_only
            )
        ].copy()

        display_columns = [
            "Concatenate",
            "Mat Grp",
            "Mat Grp Desc",
            "Material Code",
            "Material Code Desc",
            "Storage location",
            "Storage Location",
            "Storage Location Desc",
            "Plant",
            "Inve Prev Quantity",
            "Inve Pres Quantity",
            "Inve Prev Value",
            "Inve Pres Value",
            "UOM",
        ]

        available = [
            column
            for column in display_columns
            if column in manual_only_df.columns
        ]

        print(
            manual_only_df[
                available
            ].head(20).to_string(
                index=False
            )
        )

        output_file = (
            REPORT_DIR
            / f"{label.lower()}_manual_not_in_sheet1.xlsx"
        )

        manual_only_df.to_excel(
            output_file,
            index=False,
        )

        print(
            f"\nSaved manual-only records to:"
        )

        print(output_file)

    # --------------------------------------------------------
    # Inspect common records
    # --------------------------------------------------------

    print(
        "\nExample matching records:"
    )

    matching_manual = manual[
        manual["__key"].isin(
            common
        )
    ]

    print(
        matching_manual[
            [
                "Concatenate",
                "Material Code",
                "Plant",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


def main():

    print("=" * 70)
    print("BSP RAW SHEET1 INVESTIGATION")
    print("=" * 70)

    inspect_raw_sheet(
        label="JULY",
        sap_file=JULY_FILE,
        reference_sheet="Inventory Prev",
    )

    inspect_raw_sheet(
        label="AUGUST",
        sap_file=AUGUST_FILE,
        reference_sheet="Inventory Pres",
    )

    print("\n" + "=" * 70)
    print("INVESTIGATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()