"""
Inventory PO Builder
====================

Converts SAP spool TXT files into the Inventory PO Excel file.

BSP process:

    SAP Spool
        ↓
    Local TXT files
        ↓
    Combine TXT files
        ↓
    Normalize dates to YYYYMMDD
        ↓
    Inventory PO.xlsx

This module does not connect to SAP or the database.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_sap_date(
    value,
) -> str:
    """
    Normalize common SAP/Excel date representations
    into YYYYMMDD.

    Supported examples:

        24.09.2026
        24/09/2026
        24-09-2026
        2026-09-24
        2026/09/24
        20260924

    Invalid/blank values return an empty string.
    """

    if value is None:
        return ""

    try:

        if pd.isna(value):
            return ""

    except (
        TypeError,
        ValueError,
    ):

        pass

    text = str(
        value
    ).strip()

    if not text:
        return ""

    # --------------------------------------------------------
    # Already YYYYMMDD
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{8}",
        text,
    ):

        return text

    # --------------------------------------------------------
    # YYYY-MM-DD
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{4}-\d{2}-\d{2}",
        text,
    ):

        parsed = pd.to_datetime(
            text,
            format="%Y-%m-%d",
            errors="coerce",
        )

        if not pd.isna(parsed):

            return parsed.strftime(
                "%Y%m%d"
            )

        return ""

    # --------------------------------------------------------
    # YYYY/MM/DD
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{4}/\d{2}/\d{2}",
        text,
    ):

        parsed = pd.to_datetime(
            text,
            format="%Y/%m/%d",
            errors="coerce",
        )

        if not pd.isna(parsed):

            return parsed.strftime(
                "%Y%m%d"
            )

        return ""

    # --------------------------------------------------------
    # DD.MM.YYYY
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{2}\.\d{2}\.\d{4}",
        text,
    ):

        parsed = pd.to_datetime(
            text,
            format="%d.%m.%Y",
            errors="coerce",
        )

        if not pd.isna(parsed):

            return parsed.strftime(
                "%Y%m%d"
            )

        return ""

    # --------------------------------------------------------
    # DD/MM/YYYY
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{2}/\d{2}/\d{4}",
        text,
    ):

        parsed = pd.to_datetime(
            text,
            format="%d/%m/%Y",
            errors="coerce",
        )

        if not pd.isna(parsed):

            return parsed.strftime(
                "%Y%m%d"
            )

        return ""

    # --------------------------------------------------------
    # DD-MM-YYYY
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{2}-\d{2}-\d{4}",
        text,
    ):

        parsed = pd.to_datetime(
            text,
            format="%d-%m-%Y",
            errors="coerce",
        )

        if not pd.isna(parsed):

            return parsed.strftime(
                "%Y%m%d"
            )

        return ""

    # --------------------------------------------------------
    # Unsupported format
    # --------------------------------------------------------

    return ""


# ============================================================
# READ ONE TXT FILE
# ============================================================

def read_spool_txt(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Read one SAP spool TXT file.

    SAP spool exports may be tab-separated or whitespace
    separated, so the reader first attempts tab parsing and
    then falls back to whitespace parsing.
    """

    path = Path(
        file_path
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Spool TXT file not found: {path}"
        )

    if path.suffix.lower() != ".txt":

        raise ValueError(
            f"Expected a .txt spool file: {path}"
        )

    # --------------------------------------------------------
    # Read raw text
    # --------------------------------------------------------

    text = path.read_text(
        encoding="utf-8-sig"
    )

    if not text.strip():

        raise ValueError(
            f"Spool TXT file is empty: {path}"
        )

    # --------------------------------------------------------
    # Try tab-separated data
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            path,
            sep="\t",
            dtype=str,
            keep_default_na=False,
        )

        if len(df.columns) > 1:

            return df

    except Exception:
        pass

    # --------------------------------------------------------
    # Fallback: whitespace-separated
    # --------------------------------------------------------

    df = pd.read_csv(
        path,
        sep=r"\s+",
        engine="python",
        dtype=str,
        keep_default_na=False,
    )

    return df


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

def clean_inventory_po_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Clean column names while preserving their meaning.
    """

    result = df.copy()

    result.columns = [
        re.sub(
            r"\s+",
            " ",
            str(column).strip(),
        )
        for column in result.columns
    ]

    return result


# ============================================================
# NORMALIZE DATE COLUMNS
# ============================================================

def normalize_date_columns(
    df: pd.DataFrame,
    date_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """
    Normalize selected date columns to YYYYMMDD.

    If date_columns is omitted, columns whose names contain
    'date' are automatically detected.
    """

    result = df.copy()

    if date_columns is None:

        date_columns = [
            column
            for column in result.columns
            if "date" in str(
                column
            ).lower()
        ]

    for column in date_columns:

        if column not in result.columns:
            continue

        result[column] = (
            result[column]
            .apply(
                normalize_sap_date
            )
        )

    return result


# ============================================================
# COMBINE TXT FILES
# ============================================================

def combine_spool_txt_files(
    input_files: Iterable[str | Path],
) -> pd.DataFrame:
    """
    Combine multiple SAP spool TXT files into one DataFrame.

    All files are expected to represent the same logical
    output structure.
    """

    paths = [
        Path(file)
        for file in input_files
    ]

    if not paths:

        raise ValueError(
            "No spool TXT files were supplied."
        )

    frames: list[pd.DataFrame] = []

    reference_columns = None

    for path in paths:

        df = read_spool_txt(
            path
        )

        df = clean_inventory_po_columns(
            df
        )

        if reference_columns is None:

            reference_columns = list(
                df.columns
            )

        elif list(df.columns) != reference_columns:

            raise ValueError(
                "Spool TXT files have different "
                "column structures.\n"
                f"Expected: {reference_columns}\n"
                f"Found: {list(df.columns)}\n"
                f"File: {path}"
            )

        frames.append(
            df
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    return combined


# ============================================================
# BUILD INVENTORY PO
# ============================================================

def build_inventory_po(
    input_files: Iterable[str | Path],
    output_file: str | Path,
    date_columns: Iterable[str] | None = None,
) -> str:
    """
    Combine spool TXT files, normalize dates and write
    Inventory PO.xlsx.
    """

    combined = (
        combine_spool_txt_files(
            input_files
        )
    )

    combined = (
        normalize_date_columns(
            combined,
            date_columns,
        )
    )

    output_path = Path(
        output_file
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pd.ExcelWriter(
        output_path,
        engine="openpyxl",
    ) as writer:

        combined.to_excel(
            writer,
            sheet_name="Inventory PO",
            index=False,
        )

        sheet = writer.book[
            "Inventory PO"
        ]

        sheet.freeze_panes = "A2"

        if (
            sheet.max_row > 1
            and sheet.max_column > 0
        ):

            sheet.auto_filter.ref = (
                sheet.dimensions
            )

        for column in sheet.columns:

            max_length = 0

            column_letter = (
                column[0].column_letter
            )

            for cell in column:

                if cell.value is not None:

                    length = len(
                        str(
                            cell.value
                        )
                    )

                    max_length = max(
                        max_length,
                        length,
                    )

            sheet.column_dimensions[
                column_letter
            ].width = min(
                max_length + 2,
                50,
            )

    return str(
        output_path
    )