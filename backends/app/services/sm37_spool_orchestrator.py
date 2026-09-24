"""
SM37 → SAP Spool Orchestrator
=============================

Connects the existing:

    SM37Workflow
        ↓
    SAPSpoolWorkflow

BSP process:

    ZMAT-FUND_POPR
        ↓
    Background Job
        ↓
    SM37
        ↓
    ZMAT_PO_PR = FINISHED
        ↓
    Spool
        ↓
    Save as unconverted TXT

This module only orchestrates existing workflows.

It does NOT implement SAP GUI controls itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agent.state import AgentState

from app.services.sap_controller import SAPController

from app.services.sm37_workflow import (
    SM37Workflow,
)

from app.services.sap_spool_workflow import (
    SAPSpoolWorkflow,
)


DEFAULT_JOB_NAME = "ZMAT_PO_PR"

DEFAULT_TIMEOUT_SECONDS = 300

DEFAULT_POLL_INTERVAL_SECONDS = 5


class SM37SpoolOrchestrator:
    """
    Connects completed SM37 jobs to spool extraction.
    """

    def __init__(
        self,
        state: AgentState,
        controller: SAPController,
        sm37_workflow: SM37Workflow | None = None,
        spool_workflow: SAPSpoolWorkflow | None = None,
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

        self.sm37_workflow = (
            sm37_workflow
            if sm37_workflow is not None
            else SM37Workflow(
                state,
                controller,
            )
        )

        self.spool_workflow = (
            spool_workflow
            if spool_workflow is not None
            else SAPSpoolWorkflow(
                state,
                controller,
            )
        )

    # ========================================================
    # MONITOR JOB
    # ========================================================

    def monitor_job(
        self,
        job_name: str = DEFAULT_JOB_NAME,
        timeout_seconds: float = (
            DEFAULT_TIMEOUT_SECONDS
        ),
        poll_interval_seconds: float = (
            DEFAULT_POLL_INTERVAL_SECONDS
        ),
    ) -> dict[str, Any]:
        """
        Monitor an existing SAP background job.

        This does NOT extract the spool.

        It only waits until SM37 reports FINISHED,
        CANCELLED, ERROR, or TIMEOUT.
        """

        return self.sm37_workflow.monitor_job(
            job_name,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=(
                poll_interval_seconds
            ),
        )

    # ========================================================
    # EXTRACT SPOOL
    # ========================================================

    def extract_spool(
        self,
        output_file: str | Path,
    ) -> dict[str, Any]:
        """
        Extract the spool through the existing
        SAPSpoolWorkflow.

        The output is saved locally as TXT.
        """

        output_path = Path(
            output_file
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return self.spool_workflow.extract(
            output_path
        )

    # ========================================================
    # COMPLETE SM37 → SPOOL
    # ========================================================

    def run(
        self,
        output_file: str | Path,
        job_name: str = DEFAULT_JOB_NAME,
        timeout_seconds: float = (
            DEFAULT_TIMEOUT_SECONDS
        ),
        poll_interval_seconds: float = (
            DEFAULT_POLL_INTERVAL_SECONDS
        ),
    ) -> dict[str, Any]:
        """
        Complete:

            SM37
              ↓
            FINISHED
              ↓
            Spool extraction
              ↓
            TXT

        Spool extraction is started ONLY if the job
        finishes successfully.
        """

        result: dict[str, Any] = {
            "success": False,
            "job_name": job_name,
            "monitoring": None,
            "spool": None,
            "output_file": str(
                output_file
            ),
        }

        # ----------------------------------------------------
        # STEP 1 — Monitor SM37
        # ----------------------------------------------------

        monitoring = (
            self.monitor_job(
                job_name=job_name,
                timeout_seconds=(
                    timeout_seconds
                ),
                poll_interval_seconds=(
                    poll_interval_seconds
                ),
            )
        )

        result[
            "monitoring"
        ] = monitoring

        if not monitoring.get(
            "success",
            False,
        ):

            result[
                "error"
            ] = (
                monitoring.get(
                    "monitoring",
                    {},
                ).get(
                    "message"
                )
                or
                "SAP background job did not finish successfully."
            )

            return result

        # ----------------------------------------------------
        # STEP 2 — Extract spool
        # ----------------------------------------------------

        spool_result = (
            self.extract_spool(
                output_file
            )
        )

        result[
            "spool"
        ] = spool_result

        if not spool_result.get(
            "success",
            False,
        ):

            result[
                "error"
            ] = (
                spool_result.get(
                    "error"
                )
                or
                "SAP spool extraction failed."
            )

            return result

        # ----------------------------------------------------
        # STEP 3 — Verify output
        # ----------------------------------------------------

        output_path = Path(
            output_file
        )

        if not output_path.exists():

            result[
                "error"
            ] = (
                "Spool workflow reported success, "
                "but the TXT output file was not found."
            )

            return result

        result[
            "output_file"
        ] = str(
            output_path
        )

        result[
            "success"
        ] = True

        return result