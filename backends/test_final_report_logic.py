from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
REPORT_DIR = DATA_DIR / "reports"

JULY_FILE = SAMPLES_DIR / "Inventory Previous 07(month).xlsx"
AUGUST_FILE = SAMPLES_DIR / "Inventory Previous 25.08.xlsx"

FINAL_FILE = SAMPLES_DIR / "Final output file.xlsx"

OUTPUT_FILE = REPORT_DIR / "step4_final_report_investigation.xlsx"


# ============================================================
# BASIC NORMALIZATION
# ============================================================

def normalize_value(value):
    """
    Convert Excel values into a predictable string.

    Blank cells become "".
    """
    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_dataframe(df):
    """
    Normalize column names and cell values.
    """

    df = df.copy()

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    for column in df.columns:
        df[column] = df[column].apply(
            normalize_value
        )

    return df


# ============================================================
# LOAD MONTHLY SHEET 2
# ============================================================

def load_month_sheet2(file_path):
    """
    Load Sheet 2 from July or August workbook.
    """

    df = pd.read_excel(
        file_path,
        sheet_name="Sheet2"
    )

    df = normalize_dataframe(df)

    required_columns = [
        "Concatenate",
        "Mat Grp",
        "Mat Grp Desc",
        "Material Code",
        "Material Code Desc",
        "Storage Location",
        "Storage Location Desc",
        "Plant",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{file_path.name} Sheet2 is missing:\n"
            f"{missing}\n\n"
            f"Actual columns:\n{list(df.columns)}"
        )

    return df


# ============================================================
# FIND HEADER ROW IN FINAL WORKBOOK
# ============================================================

def find_header_row(
    file_path,
    sheet_name,
    required_header="Material Code",
    max_rows_to_check=10,
):
    """
    Find the row containing the actual header.

    We do NOT assume header=0 or header=1.

    This is important because Final output file.xlsx
    may contain descriptive rows before the actual header.
    """

    preview = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=None,
        nrows=max_rows_to_check,
    )

    for row_number in range(
        len(preview)
    ):

        row_values = [
            normalize_value(value)
            for value in preview.iloc[row_number]
        ]

        if required_header in row_values:
            return row_number

    raise ValueError(
        f"Could not find '{required_header}' "
        f"in first {max_rows_to_check} rows of "
        f"{sheet_name}."
    )


# ============================================================
# LOAD FINAL WORKBOOK SHEET
# ============================================================

def load_final_sheet(sheet_name):
    """
    Load a sheet from Final output file.xlsx.

    Automatically detects the header row and normalizes
    known column-name differences.
    """

    header_row = find_header_row(
        FINAL_FILE,
        sheet_name
    )

    print(
        f"\n{sheet_name}: detected header row "
        f"{header_row}"
    )

    df = pd.read_excel(
        FINAL_FILE,
        sheet_name=sheet_name,
        header=header_row
    )

    df = normalize_dataframe(df)

    # Normalize known header variations
    rename_map = {}

    for column in df.columns:

        normalized = str(column).strip().lower()

        if normalized == "storage location":
            rename_map[column] = "Storage Location"

        elif normalized == "material code":
            rename_map[column] = "Material Code"

        elif normalized == "material code desc":
            rename_map[column] = "Material Code Desc"

        elif normalized == "matrial code desc":
            rename_map[column] = "Material Code Desc"

        elif normalized == "mat grp":
            rename_map[column] = "Mat Grp"

        elif normalized == "mat grp desc":
            rename_map[column] = "Mat Grp Desc"

        elif normalized == "plant":
            rename_map[column] = "Plant"

    df = df.rename(
        columns=rename_map
    )

    return df

# ============================================================
# CANONICAL KEY
# ============================================================

def make_key(
    material_code,
    storage_location,
    plant
):
    """
    Canonical inventory key.

    Material Code | Storage Location | Plant
    """

    material_code = normalize_value(
        material_code
    )

    storage_location = normalize_value(
        storage_location
    )

    plant = normalize_value(
        plant
    )

    return (
        material_code
        + "|"
        + storage_location
        + "|"
        + plant
    )


# ============================================================
# ADD CANONICAL KEY
# ============================================================

def add_key(df):
    """
    Add canonical inventory key.
    """

    df = df.copy()

    required = [
        "Material Code",
        "Storage Location",
        "Plant",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Cannot create inventory key.\n"
            f"Missing columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    df["_Key"] = [
        make_key(
            material_code,
            storage_location,
            plant
        )
        for material_code,
        storage_location,
        plant
        in zip(
            df["Material Code"],
            df["Storage Location"],
            df["Plant"]
        )
    ]

    return df


# ============================================================
# KEY ANALYSIS
# ============================================================

