"""
Real BSP Classification Validation Test

Purpose
-------
Validate our Python RI / Capital classification against the
employee's actual final Inventory workbook.

IMPORTANT:
- RI sheet is a headerless one-column list of material codes.
- Capital sheet is a headerless one-column list of material codes.
- Inventory sheet has a descriptive first row, so header=1 is required.
- RI and Capital are validated independently, matching the employee's
  two separate VLOOKUP operations.

This test validates PROCESS CORRECTNESS.
It does NOT expect July/August inventory data to match row-for-row.
"""

from pathlib import Path
import sys

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

# test_real_bsp_classification.py
#   -> backends/
#       -> SapAi/
#
# parents[1] = SapAi

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"

FINAL_WORKBOOK = (
    DATA_DIR
    / "samples"
    / "Final output file.xlsx"
)


# ============================================================
# IMPORT PRODUCTION CLASSIFIER
# ============================================================

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.inventory_classifier import (
    normalize_material_code,
)


# ============================================================
# HELPERS
# ============================================================

def normalize_code(value) -> str:
    """
    Use the same material-code normalization as the
    production classifier.
    """
    return normalize_material_code(value)


def load_headerless_code_list(
    workbook: Path,
    sheet_name: str,
) -> set[str]:
    """
    RI and Capital in the employee workbook are raw
    one-column material-code lists with NO header.
    """

    df = pd.read_excel(
        workbook,
        sheet_name=sheet_name,
        header=None,
    )

    if df.empty:
        return set()

    codes = {
        normalize_code(value)
        for value in df.iloc[:, 0]
    }

    codes.discard("")

    return codes


def load_employee_inventory(
    workbook: Path,
) -> pd.DataFrame:
    """
    Employee Inventory sheet has a title row above
    the actual column headers.
    """

    df = pd.read_excel(
        workbook,
        sheet_name="Inventory",
        header=1,
    )

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    required_columns = {
        "Material Code",
        "RI Ind",
        "Capital Ind",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Employee Inventory sheet is missing "
            f"required columns: {sorted(missing)}\n"
            f"Available columns: {list(df.columns)}"
        )

    return df


def normalize_employee_flag(value) -> str:

    if pd.isna(value):
        return "No"

    text = str(value).strip().lower()

    if text in {
        "yes",
        "y",
        "true",
        "1",
    }:
        return "Yes"

    if text in {
        "no",
        "n",
        "false",
        "0",
        "",
    }:
        return "No"

    return str(value).strip()


# ============================================================
# RI VALIDATION
# ============================================================

def validate_ri(
    inventory_df: pd.DataFrame,
    ri_codes: set[str],
) -> dict:

    mismatches = []

    for index, row in inventory_df.iterrows():

        material_code = normalize_code(
            row["Material Code"]
        )

        employee_flag = normalize_employee_flag(
            row["RI Ind"]
        )

        expected_flag = (
            "Yes"
            if material_code in ri_codes
            else "No"
        )

        if employee_flag != expected_flag:

            mismatches.append(
                {
                    "Excel_Row": index + 2,
                    "Material_Code": material_code,
                    "Employee_RI_Ind": employee_flag,
                    "Expected_RI_Ind": expected_flag,
                }
            )

    return {
        "total_rows": len(inventory_df),
        "employee_yes": sum(
            normalize_employee_flag(value) == "Yes"
            for value in inventory_df["RI Ind"]
        ),
        "expected_yes": sum(
            normalize_code(value) in ri_codes
            for value in inventory_df["Material Code"]
        ),
        "mismatches": mismatches,
    }


# ============================================================
# CAPITAL VALIDATION
# ============================================================

