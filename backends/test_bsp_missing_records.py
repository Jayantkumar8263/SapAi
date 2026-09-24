from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "samples"


JULY_FILE = (
    DATA_DIR
    / "Inventory Previous 07(month).xlsx"
)

AUGUST_FILE = (
    DATA_DIR
    / "Inventory Previous 25.08.xlsx"
)

REFERENCE_FILE = (
    DATA_DIR
    / "Final output file.xlsx"
)


def load_keys(
    file_path,
    sheet_name,
    header=0,
):
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=header,
    )

    # Find Concatenate column case-insensitively.
    concatenate_column = None

    for column in df.columns:

        normalized = (
            str(column)
            .strip()
            .lower()
        )

        if normalized == "concatenate":
            concatenate_column = column
            break

    if concatenate_column is None:

        raise ValueError(
            f"Concatenate column not found in "
            f"{file_path.name} / {sheet_name}"
        )

    keys = (
        df[concatenate_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return df, keys


def inspect_missing(
    label,
    source_file,
    reference_sheet,
):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    # --------------------------------------------------------
    # Source SAP file
    # --------------------------------------------------------

    source_df, source_keys = load_keys(
        source_file,
        "Sheet2",
    )

    # --------------------------------------------------------
    # Manual reference
    # --------------------------------------------------------

    reference_df, reference_keys = load_keys(
        REFERENCE_FILE,
        reference_sheet,
    )

    source_key_set = set(source_keys)
    reference_key_set = set(reference_keys)

    # --------------------------------------------------------
    # Keys existing in manual report but NOT in SAP
    # --------------------------------------------------------

    missing_from_sap = (
        reference_key_set
        - source_key_set
    )

    # --------------------------------------------------------
    # Keys existing in SAP but NOT in manual report
    # --------------------------------------------------------

    missing_from_reference = (
        source_key_set
        - reference_key_set
    )

    print(
        f"\nSource SAP rows: "
        f"{len(source_df)}"
    )

    print(
        f"Manual reference rows: "
        f"{len(reference_df)}"
    )

    print(
        f"\nManual rows NOT found in SAP: "
        f"{len(missing_from_sap)}"
    )

    print(
        f"SAP rows NOT found in manual: "
        f"{len(missing_from_reference)}"
    )

    # --------------------------------------------------------
    # Inspect manual-only records
    # --------------------------------------------------------

    if missing_from_sap:

        print(
            "\nFirst 20 records present in "
            "manual report but missing from SAP:"
        )

        manual_only = reference_df[
            reference_keys.isin(
                missing_from_sap
            )
        ].copy()

        # Show useful columns only.
        preferred_columns = [
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
            "Inve Prev Value",
            "Inve Pres Quantity",
            "Inve Pres Value",
            "UOM",
        ]

        available_columns = [
            column
            for column in preferred_columns
            if column in manual_only.columns
        ]

        print(
            manual_only[
                available_columns
            ].head(20).to_string(
                index=False
            )
        )

        # Save the complete extra records.
        output_file = (
            DATA_DIR.parent
            / "reports"
            / f"{label.lower().replace(' ', '_')}_manual_only.xlsx"
        )

        manual_only.to_excel(
            output_file,
            index=False,
        )

        print(
            f"\nComplete manual-only records saved to:"
        )

        print(output_file)

    # --------------------------------------------------------
    # Inspect SAP-only records
    # --------------------------------------------------------

    if missing_from_reference:

        print(
            "\nFirst 20 records present in "
            "SAP but missing from manual:"
        )

        sap_only = source_df[
            source_keys.isin(
                missing_from_reference
            )
        ].copy()

        print(
            sap_only.head(20).to_string(
                index=False
            )
        )

        output_file = (
            DATA_DIR.parent
            / "reports"
            / f"{label.lower().replace(' ', '_')}_sap_only.xlsx"
        )

        sap_only.to_excel(
            output_file,
            index=False,
        )

        print(
            f"\nComplete SAP-only records saved to:"
        )

        print(output_file)


def main():

    print("=" * 70)
    print("BSP MANUAL vs SAP MISSING RECORD INVESTIGATION")
    print("=" * 70)

    inspect_missing(
        label="JULY_PREVIOUS",
        source_file=JULY_FILE,
        reference_sheet="Inventory Prev",
    )

    inspect_missing(
        label="AUGUST_PRESENT",
        source_file=AUGUST_FILE,
        reference_sheet="Inventory Pres",
    )

    print("\n" + "=" * 70)
    print("INVESTIGATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()