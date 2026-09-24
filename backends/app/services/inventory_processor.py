from pathlib import Path
import pandas as pd


# ============================================================
# SAP INVENTORY PROCESSOR
# ============================================================

REQUIRED_COLUMNS = [
    "Material_Code",
    "Material_Name",
    "Quantity",
    "Unit",
    "Plant",
]


# ============================================================
# 1. READ INVENTORY FILE
# ============================================================

def read_inventory_file(file_path: str) -> pd.DataFrame:
    """
    Read an SAP inventory Excel file and return it as a DataFrame.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if file_path.suffix.lower() not in [".xlsx", ".xls"]:
        raise ValueError(
            "Only Excel files (.xlsx / .xls) are supported."
        )

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        raise RuntimeError(
            f"Unable to read inventory file: {e}"
        )

    return df


# ============================================================
# 2. CLEAN DATA
# ============================================================

def clean_inventory_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean basic formatting issues in the inventory data.
    """

    df = df.copy()

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Remove completely empty columns
    df = df.dropna(axis=1, how="all")

    # Clean column names
    df.columns = [
        str(column).strip().replace(" ", "_")
        for column in df.columns
    ]

    # Clean string values
    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].apply(
                lambda value: value.strip()
                if isinstance(value, str)
                else value
            )

    return df


# ============================================================
# 3. VALIDATE COLUMNS
# ============================================================

def validate_columns(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    Check whether all required SAP inventory columns exist.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        return False, missing_columns

    return True, []


# ============================================================
# 4. VALIDATE INVENTORY DATA
# ============================================================

def validate_inventory_data(df: pd.DataFrame) -> dict:
    """
    Validate inventory records.

    Returns a dictionary containing:
        valid
        errors
        warnings
    """

    errors = []
    warnings = []

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    columns_valid, missing_columns = validate_columns(df)

    if not columns_valid:
        errors.append(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
        }

    # --------------------------------------------------------
    # Check empty dataset
    # --------------------------------------------------------

    if df.empty:
        errors.append("Inventory file contains no records.")

        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
        }

    # --------------------------------------------------------
    # Material Code validation
    # --------------------------------------------------------

    invalid_material_codes = df[
        df["Material_Code"].isna()
        | (df["Material_Code"].astype(str).str.strip() == "")
    ]

    if not invalid_material_codes.empty:
        errors.append(
            f"{len(invalid_material_codes)} record(s) have "
            "missing Material_Code."
        )

    # --------------------------------------------------------
    # Material Name validation
    # --------------------------------------------------------

    invalid_material_names = df[
        df["Material_Name"].isna()
        | (df["Material_Name"].astype(str).str.strip() == "")
    ]

    if not invalid_material_names.empty:
        errors.append(
            f"{len(invalid_material_names)} record(s) have "
            "missing Material_Name."
        )

    # --------------------------------------------------------
    # Quantity validation
    # --------------------------------------------------------

    quantity_numeric = pd.to_numeric(
        df["Quantity"],
        errors="coerce"
    )

    invalid_quantity = quantity_numeric.isna()

    if invalid_quantity.any():
        errors.append(
            f"{invalid_quantity.sum()} record(s) have "
            "invalid Quantity values."
        )

    negative_quantity = quantity_numeric < 0

    if negative_quantity.any():
        errors.append(
            f"{negative_quantity.sum()} record(s) have "
            "negative Quantity values."
        )

    # --------------------------------------------------------
    # Unit validation
    # --------------------------------------------------------

    invalid_units = df[
        df["Unit"].isna()
        | (df["Unit"].astype(str).str.strip() == "")
    ]

    if not invalid_units.empty:
        errors.append(
            f"{len(invalid_units)} record(s) have missing Unit."
        )

    # --------------------------------------------------------
    # Plant validation
    # --------------------------------------------------------

    invalid_plants = df[
        df["Plant"].isna()
        | (df["Plant"].astype(str).str.strip() == "")
    ]

    if not invalid_plants.empty:
        errors.append(
            f"{len(invalid_plants)} record(s) have missing Plant."
        )

    # --------------------------------------------------------
    # Duplicate Material Code check
    # --------------------------------------------------------

    duplicate_materials = df[
        df["Material_Code"].duplicated(keep=False)
    ]

    if not duplicate_materials.empty:
        duplicate_count = duplicate_materials[
            "Material_Code"
        ].nunique()

        warnings.append(
            f"{duplicate_count} Material_Code value(s) "
            "appear more than once."
        )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================
# 5. NORMALIZE DATA
# ============================================================

