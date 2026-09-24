from pathlib import Path
import sys
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
REPORT_DIR = DATA_DIR / "reports"

AUGUST_FILE = (
    SAMPLES_DIR
    / "Inventory Previous 25.08.xlsx"
)

AUGUST_AUTOMATED_FILE = (
    REPORT_DIR
    / "automated_august_sheet2_test.xlsx"
)

DIFFERENCE_FILE = (
    REPORT_DIR
    / "august_sheet2_differences.xlsx"
)


# ============================================================
# IMPORT THE VERIFIED CLEANER
# ============================================================

CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from test_mc1_cleaning import create_clean_sheet2


# ============================================================
# NORMALIZATION FOR COMPARISON
# ============================================================

def normalize_value(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_dataframe(df):

    df = df.copy()

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    for column in df.columns:

        df[column] = (
            df[column]
            .apply(normalize_value)
        )

    return df


# ============================================================
# LOAD EMPLOYEE SHEET 2
# ============================================================

def load_employee_sheet2():

    df = pd.read_excel(
        AUGUST_FILE,
        sheet_name="Sheet2",
    )

    return normalize_dataframe(df)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("AUGUST MC.1 SHEET 1 -> SHEET 2 VALIDATION")
    print("=" * 70)

    # ========================================================
    # CHECK FILE
    # ========================================================

    if not AUGUST_FILE.exists():

        raise FileNotFoundError(
            f"August file not found:\n{AUGUST_FILE}"
        )

    # ========================================================
    # RUN VERIFIED CLEANER
    # ========================================================

    print("\nRunning Python cleaner on August Sheet 1...")

    automated_df = create_clean_sheet2(
        AUGUST_FILE
    )

    print(
        f"\nAutomated August rows: "
        f"{len(automated_df)}"
    )

    print(
        f"Automated August columns: "
        f"{len(automated_df.columns)}"
    )

    # ========================================================
    # SAVE AUTOMATED SHEET 2
    # ========================================================

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    automated_df.to_excel(
        AUGUST_AUTOMATED_FILE,
        sheet_name="Sheet2",
        index=False,
    )

    print(
        f"\nAutomated Sheet 2 saved to:"
    )

    print(
        AUGUST_AUTOMATED_FILE
    )

    # ========================================================
    # LOAD EMPLOYEE SHEET 2
    # ========================================================

    print(
        "\nLoading employee's August Sheet 2..."
    )

    employee_df = load_employee_sheet2()

    print(
        f"Employee August rows: "
        f"{len(employee_df)}"
    )

    print(
        f"Employee August columns: "
        f"{len(employee_df.columns)}"
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

    print("\nEmployee columns:")

    for column in employee_columns:
        print(f"  {column}")

    print("\nAutomated columns:")

    for column in automated_columns:
        print(f"  {column}")

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

    print(
        f"\nMissing automated columns: "
        f"{len(missing_columns)}"
    )

    print(
        f"Extra automated columns: "
        f"{len(extra_columns)}"
    )

    # ========================================================
    # KEY COMPARISON
    # ========================================================

    print("\n" + "=" * 70)
    print("CONCATENATE KEY COMPARISON")
    print("=" * 70)

    key_column = "Concatenate"

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

    difference_records = []

    for key in common_keys:

        employee_row = employee_common.loc[key]

        automated_row = automated_common.loc[key]

        for column in common_columns:

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

    print(
        f"\nTotal cell differences: "
        f"{len(differences_df)}"
    )

    # ========================================================
    # SAVE DIFFERENCES
    # ========================================================

    if not differences_df.empty:

        differences_df.to_excel(
            DIFFERENCE_FILE,
            index=False,
        )

        print(
            f"\nDifferences saved to:"
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
    # FINAL RESULT
    # ========================================================

    print("\n" + "=" * 70)
    print("AUGUST VALIDATION RESULT")
    print("=" * 70)

    if (
        len(employee_only_keys) == 0
        and len(automated_only_keys) == 0
        and len(differences_df) == 0
        and employee_columns == automated_columns
        and len(employee_df) == len(automated_df)
    ):

        print(
            "\nSUCCESS!"
        )

        print(
            "Employee August Sheet 2 and "
            "Automated August Sheet 2 are identical."
        )

        print("\n" + "=" * 70)
        print("STEP 3 TEST PASSED")
        print("=" * 70)

    else:

        print(
            "\nDIFFERENCES FOUND."
        )

        print(
            "Do NOT modify the main builder yet."
        )

        print(
            "We need to investigate the August "
            "differences first."
        )

        print("\n" + "=" * 70)
        print("STEP 3 REQUIRES INVESTIGATION")
        print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()