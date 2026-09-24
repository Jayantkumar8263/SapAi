from pathlib import Path
from app.agent.state import AgentState
from app.services.mc1_export_manager import (
    MC1ExportManager,
)
from app.services.inventory_database_stage import (
    InventoryDatabaseStage,
)

from app.services.bsp_workbook_builder import (
    build_bsp_workbook,
)
from app.agent.state import AgentState

from app.agent.tools import (
    process_previous_inventory,
    process_current_inventory,
    compare_inventory_files,
    analyze_inventory,
    classify_inventory_materials,
    generate_report,
    validate_report,
)

from app.services.sap_controller import SAPController
from app.services.sap_workflow import SAPWorkflow


# =============================================================
# INVENTORY WORKFLOW
# =============================================================

class InventoryWorkflow:
    """
    Main workflow for SapAi inventory automation.

    Workflow:

        MC.1 Excel Export
                ↓
        MC.1 Export Handoff
                ↓
        Previous Inventory
                ↓
        Current Inventory
                ↓
        Compare Inventories
                ↓
        Analyze Inventory Changes
                ↓
        Classify RI / Capital Materials
                ↓
        Generate Report
                ↓
        Validate Report

    Deterministic spreadsheet processing remains inside
    the existing inventory services.

    The analysis layer interprets the deterministic
    comparison result.
    """

    def __init__(
        self,
        state: AgentState,
        sap_controller: SAPController | None = None,
    ):
        self.state = state

        self.sap_controller = sap_controller

        self.sap_workflow = None

        if self.sap_controller is not None:
            self.sap_workflow = SAPWorkflow(
                self.state,
                self.sap_controller,
            )

    # =========================================================
    # MC.1 EXPORT HANDOFF
    # =========================================================

    def prepare_mc1_inventory_files(
        self,
        previous_export: str | Path,
        current_export: str | Path,
    ) -> dict:
        """
        Convert previous/current MC.1 Excel exports into the
        standardized inventory files consumed by SapAi.

        This method does NOT run SAP.

        Flow:

            Previous MC.1 Excel
                    ↓
            MC1ExportManager
                    ↓
            Previous standardized Excel

            Current MC.1 Excel
                    ↓
            MC1ExportManager
                    ↓
            Current standardized Excel

                    ↓
                AgentState
        """

        self.state.start_step(
            "Prepare MC.1 Inventory Files"
        )

        try:

            # -------------------------------------------------
            # OUTPUT DIRECTORY
            # -------------------------------------------------

            output_directory = (
                Path(
                    self.state.data_directory
                )
                / "mc1_processed"
            )

            manager = MC1ExportManager(
                output_directory
            )

            # -------------------------------------------------
            # PROCESS PREVIOUS MC.1 EXPORT
            # -------------------------------------------------

            previous_result = (
                manager.process_export(
                    previous_export,
                    "previous",
                )
            )

            if not previous_result.get(
                "success",
                False,
            ):

                raise RuntimeError(
                    previous_result.get(
                        "message",
                        "Previous MC.1 export processing failed.",
                    )
                )

            # -------------------------------------------------
            # PROCESS CURRENT MC.1 EXPORT
            # -------------------------------------------------

            current_result = (
                manager.process_export(
                    current_export,
                    "current",
                )
            )

            if not current_result.get(
                "success",
                False,
            ):

                raise RuntimeError(
                    current_result.get(
                        "message",
                        "Current MC.1 export processing failed.",
                    )
                )

            # -------------------------------------------------
            # GET STANDARDIZED FILE PATHS
            # -------------------------------------------------

            previous_file = Path(
                previous_result[
                    "standardized_file"
                ]
            )

            current_file = Path(
                current_result[
                    "standardized_file"
                ]
            )

            # -------------------------------------------------
            # SAFETY CHECK
            # -------------------------------------------------

            if not previous_file.exists():

                raise FileNotFoundError(
                    "Previous standardized MC.1 file "
                    "was not created."
                )

            if not current_file.exists():

                raise FileNotFoundError(
                    "Current standardized MC.1 file "
                    "was not created."
                )

            # -------------------------------------------------
            # CONNECT TO AGENT STATE
            # -------------------------------------------------

            self.state.previous_inventory_file = (
                str(previous_file)
            )

            self.state.current_inventory_file = (
                str(current_file)
            )

            # -------------------------------------------------
            # BUILD RESULT
            # -------------------------------------------------

            result = {
                "success": True,

                "previous": previous_result,

                "current": current_result,

                "previous_inventory_file": str(
                    previous_file
                ),

                "current_inventory_file": str(
                    current_file
                ),
            }

            # -------------------------------------------------
            # STORE RESULT
            # -------------------------------------------------

            self.state.add_result(
                "mc1_export_handoff",
                result,
            )

            self.state.metadata[
                "mc1_export_handoff"
            ] = result

            # -------------------------------------------------
            # COMPLETE STEP
            # -------------------------------------------------

            self.state.complete_step(
                "Prepare MC.1 Inventory Files",
                result,
            )

            return result

        except Exception as exc:

            already_failed = any(
                step.get("step")
                == "Prepare MC.1 Inventory Files"
                and step.get("status")
                == "failed"
                for step in self.state.steps
            )

            if not already_failed:

                self.state.fail_step(
                    "Prepare MC.1 Inventory Files",
                    str(exc),
                )

            raise

    # =========================================================
    # SAP MC.1 STAGE
    # =========================================================

    def run_sap_mc1(self):
        """
        Execute SAP MC.1 through SAPWorkflow.

        This method is used for the SAP integration stage.
        """

        if self.sap_workflow is None:
            raise RuntimeError(
                "SAP workflow is not configured."
            )

        self.state.start_step(
            "SAP MC.1"
        )

        try:

            result = self.sap_workflow.run_mc1()

            # -------------------------------------------------
            # CHECK RESULT
            # -------------------------------------------------

            if isinstance(result, dict):

                if result.get("success") is False:

                    message = result.get(
                        "message",
                        "SAP MC.1 failed.",
                    )

                    self.state.fail_step(
                        "SAP MC.1",
                        message,
                    )

                    raise RuntimeError(
                        message
                    )

            # -------------------------------------------------
            # STORE RESULT
            # -------------------------------------------------

            self.state.complete_step(
                "SAP MC.1",
                result,
            )

            self.state.add_result(
                "sap_mc1",
                result,
            )

            self.state.metadata[
                "sap_mc1"
            ] = result

            return result

        except Exception as exc:

            already_failed = any(
                step.get("step") == "SAP MC.1"
                and step.get("status") == "failed"
                for step in self.state.steps
            )

            if not already_failed:

                self.state.fail_step(
                    "SAP MC.1",
                    str(exc),
                )

            raise

        finally:

            self.sap_workflow.close()

    # =========================================================
    # STEP EXECUTOR
    # =========================================================

    def execute_step(
        self,
        step_name: str,
        function,
        *args,
        **kwargs,
    ):
        """
        Execute one workflow step while updating AgentState.

        If a tool returns:

            {
                "success": False,
                "message": "..."
            }

        the workflow stops immediately.
        """

        self.state.start_step(
            step_name
        )

        try:

            result = function(
                *args,
                **kwargs,
            )

            # -------------------------------------------------
            # CHECK TOOL FAILURE
            # -------------------------------------------------

            if isinstance(
                result,
                dict,
            ):

                if result.get(
                    "success"
                ) is False:

                    error_message = result.get(
                        "message",
                        f"{step_name} failed.",
                    )

                    self.state.fail_step(
                        step_name,
                        error_message,
                    )

                    raise RuntimeError(
                        error_message
                    )

            # -------------------------------------------------
            # STEP SUCCESS
            # -------------------------------------------------

            self.state.complete_step(
                step_name,
                result,
            )

            return result

        except Exception as exc:

            error_message = (
                f"{step_name} failed: {str(exc)}"
            )

            # Avoid duplicate failure entries.

            already_failed = any(
                step.get("step") == step_name
                and step.get("status") == "failed"
                for step in self.state.steps
            )

            if not already_failed:

                self.state.fail_step(
                    step_name,
                    error_message,
                )

            raise
        # =========================================================
    # RUN COMPLETE WORKFLOW FROM MC.1 EXPORTS
    # =========================================================

    def run_from_mc1_exports(
        self,
        previous_export: str | Path,
        current_export: str | Path,
    ):
        """
        Run the complete inventory workflow starting from
        previous and current MC.1 Excel exports.

        Flow:

            MC.1 Previous Export
                    +
            MC.1 Current Export
                    ↓
            Prepare MC.1 Inventory Files
                    ↓
            Process Previous Inventory
                    ↓
            Process Current Inventory
                    ↓
            Compare
                    ↓
            Analyze
                    ↓
            RI / Capital Classification
                    ↓
            Generate Report
                    ↓
            Validate Report

        This method is the high-level entry point for the
        future SAP bot/orchestrator.
        """

        # -----------------------------------------------------
        # STEP 0
        # PREPARE MC.1 EXPORTS
        # -----------------------------------------------------

        self.prepare_mc1_inventory_files(
            previous_export=previous_export,
            current_export=current_export,
        )

        # -----------------------------------------------------
        # RUN EXISTING INVENTORY WORKFLOW
        # -----------------------------------------------------

        return self.run()
    # =========================================================
    # COMPLETE INVENTORY WORKFLOW
    # =========================================================

    def run(self):
        """
        Execute the complete 7-stage inventory workflow.

        The inventory files must already exist in:

            state.previous_inventory_file
            state.current_inventory_file

        The MC.1 handoff can be performed beforehand using:

            prepare_mc1_inventory_files(...)
        """

        self.state.status = "running"

        try:

            # =================================================
            # STEP 1
            # PROCESS PREVIOUS INVENTORY
            # =================================================

            previous_result = self.execute_step(
                "Process Previous Inventory",
                process_previous_inventory,
                self.state,
            )

            self.state.add_result(
                "previous_inventory",
                previous_result,
            )

            self.state.inspection_result = (
                previous_result
            )

            # =================================================
            # STEP 2
            # PROCESS CURRENT INVENTORY
            # =================================================

            current_result = self.execute_step(
                "Process Current Inventory",
                process_current_inventory,
                self.state,
            )

            self.state.add_result(
                "current_inventory",
                current_result,
            )

            # =================================================
            # STEP 3
            # COMPARE INVENTORIES
            # =================================================

            comparison_result = self.execute_step(
                "Compare Previous and Current Inventory",
                compare_inventory_files,
                self.state,
            )

            self.state.add_result(
                "comparison",
                comparison_result,
            )

            self.state.comparison_result = (
                comparison_result
            )

            # =================================================
            # STEP 4
            # ANALYZE INVENTORY CHANGES
            # =================================================

            analysis_result = self.execute_step(
                "Analyze Inventory Changes",
                analyze_inventory,
                self.state,
            )

            self.state.add_result(
                "analysis",
                analysis_result,
            )

            self.state.metadata[
                "inventory_analysis"
            ] = analysis_result

            # =================================================
            # STEP 5
            # CLASSIFY RI / CAPITAL MATERIALS
            # =================================================

            classification_result = self.execute_step(
                "Classify RI / Capital Materials",
                classify_inventory_materials,
                self.state,
            )

            self.state.add_result(
                "classification",
                classification_result,
            )

            self.state.metadata[
                "inventory_classification"
            ] = classification_result

            # =================================================
            # STEP 6
            # GENERATE INVENTORY REPORT
            # =================================================

            report_result = self.execute_step(
                "Generate Inventory Report",
                generate_report,
                self.state,
            )

            self.state.add_result(
                "report",
                report_result,
            )

            # -------------------------------------------------
            # EXTRACT REPORT PATH
            # -------------------------------------------------

            if isinstance(
                report_result,
                dict,
            ):

                report_path = (
                    report_result.get(
                        "report"
                    )
                    or report_result.get(
                        "report_file"
                    )
                    or report_result.get(
                        "report_path"
                    )
                )

                if report_path:

                    self.state.report_path = (
                        str(report_path)
                    )

                    self.state.report_file = (
                        str(report_path)
                    )

            elif isinstance(
                report_result,
                str,
            ):

                self.state.report_path = (
                    report_result
                )

                self.state.report_file = (
                    report_result
                )

            # =================================================
            # STEP 7
            # VALIDATE GENERATED REPORT
            # =================================================

            validation_result = self.execute_step(
                "Validate Generated Report",
                validate_report,
                self.state,
            )

            self.state.add_result(
                "validation",
                validation_result,
            )

            self.state.validation_result = (
                validation_result
            )

            # =================================================
            # VALIDATION STATUS
            # =================================================

            validation_valid = False

            if isinstance(
                validation_result,
                dict,
            ):

                validation_valid = bool(
                    validation_result.get(
                        "valid",
                        False,
                    )
                )

            # -------------------------------------------------
            # SAFETY CHECK
            # -------------------------------------------------
            #
            # This should normally never be reached with
            # validation_valid=False because validate_report()
            # returns success=False when validation fails.
            #
            # This extra check protects the workflow from
            # accidentally reporting success.
            # -------------------------------------------------

            if not validation_valid:

                raise RuntimeError(
                    validation_result.get(
                        "message",
                        "Generated report validation failed.",
                    )
                )

            # =================================================
            # WORKFLOW SUMMARY
            # =================================================

            self.state.results[
                "workflow_summary"
            ] = {

                "previous_inventory_processed":
                    True,

                "current_inventory_processed":
                    True,

                "comparison_completed":
                    True,

                "analysis_completed":
                    True,

                "classification_completed":
                    True,

                "report_generated":
                    self.state.report_path is not None,

                "report_validated":
                    validation_valid,
            }

            # =================================================
            # FINISH SUCCESSFULLY
            # =================================================

            self.state.finish(
                "completed"
            )

            return self.state.to_dict()

        except Exception:

            self.state.finish(
                "failed"
            )

            raise
    
        # =========================================================
    # BSP WORKBOOK -> mminv_new
    # =========================================================

    def run_bsp_workbook_to_mminv_new(
        self,
        database: object,
        reference_file: str | Path,
        output_file: str | Path | None = None,
        batch_output_directory: str | Path | None = None,
    ) -> dict:
        """
        Build the five-sheet BSP workbook and immediately hand
        its Inventory sheet to the existing mminv_new database
        stage.

        Flow:

            Previous MC.1 workbook
                    +
            Current MC.1 workbook
                    ↓
            BSP five-sheet workbook
                    ↓
              Inventory sheet
                    ↓
                mminv_new
                    ↓
            Unique Material Codes
                    ↓
              20,000 batches

        This method does not connect directly to the production
        SQL database itself. The supplied `database` object is
        passed to the existing InventoryDatabaseStage.

        The reference workbook must contain:
            RI
            Capital
        """

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if database is None:
            raise ValueError(
                "database is required."
            )

        if reference_file is None:
            raise ValueError(
                "reference_file is required."
            )

        reference_path = Path(
            reference_file
        )

        if not reference_path.exists():
            raise FileNotFoundError(
                "BSP RI/Capital reference workbook was not found: "
                f"{reference_path}"
            )

        previous_file = self.state.previous_inventory_file
        current_file = self.state.current_inventory_file

        if not previous_file:
            raise ValueError(
                "state.previous_inventory_file is required "
                "before building the BSP workbook."
            )

        if not current_file:
            raise ValueError(
                "state.current_inventory_file is required "
                "before building the BSP workbook."
            )

        previous_path = Path(
            previous_file
        )

        current_path = Path(
            current_file
        )

        if not previous_path.exists():
            raise FileNotFoundError(
                "Previous inventory workbook was not found: "
                f"{previous_path}"
            )

        if not current_path.exists():
            raise FileNotFoundError(
                "Current inventory workbook was not found: "
                f"{current_path}"
            )

        # -----------------------------------------------------
        # OUTPUT PATH
        # -----------------------------------------------------

        if output_file is None:

            output_path = (
                Path(
                    self.state.data_directory
                )
                / "bsp_inventory"
                / "BSP_Inventory.xlsx"
            )

        else:

            output_path = Path(
                output_file
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # -----------------------------------------------------
        # STEP 1 — BUILD BSP WORKBOOK
        # -----------------------------------------------------

        self.state.start_step(
            "Build BSP Inventory Workbook"
        )

        try:

            workbook_result = build_bsp_workbook(
                previous_file=previous_path,
                present_file=current_path,
                reference_file=reference_path,
                output_file=output_path,
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

            generated_workbook = Path(
                workbook_result[
                    "output_file"
                ]
            )

            if not generated_workbook.exists():
                raise FileNotFoundError(
                    "BSP workbook builder reported success, "
                    "but the workbook was not created: "
                    f"{generated_workbook}"
                )

            self.state.add_result(
                "bsp_workbook",
                workbook_result,
            )

            self.state.metadata[
                "bsp_workbook"
            ] = workbook_result

            self.state.complete_step(
                "Build BSP Inventory Workbook",
                workbook_result,
            )

        except Exception as exc:

            already_failed = any(
                step.get("step")
                == "Build BSP Inventory Workbook"
                and step.get("status")
                == "failed"
                for step in self.state.steps
            )

            if not already_failed:
                self.state.fail_step(
                    "Build BSP Inventory Workbook",
                    str(exc),
                )

            raise

        # -----------------------------------------------------
        # STEP 2 — IMPORT INVENTORY SHEET INTO mminv_new
        # -----------------------------------------------------

        database_result = self.run_master_database_stage(
            database=database,
            workbook_file=generated_workbook,
            output_directory=batch_output_directory,
        )

        result = {
            "success": True,
            "reference_file": str(
                reference_path
            ),
            "bsp_workbook_file": str(
                generated_workbook
            ),
            "mminv_new": database_result,
        }

        self.state.add_result(
            "bsp_workbook_to_mminv_new",
            result,
        )

        self.state.metadata[
            "bsp_workbook_to_mminv_new"
        ] = result

        return result

    # =========================================================
    # MASTER DATABASE STAGE
    # =========================================================

    def run_master_database_stage(
        self,
        database: object,
        workbook_file: str | Path,
        output_directory: str | Path | None = None,
    ) -> dict:
        """
        Execute the real deterministic database stage used
        by the master BSP automation.

        Flow:

            BSP Final Inventory
                    ↓
            Inventory sheet
                    ↓
                mminv_new
                    ↓
            unique Material Codes
                    ↓
            20,000-record batches
        """

        if database is None:
            raise ValueError(
                "database is required."
            )

        if workbook_file is None:
            raise ValueError(
                "workbook_file is required."
            )

        stage = InventoryDatabaseStage(
            database
        )

        result = stage.run_from_workbook(
            workbook_file=workbook_file,
            output_directory=output_directory,
        )

        if not result.get(
            "success",
            False,
        ):
            raise RuntimeError(
                result.get(
                    "message",
                    "Master database stage failed.",
                )
            )

        self.state.add_result(
            "master_database_stage",
            result,
        )

        self.state.metadata[
            "master_database_stage"
        ] = result

        return result
    
    # =========================================================
    # MASTER BSP AUTOMATION
    # =========================================================

    def run_full_bsp_automation(
        self,
        previous_export: str | Path,
        current_export: str | Path,
        database_stage=None,
        zmat_stage=None,
        sm37_stage=None,
        spool_stage=None,
        inventory_po_stage=None,
        final_database_stage=None,
    ):
        """
        Master BSP inventory automation pipeline.

        Complete intended flow:

            MC.1 exports
                ↓
            Inventory processing
                ↓
            RI / Capital classification
                ↓
            Final Inventory
                ↓
            mminv_new
                ↓
            Unique Material Codes
                ↓
            20,000-record batches
                ↓
            ZMAT-FUND_POPR
                ↓
            SM37
                ↓
            Spool
                ↓
            Inventory PO
                ↓
            mminv1_new
                ↓
            Complete

        IMPORTANT
        ---------
        The individual stages are injected into this method.

        This is intentional.

        We do not hard-code assumptions about the production
        database, SAP control IDs, or SAP spool format until
        those components have been validated separately.
        """

        self.state.status = "running"

        try:

            # =================================================
            # PHASE 1
            # MC.1 → INVENTORY
            # =================================================

            inventory_result = (
                self.run_from_mc1_exports(
                    previous_export=previous_export,
                    current_export=current_export,
                )
            )

            self.state.metadata[
                "master_phase"
            ] = "inventory_complete"

            # =================================================
            # PHASE 2
            # DATABASE: mminv_new
            # =================================================

            if database_stage is None:
                raise RuntimeError(
                    "Database stage is required before "
                    "continuing to mminv_new."
                )

            self.state.start_step(
                "Update mminv_new"
            )

            try:

                database_result = (
                    database_stage(
                        self.state
                    )
                )

                if (
                    isinstance(
                        database_result,
                        dict,
                    )
                    and database_result.get(
                        "success"
                    ) is False
                ):
                    raise RuntimeError(
                        database_result.get(
                            "message",
                            "mminv_new update failed.",
                        )
                    )

                self.state.add_result(
                    "mminv_new",
                    database_result,
                )

                self.state.metadata[
                    "mminv_new"
                ] = database_result

                self.state.complete_step(
                    "Update mminv_new",
                    database_result,
                )

            except Exception as exc:

                self.state.fail_step(
                    "Update mminv_new",
                    str(exc),
                )

                raise

            # =================================================
            # PHASE 3
            # ZMAT-FUND_POPR PREPARATION
            # =================================================

            if zmat_stage is None:
                raise RuntimeError(
                    "ZMAT-FUND_POPR stage is required."
                )

            self.state.start_step(
                "Prepare ZMAT-FUND_POPR"
            )

            try:

                zmat_result = (
                    zmat_stage(
                        self.state
                    )
                )

                if (
                    isinstance(
                        zmat_result,
                        dict,
                    )
                    and zmat_result.get(
                        "success"
                    ) is False
                ):
                    raise RuntimeError(
                        zmat_result.get(
                            "message",
                            "ZMAT-FUND_POPR preparation failed.",
                        )
                    )

                self.state.add_result(
                    "zmat_fund_popr",
                    zmat_result,
                )

                self.state.metadata[
                    "zmat_fund_popr"
                ] = zmat_result

                self.state.complete_step(
                    "Prepare ZMAT-FUND_POPR",
                    zmat_result,
                )

            except Exception as exc:

                self.state.fail_step(
                    "Prepare ZMAT-FUND_POPR",
                    str(exc),
                )

                raise

            # =================================================
            # PHASE 4
            # SM37 / BACKGROUND JOB
            # =================================================

            if sm37_stage is None:
                raise RuntimeError(
                    "SM37 stage is required."
                )

            self.state.start_step(
                "Monitor SM37 Job"
            )

            try:

                sm37_result = (
                    sm37_stage(
                        self.state,
                        zmat_result,
                    )
                )

                if (
                    isinstance(
                        sm37_result,
                        dict,
                    )
                    and sm37_result.get(
                        "success"
                    ) is False
                ):
                    raise RuntimeError(
                        sm37_result.get(
                            "message",
                            "SM37 job failed.",
                        )
                    )

                self.state.add_result(
                    "sm37",
                    sm37_result,
                )

                self.state.metadata[
                    "sm37"
                ] = sm37_result

                self.state.complete_step(
                    "Monitor SM37 Job",
                    sm37_result,
                )

            except Exception as exc:

                self.state.fail_step(
                    "Monitor SM37 Job",
                    str(exc),
                )

                raise

            # =================================================
            # PHASE 5
            # SPOOL
            # =================================================

            if spool_stage is None:
                raise RuntimeError(
                    "Spool extraction stage is required."
                )

            self.state.start_step(
                "Extract SAP Spool"
            )

            try:

                spool_result = (
                    spool_stage(
                        self.state,
                        sm37_result,
                    )
                )

                if (
                    isinstance(
                        spool_result,
                        dict,
                    )
                    and spool_result.get(
                        "success"
                    ) is False
                ):
                    raise RuntimeError(
                        spool_result.get(
                            "message",
                            "SAP spool extraction failed.",
                        )
                    )

                self.state.add_result(
                    "sap_spool",
                    spool_result,
                )

                self.state.metadata[
                    "sap_spool"
                ] = spool_result

                self.state.complete_step(
                    "Extract SAP Spool",
                    spool_result,
                )

            except Exception as exc:

                self.state.fail_step(
                    "Extract SAP Spool",
                    str(exc),
                )

                raise

            # =================================================
            # PHASE 6
            # INVENTORY PO
            # =================================================

            if inventory_po_stage is None:
                raise RuntimeError(
                    "Inventory PO stage is required."
                )

            self.state.start_step(
                "Generate Inventory PO"
            )

            try:

                inventory_po_result = (
                    inventory_po_stage(
                        self.state,
                        spool_result,
                    )
                )

                if (
                    isinstance(
                        inventory_po_result,
                        dict,
                    )
                    and inventory_po_result.get(
                        "success"
                    ) is False
                ):
                    raise RuntimeError(
                        inventory_po_result.get(
                            "message",
                            "Inventory PO generation failed.",
                        )
                    )

                self.state.add_result(
                    "inventory_po",
                    inventory_po_result,
                )

                self.state.metadata[
                    "inventory_po"
                ] = inventory_po_result

                self.state.complete_step(
                    "Generate Inventory PO",
                    inventory_po_result,
                )

            except Exception as exc:

                self.state.fail_step(
                    "Generate Inventory PO",
                    str(exc),
                )

                raise

            # =================================================
            # PHASE 7
            # mminv1_new
            # =================================================

            if final_database_stage is None:
                raise RuntimeError(
                    "Final database stage is required "
                    "for mminv1_new."
                )

            self.state.start_step(
                "Update mminv1_new"
            )

            try:

                final_database_result = (
                    final_database_stage(
                        self.state,
                        inventory_po_result,
                    )
                )

                if (
                    isinstance(
                        final_database_result,
                        dict,
                    )
                    and final_database_result.get(
                        "success"
                    ) is False
                ):
                    raise RuntimeError(
                        final_database_result.get(
                            "message",
                            "mminv1_new update failed.",
                        )
                    )

                self.state.add_result(
                    "mminv1_new",
                    final_database_result,
                )

                self.state.metadata[
                    "mminv1_new"
                ] = final_database_result

                self.state.complete_step(
                    "Update mminv1_new",
                    final_database_result,
                )

            except Exception as exc:

                self.state.fail_step(
                    "Update mminv1_new",
                    str(exc),
                )

                raise

            # =================================================
            # COMPLETE
            # =================================================

            self.state.results[
                "master_workflow_summary"
            ] = {
                "mc1_completed": True,
                "inventory_completed": True,
                "mminv_new_completed": True,
                "zmat_fund_popr_completed": True,
                "sm37_completed": True,
                "spool_completed": True,
                "inventory_po_completed": True,
                "mminv1_new_completed": True,
                "workflow_completed": True,
            }

            self.state.finish(
                "completed"
            )

            return self.state.to_dict()

        except Exception:

            self.state.finish(
                "failed"
            )

            raise

# =============================================================
# CONVENIENCE FUNCTION
# =============================================================

def run_inventory_workflow(
    state: AgentState | None = None,
):
    """
    Convenience function for running the complete workflow.

    Example:

        result = run_inventory_workflow()
    """

    if state is None:

        state = AgentState()

        workflow = InventoryWorkflow(
            state
        )

    return workflow.run()