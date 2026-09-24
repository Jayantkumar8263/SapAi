"""
Inventory Database → ZMAT-FUND_POPR Pipeline
=============================================

Connects the database layer to the existing
ZMAT-FUND_POPR batch preparation module.

Process:

    mminv_new
        ↓
    Read Inventory
        ↓
    Extract unique Material Codes
        ↓
    Split into 20,000-record batches
        ↓
    ZMAT-FUND_POPR

IMPORTANT
---------
This module does NOT implement another batching algorithm.

It reuses the existing:

    extract_unique_material_codes()
    create_material_batches()

from zmat_fund_popr_batcher.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.inventory_database import (
    InventoryDatabase,
)

from app.services.zmat_fund_popr_batcher import (
    DEFAULT_BATCH_SIZE,
    create_material_batches,
    extract_unique_material_codes,
    save_material_batches,
)


# ============================================================
# DATABASE → BATCH PIPELINE
# ============================================================


class InventoryDatabaseBatchPipeline:
    """
    Connects mminv_new database data to the existing
    ZMAT-FUND_POPR batch preparation logic.
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

    # =========================================================
    # READ MATERIAL CODES FROM DATABASE
    # =========================================================

    def get_material_codes(
        self,
        table_name: str = "mminv_new",
        material_code_column: str = "Material Code",
    ) -> list[str]:
        """
        Read the inventory table and extract unique
        material codes.

        Uses the exact same normalization and ordering
        rules as the existing ZMAT-FUND_POPR batcher.
        """

        dataframe = (
            self.database.read_table(
                table_name
            )
        )

        return (
            extract_unique_material_codes(
                dataframe,
                material_code_column,
            )
        )

    # =========================================================
    # CREATE BATCHES
    # =========================================================

    def create_batches(
        self,
        table_name: str = "mminv_new",
        material_code_column: str = "Material Code",
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> dict[str, Any]:
        """
        Read unique material codes from the database and
        split them using the existing ZMAT-FUND_POPR batcher.
        """

        dataframe = (
            self.database.read_table(
                table_name
            )
        )

        unique_codes = (
            extract_unique_material_codes(
                dataframe,
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
            "table": table_name,
            "total_input_rows": int(
                len(dataframe)
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

    # =========================================================
    # CREATE AND SAVE BATCH FILES
    # =========================================================

    def create_batch_files(
        self,
        output_directory: str | Path,
        table_name: str = "mminv_new",
        material_code_column: str = "Material Code",
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> dict[str, Any]:
        """
        Create ZMAT-FUND_POPR batches and save them as TXT
        files.

        The actual SAP input format will be finalized after
        real SAP ZMAT-FUND_POPR screen validation.
        """

        result = (
            self.create_batches(
                table_name=table_name,
                material_code_column=(
                    material_code_column
                ),
                batch_size=batch_size,
            )
        )

        batch_files = (
            save_material_batches(
                result["batches"],
                output_directory,
            )
        )

        result[
            "batch_files"
        ] = batch_files

        return result

    # =========================================================
    # COMPLETE DATABASE → ZMAT PREPARATION
    # =========================================================

    def prepare(
        self,
        table_name: str = "mminv_new",
        material_code_column: str = "Material Code",
        batch_size: int = DEFAULT_BATCH_SIZE,
        output_directory: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Complete database → ZMAT-FUND_POPR preparation.

        If output_directory is supplied, batch TXT files are
        created as well.
        """

        result = (
            self.create_batches(
                table_name=table_name,
                material_code_column=(
                    material_code_column
                ),
                batch_size=batch_size,
            )
        )

        if output_directory is not None:

            result[
                "batch_files"
            ] = save_material_batches(
                result["batches"],
                output_directory,
            )

        return result