def compare_keys(
    name_a,
    df_a,
    name_b,
    df_b
):
    """
    Compare two datasets by canonical inventory key.
    """

    keys_a = set(
        df_a["_Key"]
    )

    keys_b = set(
        df_b["_Key"]
    )

    common = keys_a & keys_b
    only_a = keys_a - keys_b
    only_b = keys_b - keys_a

    print("\n" + "=" * 70)
    print(
        f"{name_a} VS {name_b}"
    )
    print("=" * 70)

    print(
        f"\n{name_a} rows: "
        f"{len(df_a)}"
    )

    print(
        f"{name_b} rows: "
        f"{len(df_b)}"
    )

    print(
        f"\n{name_a} unique keys: "
        f"{len(keys_a)}"
    )

    print(
        f"{name_b} unique keys: "
        f"{len(keys_b)}"
    )

    print(
        f"Common keys: "
        f"{len(common)}"
    )

    print(
        f"{name_a} only: "
        f"{len(only_a)}"
    )

    print(
        f"{name_b} only: "
        f"{len(only_b)}"
    )

    return {
        "a_rows": len(df_a),
        "b_rows": len(df_b),
        "a_keys": len(keys_a),
        "b_keys": len(keys_b),
        "common": len(common),
        "only_a": len(only_a),
        "only_b": len(only_b),
        "common_keys": common,
        "only_a_keys": only_a,
        "only_b_keys": only_b,
    }


# ============================================================
# EXTRACT DIFFERENCE RECORDS
# ============================================================

