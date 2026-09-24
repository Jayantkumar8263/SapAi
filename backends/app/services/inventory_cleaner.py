from pathlib import Path
from typing import Union

import pandas as pd


# ---------------------------------------------------------
# COLUMN NAME NORMALIZATION
# ---------------------------------------------------------

def normalize_column_name(column) -> str:
    """
    Safely convert a dataframe column name into a normalized string.

    This prevents errors such as:
        'function' object has no attribute 'lower'
    """

    if column is None:
        return ""

    # Column names should normally be strings.
    # Convert anything else safely to string first.
    column = str(column)

    return (
        column.strip()
        .lower()
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
    )


# ---------------------------------------------------------
# FIND COLUMN
# ---------------------------------------------------------

def find_column(df: pd.DataFrame, possible_names):
    """
    Find a dataframe column using several possible names.
    """

    normalized_columns = {
        normalize_column_name(col): col
        for col in df.columns
    }

    for name in possible_names:
        normalized_name = normalize_column_name(name)

        if normalized_name in normalized_columns:
            return normalized_columns[normalized_name]

    return None


# ---------------------------------------------------------
# VALIDATE EXCEL FILE
# ---------------------------------------------------------

def validate_excel_file(file_path: Union[str, Path]) -> None:
    """
    Validate that the supplied file exists and is a readable Excel file.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Excel file not found: {file_path}"
        )

    if file_path.suffix.lower() not in [".xlsx", ".xls"]:
        raise ValueError(
            "Only Excel files (.xlsx or .xls) are supported."
        )

    try:
        pd.read_excel(file_path, nrows=5)
    except Exception as exc:
        raise ValueError(
            f"Unable to read Excel file: {exc}"
        ) from exc


# ---------------------------------------------------------
# LOAD EXCEL
# ---------------------------------------------------------

def load_inventory_excel(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Read the inventory Excel file into a dataframe.
    """

    validate_excel_file(file_path)

    try:
        df = pd.read_excel(file_path)
    except Exception as exc:
        raise ValueError(
            f"Failed to read inventory Excel file: {exc}"
        ) from exc

    if df.empty:
        raise ValueError(
            "The Excel file contains no inventory records."
        )

    # Remove completely empty rows
    df = df.dropna(how="all").copy()

    # Normalize dataframe column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ---------------------------------------------------------
# IDENTIFY IMPORTANT COLUMNS
# ---------------------------------------------------------

def identify_inventory_columns(df: pd.DataFrame) -> dict:
    """
    Identify Plant, Material Code, Storage Location,
    Quantity and Unit columns.
    """

    plant_column = find_column(
        df,
        [
            "plant",
            "plant_code",
            "plant code",
            "plantcode",
        ],
    )

    material_column = find_column(
        df,
        [
            "material",
            "material_code",
            "material code",
            "materialcode",
            "material number",
            "material_number",
        ],
    )

    storage_column = find_column(
        df,
        [
            "storage_location",
            "storage location",
            "storagelocation",
            "storage_loc",
            "sloc",
            "s_loc",
        ],
    )

    quantity_column = find_column(
        df,
        [
            "quantity",
            "qty",
            "stock quantity",
            "valuated stock",
            "valuated_stock",
        ],
    )

    unit_column = find_column(
        df,
        [
            "unit",
            "uom",
            "base unit",
            "base_unit",
        ],
    )

    return {
        "plant": plant_column,
        "material_code": material_column,
        "storage_location": storage_column,
        "quantity": quantity_column,
        "unit": unit_column,
    }


# ---------------------------------------------------------
# STANDARDIZE DATA
# ---------------------------------------------------------

