"""
SAP MC.1 Excel Adapter
======================

Supports:

1. Raw MC.1 workbook containing Sheet1 only.
2. Raw Sheet1 + cleaned Sheet2.
3. Cleaned Sheet2 workbook.

The adapter converts MC.1 data into the standardized
format expected by the SapAi inventory pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


# ================================================================
# SAP / BSP COLUMN MAPPING
# ================================================================

SAP_COLUMNS = {
    "Concatenate": "Inventory_Key",
    "Mat Grp": "Material_Group",
    "Mat Grp Desc": "Material_Group_Desc",
    "Material Code": "Material_Code",
    "Material Code Desc": "Material_Name",
    "Storage location": "Storage_Location",
    "Storage Location": "Storage_Location",
    "Storage Location Desc": "Storage_Location_Desc",
    "Plant": "Plant",
    "Inve Prev Quantity": "Quantity",
    "Inve Prev Value": "Inventory_Value",
    "UOM": "Unit",
}


REQUIRED_SAP_COLUMNS = [
    "Material Code",
    "Material Code Desc",
    "Storage location",
    "Plant",
    "Inve Prev Quantity",
    "Inve Prev Value",
    "UOM",
]


# ================================================================
# RAW MC.1 COLUMNS
# ================================================================

RAW_MC1_COLUMNS = {
    "Material Group",
    "Material",
    "Storage location",
    "Val. stock",
    "ValStckVal",
}


# ================================================================
# NORMALIZE COLUMN NAMES
# ================================================================

def _normalize_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize Excel column names.

    Handles capitalization differences such as:

        Storage location
        Storage Location

    and removes accidental spaces.
    """

    df = df.dropna(
        how="all"
    ).copy()

    # Remove leading/trailing spaces
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Normalize known column-name variations
    aliases = {
        "Storage Location": "Storage location",
        "Storage location": "Storage location",

        "Material Group": "Material Group",
        "Material": "Material",

        "Val. stock": "Val. stock",
        "ValStckVal": "ValStckVal",

        "Inve Prev Quantity ": "Inve Prev Quantity",
        "Inve Prev Quantity": "Inve Prev Quantity",

        "Inve Prev Value ": "Inve Prev Value",
        "Inve Prev Value": "Inve Prev Value",

        "UOM ": "UOM",
        "UOM": "UOM",
    }

    df = df.rename(
        columns={
            column: aliases.get(
                column,
                column,
            )
            for column in df.columns
        }
    )

    return df


# ================================================================
# DETECT RAW MC.1 DATA
# ================================================================

def _is_raw_mc1(
    df: pd.DataFrame,
) -> bool:
    """
    Determine whether the dataframe is raw MC.1 output.
    """

    columns = set(
        df.columns
    )

    return RAW_MC1_COLUMNS.issubset(
        columns
    )


# ================================================================
# DETECT CLEANED DATA
# ================================================================

def _is_cleaned_mc1(
    df: pd.DataFrame,
) -> bool:
    """
    Determine whether the dataframe already contains
    employee-style cleaned columns.
    """

    columns = set(
        df.columns
    )

    return set(
        REQUIRED_SAP_COLUMNS
    ).issubset(
        columns
    )


# ================================================================
# READ EXCEL SHEET
# ================================================================

def _read_sheet(
    excel_file: pd.ExcelFile,
    sheet_name_or_index,
) -> pd.DataFrame:

    df = pd.read_excel(
        excel_file,
        sheet_name=sheet_name_or_index,
    )

    return _normalize_columns(
        df
    )


# ================================================================
# LOAD MC.1 RAW DATA
# ================================================================

