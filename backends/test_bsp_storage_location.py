from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "samples"


FILES = {
    "JULY": DATA_DIR / "Inventory Previous 07(month).xlsx",
    "AUGUST": DATA_DIR / "Inventory Previous 25.08.xlsx",
}


def inspect_file(label, file_path):

    print("\n" + "=" * 70)
    print(f"{label}: {file_path.name}")
    print("=" * 70)

    df = pd.read_excel(
        file_path,
        sheet_name="Sheet2",
    )

    print(f"\nRows: {len(df)}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  {repr(column)}")

    # --------------------------------------------------------
    # Find storage location column
    # --------------------------------------------------------

    storage_column = None

    for column in df.columns:

        normalized = (
            str(column)
            .strip()
            .lower()
        )

        if normalized == "storage location":
            storage_column = column
            break

    if storage_column is None:

        print(
            "\nERROR: Storage Location column not found."
        )

        return

    print(
        f"\nStorage Location column: "
        f"{repr(storage_column)}"
    )

    # --------------------------------------------------------
    # Raw value statistics
    # --------------------------------------------------------

    values = df[storage_column]

    print("\nRaw Storage Location value counts:")

    print(
        values
        .value_counts(dropna=False)
        .head(20)
    )

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    missing = values.isna()

    print(
        f"\nNaN / missing values: "
        f"{missing.sum()}"
    )

    # --------------------------------------------------------
    # String empty values
    # --------------------------------------------------------

    string_values = (
        values
        .fillna("")
        .astype(str)
        .str.strip()
    )

    empty = string_values == ""

    print(
        f"Empty string values: "
        f"{empty.sum()}"
    )

    # --------------------------------------------------------
    # Zero values
    # --------------------------------------------------------

    zero = string_values == "0"

    print(
        f"String '0' values: "
        f"{zero.sum()}"
    )

    # --------------------------------------------------------
    # Other values
    # --------------------------------------------------------

    non_empty = string_values[
        (string_values != "")
        & (string_values != "0")
    ]

    print(
        f"Non-empty/non-zero values: "
        f"{len(non_empty)}"
    )

    print("\nMost common non-empty Storage Locations:")

    print(
        non_empty
        .value_counts()
        .head(20)
    )

    # --------------------------------------------------------
    # Concatenate
    # --------------------------------------------------------

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

    if concatenate_column:

        concatenate = (
            df[concatenate_column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        print(
            f"\nConcatenate column: "
            f"{repr(concatenate_column)}"
        )

        print(
            f"Unique Concatenate values: "
            f"{concatenate.nunique()}"
        )

        print(
            f"Duplicate Concatenate rows: "
            f"{concatenate.duplicated().sum()}"
        )

        print("\nFirst 10 Concatenate values:")

        for value in concatenate.head(10):
            print(
                f"  {repr(value)}"
            )


def main():

    print("=" * 70)
    print("BSP SAP STORAGE LOCATION INVESTIGATION")
    print("=" * 70)

    for label, file_path in FILES.items():

        if not file_path.exists():

            print(
                f"\nFile not found:\n{file_path}"
            )

            continue

        inspect_file(
            label,
            file_path,
        )

    print("\n" + "=" * 70)
    print("INVESTIGATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()