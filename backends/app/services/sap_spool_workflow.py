"""
SAP Spool Extraction Workflow
=============================

Handles extraction of spool output after an SAP background
job has completed.

Process:

    SM37
      ↓
    Finished job
      ↓
    Open spool
      ↓
    Read spool output
      ↓
    Save local TXT

IMPORTANT:
Real SAP control IDs are placeholders until SAP access is
available and the actual SM37/spool screen is inspected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.agent.state import AgentState
from app.services.sap_controller import SAPController


DEFAULT_CONTROL_IDS = {
    "spool": "btn_SPOOL",
    "spool_text": "txt_SPOOL",
}


class SAPSpoolWorkflow:
    """
    Extract spool output belonging to a completed SAP job.
    """

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

        configured = (
            self.state.preferences.get(
                "sap_spool_control_ids",
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
    # OPEN SPOOL
    # =========================================================

    def open_spool(self) -> Dict[str, Any]:
        """
        Open the spool associated with the currently selected
        completed SAP job.
        """

        control_ids = (
            self._get_control_ids()
        )

        result = {
            "success": False,
            "operations": [],
            "control_ids": control_ids,
        }

        spool_result = (
            self.controller.press(
                control_ids["spool"]
            )
        )

        result["operations"].append(
            {
                "step": "open_spool",
                "control_id": control_ids[
                    "spool"
                ],
                "result": spool_result,
            }
        )

        result["success"] = True

        return result

    # =========================================================
    # READ SPOOL
    # =========================================================

    def read_spool(self) -> str:
        """
        Read the visible spool text.

        The exact SAP control will be replaced after
        real SAP inspection.
        """

        control_ids = (
            self._get_control_ids()
        )

        return self.controller.read_text(
            control_ids["spool_text"]
        )

    # =========================================================
    # SAVE TXT
    # =========================================================

    def save_spool(
        self,
        spool_text: str,
        output_file: str | Path,
    ) -> Dict[str, Any]:
        """
        Save spool text as a local TXT file.
        """

        if not spool_text.strip():

            raise ValueError(
                "SAP spool output is empty."
            )

        output_path = Path(
            output_file
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            spool_text,
            encoding="utf-8",
        )

        return {
            "success": True,
            "output_file": str(
                output_path
            ),
            "bytes": output_path.stat().st_size,
        }

    # =========================================================
    # COMPLETE EXTRACTION
    # =========================================================

    def extract(
        self,
        output_file: str | Path,
    ) -> Dict[str, Any]:
        """
        Connect to SAP, open the spool, read it and save
        the spool output locally as TXT.
        """

        try:

            # -------------------------------------------------
            # 1. CONNECT
            # -------------------------------------------------

            connection = (
                self.controller.connect()
            )

            # -------------------------------------------------
            # 2. OPEN SPOOL
            # -------------------------------------------------

            opened = (
                self.open_spool()
            )

            # -------------------------------------------------
            # 3. READ SPOOL
            # -------------------------------------------------

            spool_text = (
                self.read_spool()
            )

            # -------------------------------------------------
            # 4. SAVE TXT
            # -------------------------------------------------

            saved = (
                self.save_spool(
                    spool_text,
                    output_file,
                )
            )

            return {
                "success": True,
                "connection": connection,
                "open": opened,
                "output_file": saved[
                    "output_file"
                ],
                "bytes": saved[
                    "bytes"
                ],
            }

        finally:

            # -------------------------------------------------
            # ALWAYS DISCONNECT
            # -------------------------------------------------

            self.controller.disconnect()