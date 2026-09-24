from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

AUTOMATED_FILE = (
    DATA_DIR
    / "reports"
    / "BSP_Automated_Inventory_Test.xlsx"
)

REFERENCE_FILE = (
    DATA_DIR
    / "samples"
    / "Final output file.xlsx"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_column_name(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace("\n", " ")
        .replace("_", " ")
        .replace("  ", " ")
    )


def normalize_columns(df):
    df = df.copy()

    df.columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    return df


def normalize_values(df):
    df = df.copy()

    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        else:

            df[column] = df[column].fillna(0)

    return df


# ============================================================
# LOAD FUNCTIONS
# ============================================================

def load_normal_sheet(
    file_path,
    sheet_name,
):
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
    )

    df = normalize_columns(df)
    df = normalize_values(df)

    return df


def load_inventory_reference(file_path):
    """
    The manual Inventory sheet contains a descriptive
    first row before the actual column headers.

    Therefore header=1 is required.
    """

    df = pd.read_excel(
        file_path,
        sheet_name="Inventory",
        header=1,
    )

    df = normalize_columns(df)
    df = normalize_values(df)

    return df


def load_reference_list(
    file_path,
    sheet_name,
):
    """
    RI and Capital sheets in the manual workbook are
    one-column material-code lists without a normal
    header row.
    """

    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=None,
    )

    if df.empty:
        return set()

    values = (
        df.iloc[:, 0]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[values != ""]

    return set(values)


# ============================================================
# BASIC SHEET COMPARISON
# ============================================================

def compare_basic_sheet(
    reference_file,
    automated_file,
    sheet_name,
):
    print("\n" + "=" * 70)
    print(f"COMPARING: {sheet_name}")
    print("=" * 70)

    reference = load_normal_sheet(
        reference_file,
        sheet_name,
    )

    automated = load_normal_sheet(
        automated_file,
        sheet_name,
    )

    print(
        f"Reference rows : {len(reference)}"
    )

    print(
        f"Automated rows : {len(automated)}"
    )

    print(
        f"Reference cols : {len(reference.columns)}"
    )

    print(
        f"Automated cols : {len(automated.columns)}"
    )

    reference_columns = set(
        reference.columns
    )

    automated_columns = set(
        automated.columns
    )

    missing = sorted(
        reference_columns
        - automated_columns
    )

    extra = sorted(
        automated_columns
        - reference_columns
    )

    if missing:
        print("\nMissing columns:")
        for column in missing:
            print(f"  - {column}")
    else:
        print("\nNo missing columns.")

    if extra:
        print("\nExtra columns:")
        for column in extra:
            print(f"  - {column}")
    else:
        print("No extra columns.")

    common = [
        column
        for column in reference.columns
        if column in automated.columns
    ]

    print(
        f"\nCommon columns: {len(common)}"
    )

    return reference, automated, common


# ============================================================
# INVENTORY KEY COMPARISON
# ============================================================

def compare_inventory():
    print("\n" + "=" * 70)
    print("INVENTORY KEY COMPARISON")
    print("=" * 70)

    reference = load_inventory_reference(
        REFERENCE_FILE
    )

    automated = load_normal_sheet(
        AUTOMATED_FILE,
        "Inventory",
    )

    print(
        f"Reference rows : {len(reference)}"
    )

    print(
        f"Automated rows : {len(automated)}"
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    required = [
        "material code",
        "storage location",
        "plant",
    ]

    for column in required:

        if column not in reference.columns:
            print(
                f"\nReference is missing: {column}"
            )

        if column not in automated.columns:
            print(
                f"\nAutomated is missing: {column}"
            )

    # --------------------------------------------------------
    # Create business key
    # --------------------------------------------------------

    def create_key(df):

        return (
            df["material code"]
            .fillna("")
            .astype(str)
            .str.strip()
            + "|"
            + df["storage location"]
            .fillna("")
            .astype(str)
            .str.strip()
            + "|"
            + df["plant"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    reference["_comparison_key"] = create_key(
        reference
    )

    automated["_comparison_key"] = create_key(
        automated
    )

    reference_keys = set(
        reference["_comparison_key"]
    )

    automated_keys = set(
        automated["_comparison_key"]
    )

    missing_keys = (
        reference_keys
        - automated_keys
    )

    extra_keys = (
        automated_keys
        - reference_keys
    )

    print(
        f"\nReference unique keys : "
        f"{len(reference_keys)}"
    )

    print(
        f"Automated unique keys : "
        f"{len(automated_keys)}"
    )

    print(
        f"Keys missing from automated : "
        f"{len(missing_keys)}"
    )

    print(
        f"Extra automated keys : "
        f"{len(extra_keys)}"
    )

    # --------------------------------------------------------
    # Duplicate analysis
    # --------------------------------------------------------

    reference_duplicates = int(
        reference["_comparison_key"]
        .duplicated()
        .sum()
    )

    automated_duplicates = int(
        automated["_comparison_key"]
        .duplicated()
        .sum()
    )

    print(
        f"\nReference duplicate keys : "
        f"{reference_duplicates}"
    )

    print(
        f"Automated duplicate keys : "
        f"{automated_duplicates}"
    )

    # --------------------------------------------------------
    # Show examples
    # --------------------------------------------------------

    if missing_keys:

        print(
            "\nFirst 10 keys missing from automated:"
        )

        for key in list(missing_keys)[:10]:
            print(f"  {key}")

    if extra_keys:

        print(
            "\nFirst 10 extra automated keys:"
        )

        for key in list(extra_keys)[:10]:
            print(f"  {key}")


# ============================================================
# RI / CAPITAL COMPARISON
# ============================================================

def compare_reference_list(
    sheet_name,
):
    print("\n" + "=" * 70)
    print(f"{sheet_name.upper()} MATERIAL LIST COMPARISON")
    print("=" * 70)

    reference = load_reference_list(
        REFERENCE_FILE,
        sheet_name,
    )

    automated_df = load_normal_sheet(
        AUTOMATED_FILE,
        sheet_name,
    )

    # Automated workbook has a header.
    if "material code" in automated_df.columns:

        automated = set(
            automated_df["material code"]
            .dropna()
            .astype(str)
            .str.strip()
        )

    else:

        automated = set(
            automated_df.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
        )

    missing = reference - automated
    extra = automated - reference

    print(
        f"Reference materials : {len(reference)}"
    )

    print(
        f"Automated materials : {len(automated)}"
    )

    print(
        f"Missing from automated : {len(missing)}"
    )

    print(
        f"Extra in automated : {len(extra)}"
    )

    if missing:

        print(
            "\nFirst missing materials:"
        )

        for value in list(missing)[:10]:
            print(f"  {value}")

    if extra:

        print(
            "\nFirst extra materials:"
        )

        for value in list(extra)[:10]:
            print(f"  {value}")


# ============================================================
# PREVIOUS / PRESENT KEY ANALYSIS
# ============================================================

def compare_inventory_source_sheets():
    print("\n" + "=" * 70)
    print("SOURCE INVENTORY SHEET ANALYSIS")
    print("=" * 70)

    reference_prev = load_normal_sheet(
        REFERENCE_FILE,
        "Inventory Prev",
    )

    reference_pres = load_normal_sheet(
        REFERENCE_FILE,
        "Inventory Pres",
    )

    automated_prev = load_normal_sheet(
        AUTOMATED_FILE,
        "Inventory Prev",
    )

    automated_pres = load_normal_sheet(
        AUTOMATED_FILE,
        "Inventory Pres",
    )

    print("\nInventory Prev")

    print(
        f"Reference rows : "
        f"{len(reference_prev)}"
    )

    print(
        f"Automated rows : "
        f"{len(automated_prev)}"
    )

    print("\nInventory Pres")

    print(
        f"Reference rows : "
        f"{len(reference_pres)}"
    )

    print(
        f"Automated rows : "
        f"{len(automated_pres)}"
    )

    # --------------------------------------------------------
    # Concatenate key
    # --------------------------------------------------------

    for name, df in [
        ("Reference Prev", reference_prev),
        ("Automated Prev", automated_prev),
        ("Reference Pres", reference_pres),
        ("Automated Pres", automated_pres),
    ]:

        if "concatenate" not in df.columns:
            print(
                f"{name}: missing concatenate column"
            )
            continue

        keys = (
            df["concatenate"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        print(
            f"{name} unique Concatenate keys: "
            f"{keys.nunique()}"
        )

        print(
            f"{name} duplicate Concatenate rows: "
            f"{keys.duplicated().sum()}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("BSP AUTOMATED REPORT vs MANUAL REPORT")
    print("=" * 70)

    print("\nReference:")
    print(REFERENCE_FILE)

    print("\nAutomated:")
    print(AUTOMATED_FILE)

    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(
            f"Reference file not found:\n"
            f"{REFERENCE_FILE}"
        )

    if not AUTOMATED_FILE.exists():
        raise FileNotFoundError(
            f"Automated file not found:\n"
            f"{AUTOMATED_FILE}"
        )

    print("\nBoth files found.")

    # --------------------------------------------------------
    # Previous
    # --------------------------------------------------------

    compare_basic_sheet(
        REFERENCE_FILE,
        AUTOMATED_FILE,
        "Inventory Prev",
    )

    # --------------------------------------------------------
    # Present
    # --------------------------------------------------------

    compare_basic_sheet(
        REFERENCE_FILE,
        AUTOMATED_FILE,
        "Inventory Pres",
    )

    # --------------------------------------------------------
    # RI
    # --------------------------------------------------------

    compare_reference_list(
        "RI"
    )

    # --------------------------------------------------------
    # Capital
    # --------------------------------------------------------

    compare_reference_list(
        "Capital"
    )

    # --------------------------------------------------------
    # Inventory
    # --------------------------------------------------------

    compare_inventory()

    # --------------------------------------------------------
    # Source sheets
    # --------------------------------------------------------

    compare_inventory_source_sheets()

    print("\n" + "=" * 70)
    print("BSP COMPARISON ANALYSIS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()