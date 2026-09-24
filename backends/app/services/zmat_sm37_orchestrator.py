"""
ZMAT-FUND_POPR → SM37 Orchestrator
===================================

Connects the existing ZMAT-FUND_POPR workflow with the
existing SM37 background-job monitoring workflow.

BSP process:

    ZMAT-FUND_POPR
          ↓
    Execute in Background
          ↓
        SM37
          ↓
    Search ZMAT_PO_PR
          ↓
    Wait for FINISHED
          ↓
    Continue to spool extraction

This module does NOT implement SAP GUI operations itself.

It delegates:

    ZMAT operations → ZMATFundPOPRWorkflow
    SM37 operations → SM37Workflow
"""

from __future__ import annotations

from typing import Any

from app.agent.state import AgentState

from app.services.sap_controller import (
    SAPController,
)

from app.services.zmat_fund_popr_workflow import (
    ZMATFundPOPRWorkflow,
)

from app.services.sm37_workflow import (
    SM37Workflow,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_JOB_NAME = "ZMAT_PO_PR"

DEFAULT_TIMEOUT_SECONDS = 300

DEFAULT_POLL_INTERVAL_SECONDS = 5


# ============================================================
# ORCHESTRATOR
# ============================================================


class ZMATSM37Orchestrator:
    """
    Coordinates one ZMAT-FUND_POPR batch with SM37 monitoring.

    The same SAPController instance is shared between the
    two workflows.

    ZMATFundPOPRWorkflow disconnects after its operation.
    SM37Workflow reconnects when monitoring begins.
    """

    def __init__(
        self,
        state: AgentState,
        controller: SAPController,
        zmat_workflow: ZMATFundPOPRWorkflow | None = None,
        sm37_workflow: SM37Workflow | None = None,
    ):
        if state is None:
            raise ValueError(
                "state cannot be None."
            )

        if controller is None:
            raise ValueError(
                "controller cannot be None."
            )

        self.state = state
        self.controller = controller

        self.zmat_workflow = (
            zmat_workflow
            if zmat_workflow is not None
            else ZMATFundPOPRWorkflow(
                state,
                controller,
            )
        )

        self.sm37_workflow = (
            sm37_workflow
            if sm37_workflow is not None
            else SM37Workflow(
                state,
                controller,
            )
        )

    # ========================================================
    # RUN ONE BATCH
    # ========================================================

    def run_batch(
        self,
        batch_number: int,
        material_codes: list[str],
        job_name: str = DEFAULT_JOB_NAME,
        submit_background: bool = True,
        timeout_seconds: float = (
            DEFAULT_TIMEOUT_SECONDS
        ),
        poll_interval_seconds: float = (
            DEFAULT_POLL_INTERVAL_SECONDS
        ),
    ) -> dict[str, Any]:
        """
        Execute one material-code batch through:

            ZMAT-FUND_POPR
                ↓
            Background
                ↓
            SM37
                ↓
            Job monitoring

        Parameters
        ----------
        batch_number:
            Sequential batch number.

        material_codes:
            Material codes for this batch.

        job_name:
            SAP background-job name.

            BSP documented process uses:
                ZMAT_PO_PR

        submit_background:
            Submit the ZMAT process to background.

        timeout_seconds:
            Maximum SM37 monitoring time.

        poll_interval_seconds:
            Delay between SM37 status checks.
        """

        if batch_number <= 0:
            raise ValueError(
                "batch_number must be greater than zero."
            )

        if not material_codes:
            raise ValueError(
                "material_codes cannot be empty."
            )

        if not job_name or not job_name.strip():
            raise ValueError(
                "job_name cannot be empty."
            )

        result: dict[str, Any] = {
            "success": False,
            "batch_number": batch_number,
            "job_name": job_name.strip(),
            "submit_background": submit_background,
            "zmat": None,
            "sm37": None,
        }

        # ----------------------------------------------------
        # STEP 1: ZMAT-FUND_POPR
        # ----------------------------------------------------

        zmat_result = (
            self.zmat_workflow.run(
                batch_number=batch_number,
                material_codes=material_codes,
                submit_background=submit_background,
            )
        )

        result["zmat"] = zmat_result

        if not zmat_result.get(
            "success",
            False,
        ):

            result["error"] = (
                zmat_result.get(
                    "error"
                )
                or
                "ZMAT-FUND_POPR failed."
            )

            return result

        # ----------------------------------------------------
        # STEP 2: Ensure background was submitted
        # ----------------------------------------------------

        if not zmat_result.get(
            "background_submitted",
            False,
        ):

            result["error"] = (
                "ZMAT-FUND_POPR completed, "
                "but the background job was not submitted. "
                "SM37 monitoring was therefore not started."
            )

            return result

        # ----------------------------------------------------
        # STEP 3: SM37
        # ----------------------------------------------------

        sm37_result = (
            self.sm37_workflow.monitor_job(
                job_name.strip(),
                timeout_seconds=(
                    timeout_seconds
                ),
                poll_interval_seconds=(
                    poll_interval_seconds
                ),
            )
        )

        result["sm37"] = sm37_result

        # ----------------------------------------------------
        # STEP 4: Final status
        # ----------------------------------------------------

        if not sm37_result.get(
            "success",
            False,
        ):

            result["error"] = (
                sm37_result.get(
                    "monitoring",
                    {},
                ).get(
                    "message"
                )
                or
                "SM37 background job did not finish successfully."
            )

            return result

        result["success"] = True

        return result

    # ========================================================
    # RUN MULTIPLE BATCHES
    # ========================================================

    def run_batches(
        self,
        batches: list[list[str]],
        job_name: str = DEFAULT_JOB_NAME,
        submit_background: bool = True,
        timeout_seconds: float = (
            DEFAULT_TIMEOUT_SECONDS
        ),
        poll_interval_seconds: float = (
            DEFAULT_POLL_INTERVAL_SECONDS
        ),
    ) -> dict[str, Any]:
        """
        Execute multiple material batches.

        Processing stops immediately if a ZMAT or SM37
        operation fails.

        This is important because we must not continue to
        the next batch when SAP has reported a failure.
        """

        result: dict[str, Any] = {
            "success": False,
            "job_name": job_name.strip(),
            "batch_count": len(batches),
            "completed_batches": 0,
            "batches": [],
        }

        if not batches:

            result["success"] = True

            return result

        for index, material_codes in enumerate(
            batches,
            start=1,
        ):

            batch_result = (
                self.run_batch(
                    batch_number=index,
                    material_codes=material_codes,
                    job_name=job_name,
                    submit_background=(
                        submit_background
                    ),
                    timeout_seconds=(
                        timeout_seconds
                    ),
                    poll_interval_seconds=(
                        poll_interval_seconds
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
                    f"Batch {index} failed."
                )

                return result

            result[
                "completed_batches"
            ] += 1

        result["success"] = True

        return result