def load_sap_mc1_raw(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Load MC.1 Excel data.

    Supported:

        Sheet1 only
        Sheet1 + Sheet2
        Sheet2 only
    """

    file_path = Path(
        file_path
    )

    if not file_path.exists():

        raise FileNotFoundError(
            f"SAP Excel file not found: {file_path}"
        )

    # ------------------------------------------------------------
    # Open Excel explicitly so Windows file handles are closed.
    # ------------------------------------------------------------

    with pd.ExcelFile(
        file_path,
        engine="openpyxl",
    ) as excel_file:

        sheet_names = list(
            excel_file.sheet_names
        )

        # --------------------------------------------------------
        # CASE 1
        # Sheet2 exists
        # --------------------------------------------------------

        if "Sheet2" in sheet_names:

            df = _read_sheet(
                excel_file,
                "Sheet2",
            )

        # --------------------------------------------------------
        # CASE 2
        # Multiple sheets but Sheet2 has another name
        # --------------------------------------------------------

        elif len(sheet_names) > 1:

            candidate = _read_sheet(
                excel_file,
                1,
            )

            if _is_cleaned_mc1(
                candidate
            ):

                df = candidate

            else:

                first = _read_sheet(
                    excel_file,
                    0,
                )

                if _is_raw_mc1(
                    first
                ):

                    # Convert raw column spelling into the
                    # exact spelling expected by the cleaner.
                    first = first.rename(
                        columns={
                            "Storage location":
                            "Storage Location"
                        }
                    )

                    from app.services.bsp_mc1_export import (
                        clean_mc1_sheet1
                    )

                    df = clean_mc1_sheet1(
                        first
                    )

                else:

                    df = candidate

        # --------------------------------------------------------
        # CASE 3
        # Only one worksheet
        # --------------------------------------------------------

        else:

            first = _read_sheet(
                excel_file,
                0,
            )

            # ----------------------------------------------------
            # Already cleaned
            # ----------------------------------------------------

            if _is_cleaned_mc1(
                first
            ):

                df = first

            # ----------------------------------------------------
            # Raw MC.1
            # ----------------------------------------------------

            elif _is_raw_mc1(
                first
            ):

                # The existing BSP cleaner expects
                # "Storage Location" with capital L.
                first = first.rename(
                    columns={
                        "Storage location":
                        "Storage Location"
                    }
                )

                from app.services.bsp_mc1_export import (
                    clean_mc1_sheet1
                )

                df = clean_mc1_sheet1(
                    first
                )

            # ----------------------------------------------------
            # Unknown structure
            # ----------------------------------------------------

            else:

                raise ValueError(
                    "SAP MC.1 workbook does not contain "
                    "either the expected raw MC.1 columns "
                    "or the cleaned Sheet2 columns. "
                    f"Found sheets: {sheet_names}; "
                    f"columns: {first.columns.tolist()}"
                )

    # ============================================================
    # Normalize cleaned output
    # ============================================================

    df = _normalize_columns(
        df
    )

    # The cleaner normally creates "Storage Location".
    # Normalize it to the adapter's standard spelling.
    if (
        "Storage Location" in df.columns
        and "Storage location" not in df.columns
    ):

        df = df.rename(
            columns={
                "Storage Location":
                "Storage location"
            }
        )

    # ============================================================
    # Validate final required columns
    # ============================================================

    missing = [
        column
        for column in REQUIRED_SAP_COLUMNS
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "SAP MC.1 export is missing required columns: "
            + ", ".join(missing)
        )

    return df


# ================================================================
# ADAPT DATAFRAME
# ================================================================

def adapt_sap_mc1_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert MC.1 dataframe into standardized SapAi format.
    """

    df = _normalize_columns(
        df
    )

    # ------------------------------------------------------------
    # If raw MC.1 data is passed directly, clean it first.
    # ------------------------------------------------------------

    if _is_raw_mc1(
        df
    ):

        df = df.rename(
            columns={
                "Storage location":
                "Storage Location"
            }
        )

        from app.services.bsp_mc1_export import (
            clean_mc1_sheet1
        )

        df = clean_mc1_sheet1(
            df
        )

        df = _normalize_columns(
            df
        )

        if (
            "Storage Location" in df.columns
            and "Storage location"
            not in df.columns
        ):

            df = df.rename(
                columns={
                    "Storage Location":
                    "Storage location"
                }
            )

    # ------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------

    missing = [
        column
        for column in REQUIRED_SAP_COLUMNS
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "Cannot adapt SAP data. Missing columns: "
            + ", ".join(missing)
        )

    # ------------------------------------------------------------
    # Rename into standardized SapAi names
    # ------------------------------------------------------------

    rename_map = {
        old: new
        for old, new in SAP_COLUMNS.items()
        if old in df.columns
    }

    result = df.rename(
        columns=rename_map
    ).copy()

    # ------------------------------------------------------------
    # Text fields
    # ------------------------------------------------------------

    text_columns = [
        "Material_Code",
        "Material_Name",
        "Storage_Location",
        "Storage_Location_Desc",
        "Plant",
        "Unit",
        "Material_Group",
        "Material_Group_Desc",
    ]

    for column in text_columns:

        if column in result.columns:

            result[column] = (
                result[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    # ------------------------------------------------------------
    # Numeric fields
    # ------------------------------------------------------------

    for column in [
        "Quantity",
        "Inventory_Value",
    ]:

        if column in result.columns:

            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            ).fillna(0)

    # ------------------------------------------------------------
    # Create Inventory Key
    # ------------------------------------------------------------

    result["Inventory_Key"] = (
        result["Plant"]
        .astype(str)
        .str.strip()
        +
        result["Material_Code"]
        .astype(str)
        .str.strip()
        +
        result["Storage_Location"]
        .astype(str)
        .str.strip()
    )

    return result


# ================================================================
# COMPLETE PIPELINE
# ================================================================

def load_and_adapt_sap_mc1(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Complete MC.1 loading and adaptation pipeline.
    """

    raw_df = load_sap_mc1_raw(
        file_path
    )

    return adapt_sap_mc1_dataframe(
        raw_df
    )


# ================================================================
# MANUAL TEST
# ================================================================

if __name__ == "__main__":

    sample_file = (
        Path(__file__).resolve()
        .parents[2]
        / "data"
        / "Inventory Previous 01.09.xlsx"
    )

    print("=" * 70)
    print("SapAi SAP MC.1 Excel Adapter Test")
    print("=" * 70)

    print("\nInput:")
    print(sample_file)

    df = load_and_adapt_sap_mc1(
        sample_file
    )

    print("\nRows:")
    print(len(df))

    print("\nColumns:")
    print(
        df.columns.tolist()
    )

    print("\nFirst 5 records:")

    print(
        df.head().to_string()
    )

    print("\n" + "=" * 70)

    print(
        "SAP MC.1 ADAPTER TEST PASSED"
    )

    print("=" * 70)