def standardize_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize inventory dataframe.
    """

    columns = identify_inventory_columns(df)

    # -----------------------------------------------------
    # Plant
    # -----------------------------------------------------

    if columns["plant"] is None:
        raise ValueError(
            "Plant column could not be identified. "
            f"Available columns: {list(df.columns)}"
        )

    # -----------------------------------------------------
    # Material Code
    # -----------------------------------------------------

    if columns["material_code"] is None:
        raise ValueError(
            "Material Code column could not be identified. "
            f"Available columns: {list(df.columns)}"
        )

    # -----------------------------------------------------
    # Storage Location
    # -----------------------------------------------------

    # Storage location is important for the final key.
    # If SAP export doesn't contain it, create an empty column.
    if columns["storage_location"] is None:
        df["Storage_Location"] = ""
        columns["storage_location"] = "Storage_Location"

    # -----------------------------------------------------
    # Rename important columns
    # -----------------------------------------------------

    rename_map = {
        columns["plant"]: "Plant",
        columns["material_code"]: "Material_Code",
        columns["storage_location"]: "Storage_Location",
    }

    if columns["quantity"] is not None:
        rename_map[columns["quantity"]] = "Quantity"

    if columns["unit"] is not None:
        rename_map[columns["unit"]] = "Unit"

    df = df.rename(columns=rename_map)

    # -----------------------------------------------------
    # Convert important fields to strings
    # -----------------------------------------------------

    df["Plant"] = (
        df["Plant"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["Material_Code"] = (
        df["Material_Code"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["Storage_Location"] = (
        df["Storage_Location"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # -----------------------------------------------------
    # Quantity
    # -----------------------------------------------------

    if "Quantity" in df.columns:

        df["Quantity"] = pd.to_numeric(
            df["Quantity"],
            errors="coerce"
        ).fillna(0)

    else:

        df["Quantity"] = 0

    # -----------------------------------------------------
    # Unit
    # -----------------------------------------------------

    if "Unit" not in df.columns:
        df["Unit"] = ""

    df["Unit"] = (
        df["Unit"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # -----------------------------------------------------
    # Inventory Key
    # -----------------------------------------------------

    df["Inventory_Key"] = (
        df["Plant"].astype(str)
        + "_"
        + df["Material_Code"].astype(str)
        + "_"
        + df["Storage_Location"].astype(str)
    )

    # -----------------------------------------------------
    # Remove duplicate inventory keys
    # -----------------------------------------------------

    df = df.drop_duplicates(
        subset=["Inventory_Key"],
        keep="last"
    ).reset_index(drop=True)

    # -----------------------------------------------------
    # Rearrange important columns
    # -----------------------------------------------------

    priority_columns = [
        "Inventory_Key",
        "Plant",
        "Material_Code",
        "Storage_Location",
        "Quantity",
        "Unit",
    ]

    existing_priority = [
        col for col in priority_columns
        if col in df.columns
    ]

    remaining_columns = [
        col for col in df.columns
        if col not in existing_priority
    ]

    df = df[
        existing_priority + remaining_columns
    ]

    return df


# ---------------------------------------------------------
# MAIN CLEANER FUNCTION
# ---------------------------------------------------------

def clean_inventory_file(
    file_path: Union[str, Path],
    output_path: Union[str, Path, None] = None,
) -> dict:
    """
    Clean and standardize an SAP inventory Excel file.

    Returns information about the cleaned file.
    """

    file_path = Path(file_path)

    print()
    print("=" * 60)
    print("STARTING INVENTORY CLEANING")
    print("=" * 60)

    print(f"Input file: {file_path}")

    # -----------------------------------------------------
    # Load
    # -----------------------------------------------------

    df = load_inventory_excel(file_path)

    print(f"Original records: {len(df)}")
    print(f"Original columns: {list(df.columns)}")

    # -----------------------------------------------------
    # Standardize
    # -----------------------------------------------------

    cleaned_df = standardize_inventory(df)

    print(f"Cleaned records: {len(cleaned_df)}")
    print(
        f"Removed duplicates: "
        f"{len(df) - len(cleaned_df)}"
    )

    # -----------------------------------------------------
    # Output path
    # -----------------------------------------------------

    if output_path is None:

        output_path = (
            file_path.parent
            / f"{file_path.stem}_cleaned.xlsx"
        )

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    cleaned_df.to_excel(
        output_path,
        index=False
    )

    print(f"Cleaned file saved: {output_path}")

    print("=" * 60)
    print("CLEANING COMPLETED")
    print("=" * 60)
    print()

    return {
        "input_file": str(file_path),
        "output_file": str(output_path),
        "original_records": int(len(df)),
        "cleaned_records": int(len(cleaned_df)),
        "duplicates_removed": int(
            len(df) - len(cleaned_df)
        ),
        "columns": list(cleaned_df.columns),
    }


# ---------------------------------------------------------
# OPTIONAL ALIAS
# ---------------------------------------------------------

def clean_inventory(
    file_path: Union[str, Path],
    output_path: Union[str, Path, None] = None,
):
    """
    Backward-compatible alias.
    """

    return clean_inventory_file(
        file_path,
        output_path
    )