def validate_capital(
    inventory_df: pd.DataFrame,
    capital_codes: set[str],
) -> dict:

    mismatches = []

    for index, row in inventory_df.iterrows():

        material_code = normalize_code(
            row["Material Code"]
        )

        employee_flag = normalize_employee_flag(
            row["Capital Ind"]
        )

        expected_flag = (
            "Yes"
            if material_code in capital_codes
            else "No"
        )

        if employee_flag != expected_flag:

            mismatches.append(
                {
                    "Excel_Row": index + 2,
                    "Material_Code": material_code,
                    "Employee_Capital_Ind": employee_flag,
                    "Expected_Capital_Ind": expected_flag,
                }
            )

    return {
        "total_rows": len(inventory_df),
        "employee_yes": sum(
            normalize_employee_flag(value) == "Yes"
            for value in inventory_df["Capital Ind"]
        ),
        "expected_yes": sum(
            normalize_code(value) in capital_codes
            for value in inventory_df["Material Code"]
        ),
        "mismatches": mismatches,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("REAL BSP RI / CAPITAL CLASSIFICATION VALIDATION")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # 1. Workbook
    # --------------------------------------------------------

    print("1. Checking employee workbook...")

    print(
        f"Employee workbook:\n"
        f"{FINAL_WORKBOOK}"
    )

    if not FINAL_WORKBOOK.exists():

        raise FileNotFoundError(
            f"\nEmployee workbook not found:\n"
            f"{FINAL_WORKBOOK}\n\n"
            "Make sure this file exists:\n"
            "data\\samples\\Final output file.xlsx"
        )

    print("PASS: Workbook found.")
    print()

    # --------------------------------------------------------
    # 2. RI
    # --------------------------------------------------------

    print("2. Reading RI sheet...")

    ri_codes = load_headerless_code_list(
        FINAL_WORKBOOK,
        "RI",
    )

    print(
        f"RI material codes loaded: "
        f"{len(ri_codes):,}"
    )

    if not ri_codes:
        raise ValueError(
            "RI sheet contains no material codes."
        )

    print(
        "PASS: RI loaded as a "
        "headerless one-column list."
    )
    print()

    # --------------------------------------------------------
    # 3. Capital
    # --------------------------------------------------------

    print("3. Reading Capital sheet...")

    capital_codes = load_headerless_code_list(
        FINAL_WORKBOOK,
        "Capital",
    )

    print(
        f"Capital material codes loaded: "
        f"{len(capital_codes):,}"
    )

    if not capital_codes:
        raise ValueError(
            "Capital sheet contains no material codes."
        )

    print(
        "PASS: Capital loaded as a "
        "headerless one-column list."
    )
    print()

    # --------------------------------------------------------
    # 4. Employee Inventory
    # --------------------------------------------------------

    print("4. Reading employee Inventory sheet...")

    inventory_df = load_employee_inventory(
        FINAL_WORKBOOK
    )

    print(
        f"Inventory rows loaded: "
        f"{len(inventory_df):,}"
    )

    print("PASS: Employee Inventory loaded.")
    print()

    # --------------------------------------------------------
    # 5. RI
    # --------------------------------------------------------

    print("5. Validating RI classification...")
    print()

    ri_result = validate_ri(
        inventory_df,
        ri_codes,
    )

    print(
        f"Employee RI = Yes : "
        f"{ri_result['employee_yes']:,}"
    )

    print(
        f"Expected RI = Yes : "
        f"{ri_result['expected_yes']:,}"
    )

    print(
        f"RI mismatches     : "
        f"{len(ri_result['mismatches']):,}"
    )

    if ri_result["mismatches"]:

        print()
        print("RI VALIDATION FAILED.")
        print("First 20 mismatches:")

        for mismatch in ri_result["mismatches"][:20]:
            print(mismatch)

    else:

        print(
            "PASS: RI classification matches "
            "employee data."
        )

    print()

    # --------------------------------------------------------
    # 6. Capital
    # --------------------------------------------------------

    print("6. Validating Capital classification...")
    print()

    capital_result = validate_capital(
        inventory_df,
        capital_codes,
    )

    print(
        f"Employee Capital = Yes : "
        f"{capital_result['employee_yes']:,}"
    )

    print(
        f"Expected Capital = Yes : "
        f"{capital_result['expected_yes']:,}"
    )

    print(
        f"Capital mismatches     : "
        f"{len(capital_result['mismatches']):,}"
    )

    if capital_result["mismatches"]:

        print()
        print("CAPITAL VALIDATION FAILED.")
        print("First 20 mismatches:")

        for mismatch in capital_result["mismatches"][:20]:
            print(mismatch)

    else:

        print(
            "PASS: Capital classification matches "
            "employee data."
        )

    print()

    # --------------------------------------------------------
    # 7. Final
    # --------------------------------------------------------

    ri_passed = (
        len(ri_result["mismatches"]) == 0
    )

    capital_passed = (
        len(capital_result["mismatches"]) == 0
    )

    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    if ri_passed and capital_passed:

        print()
        print(
            "ALL REAL BSP CLASSIFICATION TESTS PASSED"
        )
        print()
        print("RI classification      : PASS")
        print("Capital classification : PASS")
        print()
        print(
            "The Python classification matches "
            "the employee's RI and Capital "
            "VLOOKUP results."
        )

        return 0

    print()
    print(
        "REAL BSP CLASSIFICATION TEST FAILED"
    )
    print()

    if not ri_passed:
        print(
            f"RI mismatches: "
            f"{len(ri_result['mismatches'])}"
        )

    if not capital_passed:
        print(
            f"Capital mismatches: "
            f"{len(capital_result['mismatches'])}"
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())