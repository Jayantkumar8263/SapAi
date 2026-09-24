"""
Inventory PO → mminv1_new Database Pipeline
============================================

Connects the final Inventory PO workbook to the database
stage of the BSP inventory automation process.

Documented BSP flow:

    Inventory PO.xlsx
          ↓
    Delete/replace old mminv1_new
          ↓
    Import Inventory PO
          ↓
    Verify database
          ↓
    Final database stage complete

IMPORTANT
---------
This module does not assume a production database technology.

It reuses the existing InventoryDatabase service.

SQLite is used only for automated tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
)


DEFAULT_TABLE_NAME = "mminv1_new"
DEFAULT_SHEET_NAME = "Inventory PO"


class InventoryPODatabasePipeline:
    """
    Imports the final Inventory PO workbook into mminv1_new.
    """

    def __init__(
        self,
        database: InventoryDatabase,
    ):
        if database is None:
            raise ValueError(
                "database cannot be None."
            )

        self.database = database

    # ========================================================
    # READ INVENTORY PO
    # ========================================================

    @staticmethod
    def read_inventory_po(
        input_file: str | Path,
        sheet_name: str = DEFAULT_SHEET_NAME,
    ) -> pd.DataFrame:
        """
        Read the Inventory PO worksheet.
        """

        input_path = Path(
            input_file
        )

        if not input_path.exists():
            raise FileNotFoundError(
                f"Inventory PO file not found: "
                f"{input_path}"
            )

        if input_path.suffix.lower() not in {
            ".xlsx",
            ".xls",
        }:
            raise ValueError(
                "Inventory PO input must be an Excel file."
            )

        dataframe = pd.read_excel(
            input_path,
            sheet_name=sheet_name,
        )

        if dataframe.empty:
            raise ValueError(
                "Inventory PO contains no records."
            )

        # Normalize column names exactly as the existing
        # database service does.
        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

        return dataframe

    # ========================================================
    # VALIDATE INVENTORY PO
    # ========================================================

    @staticmethod
    def validate_inventory_po(
        dataframe: pd.DataFrame,
    ) -> dict[str, Any]:
        """
        Validate the final Inventory PO dataframe.

        At this stage we validate only structural requirements
        that are supported by the existing BSP pipeline.

        We do NOT invent production-specific column rules.
        """

        if not isinstance(
            dataframe,
            pd.DataFrame,
        ):
            raise TypeError(
                "dataframe must be a pandas DataFrame."
            )

        if dataframe.empty:
            return {
                "valid": False,
                "rows": 0,
                "columns": list(
                    dataframe.columns
                ),
                "errors": [
                    "Inventory PO contains no records."
                ],
            }

        columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

        errors: list[str] = []

        if "Material Code" not in columns:
            errors.append(
                "Required column 'Material Code' "
                "was not found."
            )

        return {
            "valid": len(errors) == 0,
            "rows": int(
                len(dataframe)
            ),
            "columns": columns,
            "errors": errors,
        }

    # ========================================================
    # IMPORT INTO mminv1_new
    # ========================================================

    def import_inventory_po(
        self,
        dataframe: pd.DataFrame,
        table_name: str = DEFAULT_TABLE_NAME,
    ) -> dict[str, Any]:
        """
        Replace the contents of mminv1_new with Inventory PO.
        """

        validation = (
            self.validate_inventory_po(
                dataframe
            )
        )

        if not validation["valid"]:
            return {
                "success": False,
                "table": table_name,
                "rows": validation["rows"],
                "error": "; ".join(
                    validation["errors"]
                ),
            }

        result = (
            self.database.replace_table(
                dataframe,
                table_name,
            )
        )

        imported_rows = (
            self.database.count_rows(
                table_name
            )
        )

        expected_rows = int(
            len(dataframe)
        )

        if imported_rows != expected_rows:
            return {
                "success": False,
                "table": table_name,
                "expected_rows": expected_rows,
                "imported_rows": imported_rows,
                "error": (
                    "Database row-count verification failed."
                ),
            }

        return {
            "success": True,
            "table": table_name,
            "expected_rows": expected_rows,
            "imported_rows": imported_rows,
            "columns": list(
                dataframe.columns
            ),
        }

    # ========================================================
    # COMPLETE FILE → DATABASE PIPELINE
    # ========================================================

    def run(
        self,
        input_file: str | Path,
        table_name: str = DEFAULT_TABLE_NAME,
        sheet_name: str = DEFAULT_SHEET_NAME,
    ) -> dict[str, Any]:
        """
        Complete:

            Inventory PO.xlsx
                  ↓
            Read Inventory PO
                  ↓
            Validate
                  ↓
            replace mminv1_new
                  ↓
            Verify row count
        """

        input_path = Path(
            input_file
        )

        try:

            dataframe = (
                self.read_inventory_po(
                    input_path,
                    sheet_name,
                )
            )

        except Exception as exc:

            return {
                "success": False,
                "input_file": str(
                    input_path
                ),
                "table": table_name,
                "error": str(exc),
            }

        validation = (
            self.validate_inventory_po(
                dataframe
            )
        )

        if not validation["valid"]:

            return {
                "success": False,
                "input_file": str(
                    input_path
                ),
                "table": table_name,
                "validation": validation,
                "error": "; ".join(
                    validation["errors"]
                ),
            }

        try:

            database_result = (
                self.import_inventory_po(
                    dataframe,
                    table_name,
                )
            )

        except Exception as exc:

            return {
                "success": False,
                "input_file": str(
                    input_path
                ),
                "table": table_name,
                "validation": validation,
                "error": str(exc),
            }

        return {
            "success": bool(
                database_result.get(
                    "success",
                    False,
                )
            ),
            "input_file": str(
                input_path
            ),
            "table": table_name,
            "input_rows": int(
                len(dataframe)
            ),
            "validation": validation,
            "database": database_result,
            "error": database_result.get(
                "error"
            ),
        }