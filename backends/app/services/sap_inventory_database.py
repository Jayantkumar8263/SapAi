"""
SAP Inventory Database Adapter
==============================

Connects the BSP Final Inventory workbook to the database
stage represented by mminv_new.

IMPORTANT
---------
For now mminv_new is treated as the SAP-side inventory table,
but the actual SAP database connection mechanism has NOT been
validated yet.

Therefore this service works through the existing generic
InventoryDatabase abstraction.

Real SAP database connectivity can be plugged in later
without changing the inventory workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.services.inventory_database import InventoryDatabase


class SAPInventoryDatabase:
    """
    Adapter between BSP Inventory data and the database layer.

    Current target tables:

        mminv_new
        mminv1_new

    The actual SAP database connection is intentionally left
    outside this class until the real SAP DB interface is known.
    """

    INVENTORY_TABLE = "mminv_new"

    INVENTORY_PO_TABLE = "mminv1_new"

    INVENTORY_SHEET = "Inventory"

    def __init__(
        self,
        database: InventoryDatabase,
    ):
        self.database = database

    # =========================================================
    # LOAD FINAL INVENTORY
    # =========================================================

    @classmethod
    def load_inventory_sheet(
        cls,
        workbook_file: str | Path,
    ) -> pd.DataFrame:
        """
        Load the final Inventory sheet from the BSP workbook.
        """

        workbook_file = Path(workbook_file)

        if not workbook_file.exists():
            raise FileNotFoundError(
                f"Inventory workbook was not found: "
                f"{workbook_file}"
            )

        df = pd.read_excel(
            workbook_file,
            sheet_name=cls.INVENTORY_SHEET,
        )

        if df.empty:
            raise ValueError(
                "The Inventory sheet is empty."
            )

        # Clean column names.
        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        required_columns = [
            "Material Code",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                "Inventory sheet is missing required "
                f"columns: {missing_columns}"
            )

        return df

    # =========================================================
    # WRITE mminv_new
    # =========================================================

    def replace_inventory_table(
        self,
        workbook_file: str | Path,
    ) -> dict[str, Any]:
        """
        Replace mminv_new with the Inventory sheet.

        This mirrors the documented BSP process:

            old mminv_new
                  ↓
             delete/replace
                  ↓
            Inventory sheet
        """

        df = self.load_inventory_sheet(
            workbook_file
        )

        rows_before = len(df)

        self.database.replace_table(
            table_name=self.INVENTORY_TABLE,
            dataframe=df,
        )

        rows_after = self.database.count_rows(
            self.INVENTORY_TABLE
        )

        if rows_after != rows_before:
            raise RuntimeError(
                "mminv_new row-count verification failed. "
                f"Expected {rows_before}, "
                f"found {rows_after}."
            )

        return {
            "success": True,
            "table": self.INVENTORY_TABLE,
            "rows_imported": rows_after,
            "workbook": str(
                Path(workbook_file)
            ),
        }

    # =========================================================
    # UNIQUE MATERIAL CODES
    # =========================================================

    def get_unique_material_codes(
        self,
    ) -> list[str]:
        """
        Read unique Material Codes from mminv_new.

        These codes are the input for the next stage:

            mminv_new
                 ↓
            unique codes
                 ↓
            20,000-record batches
        """

        codes = (
            self.database.get_unique_material_codes(
                table_name=self.INVENTORY_TABLE
            )
        )

        normalized: list[str] = []

        seen: set[str] = set()

        for value in codes:

            if value is None:
                continue

            code = str(value).strip()

            if not code:
                continue

            # Handle Excel/Pandas numeric representation.
            if code.endswith(".0"):
                try:
                    number = float(code)

                    if number.is_integer():
                        code = str(int(number))

                except ValueError:
                    pass

            if code in seen:
                continue

            seen.add(code)
            normalized.append(code)

        return normalized

    # =========================================================
    # DATABASE + MATERIAL CODE PREPARATION
    # =========================================================

    def prepare_material_codes(
        self,
        workbook_file: str | Path,
    ) -> dict[str, Any]:
        """
        Import Inventory into mminv_new and prepare unique
        material codes for ZMAT-FUND_POPR.
        """

        import_result = (
            self.replace_inventory_table(
                workbook_file
            )
        )

        material_codes = (
            self.get_unique_material_codes()
        )

        return {
            "success": True,
            "database": import_result,
            "material_code_count": len(
                material_codes
            ),
            "material_codes": material_codes,
        }