"""
Inventory → ZMAT-FUND_POPR Orchestrator
========================================

Connects the already-tested inventory database/batching
pipeline to the already-tested ZMAT-FUND_POPR workflow.

Process:

    mminv_new
        ↓
    unique material codes
        ↓
    20,000-record batches
        ↓
    ZMAT-FUND_POPR
        ↓
    optional background submission

This module does NOT implement:
    - database logic
    - material-code normalization
    - batch splitting
    - SAP GUI control logic

Those responsibilities remain in their existing modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.inventory_db_batch_pipeline import (
    InventoryDatabaseBatchPipeline,
)

from app.services.zmat_fund_popr_workflow import (
    ZMATFundPOPRWorkflow,
)


class InventoryZMATOrchestrator:
    """
    Connect inventory database preparation with the
    ZMAT-FUND_POPR SAP workflow.
    """

    def __init__(
        self,
        batch_pipeline: InventoryDatabaseBatchPipeline,
        zmat_workflow: ZMATFundPOPRWorkflow,
    ):
        if batch_pipeline is None:
            raise ValueError(
                "batch_pipeline cannot be None."
            )

        if zmat_workflow is None:
            raise ValueError(
                "zmat_workflow cannot be None."
            )

        self.batch_pipeline = batch_pipeline
        self.zmat_workflow = zmat_workflow

    # ========================================================
    # PREPARE DATABASE BATCHES
    # ========================================================

    def prepare_batches(
        self,
        table_name: str = "mminv_new",
        material_code_column: str = "Material Code",
        batch_size: int = 20_000,
    ) -> dict[str, Any]:
        """
        Prepare unique material-code batches from the
        inventory database.

        This delegates completely to the existing
        InventoryDatabaseBatchPipeline.

        No SAP execution occurs here.
        """

        return self.batch_pipeline.create_batches(
            table_name=table_name,
            material_code_column=material_code_column,
            batch_size=batch_size,
        )

    # ========================================================
    # PREPARE AND SAVE DATABASE BATCHES
    # ========================================================

    def prepare_batch_files(
        self,
        output_directory: str | Path,
        table_name: str = "mminv_new",
        material_code_column: str = "Material Code",
        batch_size: int = 20_000,
    ) -> dict[str, Any]:
        """
        Prepare unique material-code batches from mminv_new
        and save them as TXT files.

        This method performs preparation only.

        It does NOT execute SAP.

        Flow:

            mminv_new
                ↓
            unique Material Codes
                ↓
            20,000-record batches
                ↓
            TXT files

        SAP execution is handled separately by:

            ZMATFundPOPRWorkflow
        """

        if output_directory is None:
            raise ValueError(
                "output_directory cannot be None."
            )

        result = (
            self.batch_pipeline.create_batch_files(
                output_directory=output_directory,
                table_name=table_name,
                material_code_column=material_code_column,
                batch_size=batch_size,
            )
        )

        result["preparation_only"] = True
        result["sap_execution"] = False

        return result

    # ========================================================
    # RUN ALL BATCHES
    # ========================================================

    def run(
        self,
        table_name: str = "mminv_new",
        material_code_column: str = "Material Code",
        batch_size: int = 20_000,
        submit_background: bool = False,
    ) -> dict[str, Any]:
        """
        Prepare material batches from mminv_new and execute
        every batch through ZMAT-FUND_POPR.

        Parameters
        ----------
        table_name:
            Inventory database table.

        material_code_column:
            Material-code column.

        batch_size:
            Maximum number of material codes per batch.

        submit_background:
            Whether each ZMAT batch should submit to
            background processing.

            False is the safe default because the exact
            real-SAP background sequence has not yet been
            validated.
        """

        preparation = self.prepare_batches(
            table_name=table_name,
            material_code_column=material_code_column,
            batch_size=batch_size,
        )

        batches = preparation["batches"]

        result: dict[str, Any] = {
            "success": False,
            "table": table_name,
            "total_input_rows": (
                preparation["total_input_rows"]
            ),
            "unique_material_codes": (
                preparation["unique_material_codes"]
            ),
            "batch_size": (
                preparation["batch_size"]
            ),
            "batch_count": (
                preparation["batch_count"]
            ),
            "submit_background": (
                submit_background
            ),
            "batches": [],
        }

        # ----------------------------------------------------
        # No material codes
        # ----------------------------------------------------

        if not batches:

            result["success"] = True

            return result

        # ----------------------------------------------------
        # Execute each batch
        # ----------------------------------------------------

        for index, batch in enumerate(
            batches,
            start=1,
        ):

            batch_result = (
                self.zmat_workflow.run(
                    batch_number=index,
                    material_codes=batch,
                    submit_background=(
                        submit_background
                    ),
                )
            )

            result["batches"].append(
                batch_result
            )

            # ------------------------------------------------
            # Stop immediately if SAP batch fails.
            # ------------------------------------------------

            if not batch_result.get(
                "success",
                False,
            ):

                result[
                    "failed_batch"
                ] = index

                result[
                    "error"
                ] = (
                    batch_result.get(
                        "error"
                    )
                    or
                    f"ZMAT-FUND_POPR "
                    f"batch {index} failed."
                )

                return result

        # ----------------------------------------------------
        # All batches completed
        # ----------------------------------------------------

        result["success"] = True

        return result

    # ========================================================
    # RUN FROM SAVED BATCH FILES
    # ========================================================

    def run_saved_batches(
        self,
        batch_files: list[str | Path],
        submit_background: bool = False,
    ) -> dict[str, Any]:
        """
        Execute previously-created ZMAT batch TXT files.

        This is useful when batch preparation and SAP execution
        are intentionally separated.
        """

        result: dict[str, Any] = {
            "success": False,
            "batch_count": len(batch_files),
            "submit_background": (
                submit_background
            ),
            "batches": [],
        }

        if not batch_files:

            result["success"] = True

            return result

        for index, batch_file in enumerate(
            batch_files,
            start=1,
        ):

            batch_result = (
                self.zmat_workflow.run_from_file(
                    batch_number=index,
                    batch_file=batch_file,
                    submit_background=(
                        submit_background
                    ),
                )
            )

            result["batches"].append(
                batch_result
            )

            if not batch_result.get(
                "success",
                False,
            ):

                result[
                    "failed_batch"
                ] = index

                result[
                    "error"
                ] = (
                    batch_result.get(
                        "error"
                    )
                    or
                    f"ZMAT-FUND_POPR "
                    f"batch {index} failed."
                )

                return result

        result["success"] = True

        return result