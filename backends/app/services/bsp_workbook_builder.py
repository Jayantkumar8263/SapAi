"""
BSP Inventory Workbook Builder
==============================

Builds the final BSP-style inventory workbook from SAP-exported
inventory Excel files.

Expected final workbook:

1. Inventory Prev
2. Inventory Pres
3. RI
4. Capital
5. Inventory

The builder supports SAP workbooks containing:
- Sheet1: raw/less-structured SAP data
- Sheet2: already structured data

It automatically detects the structured sheet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


# ============================================================
# REQUIRED STRUCTURED COLUMNS
# ============================================================

STRUCTURED_COLUMNS = {
    "concatenate",
    "mat grp",
    "mat grp desc",
    "material code",
    "material code desc",
    "storage location",
    "storage location desc",
    "plant",
    "inve prev quantity",
    "inve prev value",
    "uom",
}


# ============================================================
# FINAL COLUMN STRUCTURES
# ============================================================

PREVIOUS_COLUMNS = [
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

PRESENT_COLUMNS = [
    "Concatenate",
    "Mat Grp",
    "Mat Grp Desc",
    "Material Code",
    "Material Code Desc",
    "Storage Location",
    "Storage Location Desc",
    "Plant",
    "Inve Pres Quantity",
    "Inve Pres Value",
    "UOM",
]

FINAL_INVENTORY_COLUMNS = [
    "Mat Grp",
    "Mat Grp Desc",
    "Material Code",
    "Matrial Code Desc",
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
]


# ============================================================
# HELPERS
# ============================================================

def _normalise_column_name(value: object) -> str:
    """Normalise a column name for matching."""

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("\n", " ")
        .replace("  ", " ")
    )


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strip whitespace from column names while preserving the
    original semantic names where possible.
    """

    df = df.copy()

    cleaned = []

    for column in df.columns:
        name = str(column).strip()

        # Handle the sample file typo/variation.
        if name == "Inve Prev Quantity ":
            name = "Inve Prev Quantity"

        cleaned.append(name)

    df.columns = cleaned

    return df


def _find_structured_sheet(
    excel_file: str | Path,
) -> tuple[str, pd.DataFrame]:
    """
    Find the workbook sheet containing the structured
    inventory representation.

    This is intentionally detected from column names rather
    than assuming Sheet1 or Sheet2.
    """

    excel_file = str(excel_file)

    workbook = pd.ExcelFile(excel_file)

    for sheet_name in workbook.sheet_names:

        sample = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            nrows=5,
        )

        sample = _normalise_columns(sample)

        columns = {
            _normalise_column_name(column)
            for column in sample.columns
        }

        # We only need the important identifying fields to
        # recognise the structured inventory sheet.
        required = {
            "material code",
            "material code desc",
            "plant",
            "uom",
        }

        if required.issubset(columns):
            return sheet_name, pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
            )

    raise ValueError(
        f"No structured inventory sheet found in {excel_file}. "
        f"Expected columns such as Material Code, "
        f"Material Code Desc, Plant and UOM."
    )


def _rename_case_insensitive(
    df: pd.DataFrame,
    mapping: dict[str, str],
) -> pd.DataFrame:
    """Rename columns without depending on exact casing/spacing."""

    df = df.copy()

    lookup = {
        _normalise_column_name(column): column
        for column in df.columns
    }

    rename_map = {}

    for source, target in mapping.items():

        actual = lookup.get(
            _normalise_column_name(source)
        )

        if actual is not None:
            rename_map[actual] = target

    return df.rename(columns=rename_map)


