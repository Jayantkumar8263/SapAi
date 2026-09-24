from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
REPORT_DIR = DATA_DIR / "reports"

REFERENCE_FILE = SAMPLES_DIR / "Final output file.xlsx"

JULY_FILE = SAMPLES_DIR / "Inventory Previous 07(month).xlsx"
AUGUST_FILE = SAMPLES_DIR / "Inventory Previous 25.08.xlsx"

JULY_OUTPUT = REPORT_DIR / "sheet2_to_inventory_july_analysis.xlsx"
AUGUST_OUTPUT = REPORT_DIR / "sheet2_to_inventory_august_analysis.xlsx"


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_value(value):
    """
    Convert Excel values into a predictable string representation.
    Blank Excel cells become an empty string.
    """
    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_dataframe(df):
    """
    Normalize column names and cell values.
    """
    df = df.copy()

    # Normalize column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Normalize cell values
    for column in df.columns:
        df[column] = df[column].apply(normalize_value)

    return df


# ============================================================
# LOAD SHEET 2
# ============================================================

def load_sheet2(file_path):
    """
    Load employee Sheet 2 from the SAP-generated workbook.
    """

    df = pd.read_excel(
        file_path,
        sheet_name="Sheet2"
    )

    return normalize_dataframe(df)


# ============================================================
# LOAD INVENTORY SHEET
# ============================================================

def load_inventory_sheet(sheet_name):
    """
    Load Inventory Prev / Inventory Pres from the
    employee's final workbook.

    The Inventory sheets have a descriptive row above
    the actual header, therefore header=1 is required.
    """

    df = pd.read_excel(
        REFERENCE_FILE,
        sheet_name=sheet_name,
        header=1
    )

    df = normalize_dataframe(df)

    return df


# ============================================================
# HEADER NORMALIZATION
# ============================================================

def normalize_inventory_headers(df):
    """
    Normalize known header differences between:
    
    Sheet 2:
        Storage location

    Inventory:
        Storage Location

    Also handles the spelling:
        Matrial Code Desc
    """

    df = df.copy()

    rename_map = {}

    for column in df.columns:

        normalized = str(column).strip().lower()

        if normalized == "storage location":
            rename_map[column] = "Storage Location"

        elif normalized == "material code":
            rename_map[column] = "Material Code"

        elif normalized == "matrial code desc":
            rename_map[column] = "Material Code Desc"

        elif normalized == "material code desc":
            rename_map[column] = "Material Code Desc"

        elif normalized == "mat grp":
            rename_map[column] = "Mat Grp"

        elif normalized == "mat grp desc":
            rename_map[column] = "Mat Grp Desc"

        elif normalized == "plant":
            rename_map[column] = "Plant"

    df = df.rename(columns=rename_map)

    return df


# ============================================================
# CANONICAL KEY
# ============================================================

def create_canonical_key(
    material_code,
    storage_location,
    plant
):
    """
    Create one standard key for comparison.

    We deliberately use:

        Material Code | Storage Location | Plant

    Example:

        15111201000046|UP03|1000
    """

    material_code = normalize_value(material_code)
    storage_location = normalize_value(storage_location)
    plant = normalize_value(plant)

    return (
        material_code
        + "|"
        + storage_location
        + "|"
        + plant
    )


# ============================================================
# SHEET 2 KEY
# ============================================================

def create_sheet2_keys(df):
    """
    Sheet 2 already contains:
        Material Code
        Storage Location
        Plant

    Therefore we recreate the canonical key from
    these columns instead of comparing the Concatenate
    column directly.
    """

    df = df.copy()

    required_columns = [
        "Material Code",
        "Storage Location",
        "Plant",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Sheet 2 is missing required columns:\n"
            f"{missing}\n\n"
            f"Actual columns:\n{list(df.columns)}"
        )

    df["_Canonical_Key"] = [
        create_canonical_key(
            material_code,
            storage_location,
            plant
        )
        for material_code, storage_location, plant
        in zip(
            df["Material Code"],
            df["Storage Location"],
            df["Plant"]
        )
    ]

    return df


# ============================================================
# INVENTORY KEY
# ============================================================