def get_difference_records(
    df,
    keys,
):
    """
    Return records whose canonical keys
    belong to the supplied set.
    """

    return df[
        df["_Key"].isin(keys)
    ].copy()


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("STEP 4 - FINAL REPORT LOGIC INVESTIGATION")
    print("=" * 70)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # 1. LOAD JULY
    # ========================================================

    print("\n" + "=" * 70)
    print("LOADING JULY SHEET 2")
    print("=" * 70)

    july = load_month_sheet2(
        JULY_FILE
    )

    print(
        f"July Sheet 2 rows: "
        f"{len(july)}"
    )

    july = add_key(july)

    # ========================================================
    # 2. LOAD AUGUST
    # ========================================================

    print("\n" + "=" * 70)
    print("LOADING AUGUST SHEET 2")
    print("=" * 70)

    august = load_month_sheet2(
        AUGUST_FILE
    )

    print(
        f"August Sheet 2 rows: "
        f"{len(august)}"
    )

    august = add_key(august)

    # ========================================================
    # 3. LOAD FINAL INVENTORY PREV
    # ========================================================

    print("\n" + "=" * 70)
    print("LOADING FINAL INVENTORY PREV")
    print("=" * 70)

    inventory_prev = load_final_sheet(
        "Inventory Prev"
    )

    print(
        f"Inventory Prev rows: "
        f"{len(inventory_prev)}"
    )

    inventory_prev = add_key(
        inventory_prev
    )

    # ========================================================
    # 4. LOAD FINAL INVENTORY PRES
    # ========================================================

    print("\n" + "=" * 70)
    print("LOADING FINAL INVENTORY PRES")
    print("=" * 70)

    inventory_pres = load_final_sheet(
        "Inventory Pres"
    )

    print(
        f"Inventory Pres rows: "
        f"{len(inventory_pres)}"
    )

    inventory_pres = add_key(
        inventory_pres
    )

    # ========================================================
    # 5. LOAD FINAL INVENTORY
    # ========================================================

    print("\n" + "=" * 70)
    print("LOADING FINAL INVENTORY")
    print("=" * 70)

    inventory = load_final_sheet(
        "Inventory"
    )

    print(
        f"Inventory rows: "
        f"{len(inventory)}"
    )

    inventory = add_key(
        inventory
    )

    # ========================================================
    # 6. JULY VS INVENTORY PREV
    # ========================================================

    july_result = compare_keys(
        "July Sheet 2",
        july,
        "Inventory Prev",
        inventory_prev
    )

    # ========================================================
    # 7. AUGUST VS INVENTORY PRES
    # ========================================================

    august_result = compare_keys(
        "August Sheet 2",
        august,
        "Inventory Pres",
        inventory_pres
    )

    # ========================================================
    # 8. JULY VS AUGUST
    # ========================================================

    monthly_result = compare_keys(
        "July Sheet 2",
        july,
        "August Sheet 2",
        august
    )

    # ========================================================
    # 9. BUILD UNION OF JULY + AUGUST
    # ========================================================

    print("\n" + "=" * 70)
    print("JULY + AUGUST UNION")
    print("=" * 70)

    july_keys = set(
        july["_Key"]
    )

    august_keys = set(
        august["_Key"]
    )

    union_keys = (
        july_keys
        |
        august_keys
    )

    intersection_keys = (
        july_keys
        &
        august_keys
    )

    print(
        f"\nJuly unique keys: "
        f"{len(july_keys)}"
    )

    print(
        f"August unique keys: "
        f"{len(august_keys)}"
    )

    print(
        f"Keys present in BOTH months: "
        f"{len(intersection_keys)}"
    )

    print(
        f"Total unique July + August keys: "
        f"{len(union_keys)}"
    )

    # ========================================================
    # 10. UNION VS FINAL INVENTORY
    # ========================================================

    union_only = (
        union_keys
        -
        set(inventory["_Key"])
    )

    inventory_only = (
        set(inventory["_Key"])
        -
        union_keys
    )

    common_final = (
        union_keys
        &
        set(inventory["_Key"])
    )

    print("\n" + "=" * 70)
    print("JULY + AUGUST VS FINAL INVENTORY")
    print("=" * 70)

    print(
        f"\nJuly + August unique keys: "
        f"{len(union_keys)}"
    )

    print(
        f"Final Inventory unique keys: "
        f"{len(set(inventory['_Key']))}"
    )

    print(
        f"Common keys: "
        f"{len(common_final)}"
    )

    print(
        f"July/August keys NOT in Final Inventory: "
        f"{len(union_only)}"
    )

    print(
        f"Final Inventory keys NOT in July/August: "
        f"{len(inventory_only)}"
    )

    # ========================================================
    # 11. DISPLAY FINAL INVENTORY-ONLY RECORDS
    # ========================================================

    final_only_records = inventory[
        inventory["_Key"].isin(
            inventory_only
        )
    ].copy()

    print("\n" + "=" * 70)
    print("RECORDS IN FINAL INVENTORY BUT NOT IN JULY/AUGUST")
    print("=" * 70)

    print(
        f"\nRows: "
        f"{len(final_only_records)}"
    )

    if not final_only_records.empty:

        display_columns = [
            "Mat Grp",
            "Mat Grp Desc",
            "Material Code",
            "Matrial Code Desc",
            "Material Code Desc",
            "Storage Location",
            "Storage Location Desc",
            "Plant",
            "Inve Prev Quantity",
            "Inve Prev Value",
            "Inve Pres Quantity",
            "Inve Pres Value",
            "UOM",
            "RI Ind",
            "Capital Ind",
            "_Key",
        ]

        display_columns = [
            column
            for column in display_columns
            if column in final_only_records.columns
        ]

        print(
            final_only_records[
                display_columns
            ].head(50).to_string(
                index=False
            )
        )

    # ========================================================
    # 12. JULY-ONLY RECORDS
    # ========================================================

    july_only_records = july[
        july["_Key"].isin(
            july_result["only_a_keys"]
        )
    ].copy()

    print("\n" + "=" * 70)
    print("JULY-ONLY RECORDS")
    print("=" * 70)

    print(
        f"\nJuly-only unique records: "
        f"{len(july_only_records)}"
    )

    # ========================================================
    # 13. AUGUST-ONLY RECORDS
    # ========================================================

    august_only_records = august[
        august["_Key"].isin(
            august_result["only_a_keys"]
        )
    ].copy()

    print("\n" + "=" * 70)
    print("AUGUST-ONLY RECORDS")
    print("=" * 70)

    print(
        f"\nAugust-only unique records: "
        f"{len(august_only_records)}"
    )

    # ========================================================
    # 14. RI / CAPITAL ANALYSIS
    # ========================================================

    print("\n" + "=" * 70)
    print("RI / CAPITAL COLUMNS")
    print("=" * 70)

    print(
        "\nFinal Inventory columns:"
    )

    for column in inventory.columns:
        print(
            f"  {column}"
        )

    if "RI Ind" in inventory.columns:

        print("\nRI Ind values:")

        print(
            inventory[
                "RI Ind"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    if "Capital Ind" in inventory.columns:

        print("\nCapital Ind values:")

        print(
            inventory[
                "Capital Ind"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    # ========================================================
    # 15. SAVE INVESTIGATION REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("SAVING INVESTIGATION REPORT")
    print("=" * 70)

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:

        july.to_excel(
            writer,
            sheet_name="July_Sheet2",
            index=False
        )

        august.to_excel(
            writer,
            sheet_name="August_Sheet2",
            index=False
        )

        inventory_prev.to_excel(
            writer,
            sheet_name="Inventory_Prev",
            index=False
        )

        inventory_pres.to_excel(
            writer,
            sheet_name="Inventory_Pres",
            index=False
        )

        inventory.to_excel(
            writer,
            sheet_name="Final_Inventory",
            index=False
        )

        final_only_records.to_excel(
            writer,
            sheet_name="Final_Only",
            index=False
        )

        july_only_records.to_excel(
            writer,
            sheet_name="July_Only",
            index=False
        )

        august_only_records.to_excel(
            writer,
            sheet_name="August_Only",
            index=False
        )

    print(
        f"\nInvestigation report saved to:\n"
        f"{OUTPUT_FILE}"
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("STEP 4 INVESTIGATION SUMMARY")
    print("=" * 70)

    print(
        f"\nJuly Sheet 2: "
        f"{len(july)} rows"
    )

    print(
        f"August Sheet 2: "
        f"{len(august)} rows"
    )

    print(
        f"July + August unique keys: "
        f"{len(union_keys)}"
    )

    print(
        f"Final Inventory: "
        f"{len(inventory)} rows"
    )

    print(
        f"Final Inventory unique keys: "
        f"{len(set(inventory['_Key']))}"
    )

    print(
        f"Final Inventory extra keys: "
        f"{len(inventory_only)}"
    )

    print(
        f"July/August missing from Final Inventory: "
        f"{len(union_only)}"
    )

    print("\n" + "=" * 70)
    print("STEP 4A COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()