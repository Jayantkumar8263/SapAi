"""
SM37 SAP Job Monitoring Workflow
================================

Monitors background jobs created by SAP automation.

Expected process:

    ZMAT-FUND_POPR
          ↓
    Background Job
          ↓
         SM37
          ↓
    Search Job
          ↓
    Read Status
          ↓
    FINISHED / CANCELLED / TIMEOUT

IMPORTANT
---------
Real SM37 control IDs are not known yet because real SAP
access is unavailable.

Therefore all relevant controls are configurable through:

    state.preferences["sm37_control_ids"]
"""

from __future__ import annotations

import time
from typing import Any, Dict

from app.agent.state import AgentState
from app.services.sap_controller import SAPController


# ============================================================
# DEFAULT CONTROL IDS
# ============================================================

DEFAULT_CONTROL_IDS = {
    "job_name": "txt_JOB_NAME",
    "execute": "btn_EXECUTE",
    "status": "txt_JOB_STATUS",
    "job_number": "txt_JOB_NUMBER",
}


# ============================================================
# JOB STATUS
# ============================================================

FINISHED_STATUSES = {
    "FINISHED",
    "COMPLETED",
    "COMPLETE",
}

FAILED_STATUSES = {
    "CANCELLED",
    "CANCELED",
    "ERROR",
    "FAILED",
    "ABORTED",
}


# ============================================================
# SM37 WORKFLOW
# ============================================================

