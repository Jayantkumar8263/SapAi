from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
REPORT_DIR = DATA_DIR / "reports"

# Original employee workbook
ORIGINAL_FILE = (
    SAMPLES_DIR
    / "Inventory Previous 07(month).xlsx"
)

# Our Python-generated Sheet 2
AUTOMATED_FILE = (
    REPORT_DIR
    / "automated_sheet2_test.xlsx"
)

# File where differences will be saved
DIFFERENCE_FILE = (
    REPORT_DIR
    / "sheet2_differences.xlsx"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_value(value):
    """
    Normalize values for comparison.

    This is ONLY for the comparison test.
    It does not modify the actual cleaning process.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_dataframe(df):
    """
    Normalize column names and cell values
    for comparison.
    """

    df = df.copy()

    # Normalize column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Normalize values
    for column in df.columns:

        df[column] = (
            df[column]
            .apply(normalize_value)
        )

    return df


# ============================================================
# LOAD SHEET 2
# ============================================================

def load_sheet2(file_path, sheet_name):
    """
    Load and normalize Sheet 2.
    """

    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
    )

    return normalize_dataframe(df)


# ============================================================
# MAIN COMPARISON
# ============================================================

def main():

    print("=" * 70)
    print("EMPLOYEE SHEET 2 vs AUTOMATED SHEET 2")
    print("=" * 70)

    # ========================================================
    # CHECK FILES
    # ========================================================

    if not ORIGINAL_FILE.exists():

        raise FileNotFoundError(
            f"Original workbook not found:\n"
            f"{ORIGINAL_FILE}"
        )

    if not AUTOMATED_FILE.exists():

        raise FileNotFoundError(
            f"Automated Sheet 2 not found:\n"
            f"{AUTOMATED_FILE}"
        )

    # ========================================================
    # LOAD FILES
    # ========================================================

    print("\nLoading employee's Sheet 2...")

    employee_df = load_sheet2(
        ORIGINAL_FILE,
        "Sheet2",
    )

    print("Loading automated Sheet 2...")

    automated_df = load_sheet2(
        AUTOMATED_FILE,
        "Sheet2",
    )

    # ========================================================
    # BASIC COMPARISON
    # ========================================================

    print("\n" + "=" * 70)
    print("BASIC COMPARISON")
    print("=" * 70)

    print(
        f"\nEmployee Sheet 2 rows: "
        f"{len(employee_df)}"
    )

    print(
        f"Automated Sheet 2 rows: "
        f"{len(automated_df)}"
    )

    print(
        f"\nEmployee Sheet 2 columns: "
        f"{len(employee_df.columns)}"
    )

    print(
        f"Automated Sheet 2 columns: "
        f"{len(automated_df.columns)}"
    )

    # ========================================================
    # COLUMN COMPARISON
    # ========================================================

    print("\n" + "=" * 70)
    print("COLUMN COMPARISON")
    print("=" * 70)

    employee_columns = list(
        employee_df.columns
    )

    automated_columns = list(
        automated_df.columns
    )

    missing_columns = [
        column
        for column in employee_columns
        if column not in automated_columns
    ]

    extra_columns = [
        column
        for column in automated_columns
        if column not in employee_columns
    ]

    print("\nEmployee columns:")

    for column in employee_columns:
        print(f"  {column}")

    print("\nAutomated columns:")

    for column in automated_columns:
        print(f"  {column}")

    print(
        f"\nMissing automated columns: "
        f"{len(missing_columns)}"
    )

    print(
        f"Extra automated columns: "
        f"{len(extra_columns)}"
    )

    if missing_columns:

        print("\nMissing columns:")

        for column in missing_columns:
            print(f"  {column}")

    if extra_columns:

        print("\nExtra columns:")

        for column in extra_columns:
            print(f"  {column}")

    # ========================================================
    # CONCATENATE KEY COMPARISON
    # ========================================================

    print("\n" + "=" * 70)
    print("CONCATENATE KEY COMPARISON")
    print("=" * 70)

    key_column = "Concatenate"

    if key_column not in employee_df.columns:

        raise ValueError(
            "Employee Sheet 2 does not contain "
            "'Concatenate'."
        )

    if key_column not in automated_df.columns:

        raise ValueError(
            "Automated Sheet 2 does not contain "
            "'Concatenate'."
        )

    employee_keys = set(
        employee_df[key_column]
    )

    automated_keys = set(
        automated_df[key_column]
    )

    common_keys = (
        employee_keys
        & automated_keys
    )

    employee_only_keys = (
        employee_keys
        - automated_keys
    )

    automated_only_keys = (
        automated_keys
        - employee_keys
    )

    print(
        f"\nEmployee unique keys: "
        f"{len(employee_keys)}"
    )

    print(
        f"Automated unique keys: "
        f"{len(automated_keys)}"
    )

    print(
        f"Common keys: "
        f"{len(common_keys)}"
    )

    print(
        f"Employee-only keys: "
        f"{len(employee_only_keys)}"
    )

    print(
        f"Automated-only keys: "
        f"{len(automated_only_keys)}"
    )

    # ========================================================
    # DATA COMPARISON
    # ========================================================

    print("\n" + "=" * 70)
    print("DATA COMPARISON")
    print("=" * 70)

    common_columns = [
        column
        for column in employee_columns
        if column in automated_columns
    ]

    # --------------------------------------------------------
    # Create indexed copies.
    #
    # IMPORTANT:
    # Concatenate becomes the index here.
    # Therefore we must NOT later access:
    #
    # row["Concatenate"]
    #
    # The key is available through:
    #
    # row.name
    # --------------------------------------------------------

    employee_common = (
        employee_df[
            employee_df[key_column].isin(
                common_keys
            )
        ]
        .set_index(key_column)
        .sort_index()
    )

    automated_common = (
        automated_df[
            automated_df[key_column].isin(
                common_keys
            )
        ]
        .set_index(key_column)
        .sort_index()
    )

    # --------------------------------------------------------
    # Compare every common record
    # --------------------------------------------------------

    difference_records = []

    for key in common_keys:

        employee_row = employee_common.loc[key]

        automated_row = automated_common.loc[key]

        for column in common_columns:

            # Concatenate is already the index.
            if column == key_column:
                continue

            employee_value = normalize_value(
                employee_row[column]
            )

            automated_value = normalize_value(
                automated_row[column]
            )

            if employee_value != automated_value:

                difference_records.append(
                    {
                        "Concatenate": key,
                        "Column": column,
                        "Employee_Value": employee_value,
                        "Automated_Value": automated_value,
                    }
                )

    differences_df = pd.DataFrame(
        difference_records
    )

    # ========================================================
    # DIFFERENCE RESULTS
    # ========================================================

    print(
        f"\nTotal cell differences: "
        f"{len(differences_df)}"
    )

    if not differences_df.empty:

        differences_df.to_excel(
            DIFFERENCE_FILE,
            index=False,
        )

        print(
            "\nDifferences saved to:"
        )

        print(
            DIFFERENCE_FILE
        )

        print(
            "\nFirst 20 differences:"
        )

        print(
            differences_df
            .head(20)
            .to_string(index=False)
        )

    else:

        print(
            "\nNO CELL DIFFERENCES FOUND."
        )

    # ========================================================
    # SAMPLE RECORD COMPARISON
    # ========================================================

    print("\n" + "=" * 70)
    print("SAMPLE RECORD COMPARISON")
    print("=" * 70)

    # --------------------------------------------------------
    # Only compare samples if common keys exist.
    # --------------------------------------------------------

    sample_keys = sorted(
        common_keys
    )[:5]

    for key in sample_keys:

        print(
            f"\nConcatenate: {key}"
        )

        employee_row = (
            employee_common.loc[key]
        )

        automated_row = (
            automated_common.loc[key]
        )

        for column in common_columns:

            # Concatenate is the index,
            # so don't try to access it as a column.
            if column == key_column:
                continue

            print(
                f"  {column}:"
            )

            print(
                f"    Employee : "
                f"{employee_row[column]}"
            )

            print(
                f"    Automated: "
                f"{automated_row[column]}"
            )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print("\n" + "=" * 70)
    print("COMPARISON RESULT")
    print("=" * 70)

    if (
        len(employee_only_keys) == 0
        and len(automated_only_keys) == 0
        and len(differences_df) == 0
        and employee_columns == automated_columns
    ):

        print(
            "\nSUCCESS!"
        )

        print(
            "Employee Sheet 2 and Automated "
            "Sheet 2 are identical."
        )

        print("\n" + "=" * 70)
        print("STEP 2 TEST PASSED")
        print("=" * 70)

    else:

        print(
            "\nDIFFERENCES FOUND."
        )

        print(
            "Do NOT modify the main builder yet."
        )

        print(
            "We need to investigate the differences "
            "before continuing."
        )

        print("\n" + "=" * 70)
        print("STEP 2 REQUIRES INVESTIGATION")
        print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()