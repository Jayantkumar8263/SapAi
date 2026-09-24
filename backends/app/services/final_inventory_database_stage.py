"""
Final Inventory PO → mminv1_new Database Stage
================================================

BSP process:

    Inventory PO.xlsx
          ↓
    Inventory PO sheet
          ↓
    mminv1_new
          ↓
    Verify database update

This module does NOT implement database access itself.

It delegates the actual database operation to the
existing InventoryPODatabasePipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.inventory_po_database_pipeline import (
    InventoryPODatabasePipeline,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TABLE_NAME = "mminv1_new"

DEFAULT_SHEET_NAME = "Inventory PO"


# ============================================================
# FINAL DATABASE STAGE
# ============================================================


class FinalInventoryDatabaseStage:
    """
    Handles the final BSP database stage.

    Process:

        Inventory PO.xlsx
              ↓
        Inventory PO sheet
              ↓
        mminv1_new
    """

    def __init__(
        self,
        database: object,
    ):
        if database is None:
            raise ValueError(
                "database cannot be None."
            )

        self.database = database

        self.pipeline = (
            InventoryPODatabasePipeline(
                database
            )
        )

    # ========================================================
    # RUN
    # ========================================================

    def run(
        self,
        inventory_po_file: str | Path,
        table_name: str = DEFAULT_TABLE_NAME,
        sheet_name: str = DEFAULT_SHEET_NAME,
        date_columns=None,
    ) -> dict[str, Any]:
        """
        Import Inventory PO.xlsx into mminv1_new.

        Parameters
        ----------
        inventory_po_file:
            Path to Inventory PO.xlsx.

        table_name:
            Destination database table.

        sheet_name:
            Excel sheet containing Inventory PO data.

        date_columns:
            Optional date columns passed to the existing
            database pipeline.
        """

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if inventory_po_file is None:
            raise ValueError(
                "inventory_po_file is required."
            )

        inventory_po_path = Path(
            inventory_po_file
        )

        if not inventory_po_path.exists():
            raise FileNotFoundError(
                "Inventory PO file not found: "
                f"{inventory_po_path}"
            )

        if (
            inventory_po_path.suffix.lower()
            != ".xlsx"
        ):
            raise ValueError(
                "Inventory PO file must be an .xlsx file."
            )

        # ----------------------------------------------------
        # DATABASE PIPELINE
        # ----------------------------------------------------

        result = self.pipeline.run(
            input_file=inventory_po_path,
            table_name=table_name,
            sheet_name=sheet_name,
        )

        # ----------------------------------------------------
        # FAILURE HANDLING
        # ----------------------------------------------------

        if not result.get(
            "success",
            False,
        ):
            raise RuntimeError(
                result.get(
                    "message",
                    "mminv1_new update failed.",
                )
            )

        # ----------------------------------------------------
# VERIFY ACTUAL DATABASE ROW COUNT
# ----------------------------------------------------

        rows_imported = self.database.count_rows(
            table_name
            )       

# ----------------------------------------------------
# FINAL RESULT
# ----------------------------------------------------

        return {
    "success": True,
    "table_name": table_name,
    "sheet_name": sheet_name,
    "inventory_po_file": str(
        inventory_po_path
    ),
    "rows_imported": int(
        rows_imported
    ),
    "message": (
        "Inventory PO successfully "
        "imported into mminv1_new."
    ),
    "pipeline": result,
}