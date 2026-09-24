"""BSP MC.1 raw-export cleaner.

Implements the documented Sheet1 -> Sheet2 transformation used by the
BSP inventory process.  This module is intentionally deterministic; it does
not infer fields with an LLM.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


RAW_COLUMNS = [
    "Material Group",
    "Material",
    "Storage Location",
    "Val. stock",
    "ValStckVal",
    "Val. stock.1",
]


def clean_raw_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def excel_trim(value) -> str:
    """Approximate Excel TRIM for the strings used by the BSP formulas."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return re.sub(r" {2,}", " ", text)


def _require_columns(df: pd.DataFrame) -> None:
    normalized = {str(c).strip(): c for c in df.columns}
    missing = [c for c in RAW_COLUMNS[:-1] if c not in normalized]
    # Excel/pandas may rename the duplicate last header to '.1'.
    if "Val. stock.1" not in normalized and "Val. stock" in normalized:
        candidates = [c for c in df.columns if str(c).strip().startswith("Val. stock")]
        if len(candidates) < 2:
            missing.append("Val. stock.1")
    if missing:
        raise ValueError(
            "Raw BSP MC.1 Sheet1 is missing required columns: "
            + ", ".join(missing)
        )


def clean_mc1_sheet1(df: pd.DataFrame) -> pd.DataFrame:
    """Create the employee-style cleaned Sheet2 from raw MC.1 Sheet1."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    _require_columns(df)

    # pandas normally calls the duplicate 'Val. stock' header 'Val. stock.1'.
    uom_col = "Val. stock.1" if "Val. stock.1" in df.columns else [
        c for c in df.columns if c.startswith("Val. stock")
    ][1]

    material_group = df["Material Group"].apply(clean_raw_text)
    material = df["Material"].apply(clean_raw_text)
    storage_location = df["Storage Location"].apply(clean_raw_text)

    result = pd.DataFrame()
    result["Mat Grp"] = material_group.str.slice(0, 3).apply(excel_trim)
    result["Mat Grp Desc"] = material_group.str.slice(4).apply(excel_trim)
    result["Material Code"] = material.str.slice(0, 14).apply(excel_trim)
    result["Material Code Desc"] = material.str.slice(14).apply(excel_trim)
    result["Storage Location"] = storage_location.str.slice(4, 13).apply(excel_trim)
    result["Storage Location Desc"] = storage_location.str.slice(8).apply(excel_trim)
    result["Plant"] = storage_location.str.slice(0, 4).apply(excel_trim)
    result["Inve Prev Quantity"] = df["Val. stock"]
    result["Inve Prev Value"] = df["ValStckVal"]
    result["UOM"] = df[uom_col].apply(clean_raw_text)

    result.insert(
        0,
        "Concatenate",
        result["Plant"].astype(str)
        + result["Material Code"].astype(str)
        + result["Storage Location"].astype(str),
    )
    return result


def load_mc1_sheet1(file_path: str | Path) -> pd.DataFrame:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"SAP MC.1 Excel file not found: {file_path}")
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    df = df.dropna(how="all").copy()
    return clean_mc1_sheet1(df)


def clean_mc1_workbook(
    input_file: str | Path,
    output_file: str | Path,
) -> Path:
    """
    Read a raw MC.1 workbook and create an employee-style
    workbook containing:

        Sheet1 = original raw data
        Sheet2 = cleaned MC.1 data

    The ExcelWriter is explicitly managed with a context manager
    so that the workbook is completely closed before the function
    returns. This is important on Windows because otherwise the
    output file can remain locked.
    """

    input_file = Path(input_file)
    output_file = Path(output_file)

    if not input_file.exists():
        raise FileNotFoundError(
            f"MC.1 input file not found: {input_file}"
        )

    # ---------------------------------------------------------
    # Read input workbook completely and close it.
    # ---------------------------------------------------------

    with pd.ExcelFile(
        input_file,
        engine="openpyxl",
    ) as excel_file:

        raw_df = pd.read_excel(
            excel_file,
            sheet_name=0,
        )

    # ---------------------------------------------------------
    # Clean raw MC.1 data.
    # ---------------------------------------------------------

    cleaned_df = clean_mc1_sheet1(
        raw_df
    )

    # ---------------------------------------------------------
    # Write output workbook.
    #
    # IMPORTANT:
    # Using "with" guarantees ExcelWriter is closed.
    # ---------------------------------------------------------

    with pd.ExcelWriter(
        output_file,
        engine="openpyxl",
    ) as writer:

        raw_df.to_excel(
            writer,
            sheet_name="Sheet1",
            index=False,
        )

        cleaned_df.to_excel(
            writer,
            sheet_name="Sheet2",
            index=False,
        )

    # At this point the writer is CLOSED.

    return output_file
