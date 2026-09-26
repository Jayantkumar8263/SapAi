"""BSP MC.1 raw-export cleaner.

Implements the documented Sheet1 -> Sheet2 transformation used by the
BSP inventory process.

This module is intentionally deterministic. It does not infer fields
with an LLM.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


# ============================================================
# REQUIRED RAW MC.1 COLUMNS
# ============================================================

RAW_COLUMNS = [
    "Material Group",
    "Material",
    "Storage Location",
    "Val. stock",
    "ValStckVal",
    "Val. stock.1",
]


# ============================================================
# BASIC TEXT HELPERS
# ============================================================

def clean_raw_text(value) -> str:
    """Convert a raw Excel value into a clean string."""

    if pd.isna(value):
        return ""

    return str(value).strip()


def excel_trim(value) -> str:
    """
    Approximate Excel TRIM for the strings used by the BSP formulas.

    Excel TRIM:
    - removes leading/trailing spaces
    - reduces repeated spaces between words
    """

    if pd.isna(value):
        return ""

    text = str(value).strip()

    return re.sub(r" {2,}", " ", text)


# ============================================================
# COLUMN VALIDATION
# ============================================================

def _require_columns(df: pd.DataFrame) -> None:
    """
    Validate that the raw MC.1 dataframe contains the columns
    required by the documented BSP transformation.
    """

    normalized = {
        str(column).strip(): column
        for column in df.columns
    }

    missing = [
        column
        for column in RAW_COLUMNS[:-1]
        if column not in normalized
    ]

    # --------------------------------------------------------
    # SAP/Excel may contain two columns named "Val. stock".
    #
    # pandas/openpyxl normally changes the second one to:
    #
    #     Val. stock.1
    #
    # --------------------------------------------------------

    if (
        "Val. stock.1" not in normalized
        and "Val. stock" in normalized
    ):
        candidates = [
            column
            for column in df.columns
            if str(column).strip().startswith("Val. stock")
        ]

        if len(candidates) < 2:
            missing.append("Val. stock.1")

    if missing:
        raise ValueError(
            "Raw BSP MC.1 Sheet1 is missing required columns: "
            + ", ".join(missing)
        )


# ============================================================
# MC.1 SHEET1 -> CLEANED DATA
# ============================================================

def clean_mc1_sheet1(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create the employee-style cleaned MC.1 data.

    This implements the documented Excel formulas:

        Mat Grp
        Mat Grp Desc
        Material Code
        Material Code Desc
        Storage Location
        Storage Location Desc
        Plant
        Concatenate
    """

    df = df.copy()

    # Normalize column names.
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    _require_columns(df)

    # --------------------------------------------------------
    # Determine UOM column.
    # --------------------------------------------------------

    if "Val. stock.1" in df.columns:

        uom_col = "Val. stock.1"

    else:

        stock_columns = [
            column
            for column in df.columns
            if str(column).strip().startswith("Val. stock")
        ]

        if len(stock_columns) < 2:
            raise ValueError(
                "Could not identify the UOM column "
                "(second Val. stock column)."
            )

        uom_col = stock_columns[1]

    # --------------------------------------------------------
    # Read source columns.
    # --------------------------------------------------------

    material_group = (
        df["Material Group"]
        .apply(clean_raw_text)
    )

    material = (
        df["Material"]
        .apply(clean_raw_text)
    )

    storage_location = (
        df["Storage Location"]
        .apply(clean_raw_text)
    )

    # --------------------------------------------------------
    # Build cleaned dataframe.
    # --------------------------------------------------------

    result = pd.DataFrame()

    # Material Group
    result["Mat Grp"] = (
        material_group
        .str.slice(0, 3)
        .apply(excel_trim)
    )

    result["Mat Grp Desc"] = (
        material_group
        .str.slice(4)
        .apply(excel_trim)
    )

    # Material
    result["Material Code"] = (
        material
        .str.slice(0, 14)
        .apply(excel_trim)
    )

    result["Material Code Desc"] = (
        material
        .str.slice(14)
        .apply(excel_trim)
    )

    # Storage Location
    result["Storage Location"] = (
        storage_location
        .str.slice(4, 13)
        .apply(excel_trim)
    )

    result["Storage Location Desc"] = (
        storage_location
        .str.slice(8)
        .apply(excel_trim)
    )

    # Plant
    result["Plant"] = (
        storage_location
        .str.slice(0, 4)
        .apply(excel_trim)
    )

    # Inventory values
    result["Inve Prev Quantity"] = df["Val. stock"]

    result["Inve Prev Value"] = df["ValStckVal"]

    # Unit of measurement
    result["UOM"] = (
        df[uom_col]
        .apply(clean_raw_text)
    )

    # --------------------------------------------------------
    # Concatenate:
    #
    # Plant + Material Code + Storage Location
    # --------------------------------------------------------

    result.insert(
        0,
        "Concatenate",
        (
            result["Plant"].astype(str)
            + result["Material Code"].astype(str)
            + result["Storage Location"].astype(str)
        ),
    )

    return result


