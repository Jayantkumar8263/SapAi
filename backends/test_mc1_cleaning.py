from pathlib import Path
import re

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
REPORT_DIR = DATA_DIR / "reports"

INPUT_FILE = (
    SAMPLES_DIR
    / "Inventory Previous 07(month).xlsx"
)

OUTPUT_FILE = (
    REPORT_DIR
    / "automated_sheet2_test.xlsx"
)


# ============================================================
# TEXT CLEANING HELPERS
# ============================================================

def clean_raw_text(value):
    """
    Clean only the outside of a raw MC.1 field.

    IMPORTANT:
    We intentionally DO NOT collapse internal spaces here.

    The employee's Excel formulas use fixed character positions
    with MID(), so the original spacing must be preserved while
    extracting the fields.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def excel_trim(value):
    """
    Approximate Excel's TRIM() behavior for the extracted text.

    Excel TRIM:
    - removes leading spaces
    - removes trailing spaces
    - converts repeated normal spaces between words
      into a single space

    We deliberately do NOT use:
        " ".join(value.split())

    because split() also changes tabs and other whitespace,
    which could make the result different from Excel.
    """

    if pd.isna(value):
        return ""

    text = str(value).strip()

    # Collapse repeated NORMAL spaces only.
    text = re.sub(r" {2,}", " ", text)

    return text


# ============================================================
# RAW SHEET 1 -> CLEAN SHEET 2
# ============================================================

def create_clean_sheet2(input_file: Path) -> pd.DataFrame:

    print("\nReading RAW Sheet 1...")

    # --------------------------------------------------------
    # Read Sheet 1
    # --------------------------------------------------------

    df = pd.read_excel(
        input_file,
        sheet_name="Sheet1",
    )

    print(f"Raw rows: {len(df)}")
    print(f"Raw columns: {len(df.columns)}")

    print("\nRaw columns:")

    for column in df.columns:
        print(f"  {column}")

    # --------------------------------------------------------
    # Normalize column names ONLY
    #
    # We do not alter the actual cell contents here.
    # --------------------------------------------------------

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # --------------------------------------------------------
    # RAW MC.1 COLUMNS
    #
    # Actual structure from the July MC.1 export:
    #
    # Material Group
    # Material
    # Storage Location
    # Val. stock
    # ValStckVal
    # Val. stock.1
    #
    # Pandas automatically changes the duplicate Excel
    # "Val. stock" header to "Val. stock.1".
    # --------------------------------------------------------

    material_group_col = "Material Group"
    material_col = "Material"
    storage_location_col = "Storage Location"

    quantity_col = "Val. stock"
    value_col = "ValStckVal"
    uom_col = "Val. stock.1"

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    required_columns = [
        material_group_col,
        material_col,
        storage_location_col,
        quantity_col,
        value_col,
        uom_col,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "The following required columns were not found "
            "in the MC.1 export:\n"
            f"{missing_columns}\n\n"
            "Actual columns:\n"
            f"{list(df.columns)}"
        )

    # ========================================================
    # RAW TEXT
    #
    # IMPORTANT:
    # Preserve internal spaces at this stage.
    #
    # Why?
    #
    # Employee uses formulas such as:
    #
    # =MID(A2,1,3)
    # =MID(A2,5,LEN(A2))
    #
    # Therefore we must extract characters from the original
    # raw value BEFORE applying TRIM-like cleanup.
    # ========================================================

    material_group = (
        df[material_group_col]
        .apply(clean_raw_text)
    )

    material = (
        df[material_col]
        .apply(clean_raw_text)
    )

    storage_location = (
        df[storage_location_col]
        .apply(clean_raw_text)
    )

    # ========================================================
    # CREATE RESULT DATAFRAME
    # ========================================================

    result = pd.DataFrame()

    # ========================================================
    # MATERIAL GROUP
    # ========================================================
    #
    # Employee:
    #
    # Mat Grp
    # =MID(A2,1,3)
    #
    # Mat Grp Desc
    # =TRIM(MID(A2,5,LEN(A2)))
    #
    # Python:
    # 0:3  -> first 3 characters
    # 4:   -> characters after position 4
    # ========================================================

    result["Mat Grp"] = (
        material_group
        .str.slice(0, 3)
        .apply(excel_trim)
    )

    result["Mat Grp Desc"] = (
        material_group
        .str.slice(4)
        .apply(excel_trim)
    )

    # ========================================================
    # MATERIAL
    # ========================================================
    #
    # Employee:
    #
    # Material Code
    # =MID(C2,1,14)
    #
    # Material Code Desc
    # =TRIM(MID(C2,15,LEN(C2)))
    # ========================================================

    result["Material Code"] = (
        material
        .str.slice(0, 14)
        .apply(excel_trim)
    )

    result["Material Code Desc"] = (
        material
        .str.slice(14)
        .apply(excel_trim)
    )

    # ========================================================
    # STORAGE LOCATION
    # ========================================================
    #
    # Employee:
    #
    # Storage Location
    # =MID(E2,5,9)
    #
    # Storage Location Desc
    # =TRIM(MID(E2,9,LEN(E2)))
    #
    # IMPORTANT:
    # We slice the RAW string first.
    # Then we apply Excel-like TRIM.
    # ========================================================

    result["Storage Location"] = (
        storage_location
        .str.slice(4, 13)
        .apply(excel_trim)
    )

    result["Storage Location Desc"] = (
        storage_location
        .str.slice(8)
        .apply(excel_trim)
    )

    # ========================================================
    # PLANT
    # ========================================================
    #
    # Employee:
    #
    # Plant
    # =MID(E2,1,4)
    # ========================================================

    result["Plant"] = (
        storage_location
        .str.slice(0, 4)
        .apply(excel_trim)
    )

    # ========================================================
    # INVENTORY QUANTITY
    # ========================================================

    result["Inve Prev Quantity"] = (
        df[quantity_col]
    )

    # ========================================================
    # INVENTORY VALUE
    # ========================================================

    result["Inve Prev Value"] = (
        df[value_col]
    )

    # ========================================================
    # UOM
    # ========================================================

    result["UOM"] = (
        df[uom_col]
        .apply(clean_raw_text)
    )

    # ========================================================
    # CONCATENATE
    # ========================================================
    #
    # Employee:
    #
    # =CONCATENATE(
    #     Plant,
    #     Material Code,
    #     Storage Location
    # )
    #
    # Example:
    #
    # Plant          = 1000
    # Material Code  = 15111201000046
    # Storage Loc.   = UP03
    #
    # Result:
    #
    # 100015111201000046UP03
    # ========================================================

    result.insert(
        0,
        "Concatenate",
        (
            result["Plant"].astype(str)
            + result["Material Code"].astype(str)
            + result["Storage Location"].astype(str)
        ),
    )

    # ========================================================
    # FINAL SHEET 2 COLUMN ORDER
    # ========================================================

    result = result[
        [
            "Concatenate",
            "Mat Grp",
            "Mat Grp Desc",
            "Material Code",
            "Material Code Desc",
            "Storage Location",
            "Storage Location Desc",
            "Plant",
            "Inve Prev Quantity",
            "Inve Prev Value",
            "UOM",
        ]
    ]

    return result


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("=" * 70)
    print("MC.1 RAW SHEET 1 -> CLEAN SHEET 2 TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Check input file
    # --------------------------------------------------------

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Run cleaning
    # --------------------------------------------------------

    result = create_clean_sheet2(
        INPUT_FILE
    )

    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    print("\n" + "=" * 70)
    print("AUTOMATED SHEET 2")
    print("=" * 70)

    print(
        f"\nRows created: {len(result)}"
    )

    print(
        f"Columns created: {len(result.columns)}"
    )

    print("\nColumns:")

    for column in result.columns:
        print(f"  {column}")

    print("\nFirst 10 rows:")

    print(
        result.head(10).to_string(
            index=False
        )
    )

    # ========================================================
    # SAVE OUTPUT
    # ========================================================

    print("\nSaving automated Sheet 2...")

    result.to_excel(
        OUTPUT_FILE,
        sheet_name="Sheet2",
        index=False,
    )

    print(
        f"\nSaved to:\n{OUTPUT_FILE}"
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    expected_columns = [
        "Concatenate",
        "Mat Grp",
        "Mat Grp Desc",
        "Material Code",
        "Material Code Desc",
        "Storage Location",
        "Storage Location Desc",
        "Plant",
        "Inve Prev Quantity",
        "Inve Prev Value",
        "UOM",
    ]

    # --------------------------------------------------------
    # Check columns
    # --------------------------------------------------------

    if list(result.columns) != expected_columns:

        raise AssertionError(
            "Generated columns do not match "
            "the expected Sheet 2 structure."
        )

    # --------------------------------------------------------
    # Check rows
    # --------------------------------------------------------

    if len(result) == 0:

        raise AssertionError(
            "Generated Sheet 2 contains zero rows."
        )

    # --------------------------------------------------------
    # Check Material Code
    # --------------------------------------------------------

    if result["Material Code"].eq("").all():

        raise AssertionError(
            "Material Code column is empty."
        )

    # --------------------------------------------------------
    # Check Plant
    # --------------------------------------------------------

    if result["Plant"].eq("").all():

        raise AssertionError(
            "Plant column is empty."
        )

    # --------------------------------------------------------
    # Check Concatenate
    # --------------------------------------------------------

    if result["Concatenate"].eq("").all():

        raise AssertionError(
            "Concatenate column is empty."
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    print("\n" + "=" * 70)
    print("STEP 1 TEST PASSED")
    print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()