def create_inventory_keys(df):
    """
    Create canonical keys for Inventory Prev / Pres.
    """

    df = df.copy()

    required_columns = [
        "Material Code",
        "Storage Location",
        "Plant",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Inventory sheet is missing required columns:\n"
            f"{missing}\n\n"
            f"Actual columns:\n{list(df.columns)}"
        )

    df["_Canonical_Key"] = [
        create_canonical_key(
            material_code,
            storage_location,
            plant
        )
        for material_code, storage_location, plant
        in zip(
            df["Material Code"],
            df["Storage Location"],
            df["Plant"]
        )
    ]

    return df


# ============================================================
# ANALYZE ONE MONTH
# ============================================================

def analyze_month(
    label,
    sap_file,
    inventory_sheet,
    output_file
):

    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    # --------------------------------------------------------
    # LOAD SHEET 2
    # --------------------------------------------------------

    print("\nLoading employee Sheet 2...")

    sheet2 = load_sheet2(sap_file)

    print(
        f"Sheet 2 rows: {len(sheet2)}"
    )

    print("\nSheet 2 columns:")

    for column in sheet2.columns:
        print(f"  {column}")

    sheet2 = create_sheet2_keys(sheet2)

    # --------------------------------------------------------
    # LOAD INVENTORY
    # --------------------------------------------------------

    print(
        f"\nLoading employee {inventory_sheet}..."
    )

    inventory = load_inventory_sheet(
        inventory_sheet
    )

    print(
        f"{inventory_sheet} rows: {len(inventory)}"
    )

    print("\nInventory columns BEFORE normalization:")

    for column in inventory.columns:
        print(f"  {column}")

    inventory = normalize_inventory_headers(
        inventory
    )

    print("\nInventory columns AFTER normalization:")

    for column in inventory.columns:
        print(f"  {column}")

    inventory = create_inventory_keys(
        inventory
    )

    # --------------------------------------------------------
    # UNIQUE KEYS
    # --------------------------------------------------------

    sheet2_keys = set(
        sheet2["_Canonical_Key"]
    )

    inventory_keys = set(
        inventory["_Canonical_Key"]
    )

    common_keys = (
        sheet2_keys
        &
        inventory_keys
    )

    sheet2_only_keys = (
        sheet2_keys
        -
        inventory_keys
    )

    inventory_only_keys = (
        inventory_keys
        -
        sheet2_keys
    )

    # --------------------------------------------------------
    # KEY COMPARISON
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("KEY COMPARISON")
    print("=" * 70)

    print(
        f"\nSheet 2 unique keys: "
        f"{len(sheet2_keys)}"
    )

    print(
        f"Inventory unique keys: "
        f"{len(inventory_keys)}"
    )

    print(
        f"Common keys: "
        f"{len(common_keys)}"
    )

    print(
        f"Sheet 2 only: "
        f"{len(sheet2_only_keys)}"
    )

    print(
        f"Inventory only: "
        f"{len(inventory_only_keys)}"
    )

    # --------------------------------------------------------
    # RECORDS ADDED AFTER SHEET 2
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("RECORDS ADDED AFTER SHEET 2")
    print("=" * 70)

    inventory_only = inventory[
        inventory["_Canonical_Key"].isin(
            inventory_only_keys
        )
    ].copy()

    print(
        f"\nInventory-only rows: "
        f"{len(inventory_only)}"
    )

    if not inventory_only.empty:

        print(
            "\nFirst 50 Inventory-only records:"
        )

        display_columns = [
            "Mat Grp",
            "Mat Grp Desc",
            "Material Code",
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
            "_Canonical_Key",
        ]

        display_columns = [
            column
            for column in display_columns
            if column in inventory_only.columns
        ]

        print(
            inventory_only[
                display_columns
            ].head(50).to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # SHEET 2 RECORDS NOT IN INVENTORY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("SHEET 2 RECORDS NOT IN INVENTORY")
    print("=" * 70)

    sheet2_only = sheet2[
        sheet2["_Canonical_Key"].isin(
            sheet2_only_keys
        )
    ].copy()

    print(
        f"\nSheet 2-only rows: "
        f"{len(sheet2_only)}"
    )

    if not sheet2_only.empty:

        print(
            "\nFirst 50 Sheet 2-only records:"
        )

        display_columns = [
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
            "_Canonical_Key",
        ]

        display_columns = [
            column
            for column in display_columns
            if column in sheet2_only.columns
        ]

        print(
            sheet2_only[
                display_columns
            ].head(50).to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # STORAGE LOCATION ANALYSIS
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("STORAGE LOCATION ANALYSIS")
    print("=" * 70)

    if not inventory_only.empty:

        print(
            "\nInventory-only Storage Location counts:"
        )

        print(
            inventory_only[
                "Storage Location"
            ]
            .value_counts(
                dropna=False
            )
            .head(30)
            .to_string()
        )

    # --------------------------------------------------------
    # RI / CAPITAL ANALYSIS
    # --------------------------------------------------------

    if not inventory_only.empty:

        print("\n" + "=" * 70)
        print("RI / CAPITAL ANALYSIS")
        print("=" * 70)

        if "RI Ind" in inventory_only.columns:

            print("\nRI Ind:")

            print(
                inventory_only[
                    "RI Ind"
                ]
                .value_counts(
                    dropna=False
                )
                .to_string()
            )

        if "Capital Ind" in inventory_only.columns:

            print("\nCapital Ind:")

            print(
                inventory_only[
                    "Capital Ind"
                ]
                .value_counts(
                    dropna=False
                )
                .to_string()
            )

    # --------------------------------------------------------
    # MATERIAL CODE ANALYSIS
    # --------------------------------------------------------

    if not inventory_only.empty:

        print("\n" + "=" * 70)
        print("MATERIAL CODE ANALYSIS")
        print("=" * 70)

        material_counts = (
            inventory_only[
                "Material Code"
            ]
            .value_counts()
        )

        repeated_materials = (
            material_counts[
                material_counts > 1
            ]
        )

        print(
            "\nMaterial codes appearing "
            "multiple times in added records:"
        )

        if repeated_materials.empty:

            print(
                "No repeated material codes."
            )

        else:

            print(
                repeated_materials
                .head(50)
                .to_string()
            )

    # --------------------------------------------------------
    # SAVE INVESTIGATION
    # --------------------------------------------------------

    with pd.ExcelWriter(
        output_file,
        engine="openpyxl"
    ) as writer:

        inventory_only.to_excel(
            writer,
            sheet_name="Inventory_Only",
            index=False
        )

        sheet2_only.to_excel(
            writer,
            sheet_name="Sheet2_Only",
            index=False
        )

        common_sample = inventory[
            inventory["_Canonical_Key"].isin(common_keys)
        ].head(100)

        common_sample.to_excel(
            writer,
            sheet_name="Common_Sample",
            index=False
        )

    print(
        "\nFull investigation saved to:"
    )

    print(output_file)

    return {
        "sheet2_rows": len(sheet2),
        "inventory_rows": len(inventory),
        "sheet2_keys": len(sheet2_keys),
        "inventory_keys": len(inventory_keys),
        "common_keys": len(common_keys),
        "sheet2_only": len(sheet2_only_keys),
        "inventory_only": len(inventory_only_keys),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "STEP 4 - SHEET 2 -> INVENTORY INVESTIGATION"
    )
    print("=" * 70)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # JULY
    # --------------------------------------------------------

    july_result = analyze_month(
        label="JULY: SHEET 2 -> INVENTORY PREV",
        sap_file=JULY_FILE,
        inventory_sheet="Inventory Prev",
        output_file=JULY_OUTPUT,
    )

    # --------------------------------------------------------
    # AUGUST
    # --------------------------------------------------------

    august_result = analyze_month(
        label="AUGUST: SHEET 2 -> INVENTORY PRES",
        sap_file=AUGUST_FILE,
        inventory_sheet="Inventory Pres",
        output_file=AUGUST_OUTPUT,
    )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("STEP 4 INVESTIGATION SUMMARY")
    print("=" * 70)

    print("\nJULY:")

    for key, value in july_result.items():
        print(
            f"  {key}: {value}"
        )

    print("\nAUGUST:")

    for key, value in august_result.items():
        print(
            f"  {key}: {value}"
        )

    print("\n" + "=" * 70)
    print("STEP 4A COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()