# ============================================================
# LOAD MC.1 SHEET1
# ============================================================

def load_mc1_sheet1(
    file_path: str | Path,
) -> pd.DataFrame:
    """Load and clean the Sheet1 data from an MC.1 workbook."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"SAP MC.1 Excel file not found: {file_path}"
        )

    with pd.ExcelFile(
        file_path,
        engine="openpyxl",
    ) as excel_file:

        if "Sheet1" not in excel_file.sheet_names:
            raise ValueError(
                "MC.1 workbook must contain Sheet1."
            )

        df = pd.read_excel(
            excel_file,
            sheet_name="Sheet1",
        )

    df = df.dropna(
        how="all"
    ).copy()

    return clean_mc1_sheet1(df)


# ============================================================
# CREATE EMPLOYEE-STYLE WORKBOOK
# ============================================================

def clean_mc1_workbook(
    input_file: str | Path,
    output_file: str | Path,
) -> Path:
    """
    Read a raw MC.1 workbook and create:

        Sheet1 = original raw data
        Sheet2 = cleaned MC.1 data

    The ExcelWriter is explicitly managed with a context manager
    so the workbook is completely closed before returning.
    """

    input_file = Path(input_file)

    output_file = Path(output_file)

    if not input_file.exists():
        raise FileNotFoundError(
            f"MC.1 input file not found: {input_file}"
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Read input workbook.
    # --------------------------------------------------------

    with pd.ExcelFile(
        input_file,
        engine="openpyxl",
    ) as excel_file:

        raw_df = pd.read_excel(
            excel_file,
            sheet_name=0,
        )

    # --------------------------------------------------------
    # Clean raw MC.1 data.
    # --------------------------------------------------------

    cleaned_df = clean_mc1_sheet1(
        raw_df
    )

    # --------------------------------------------------------
    # Write workbook.
    # --------------------------------------------------------

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

    return output_file


# ============================================================
# STANDARDIZED INTERNAL WORKBOOK
# ============================================================

def standardize_mc1_workbook(
    input_file: str | Path,
    output_file: str | Path,
) -> Path:
    """
    Convert raw Sheet1 MC.1 data into the internal standardized
    workbook.

    Output:

        Inventory.xlsx

    containing:

        Inventory
    """

    input_file = Path(input_file)

    output_file = Path(output_file)

    if not input_file.exists():
        raise FileNotFoundError(
            f"MC.1 input file not found: {input_file}"
        )

    # --------------------------------------------------------
    # Read raw workbook.
    # --------------------------------------------------------

    with pd.ExcelFile(
        input_file,
        engine="openpyxl",
    ) as excel_file:

        if "Sheet1" not in excel_file.sheet_names:
            raise ValueError(
                "MC.1 workbook must contain Sheet1."
            )

        raw_df = pd.read_excel(
            excel_file,
            sheet_name="Sheet1",
        )

    # --------------------------------------------------------
    # Normalize column names.
    # --------------------------------------------------------

    raw_df.columns = [
        str(column).strip()
        for column in raw_df.columns
    ]

    # SAP exports can sometimes use:
    #
    #     Storage location
    #
    # instead of:
    #
    #     Storage Location
    #

    if (
        "Storage location" in raw_df.columns
        and "Storage Location" not in raw_df.columns
    ):
        raw_df = raw_df.rename(
            columns={
                "Storage location": "Storage Location"
            }
        )

    # --------------------------------------------------------
    # Clean MC.1.
    # --------------------------------------------------------

    cleaned_df = clean_mc1_sheet1(
        raw_df
    )

    # --------------------------------------------------------
    # Create output directory.
    # --------------------------------------------------------

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Write standardized workbook.
    # --------------------------------------------------------

    with pd.ExcelWriter(
        output_file,
        engine="openpyxl",
    ) as writer:

        cleaned_df.to_excel(
            writer,
            sheet_name="Inventory",
            index=False,
        )

    return output_file


# ============================================================
# MC.1 EXPORT MANAGER
# ============================================================

class MC1ExportManager:
    """
    High-level manager for processing previous/current SAP MC.1
    exports.

    Flow:

        Raw MC.1 Excel
              |
              v
        validate_file()
              |
              v
        process_export()
              |
              v
        clean_mc1_sheet1()
              |
              v
        Standardized Inventory Excel
    """

    def __init__(
        self,
        output_directory: str | Path,
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------------
    # VALIDATE FILE
    # --------------------------------------------------------

    @staticmethod
    def validate_file(
        file_path: str | Path,
    ) -> dict:
        """
        Validate an MC.1 Excel export.

        Returns:

            {
                "valid": True/False,
                "file": "...",
                "rows": ...,
                "columns": [...]
            }

        Invalid files return valid=False rather than raising.
        """

        file_path = Path(file_path)

        # ----------------------------------------------------
        # File exists?
        # ----------------------------------------------------

        if not file_path.exists():

            return {
                "valid": False,
                "file": str(file_path),
                "error": (
                    f"MC.1 Excel file not found: "
                    f"{file_path}"
                ),
            }

        # ----------------------------------------------------
        # Is file?
        # ----------------------------------------------------

        if not file_path.is_file():

            return {
                "valid": False,
                "file": str(file_path),
                "error": (
                    f"MC.1 path is not a file: "
                    f"{file_path}"
                ),
            }

        # ----------------------------------------------------
        # Supported Excel format.
        #
        # We intentionally support only .xlsx/.xlsm here
        # because the implementation uses openpyxl.
        # ----------------------------------------------------

        if file_path.suffix.lower() not in {
            ".xlsx",
            ".xlsm",
        }:

            return {
                "valid": False,
                "file": str(file_path),
                "error": (
                    "MC.1 export must be an Excel file "
                    "(.xlsx or .xlsm)."
                ),
            }

        # ----------------------------------------------------
        # Open workbook.
        # ----------------------------------------------------

        try:

            with pd.ExcelFile(
                file_path,
                engine="openpyxl",
            ) as excel_file:

                # Sheet1 required.
                if "Sheet1" not in excel_file.sheet_names:

                    return {
                        "valid": False,
                        "file": str(file_path),
                        "error": (
                            "MC.1 workbook must contain "
                            "Sheet1."
                        ),
                    }

                df = pd.read_excel(
                    excel_file,
                    sheet_name="Sheet1",
                )

            # Normalize columns.
            df.columns = [
                str(column).strip()
                for column in df.columns
            ]

            # Validate required MC.1 columns.
            _require_columns(df)

            return {
                "valid": True,
                "file": str(file_path),
                "rows": int(len(df)),
                "columns": list(df.columns),
            }

        except Exception as exc:

            return {
                "valid": False,
                "file": str(file_path),
                "error": str(exc),
            }

    # --------------------------------------------------------
    # PROCESS ONE EXPORT
    # --------------------------------------------------------

    def process_export(
        self,
        input_file: str | Path,
        period: str,
    ) -> dict:
        """
        Process one MC.1 export.

        period must be:

            previous

        or:

            current
        """

        input_file = Path(
            input_file
        )

        # ----------------------------------------------------
        # Validate.
        # ----------------------------------------------------

        validation = self.validate_file(
            input_file
        )

        if not validation["valid"]:

            raise ValueError(
                validation["error"]
            )

        # ----------------------------------------------------
        # Normalize period.
        # ----------------------------------------------------

        period = str(
            period
        ).strip().lower()

        if period not in {
            "previous",
            "current",
        }:

            raise ValueError(
                "period must be "
                "'previous' or 'current'"
            )

        # ----------------------------------------------------
        # Output filename.
        # ----------------------------------------------------

        output_file = (
            self.output_directory
            / f"Inventory_{period.capitalize()}.xlsx"
        )

        # ----------------------------------------------------
        # Generate standardized workbook.
        # ----------------------------------------------------

        standardized_file = (
            standardize_mc1_workbook(
                input_file=input_file,
                output_file=output_file,
            )
        )

        # ----------------------------------------------------
        # Return workflow-compatible result.
        # ----------------------------------------------------

        return {
            "success": True,
            "period": period,
            "input_file": str(
                input_file
            ),
            "output_file": str(
                standardized_file
            ),
            "rows": validation["rows"],
        }

    # --------------------------------------------------------
    # PROCESS BOTH EXPORTS
    # --------------------------------------------------------

    def process_previous_and_current(
        self,
        previous_export: str | Path,
        current_export: str | Path,
    ) -> dict:
        """
        Process both previous and current MC.1 exports.
        """

        previous_result = self.process_export(
            previous_export,
            "previous",
        )

        current_result = self.process_export(
            current_export,
            "current",
        )

        return {
            "success": True,
            "previous": previous_result,
            "current": current_result,
        }