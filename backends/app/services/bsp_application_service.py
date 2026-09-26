from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import sqlite3
from typing import Any

import pandas as pd

from app.agent.state import AgentState
from app.services.inventory_database import InventoryDatabase
from app.services.inventory_database_stage import InventoryDatabaseStage
from app.services.final_inventory_database_stage import FinalInventoryDatabaseStage
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.sm37_spool_orchestrator import SM37SpoolOrchestrator
from app.services.spool_inventory_po_orchestrator import (
    SpoolInventoryPOOrchestrator,
)
from app.services.zmat_sm37_orchestrator import ZMATSM37Orchestrator
from app.services.bsp_mc1_export import (
    standardize_mc1_workbook,
)

class BSPApplicationService:
    """
    Main application-level BSP Inventory automation service.

    This is NOT the demo runner.

    It receives the two Excel files uploaded from the frontend
    and executes the actual application pipeline.

    Current mode:
        offline

    Offline mode uses MockSAPClient for SAP-dependent steps.
    This lets us test the complete application before connecting
    the pipeline to the real SAP GUI.
    """

    def __init__(self, state: AgentState):
        self.state = state

        self.project_root = Path(__file__).resolve().parents[3]

        self.data_root = self.project_root / "data"

        self.run_dir = (
            self.data_root
            / "runs"
            / state.run_id
        )

        self.run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # =========================================================
    # STEP HELPERS
    # =========================================================

    def _step(self, name: str):
        self.state.start_step(name)

    def _done(self, name: str, result: Any):
        self.state.complete_step(
            name,
            result,
        )

    def _fail(
        self,
        name: str,
        exc: Exception,
    ):
        self.state.fail_step(
            name,
            str(exc),
        )

    # =========================================================
    # MAIN OFFLINE PIPELINE
    # =========================================================

    def run_offline(
        self,
        previous_file: str | Path,
        current_file: str | Path,
        reference_file: str | Path | None = None,
    ) -> dict[str, Any]:

        self.state.status = "running"

        previous_file = Path(previous_file)
        current_file = Path(current_file)

        reference_file = Path(
            reference_file
            or self.data_root
            / "config"
            / "references.xlsx"
        )

        # -----------------------------------------------------
        # Validate input files
        # -----------------------------------------------------

        if not previous_file.exists():
            raise FileNotFoundError(
                f"Previous inventory file not found: "
                f"{previous_file}"
            )

        if not current_file.exists():
            raise FileNotFoundError(
                f"Current inventory file not found: "
                f"{current_file}"
            )

        if not reference_file.exists():
            raise FileNotFoundError(
                f"RI/Capital reference file not found: "
                f"{reference_file}"
            )

        # =====================================================
        # 1. PROCESS RAW MC.1 DATA
        # =====================================================

        self._step(
            "Process MC.1 Raw Data"
        )

        try:

            previous_standardized = (
                self.run_dir
                / "MC1_Previous_Standardized.xlsx"
            )

            current_standardized = (
                self.run_dir
                / "MC1_Current_Standardized.xlsx"
            )

            standardize_mc1_workbook(
                previous_file,
                previous_standardized,
            )

            standardize_mc1_workbook(
                current_file,
                current_standardized,
            )

            self.state.previous_inventory_file = (
                str(previous_standardized)
            )

            self.state.current_inventory_file = (
                str(current_standardized)
            )

            handoff = {
                "success": True,
                "previous_raw": str(
                    previous_file
                ),
                "current_raw": str(
                    current_file
                ),
                "previous_standardized": str(
                    previous_standardized
                ),
                "current_standardized": str(
                    current_standardized
                ),
            }

            self._done(
                "Process MC.1 Raw Data",
                handoff,
            )

            self.state.metadata[
                "mc1_export_handoff"
            ] = handoff

        except Exception as exc:

            self._fail(
                "Process MC.1 Raw Data",
                exc,
            )

            raise

        # =====================================================
        # 2. BUILD BSP INVENTORY WORKBOOK
        # =====================================================

        self._step(
            "Build BSP Inventory Workbook"
        )

        workbook_path = (
            self.run_dir
            / "BSP_Inventory.xlsx"
        )

        try:

            from app.services.bsp_workbook_builder import (
                build_bsp_workbook
            )

            workbook_result = (
                build_bsp_workbook(
                    previous_file=(
                        self.state
                        .previous_inventory_file
                    ),
                    present_file=(
                        self.state
                        .current_inventory_file
                    ),
                    reference_file=reference_file,
                    output_file=workbook_path,
                )
            )

            if not workbook_result.get(
                "success",
                False,
            ):

                raise RuntimeError(
                    workbook_result.get(
                        "message",
                        "BSP workbook generation failed.",
                    )
                )

            self._done(
                "Build BSP Inventory Workbook",
                workbook_result,
            )

            self.state.metadata[
                "bsp_workbook"
            ] = workbook_result

        except Exception as exc:

            self._fail(
                "Build BSP Inventory Workbook",
                exc,
            )

            raise

        # =====================================================
        # 3. UPDATE mminv_new
        # =====================================================

        self._step(
            "Update mminv_new"
        )

        db_path = (
            self.run_dir
            / "inventory.db"
        )

        conn = None

        try:

            conn = sqlite3.connect(
                db_path
            )

            database = InventoryDatabase(
                conn
            )

            db_stage = InventoryDatabaseStage(
                database
            )

            db_result = (
                db_stage.run_from_workbook(
                    workbook_file=workbook_path,
                    output_directory=(
                        self.run_dir
                        / "zmat_batches"
                    ),
                )
            )

            if not db_result.get(
                "success",
                False,
            ):

                raise RuntimeError(
                    db_result.get(
                        "message",
                        "mminv_new update failed.",
                    )
                )

            self._done(
                "Update mminv_new",
                db_result,
            )

            self.state.metadata[
                "mminv_new"
            ] = db_result

            # =================================================
            # 4. ZMAT + SM37
            # =================================================

            self._step(
                "Run ZMAT-FUND_POPR"
            )

            client = MockSAPClient()

            client.controls[
                "txt_JOB_STATUS"
            ] = "FINISHED"

            client.controls[
                "txt_JOB_NUMBER"
            ] = (
                f"DEMO-"
                f"{self.state.run_id[:8]}"
            )

            controller = SAPController(
                client
            )

            zmat_sm37 = (
                ZMATSM37Orchestrator(
                    self.state,
                    controller,
                )
            )

            batch_results = []

            batches = (
                db_result
                .get(
                    "batches",
                    {}
                )
                .get(
                    "batches",
                    []
                )
            )

            for index, batch in enumerate(
                batches,
                start=1,
            ):

                result = (
                    zmat_sm37.run_batch(
                        batch_number=index,
                        material_codes=batch,
                        job_name="ZMAT_PO_PR",
                        submit_background=True,
                        timeout_seconds=1,
                        poll_interval_seconds=0.01,
                    )
                )

                batch_results.append(
                    result
                )

            zmat_result = {
                "success": all(
                    result.get(
                        "success",
                        False,
                    )
                    for result
                    in batch_results
                ),
                "batch_count": len(
                    batch_results
                ),
                "batches": batch_results,
                "mode": "offline-mock-sap",
            }

            if not zmat_result[
                "success"
            ]:

                raise RuntimeError(
                    "One or more mock "
                    "ZMAT/SM37 batches failed."
                )

            self._done(
                "Run ZMAT-FUND_POPR",
                zmat_result,
            )

            self.state.metadata[
                "zmat_fund_popr"
            ] = zmat_result

            # =================================================
            # 5. SPOOL → INVENTORY PO
            # =================================================

            self._step(
                "Extract Spool and Build Inventory PO"
            )

            spool_client = MockSAPClient()

            spool_client.controls[
                "txt_JOB_STATUS"
            ] = "FINISHED"

            spool_client.controls[
                "txt_JOB_NUMBER"
            ] = (
                f"DEMO-"
                f"{self.state.run_id[:8]}"
            )

            current_df = pd.read_excel(
                workbook_path,
                sheet_name="Inventory",
            )

            material_col = (
                "Material Code"
            )

            qty_col = (
                "Inve Pres Quantity"
            )

            if material_col not in current_df.columns:

                raise ValueError(
                    f"Current workbook is missing "
                    f"'{material_col}'."
                )

            if qty_col not in current_df.columns:

                raise ValueError(
                    f"Current workbook is missing "
                    f"'{qty_col}'."
                )

            lines = [
                "Material\tQuantity\tDate"
            ]

            spool_date = (
                datetime.now()
                .strftime(
                    "%d.%m.%Y"
                )
            )

            for _, row in (
                current_df[
                    [
                        material_col,
                        qty_col,
                    ]
                ]
                .dropna(
                    subset=[
                        material_col
                    ]
                )
                .iterrows()
            ):

                material = str(
                    row[
                        material_col
                    ]
                ).strip()

                quantity = row[
                    qty_col
                ]

                if (
                    not material
                    or material.lower()
                    == "nan"
                ):
                    continue

                if pd.isna(
                    quantity
                ):

                    quantity = 0

                lines.append(
                    f"{material}\t"
                    f"{quantity}\t"
                    f"{spool_date}"
                )

            spool_client.controls[
                "txt_SPOOL"
            ] = (
                "\n".join(lines)
                + "\n"
            )

            spool_controller = (
                SAPController(
                    spool_client
                )
            )

            spool_workflow = (
                SM37SpoolOrchestrator(
                    self.state,
                    spool_controller,
                )
            )

            spool_po = (
                SpoolInventoryPOOrchestrator(
                    spool_workflow
                )
            )

            spool_file = (
                self.run_dir
                / "Inventory_Spool.txt"
            )

            po_file = (
                self.run_dir
                / "Inventory PO.xlsx"
            )

            po_result = spool_po.run(
                spool_output_file=spool_file,
                inventory_po_file=po_file,
                job_name="ZMAT_PO_PR",
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )

            if not po_result.get(
                "success",
                False,
            ):

                raise RuntimeError(
                    po_result.get(
                        "error",
                        "Spool/Inventory PO failed.",
                    )
                )

            self._done(
                "Extract Spool and Build Inventory PO",
                po_result,
            )

            self.state.metadata[
                "inventory_po"
            ] = po_result

            # =================================================
            # 6. UPDATE mminv1_new
            # =================================================

            self._step(
                "Update mminv1_new"
            )

            final_stage = (
                FinalInventoryDatabaseStage(
                    database
                )
            )

            final_result = (
                final_stage.run(
                    po_file
                )
            )

            if not final_result.get(
                "success",
                False,
            ):

                raise RuntimeError(
                    final_result.get(
                        "message",
                        "mminv1_new update failed.",
                    )
                )

            self._done(
                "Update mminv1_new",
                final_result,
            )

            self.state.metadata[
                "mminv1_new"
            ] = final_result

            # =================================================
            # FINAL SUMMARY
            # =================================================

            summary = {
                "success": True,
                "mode": "offline",
                "run_id": self.state.run_id,
                "files": {
                    "previous_raw": str(
                        previous_file
                    ),
                    "current_raw": str(
                        current_file
                    ),
                    "previous_standardized": (
                        self.state
                        .previous_inventory_file
                    ),
                    "current_standardized": (
                        self.state
                        .current_inventory_file
                    ),
                    "bsp_workbook": str(
                        workbook_path
                    ),
                    "database": str(
                        db_path
                    ),
                    "inventory_spool": str(
                        spool_file
                    ),
                    "inventory_po": str(
                        po_file
                    ),
                },
                "metrics": {
                    "mminv_new_rows": (
                        db_result
                        .get(
                            "database",
                            {}
                        )
                        .get(
                            "database_rows"
                        )
                    ),
                    "unique_material_codes": (
                        db_result
                        .get(
                            "batches",
                            {}
                        )
                        .get(
                            "unique_material_codes"
                        )
                    ),
                    "zmat_batches": (
                        db_result
                        .get(
                            "batches",
                            {}
                        )
                        .get(
                            "batch_count"
                        )
                    ),
                    "inventory_po_rows": (
                        po_result
                        .get(
                            "inventory_po",
                            {}
                        )
                        .get(
                            "rows"
                        )
                    ),
                    "mminv1_new_rows": (
                        final_result
                        .get(
                            "rows_imported"
                        )
                    ),
                },
            }

            self.state.results[
                "bsp_automation"
            ] = summary

            self.state.metadata[
                "bsp_automation"
            ] = summary

            self.state.finish(
                "completed"
            )

            summary_file = (
                self.run_dir
                / "run_summary.json"
            )

            summary_file.write_text(
                json.dumps(
                    summary,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            summary[
                "files"
            ][
                "summary"
            ] = str(
                summary_file
            )

            return self.state.to_dict()

        except Exception:

            self.state.finish(
                "failed"
            )

            raise

        finally:

            if conn is not None:

                conn.close()