"""
ZMMRIREP SAP Workflow
=====================

Automates the SAP ZMMRIREP stage used to obtain
RI material codes.

IMPORTANT:
- This workflow does not hard-code real SAP GUI control IDs.
- Control IDs are configurable through AgentState.preferences.
- MockSAPClient is used during development.
- Real SAP IDs must be discovered from the actual SAP screen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from app.agent.state import AgentState
from app.services.sap_controller import SAPController


# ============================================================
# DEFAULT CONTROL IDs
# ============================================================

DEFAULT_CONTROL_IDS = {
    "execute": "btn_EXECUTE",
}


# ============================================================
# ZMMRIREP WORKFLOW
# ============================================================

class ZMMRIREPWorkflow:
    """
    High-level workflow for the BSP ZMMRIREP transaction.

    Current development flow:

        Connect
          ↓
        ZMMRIREP
          ↓
        Execute
          ↓
        Capture output location

    The actual SAP control IDs remain configurable because
    real SAP access is not currently available.
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
        """
        Return ZMMRIREP control IDs.

        User-specific control IDs can be supplied through:

            state.preferences["zmmrirep_control_ids"]
        """

        configured = (
            self.state.preferences.get(
                "zmmrirep_control_ids",
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
    # RUN ZMMRIREP
    # =========================================================

    def run(
        self,
        output_file: str | Path | None = None,
    ) -> Dict[str, Any]:
        """
        Execute ZMMRIREP.

        output_file is optional because the actual SAP output
        mechanism has not yet been validated against real SAP.
        """

        result: Dict[str, Any] = {
            "success": False,
            "transaction": "ZMMRIREP",
            "parameters": {},
            "operations": [],
            "ri_output_file": None,
            "control_ids": {},
        }

        control_ids = (
            self._get_control_ids()
        )

        result["control_ids"] = (
            control_ids
        )

        # -----------------------------------------------------
        # 1. CONNECT
        # -----------------------------------------------------

        connection = (
            self.controller.connect()
        )

        result["operations"].append(
            {
                "step": "connect",
                "result": connection,
            }
        )

        # -----------------------------------------------------
        # 2. START TRANSACTION
        # -----------------------------------------------------

        transaction = (
            self.controller.start_transaction(
                "ZMMRIREP"
            )
        )

        result["operations"].append(
            {
                "step": "start_transaction",
                "result": transaction,
            }
        )

        # -----------------------------------------------------
        # 3. EXECUTE
        # -----------------------------------------------------

        execute_result = (
            self.controller.press(
                control_ids["execute"]
            )
        )

        result["operations"].append(
            {
                "step": "execute",
                "result": execute_result,
            }
        )

        # -----------------------------------------------------
        # 4. OUTPUT FILE
        # -----------------------------------------------------

        if output_file is not None:

            output_path = Path(
                output_file
            )

            result[
                "ri_output_file"
            ] = str(output_path)

        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------

        result["success"] = True

        return result

    # =========================================================
    # LOAD RI MATERIAL CODES
    # =========================================================

    @staticmethod
    def load_ri_material_codes(
        output_file: str | Path,
    ) -> set[str]:
        """
        Load RI material codes from a ZMMRIREP output file.

        Expected format:
            one material code per row.

        The output is read without assuming a header.
        """

        output_file = Path(
            output_file
        )

        if not output_file.exists():

            raise FileNotFoundError(
                f"ZMMRIREP output file not found: "
                f"{output_file}"
            )

        df = pd.read_excel(
            output_file,
            header=None,
        )

        if df.empty:
            return set()

        values = (
            df.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
        )

        codes: set[str] = set()

        for value in values:

            # Ignore accidental headers.
            if value.lower() in {
                "material",
                "material code",
                "material_code",
                "matnr",
            }:
                continue

            # Excel may represent numeric material codes
            # as values such as 123456.0
            if value.endswith(".0"):

                try:

                    number = float(
                        value
                    )

                    if number.is_integer():

                        value = str(
                            int(number)
                        )

                except ValueError:

                    pass

            if value:
                codes.add(value)

        return codes