class SM37Workflow:
    """
    SAP SM37 background-job monitoring workflow.

    This class does not create the background job.

    It searches for and monitors a job that was already
    submitted by a previous SAP workflow.
    """

    TRANSACTION = "SM37"

    def __init__(
        self,
        state: AgentState,
        controller: SAPController,
    ):
        self.state = state
        self.controller = controller

    # =========================================================
    # CONTROL IDS
    # =========================================================

    def _get_control_ids(self) -> dict[str, str]:
        """
        Get configurable SM37 control IDs.
        """

        configured = (
            self.state.preferences.get(
                "sm37_control_ids",
                {},
            )
        )

        control_ids = (
            DEFAULT_CONTROL_IDS.copy()
        )

        if isinstance(
            configured,
            dict,
        ):
            control_ids.update(
                configured
            )

        return control_ids

    # =========================================================
    # NORMALIZE STATUS
    # =========================================================

    @staticmethod
    def normalize_status(
        status: str,
    ) -> str:
        """
        Normalize an SAP job status.
        """

        if status is None:
            return ""

        return (
            str(status)
            .strip()
            .upper()
        )

    # =========================================================
    # OPEN SM37
    # =========================================================

    def open_sm37(
        self,
    ) -> Dict[str, Any]:
        """
        Connect to SAP and open SM37.
        """

        control_ids = (
            self._get_control_ids()
        )

        result = {
            "success": False,
            "transaction": self.TRANSACTION,
            "control_ids": control_ids,
            "operations": [],
        }

        connection = (
            self.controller.connect()
        )

        result["operations"].append(
            {
                "step": "connect",
                "result": connection,
            }
        )

        transaction = (
            self.controller.start_transaction(
                self.TRANSACTION
            )
        )

        result["operations"].append(
            {
                "step": "start_transaction",
                "result": transaction,
            }
        )

        result["success"] = True

        return result

    # =========================================================
    # SEARCH JOB
    # =========================================================

    def search_job(
        self,
        job_name: str,
    ) -> Dict[str, Any]:
        """
        Search for a background job by name.

        The exact SM37 screen interaction will be finalized
        after real SAP screen inspection.
        """

        if not job_name or not job_name.strip():

            raise ValueError(
                "job_name cannot be empty."
            )

        control_ids = (
            self._get_control_ids()
        )

        result = {
            "success": False,
            "job_name": job_name.strip(),
            "operations": [],
        }

        input_result = (
            self.controller.set_text(
                control_ids["job_name"],
                job_name.strip(),
            )
        )

        result["operations"].append(
            {
                "step": "job_name",
                "control_id": control_ids[
                    "job_name"
                ],
                "result": input_result,
            }
        )

        execute_result = (
            self.controller.press(
                control_ids["execute"]
            )
        )

        result["operations"].append(
            {
                "step": "execute_search",
                "control_id": control_ids[
                    "execute"
                ],
                "result": execute_result,
            }
        )

        result["success"] = True

        return result

    # =========================================================
    # READ JOB STATUS
    # =========================================================

    def read_job_status(
        self,
    ) -> str:
        """
        Read the current job status from the configured
        SAP control.
        """

        control_ids = (
            self._get_control_ids()
        )

        status = (
            self.controller.read_text(
                control_ids["status"]
            )
        )

        return self.normalize_status(
            status
        )

    # =========================================================
    # READ JOB NUMBER
    # =========================================================

    def read_job_number(
        self,
    ) -> str:
        """
        Read the current SAP background-job number.
        """

        control_ids = (
            self._get_control_ids()
        )

        job_number = (
            self.controller.read_text(
                control_ids["job_number"]
            )
        )

        return str(
            job_number
        ).strip()

    # =========================================================
    # WAIT UNTIL FINISHED
    # =========================================================

    def wait_until_finished(
        self,
        timeout_seconds: float = 300,
        poll_interval_seconds: float = 5,
    ) -> Dict[str, Any]:
        """
        Poll SM37 until the job finishes, fails, or times out.

        Returns a structured result.

        The timeout prevents the automation from waiting
        forever if SAP gets stuck.
        """

        if timeout_seconds <= 0:

            raise ValueError(
                "timeout_seconds must be greater than zero."
            )

        if poll_interval_seconds <= 0:

            raise ValueError(
                "poll_interval_seconds must be greater than zero."
            )

        started_at = time.monotonic()

        status_history: list[str] = []

        while True:

            status = (
                self.read_job_status()
            )

            status_history.append(
                status
            )

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            if status in FINISHED_STATUSES:

                elapsed = (
                    time.monotonic()
                    - started_at
                )

                return {
                    "success": True,
                    "status": status,
                    "job_number": (
                        self.read_job_number()
                    ),
                    "elapsed_seconds": elapsed,
                    "status_history": status_history,
                }

            # -------------------------------------------------
            # FAILURE
            # -------------------------------------------------

            if status in FAILED_STATUSES:

                elapsed = (
                    time.monotonic()
                    - started_at
                )

                return {
                    "success": False,
                    "status": status,
                    "job_number": (
                        self.read_job_number()
                    ),
                    "elapsed_seconds": elapsed,
                    "status_history": status_history,
                    "message": (
                        "SAP background job failed."
                    ),
                }

            # -------------------------------------------------
            # TIMEOUT
            # -------------------------------------------------

            elapsed = (
                time.monotonic()
                - started_at
            )

            if elapsed >= timeout_seconds:

                return {
                    "success": False,
                    "status": status,
                    "job_number": (
                        self.read_job_number()
                    ),
                    "elapsed_seconds": elapsed,
                    "status_history": status_history,
                    "message": (
                        "SAP background job monitoring "
                        "timed out."
                    ),
                }

            time.sleep(
                poll_interval_seconds
            )

    # =========================================================
    # COMPLETE MONITORING FLOW
    # =========================================================

    def monitor_job(
        self,
        job_name: str,
        timeout_seconds: float = 300,
        poll_interval_seconds: float = 5,
    ) -> Dict[str, Any]:
        """
        Open SM37, search for a job, then monitor it.
        """

        try:

            result = self.open_sm37()

            search_result = (
                self.search_job(
                    job_name
                )
            )

            monitoring_result = (
                self.wait_until_finished(
                    timeout_seconds=timeout_seconds,
                    poll_interval_seconds=(
                        poll_interval_seconds
                    ),
                )
            )

            return {
                "success": monitoring_result[
                    "success"
                ],
                "transaction": self.TRANSACTION,
                "job_name": job_name,
                "open": result,
                "search": search_result,
                "monitoring": monitoring_result,
            }

        finally:

            self.controller.disconnect()