def normalize_inventory_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize inventory values into consistent formats.
    """

    df = df.copy()

    # Material Code
    df["Material_Code"] = (
        df["Material_Code"]
        .astype(str)
        .str.strip()
    )

    # Material Name
    df["Material_Name"] = (
        df["Material_Name"]
        .astype(str)
        .str.strip()
    )

    # Quantity
    df["Quantity"] = pd.to_numeric(
        df["Quantity"],
        errors="coerce"
    )

    # Unit
    df["Unit"] = (
        df["Unit"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Plant
    df["Plant"] = (
        df["Plant"]
        .astype(str)
        .str.strip()
    )

    return df


# ============================================================
# 6. INVENTORY SUMMARY
# ============================================================

def generate_inventory_summary(df: pd.DataFrame) -> dict:
    """
    Generate basic inventory statistics.
    """

    summary = {
        "total_records": len(df),
        "total_quantity": 0,
        "unique_materials": 0,
        "unique_plants": 0,
        "units": [],
    }

    if df.empty:
        return summary

    summary["total_quantity"] = float(
        df["Quantity"].sum()
    )

    summary["unique_materials"] = int(
        df["Material_Code"].nunique()
    )

    summary["unique_plants"] = int(
        df["Plant"].nunique()
    )

    summary["units"] = (
        df["Unit"]
        .dropna()
        .unique()
        .tolist()
    )

    return summary


# ============================================================
# 7. PROCESS INVENTORY FILE
# ============================================================

def process_inventory_file(file_path: str) -> dict:
    """
    Main inventory processing pipeline.

    Steps:
        1. Read Excel file
        2. Clean data
        3. Validate structure
        4. Validate records
        5. Normalize data
        6. Generate summary
    """

    print("\n" + "=" * 55)
    print("SAP INVENTORY PROCESSOR")
    print("=" * 55)

    # --------------------------------------------------------
    # READ FILE
    # --------------------------------------------------------

    print("\nReading inventory file...")

    df = read_inventory_file(file_path)

    # --------------------------------------------------------
    # CLEAN DATA
    # --------------------------------------------------------

    df = clean_inventory_data(df)

    # --------------------------------------------------------
    # DISPLAY RAW INVENTORY
    # --------------------------------------------------------

    print("\nInventory data:")
    print(df.to_string())

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    print("\nRunning validation...")

    validation_result = validate_inventory_data(df)

    print("\nValidation Result:")

    if validation_result["valid"]:

        print("VALID - Data is ready for the next stage.")

    else:

        print("INVALID - Data requires correction.")

        print("\nErrors:")

        for error in validation_result["errors"]:
            print(f"- {error}")

    # --------------------------------------------------------
    # WARNINGS
    # --------------------------------------------------------

    if validation_result["warnings"]:

        print("\nWarnings:")

        for warning in validation_result["warnings"]:
            print(f"- {warning}")

    # --------------------------------------------------------
    # STOP IF INVALID
    # --------------------------------------------------------

    if not validation_result["valid"]:

        print("\n" + "=" * 55)
        print("PROCESS FAILED")
        print("=" * 55)

        return {
            "success": False,
            "data": None,
            "validation": validation_result,
            "summary": None,
        }

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    processed_df = normalize_inventory_data(df)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = generate_inventory_summary(
        processed_df
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print("\nProcessing completed.")

    print(
        processed_df.to_string(index=True)
    )

    print("\nInventory Summary:")

    print(
        f"Total records    : {summary['total_records']}"
    )

    print(
        f"Total quantity   : {summary['total_quantity']}"
    )

    print(
        f"Unique materials : {summary['unique_materials']}"
    )

    print(
        f"Unique plants    : {summary['unique_plants']}"
    )

    print(
        f"Units            : {', '.join(summary['units'])}"
    )

    print("\n" + "=" * 55)
    print("PROCESS COMPLETED")
    print("=" * 55)

    return {
        "success": True,
        "data": processed_df,
        "validation": validation_result,
        "summary": summary,
    }


# ============================================================
# 8. TEST / STANDALONE EXECUTION
# ============================================================

if __name__ == "__main__":

    # Project root:
    #
    # SapAi/
    # ├── backends/
    # │   └── app/
    # │       └── services/
    # │           └── inventory_processor.py
    # └── data/
    #     └── sample_inventory.xlsx
    #
    # Therefore:
    # inventory_processor.py
    #       -> services
    #       -> app
    #       -> backends
    #       -> SapAi
    #
    # parents[3] = SapAi

    project_root = (
        Path(__file__)
        .resolve()
        .parents[3]
    )

    sample_file = (
        project_root
        / "data"
        / "sample_inventory.xlsx"
    )

    result = process_inventory_file(
        str(sample_file)
    )