"""
BSP Inventory Database Stage
============================

Connects the generated BSP Inventory workbook to:

    mminv_new
        ↓
    InventoryDatabaseBatchPipeline
        ↓
    ZMAT-FUND_POPR batches

IMPORTANT
---------
This module does not decide how the production SAP database
is connected.

It receives an InventoryDatabase instance.

That means:

    Tests
        → SQLite-backed InventoryDatabase

    Production
        → SAP-compatible InventoryDatabase adapter

The database-specific connection remains outside this stage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
)

from app.services.inventory_db_batch_pipeline import (
    InventoryDatabaseBatchPipeline,
)


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_TABLE_NAME = "mminv_new"

DEFAULT_MATERIAL_CODE_COLUMN = "Material Code"

DEFAULT_BATCH_SIZE = 20_000


# ============================================================
# DATABASE STAGE
# ============================================================


class InventoryDatabaseStage:
    """
    Handles:

        Final Inventory
              ↓
        mminv_new
              ↓
        unique material codes
              ↓
        20,000-record batches
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

        self.batch_pipeline = (
            InventoryDatabaseBatchPipeline(
                database
            )
        )

        # ========================================================
    # LOAD BSP INVENTORY WORKBOOK
    # ========================================================

    def load_inventory_workbook(
        self,
        workbook_file: str | Path,
    ) -> pd.DataFrame:
        """
        Load the final Inventory sheet from the BSP workbook.

        Expected workbook:

            BSP_Final_Inventory.xlsx

        Expected sheet:

            Inventory
        """

        workbook_file = Path(
            workbook_file
        )

        if not workbook_file.exists():
            raise FileNotFoundError(
                f"BSP Inventory workbook was not found: "
                f"{workbook_file}"
            )

        dataframe = pd.read_excel(
            workbook_file,
            sheet_name="Inventory",
        )

        if dataframe.empty:
            raise ValueError(
                "The BSP Inventory sheet is empty."
            )

        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

        if "Material Code" not in dataframe.columns:
            raise ValueError(
                "BSP Inventory sheet is missing "
                "'Material Code'."
            )

        return dataframe
    
    # ========================================================
    # UPDATE mminv_new
    # ========================================================

    def update_mminv_new(
        self,
        inventory_dataframe: pd.DataFrame,
        table_name: str = DEFAULT_TABLE_NAME,
    ) -> dict[str, Any]:
        """
        Replace mminv_new with the generated Inventory data.

        This mirrors the documented BSP process:

            delete old mminv_new
            ↓
            import Inventory
            ↓
            mminv_new updated
        """

        if inventory_dataframe is None:
            raise ValueError(
                "inventory_dataframe cannot be None."
            )

        if not isinstance(
            inventory_dataframe,
            pd.DataFrame,
        ):
            raise TypeError(
                "inventory_dataframe must be a pandas DataFrame."
            )

        if inventory_dataframe.empty:
            raise ValueError(
                "Inventory dataframe is empty."
            )

        if (
            DEFAULT_MATERIAL_CODE_COLUMN
            not in inventory_dataframe.columns
        ):
            raise ValueError(
                "Inventory dataframe must contain "
                f"'{DEFAULT_MATERIAL_CODE_COLUMN}'."
            )

        # ----------------------------------------------------
        # Replace database table
        # ----------------------------------------------------

        self.database.replace_table(
            dataframe=inventory_dataframe,
            table_name=table_name,
        )

        # ----------------------------------------------------
        # Verify row count
        # ----------------------------------------------------

        database_rows = (
            self.database.count_rows(
                table_name
            )
        )

        input_rows = len(
            inventory_dataframe
        )

        if database_rows != input_rows:
            raise RuntimeError(
                "mminv_new row-count verification failed. "
                f"Expected {input_rows}, "
                f"found {database_rows}."
            )

        return {
            "success": True,
            "table": table_name,
            "input_rows": int(input_rows),
            "database_rows": int(database_rows),
        }

    # ========================================================
    # PREPARE ZMAT BATCHES
    # ========================================================

    def prepare_zmat_batches(
        self,
        table_name: str = DEFAULT_TABLE_NAME,
        material_code_column: str = DEFAULT_MATERIAL_CODE_COLUMN,
        batch_size: int = DEFAULT_BATCH_SIZE,
        output_directory: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Read mminv_new and prepare ZMAT-FUND_POPR batches.

        Reuses the existing
        InventoryDatabaseBatchPipeline.
        """

        result = (
            self.batch_pipeline.prepare(
                table_name=table_name,
                material_code_column=material_code_column,
                batch_size=batch_size,
                output_directory=output_directory,
            )
        )

        return result

    # ========================================================
    # COMPLETE STAGE
    # ========================================================

    def run(
        self,
        inventory_dataframe: pd.DataFrame,
        table_name: str = DEFAULT_TABLE_NAME,
        material_code_column: str = DEFAULT_MATERIAL_CODE_COLUMN,
        batch_size: int = DEFAULT_BATCH_SIZE,
        output_directory: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Complete database stage:

            Inventory
                ↓
            mminv_new
                ↓
            unique material codes
                ↓
            ZMAT batches
        """

        database_result = (
            self.update_mminv_new(
                inventory_dataframe=inventory_dataframe,
                table_name=table_name,
            )
        )

        batch_result = (
            self.prepare_zmat_batches(
                table_name=table_name,
                material_code_column=material_code_column,
                batch_size=batch_size,
                output_directory=output_directory,
            )
        )

        return {
            "success": True,
            "database": database_result,
            "batches": batch_result,
        }
    
    
        # ========================================================
    # RUN FROM BSP WORKBOOK
    # ========================================================

    def run_from_workbook(
        self,
        workbook_file: str | Path,
        table_name: str = DEFAULT_TABLE_NAME,
        material_code_column: str = DEFAULT_MATERIAL_CODE_COLUMN,
        batch_size: int = DEFAULT_BATCH_SIZE,
        output_directory: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Complete database stage starting from the actual
        BSP Final Inventory workbook.

        Flow:

            BSP_Final_Inventory.xlsx
                    ↓
                Inventory
                    ↓
                mminv_new
                    ↓
             unique Material Codes
                    ↓
             20,000-record batches
        """

        inventory_dataframe = (
            self.load_inventory_workbook(
                workbook_file
            )
        )

        result = self.run(
            inventory_dataframe=inventory_dataframe,
            table_name=table_name,
            material_code_column=material_code_column,
            batch_size=batch_size,
            output_directory=output_directory,
        )

        result["workbook"] = str(
            Path(workbook_file)
        )

        result["inventory_rows"] = int(
            len(inventory_dataframe)
        )

        return result