"""
MC.1 Export Manager
===================

Bridges SAP MC.1 Excel exports with the existing
SapAi inventory pipeline.

Flow:

    Raw MC.1 Excel
          ↓
    Validate structure
          ↓
    BSP Sheet1 → Sheet2 cleaning
          ↓
    SAP Excel adapter
          ↓
    Standardized SapAi Excel
          ↓
    Previous / Current inventory pipeline
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from app.services.bsp_mc1_export import (
    clean_mc1_sheet1,
)

from app.services.sap_excel_adapter import (
    load_and_adapt_sap_mc1,
)


InventoryPeriod = Literal[
    "previous",
    "current",
]


class MC1ExportManager:
    """
    Manage raw MC.1 Excel exports.

    This service does NOT communicate with SAP.

    SAP is responsible for producing the Excel file.
    This service handles everything after the export.
    """

    RAW_REQUIRED_COLUMNS = {
        "material group",
        "material",
        "storage location",
        "val. stock",
        "valstckval",
    }

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

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def validate_file(
        file_path: str | Path,
    ) -> dict:
        """
        Validate an MC.1 workbook.

        Production rule:
        ----------------
        If Sheet1 contains raw MC.1 data, Sheet1 is authoritative.

        Sheet2 is only used as a fallback when raw Sheet1
        is not available.
        """

        file_path = Path(file_path)

        if not file_path.exists():
            return {
                "valid": False,
                "message": (
                    f"MC.1 export does not exist: "
                    f"{file_path}"
                ),
                "file": str(file_path),
            }

        if file_path.suffix.lower() not in {
            ".xlsx",
            ".xlsm",
            ".xls",
        }:
            return {
                "valid": False,
                "message": (
                    "MC.1 export must be an Excel file."
                ),
                "file": str(file_path),
            }

        try:

            with pd.ExcelFile(
                file_path,
                engine="openpyxl",
            ) as workbook:

                sheet_names = list(
                    workbook.sheet_names
                )

                if not sheet_names:
                    return {
                        "valid": False,
                        "message": (
                            "MC.1 workbook contains "
                            "no worksheets."
                        ),
                        "file": str(file_path),
                    }

                def normalized_columns(
                    sheet_name: str,
                ) -> set[str]:

                    sample = pd.read_excel(
                        workbook,
                        sheet_name=sheet_name,
                        nrows=5,
                    )

                    return {
                        str(column)
                        .strip()
                        .lower()
                        for column in sample.columns
                    }

                # =================================================
                # SHEET1 = SOURCE OF TRUTH
                # =================================================

                if "Sheet1" in sheet_names:

                    columns = normalized_columns(
                        "Sheet1"
                    )

                    if (
                        MC1ExportManager
                        .RAW_REQUIRED_COLUMNS
                        .issubset(columns)
                    ):

                        return {
                            "valid": True,
                            "format": "raw_mc1",
                            "sheet": "Sheet1",
                            "file": str(file_path),
                            "sheets": sheet_names,
                        }

                # =================================================
                # FALLBACK TO CLEANED SHEET
                # =================================================

                cleaned_required = {
                    "material code",
                    "material code desc",
                    "plant",
                    "uom",
                }

                for sheet_name in sheet_names:

                    columns = normalized_columns(
                        sheet_name
                    )

                    if cleaned_required.issubset(
                        columns
                    ):

                        return {
                            "valid": True,
                            "format": "cleaned_mc1",
                            "sheet": sheet_name,
                            "file": str(file_path),
                            "sheets": sheet_names,
                        }

                return {
                    "valid": False,
                    "message": (
                        "Workbook does not contain "
                        "recognized raw MC.1 data "
                        "in Sheet1 or a cleaned MC.1 sheet."
                    ),
                    "file": str(file_path),
                    "sheets": sheet_names,
                }

        except Exception as exc:

            return {
                "valid": False,
                "message": (
                    f"Unable to inspect MC.1 workbook: "
                    f"{exc}"
                ),
                "file": str(file_path),
            }

    # =========================================================
    # PROCESS ONE EXPORT
    # =========================================================

    def process_export(
        self,
        file_path: str | Path,
        period: InventoryPeriod,
    ) -> dict:
        """
        Process one MC.1 export.

        period:
            "previous"
            "current"
        """

        file_path = Path(
            file_path
        )

        if period not in {
            "previous",
            "current",
        }:
            raise ValueError(
                "period must be 'previous' or 'current'."
            )

        # -----------------------------------------------------
        # Validate
        # -----------------------------------------------------

        validation = self.validate_file(
            file_path
        )

        if not validation["valid"]:

            raise ValueError(
                validation["message"]
            )

        # -----------------------------------------------------
        # Load through the existing SAP Excel adapter.
        # -----------------------------------------------------

        standardized = (
            load_and_adapt_sap_mc1(
                file_path
            )
        )

        if standardized.empty:

            raise ValueError(
                "MC.1 export contains no inventory records."
            )

        # -----------------------------------------------------
        # Output name
        # -----------------------------------------------------

        output_name = (
            f"mc1_{period}_standardized.xlsx"
        )

        output_file = (
            self.output_directory
            / output_name
        )

        # -----------------------------------------------------
        # Save standardized data
        # -----------------------------------------------------

        with pd.ExcelWriter(
            output_file,
            engine="openpyxl",
        ) as writer:

            standardized.to_excel(
                writer,
                sheet_name="Inventory",
                index=False,
            )

        # -----------------------------------------------------
        # Build summary
        # -----------------------------------------------------

        material_codes = (
            standardized[
                "Material_Code"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        inventory_keys = (
            standardized[
                "Inventory_Key"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        result = {
            "success": True,
            "period": period,
            "source_file": str(
                file_path
            ),
            "standardized_file": str(
                output_file
            ),
            "source_format": validation.get(
                "format"
            ),
            "source_sheet": validation.get(
                "sheet"
            ),
            "rows": int(
                len(standardized)
            ),
            "unique_material_codes": int(
                material_codes[
                    material_codes != ""
                ].nunique()
            ),
            "unique_inventory_keys": int(
                inventory_keys[
                    inventory_keys != ""
                ].nunique()
            ),
            "columns": [
                str(column)
                for column in standardized.columns
            ],
        }

        return result

    # =========================================================
    # PROCESS BOTH PERIODS
    # =========================================================

    def process_previous_and_current(
        self,
        previous_file: str | Path,
        current_file: str | Path,
    ) -> dict:
        """
        Process both MC.1 exports and return their
        standardized file information.
        """

        previous = self.process_export(
            previous_file,
            "previous",
        )

        current = self.process_export(
            current_file,
            "current",
        )

        return {
            "success": True,
            "previous": previous,
            "current": current,
        }