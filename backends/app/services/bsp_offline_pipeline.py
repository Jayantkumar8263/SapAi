"""
BSP offline pipeline
====================

This module contains the part of the BSP automation that can be
completed without an active SAP session.

Boundary:
    MC.1 Excel exports
        -> BSP Inventory workbook
        -> mminv_new
        -> unique material codes / 20,000-code batches
        -> WAITING_FOR_SAP

A second method resumes after SAP has produced spool TXT files:
    spool TXT files
        -> Inventory PO.xlsx
        -> mminv1_new

The real SAP operations (MC.1 export, ZMMRIREP, ZMAT, SM37 and
spool extraction) are deliberately NOT simulated here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from app.agent.state import AgentState
from app.services.bsp_workbook_builder import build_bsp_workbook
from app.services.final_inventory_database_stage import FinalInventoryDatabaseStage
from app.services.inventory_database import InventoryDatabase
from app.services.inventory_database_stage import InventoryDatabaseStage
from app.services.inventory_po_builder import build_inventory_po
from app.services.bsp_mc1_export import clean_mc1_sheet1
import pandas as pd


class BSPOfflinePipeline:
    """Run all BSP stages that do not require live SAP GUI access."""

    WAITING_FOR_SAP = "waiting_for_sap"
    COMPLETED = "completed"

    def __init__(
        self,
        state: AgentState,
        database: InventoryDatabase,
        run_directory: str | Path | None = None,
    ) -> None:
        if state is None:
            raise ValueError("state cannot be None.")
        if database is None:
            raise ValueError("database cannot be None.")

        self.state = state
        self.database = database

        if run_directory is None:
            run_directory = (
                Path(state.data_directory)
                / "runs"
                / state.run_id
            )

        self.run_directory = Path(run_directory)
        self.mc1_directory = self.run_directory / "mc1"
        self.batch_directory = self.run_directory / "zmat_batches"
        self.spool_directory = self.run_directory / "spool"
        self.output_directory = self.run_directory / "output"
        self.manifest_file = self.run_directory / "manifest.json"

        for directory in (
            self.mc1_directory,
            self.batch_directory,
            self.spool_directory,
            self.output_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # MANIFEST
    # ---------------------------------------------------------

    def _write_manifest(self, status: str, **extra: Any) -> Path:
        manifest = {
            "run_id": self.state.run_id,
            "status": status,
            "run_directory": str(self.run_directory),
            "completed_steps": list(self.state.completed_steps),
            "artifacts": extra,
        }
        self.manifest_file.write_text(
            json.dumps(manifest, indent=2, default=str),
            encoding="utf-8",
        )
        return self.manifest_file

    # ---------------------------------------------------------
    # PRE-SAP PREPARATION
    # ---------------------------------------------------------

    def prepare_for_sap(
        self,
        previous_export: str | Path,
        current_export: str | Path,
        reference_file: str | Path,
    ) -> dict[str, Any]:
        """
        Complete the offline portion of BSP automation.

        Produces:
            - standardized MC.1 files
            - BSP five-sheet workbook
            - mminv_new
            - unique material-code batches
            - persistent run manifest

        Stops explicitly at the SAP boundary instead of pretending
        that ZMAT/SM37/spool have run.
        """

        previous_export = Path(previous_export)
        current_export = Path(current_export)
        reference_file = Path(reference_file)

        for path, label in (
            (previous_export, "previous MC.1 export"),
            (current_export, "current MC.1 export"),
            (reference_file, "RI/Capital reference workbook"),
        ):
            if not path.exists():
                raise FileNotFoundError(f"{label} not found: {path}")

        self.state.status = "running"

        try:
            # 1. MC.1 export handoff/standardization
            self.state.start_step("Prepare MC.1 Inventory Files")
            previous_file = self.mc1_directory / "mc1_previous_cleaned.xlsx"
            current_file = self.mc1_directory / "mc1_current_cleaned.xlsx"

            for source, target in ((previous_export, previous_file), (current_export, current_file)):
                raw = pd.read_excel(source, sheet_name="Sheet1")
                cleaned = clean_mc1_sheet1(raw)
                with pd.ExcelWriter(target, engine="openpyxl") as writer:
                    cleaned.to_excel(writer, sheet_name="Sheet2", index=False)

            previous_result = {
                "success": True,
                "period": "previous",
                "source_file": str(previous_export),
                "standardized_file": str(previous_file),
            }
            current_result = {
                "success": True,
                "period": "current",
                "source_file": str(current_export),
                "standardized_file": str(current_file),
            }
            self.state.previous_inventory_file = str(previous_file)
            self.state.current_inventory_file = str(current_file)
            handoff = {
                "success": True,
                "previous": previous_result,
                "current": current_result,
                "previous_inventory_file": str(previous_file),
                "current_inventory_file": str(current_file),
            }
            self.state.add_result("mc1_export_handoff", handoff)
            self.state.complete_step("Prepare MC.1 Inventory Files", handoff)

            # 2. Build final BSP workbook directly.  Do NOT call the
            # generic InventoryWorkflow.run(), because its optional
            # change-analysis stage is not part of the documented BSP path.
            self.state.start_step("Build BSP Inventory Workbook")
            workbook_file = self.output_directory / "BSP_Inventory.xlsx"
            workbook_result = build_bsp_workbook(
                previous_file=previous_file,
                present_file=current_file,
                reference_file=reference_file,
                output_file=workbook_file,
            )
            if not workbook_result.get("success", False):
                raise RuntimeError("BSP workbook generation failed.")
            self.state.add_result("bsp_workbook", workbook_result)
            self.state.complete_step("Build BSP Inventory Workbook", workbook_result)

            # 3. mminv_new + batches
            self.state.start_step("Update mminv_new and Prepare ZMAT Batches")
            database_stage = InventoryDatabaseStage(self.database)
            database_result = database_stage.run_from_workbook(
                workbook_file=workbook_file,
                output_directory=self.batch_directory,
            )
            if not database_result.get("success", False):
                raise RuntimeError("mminv_new/batch preparation failed.")
            self.state.add_result("mminv_new", database_result)
            self.state.complete_step(
                "Update mminv_new and Prepare ZMAT Batches",
                database_result,
            )

            batches = database_result.get("batches", {})
            result = {
                "success": True,
                "status": self.WAITING_FOR_SAP,
                "run_id": self.state.run_id,
                "bsp_workbook_file": str(workbook_file),
                "mminv_new": database_result.get("database", {}),
                "batches": {
                    "unique_material_codes": batches.get("unique_material_codes", 0),
                    "batch_size": batches.get("batch_size", 20000),
                    "batch_count": batches.get("batch_count", 0),
                    "files": batches.get("batch_files", batches.get("files", [])),
                },
                "next_sap_steps": [
                    "ZMAT-FUND_POPR",
                    "Background execution",
                    "SM37",
                    "Spool extraction",
                ],
            }

            self.state.metadata["offline_boundary"] = self.WAITING_FOR_SAP
            self.state.metadata["offline_prepare"] = result
            self.state.finish(self.WAITING_FOR_SAP)
            self._write_manifest(
                self.WAITING_FOR_SAP,
                bsp_workbook_file=str(workbook_file),
                mminv_new=database_result.get("database", {}),
                batches=result["batches"],
            )
            return result

        except Exception as exc:
            self.state.add_error(str(exc))
            self.state.finish("failed")
            self._write_manifest("failed", error=str(exc))
            raise

    # ---------------------------------------------------------
    # POST-SAP FINALIZATION
    # ---------------------------------------------------------

    def finalize_from_spool(
        self,
        spool_files: Iterable[str | Path],
        date_columns: Iterable[str] | None = None,
        inventory_po_file: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Finish the non-SAP portion after SAP spool TXT files exist.

        This method intentionally starts at TXT files.  It does not
        pretend to execute SM37 or extract spool data itself.
        """

        files = [Path(file) for file in spool_files]
        if not files:
            raise ValueError("At least one spool TXT file is required.")
        for file in files:
            if not file.exists():
                raise FileNotFoundError(f"Spool TXT file not found: {file}")

        if inventory_po_file is None:
            inventory_po_file = self.output_directory / "Inventory PO.xlsx"
        else:
            inventory_po_file = Path(inventory_po_file)

        self.state.start_step("Build Inventory PO from SAP Spool TXT")
        try:
            build_inventory_po(
                input_files=files,
                output_file=inventory_po_file,
                date_columns=date_columns,
            )
            if not inventory_po_file.exists():
                raise FileNotFoundError("Inventory PO.xlsx was not created.")
            self.state.complete_step(
                "Build Inventory PO from SAP Spool TXT",
                {"inventory_po_file": str(inventory_po_file)},
            )

            self.state.start_step("Update mminv1_new")
            final_stage = FinalInventoryDatabaseStage(self.database)
            final_result = final_stage.run(inventory_po_file)
            if not final_result.get("success", False):
                raise RuntimeError("mminv1_new update failed.")
            self.state.add_result("mminv1_new", final_result)
            self.state.complete_step("Update mminv1_new", final_result)
            self.state.finish(self.COMPLETED)

            result = {
                "success": True,
                "status": self.COMPLETED,
                "run_id": self.state.run_id,
                "inventory_po_file": str(inventory_po_file),
                "mminv1_new": final_result,
            }
            self._write_manifest(
                self.COMPLETED,
                inventory_po_file=str(inventory_po_file),
                mminv1_new=final_result,
            )
            return result
        except Exception as exc:
            self.state.add_error(str(exc))
            self.state.finish("failed")
            self._write_manifest("failed", error=str(exc))
            raise