def _clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean string values while preserving numeric fields."""

    df = df.copy()

    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df


def _numeric_column(
    df: pd.DataFrame,
    column: str,
) -> pd.DataFrame:
    """Convert a numeric inventory field safely."""

    df = df.copy()

    if column not in df.columns:
        df[column] = 0

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    ).fillna(0)

    return df


# ============================================================
# SAP FILE LOADING
# ============================================================

def load_sap_inventory(
    excel_file: str | Path,
) -> tuple[pd.DataFrame, str]:
    """
    Load the structured inventory representation from an
    SAP-exported workbook.

    Returns:
        dataframe
        sheet_name_used
    """

    sheet_name, df = _find_structured_sheet(excel_file)

    df = _normalise_columns(df)

    # Normalise known variation in source files.
    rename_mapping = {
        "Inve Prev Quantity ": "Inve Prev Quantity",
    }

    df = _rename_case_insensitive(
        df,
        rename_mapping,
    )

    df = _clean_text_columns(df)

    return df, sheet_name


# ============================================================
# PREVIOUS INVENTORY
# ============================================================

def prepare_previous_inventory(
    excel_file: str | Path,
) -> pd.DataFrame:
    """
    Convert a SAP inventory workbook into the
    Inventory Prev format.
    """

    df, _ = load_sap_inventory(excel_file)

    # Normalise column names.
    lookup = {
        _normalise_column_name(column): column
        for column in df.columns
    }

    def get_column(name: str):
        actual = lookup.get(
            _normalise_column_name(name)
        )

        if actual is None:
            raise ValueError(
                f"Required column '{name}' not found "
                f"in {excel_file}."
            )

        return actual

    columns = {
        "Concatenate": get_column("Concatenate"),
        "Mat Grp": get_column("Mat Grp"),
        "Mat Grp Desc": get_column("Mat Grp Desc"),
        "Material Code": get_column("Material Code"),
        "Material Code Desc": get_column("Material Code Desc"),
        "Storage Location": get_column("Storage location"),
        "Storage Location Desc": get_column(
            "Storage Location Desc"
        ),
        "Plant": get_column("Plant"),
        "Inve Prev Quantity": get_column(
            "Inve Prev Quantity"
        ),
        "Inve Prev Value": get_column(
            "Inve Prev Value"
        ),
        "UOM": get_column("UOM"),
    }

    result = df[
        list(columns.values())
    ].copy()

    result.columns = list(columns.keys())

    result = _numeric_column(
        result,
        "Inve Prev Quantity",
    )

    result = _numeric_column(
        result,
        "Inve Prev Value",
    )

    return result[PREVIOUS_COLUMNS]


# ============================================================
# PRESENT INVENTORY
# ============================================================

def prepare_present_inventory(
    excel_file: str | Path,
) -> pd.DataFrame:
    """
    Convert a SAP inventory workbook into the
    Inventory Pres format.
    """

    df, _ = load_sap_inventory(excel_file)

    lookup = {
        _normalise_column_name(column): column
        for column in df.columns
    }

    def get_column(name: str):
        actual = lookup.get(
            _normalise_column_name(name)
        )

        if actual is None:
            raise ValueError(
                f"Required column '{name}' not found "
                f"in {excel_file}."
            )

        return actual

    columns = {
        "Concatenate": get_column("Concatenate"),
        "Mat Grp": get_column("Mat Grp"),
        "Mat Grp Desc": get_column("Mat Grp Desc"),
        "Material Code": get_column("Material Code"),
        "Material Code Desc": get_column("Material Code Desc"),
        "Storage Location": get_column("Storage location"),
        "Storage Location Desc": get_column(
            "Storage Location Desc"
        ),
        "Plant": get_column("Plant"),
        "Inve Pres Quantity": get_column(
            "Inve Prev Quantity"
        ),
        "Inve Pres Value": get_column(
            "Inve Prev Value"
        ),
        "UOM": get_column("UOM"),
    }

    result = df[
        list(columns.values())
    ].copy()

    result.columns = list(columns.keys())

    result = _numeric_column(
        result,
        "Inve Pres Quantity",
    )

    result = _numeric_column(
        result,
        "Inve Pres Value",
    )

    return result[PRESENT_COLUMNS]


# ============================================================
# REFERENCE LISTS
# ============================================================

def load_material_reference(
    excel_file: str | Path,
    sheet_name: str,
) -> set[str]:
    """
    Load a one-column material reference list.

    Used for RI and Capital material codes.
    """

    df = pd.read_excel(
        excel_file,
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

    # Ignore accidental header-like text.
    values = values[
        values.str.lower()
        != "material code"
    ]

    return set(values)


# ============================================================
# FINAL INVENTORY
# ============================================================

def build_final_inventory(
    previous: pd.DataFrame,
    present: pd.DataFrame,
    ri_materials: Iterable[str],
    capital_materials: Iterable[str],
) -> pd.DataFrame:
    """
    Combine previous/current inventory and classify
    each material as RI and/or Capital.
    """

    previous = previous.copy()
    present = present.copy()

    # ------------------------------------------------------------
    # NORMALIZE METADATA COLUMN NAMES
    # ------------------------------------------------------------
    # SAP exports can use slightly different capitalization such as:
    #   "Storage location"
    #   "Storage Location"
    #
    # Pandas treats these as different columns during merge().
    # Both dataframes are therefore converted to one canonical
    # naming convention before the merge.
    previous = previous.rename(
        columns={
            "Storage location": "Storage Location",
        }
    )

    present = present.rename(
        columns={
            "Storage location": "Storage Location",
        }
    )

    required_merge_columns = [
        "Concatenate",
        "Mat Grp",
        "Mat Grp Desc",
        "Material Code",
        "Material Code Desc",
        "Storage Location",
        "Storage Location Desc",
        "Plant",
        "UOM",
    ]

    missing_previous = [
        column
        for column in required_merge_columns
        if column not in previous.columns
    ]
    missing_present = [
        column
        for column in required_merge_columns
        if column not in present.columns
    ]

    if missing_previous:
        raise ValueError(
            "Previous inventory is missing required columns: "
            + ", ".join(missing_previous)
        )

    if missing_present:
        raise ValueError(
            "Present inventory is missing required columns: "
            + ", ".join(missing_present)
        )

    # Use Concatenate as the primary inventory key.
    previous["_key"] = (
        previous["Concatenate"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    present["_key"] = (
        present["Concatenate"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Remove exact duplicate keys while preserving first record.
    previous = previous.drop_duplicates(
        subset=["_key"],
        keep="first",
    )

    present = present.drop_duplicates(
        subset=["_key"],
        keep="first",
    )

    # Merge previous and current inventory.
    merged = previous.merge(
        present[
            [
                "_key",
                "Mat Grp",
                "Mat Grp Desc",
                "Material Code",
                "Material Code Desc",
                "Storage Location",
                "Storage Location Desc",
                "Plant",
                "Inve Pres Quantity",
                "Inve Pres Value",
                "UOM",
            ]
        ],
        on="_key",
        how="outer",
        suffixes=("_prev", "_pres"),
    )

    # Helper for choosing previous/current metadata.
    def combine_columns(
        prev_name: str,
        pres_name: str,
    ):
        prev_col = f"{prev_name}_prev"
        pres_col = f"{pres_name}_pres"

        if prev_col in merged.columns and pres_col in merged.columns:
            return (
                merged[prev_col]
                .replace("", pd.NA)
                .fillna(merged[pres_col])
            )

        if prev_col in merged.columns:
            return merged[prev_col]

        if pres_col in merged.columns:
            return merged[pres_col]

        raise KeyError(
            f"Neither '{prev_col}' nor '{pres_col}' exists "
            "after the Previous/Present inventory merge."
        )

    final = pd.DataFrame()

    final["Mat Grp"] = combine_columns(
        "Mat Grp",
        "Mat Grp",
    )

    final["Mat Grp Desc"] = combine_columns(
        "Mat Grp Desc",
        "Mat Grp Desc",
    )

    final["Material Code"] = combine_columns(
        "Material Code",
        "Material Code",
    )

    final["Matrial Code Desc"] = combine_columns(
        "Material Code Desc",
        "Material Code Desc",
    )

    final["Storage Location"] = combine_columns(
        "Storage Location",
        "Storage Location",
    )

    final["Storage Location Desc"] = combine_columns(
        "Storage Location Desc",
        "Storage Location Desc",
    )

    final["Plant"] = combine_columns(
        "Plant",
        "Plant",
    )

    final["Inve Prev Quantity"] = merged.get(
        "Inve Prev Quantity",
        0,
    )

    final["Inve Prev Value"] = merged.get(
        "Inve Prev Value",
        0,
    )

    final["Inve Pres Quantity"] = merged.get(
        "Inve Pres Quantity",
        0,
    )

    final["Inve Pres Value"] = merged.get(
        "Inve Pres Value",
        0,
    )

    final["UOM"] = combine_columns(
        "UOM",
        "UOM",
    )

    # Numeric cleanup.
    for column in [
        "Inve Prev Quantity",
        "Inve Prev Value",
        "Inve Pres Quantity",
        "Inve Pres Value",
    ]:
        final[column] = pd.to_numeric(
            final[column],
            errors="coerce",
        ).fillna(0)

    # Material code matching.
    material_codes = (
        final["Material Code"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    ri_set = {
        str(value).strip()
        for value in ri_materials
    }

    capital_set = {
        str(value).strip()
        for value in capital_materials
    }

    final["RI Ind"] = material_codes.map(
        lambda value: "Yes"
        if value in ri_set
        else "No"
    )

    final["Capital Ind"] = material_codes.map(
        lambda value: "Yes"
        if value in capital_set
        else "No"
    )

    return final[FINAL_INVENTORY_COLUMNS]


# ============================================================
# WORKBOOK GENERATION
# ============================================================

def build_bsp_workbook(
    previous_file: str | Path,
    present_file: str | Path,
    reference_file: str | Path,
    output_file: str | Path,
) -> dict:
    """
    Build the complete five-sheet BSP workbook.

    The reference_file is expected to contain:
        RI
        Capital
    """

    previous = prepare_previous_inventory(
        previous_file,
    )

    present = prepare_present_inventory(
        present_file,
    )

    ri_materials = load_material_reference(
        reference_file,
        "RI",
    )

    capital_materials = load_material_reference(
        reference_file,
        "Capital",
    )

    inventory = build_final_inventory(
        previous,
        present,
        ri_materials,
        capital_materials,
    )

    output_file = Path(output_file)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pd.ExcelWriter(
        output_file,
        engine="openpyxl",
    ) as writer:

        previous.to_excel(
            writer,
            sheet_name="Inventory Prev",
            index=False,
        )

        present.to_excel(
            writer,
            sheet_name="Inventory Pres",
            index=False,
        )

        pd.DataFrame(
            sorted(ri_materials),
            columns=["Material Code"],
        ).to_excel(
            writer,
            sheet_name="RI",
            index=False,
        )

        pd.DataFrame(
            sorted(capital_materials),
            columns=["Material Code"],
        ).to_excel(
            writer,
            sheet_name="Capital",
            index=False,
        )

        inventory.to_excel(
            writer,
            sheet_name="Inventory",
            index=False,
        )

    return {
        "success": True,
        "output_file": str(output_file),
        "previous_rows": len(previous),
        "present_rows": len(present),
        "ri_materials": len(ri_materials),
        "capital_materials": len(capital_materials),
        "final_inventory_rows": len(inventory),
    }