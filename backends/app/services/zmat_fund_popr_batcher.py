"""
ZMAT-FUND_POPR Material Batch Preparation
==========================================

Prepares unique material codes for the BSP
ZMAT-FUND_POPR SAP process.

Documented BSP process:

    Inventory
        ↓
    Unique Material Codes
        ↓
    Split into 20,000-record batches
        ↓
    ZMAT-FUND_POPR

This module does NOT connect to SAP.

It only performs deterministic preparation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_BATCH_SIZE = 20_000


# ============================================================
# MATERIAL CODE NORMALIZATION
# ============================================================

def normalize_material_code(
    value: Any,
) -> str:
    """
    Normalize a material code.

    Examples:

        15111201000046
        "15111201000046"
        15111201000046.0

    become:

        "15111201000046"
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

    text = str(value).strip()

    if not text:
        return ""

    # --------------------------------------------------------
    # Handle Excel numeric representation
    # --------------------------------------------------------

    if text.endswith(".0"):

        try:

            number = float(text)

            if number.is_integer():

                text = str(
                    int(number)
                )

        except ValueError:

            pass

    return text


# ============================================================
# UNIQUE MATERIAL CODES
# ============================================================

def extract_unique_material_codes(
    df: pd.DataFrame,
    material_code_column: str = "Material Code",
) -> list[str]:
    """
    Extract unique material codes while preserving
    their first-seen order.

    Blank material codes are ignored.

    Duplicate material codes are removed.
    """

    if not isinstance(
        df,
        pd.DataFrame,
    ):

        raise TypeError(
            "df must be a pandas DataFrame."
        )

    if material_code_column not in df.columns:

        raise ValueError(
            "Material code column not found: "
            f"{material_code_column}"
        )

    seen: set[str] = set()

    unique_codes: list[str] = []

    for value in df[
        material_code_column
    ]:

        code = normalize_material_code(
            value
        )

        if not code:
            continue

        if code in seen:
            continue

        seen.add(code)

        unique_codes.append(
            code
        )

    return unique_codes


# ============================================================
# BATCH MATERIAL CODES
# ============================================================

def create_material_batches(
    material_codes: Iterable[str],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[list[str]]:
    """
    Split material codes into batches.

    Example:

        45,000 codes
        batch_size = 20,000

    produces:

        Batch 1 = 20,000
        Batch 2 = 20,000
        Batch 3 = 5,000
    """

    if batch_size <= 0:

        raise ValueError(
            "batch_size must be greater than zero."
        )

    codes = [
        normalize_material_code(code)
        for code in material_codes
    ]

    codes = [
        code
        for code in codes
        if code
    ]

    return [
        codes[start:start + batch_size]
        for start in range(
            0,
            len(codes),
            batch_size,
        )
    ]


# ============================================================
# COMPLETE PREPARATION
# ============================================================

def prepare_zmat_fund_popr_batches(
    df: pd.DataFrame,
    material_code_column: str = "Material Code",
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Extract unique material codes and split them into
    ZMAT-FUND_POPR batches.
    """

    unique_codes = (
        extract_unique_material_codes(
            df,
            material_code_column,
        )
    )

    batches = (
        create_material_batches(
            unique_codes,
            batch_size,
        )
    )

    return {
        "success": True,
        "total_input_rows": int(
            len(df)
        ),
        "unique_material_codes": int(
            len(unique_codes)
        ),
        "batch_size": int(
            batch_size
        ),
        "batch_count": int(
            len(batches)
        ),
        "batches": batches,
    }


# ============================================================
# SAVE BATCHES
# ============================================================

def save_material_batches(
    batches: list[list[str]],
    output_directory: str | Path,
) -> list[str]:
    """
    Save each material-code batch as a TXT file.

    One material code is written per line.

    Example:

        zmat_batch_001.txt
        zmat_batch_002.txt
        zmat_batch_003.txt

    The TXT format is intentionally simple because the exact
    SAP ZMAT-FUND_POPR input screen has not yet been validated
    against real SAP.
    """

    output_dir = Path(
        output_directory
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_files: list[str] = []

    for index, batch in enumerate(
        batches,
        start=1,
    ):

        output_file = (
            output_dir
            / f"zmat_batch_{index:03d}.txt"
        )

        output_file.write_text(
            "\n".join(batch),
            encoding="utf-8",
        )

        output_files.append(
            str(output_file)
        )

    return output_files


# ============================================================
# LOAD EXCEL + PREPARE
# ============================================================

def prepare_zmat_fund_popr_from_excel(
    input_file: str | Path,
    material_code_column: str = "Material Code",
    batch_size: int = DEFAULT_BATCH_SIZE,
    output_directory: str | Path | None = None,
) -> dict[str, Any]:
    """
    Read an Excel file and prepare ZMAT-FUND_POPR batches.
    """

    input_path = Path(
        input_file
    )

    if not input_path.exists():

        raise FileNotFoundError(
            f"Input file not found: "
            f"{input_path}"
        )

    df = pd.read_excel(
        input_path
    )

    result = (
        prepare_zmat_fund_popr_batches(
            df,
            material_code_column,
            batch_size,
        )
    )

    if output_directory is not None:

        files = save_material_batches(
            result["batches"],
            output_directory,
        )

        result[
            "batch_files"
        ] = files

    return result