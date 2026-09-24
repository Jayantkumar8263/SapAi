"""
ZMAT-FUND_POPR SAP Workflow
===========================

Automates one material-code batch through the
ZMAT-FUND_POPR SAP transaction.

Architecture:

    Prepared material batch
            ↓
        SAPController
            ↓
       ZMAT-FUND_POPR
            ↓
       Material input
            ↓
          Execute
            ↓
    Optional background submit

IMPORTANT
---------
The actual SAP GUI control IDs are not currently known
because real SAP access is not available.

Therefore all control IDs are configurable through:

    state.preferences["zmat_fund_popr_control_ids"]

The workflow can be tested using MockSAPClient.
"""


from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from app.agent.state import AgentState
from app.services.sap_controller import SAPController


# ============================================================
# DEFAULT CONTROL IDs
# ============================================================

DEFAULT_CONTROL_IDS = {
    # Material-code input field.
    #
    # This is a DEVELOPMENT placeholder.
    "material_input": "txt_MATERIAL",

    # Execute button.
    #
    # This is a DEVELOPMENT placeholder.
    "execute": "btn_EXECUTE",

    # Background button.
    #
    # This is a DEVELOPMENT placeholder.
    "background": "btn_BACKGROUND",
}


# ============================================================
# ZMAT-FUND_POPR WORKFLOW
# ============================================================

class ZMATFundPOPRWorkflow:
    """
    High-level SAP workflow for ZMAT-FUND_POPR.

    One instance processes one material-code batch.

    Example:

        workflow = ZMATFundPOPRWorkflow(
            state,
            controller,
        )

        result = workflow.run(
            batch_number=1,
            material_codes=[
                "15111201000046",
                "15111301000109",
            ],
        )
    """

    TRANSACTION = "ZMAT-FUND_POPR"

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
        Return configurable SAP control IDs.

        Configuration location:

            state.preferences[
                "zmat_fund_popr_control_ids"
            ]

        Any configured values override the development
        defaults.
        """

        configured = (
            self.state.preferences.get(
                "zmat_fund_popr_control_ids",
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
    # NORMALIZE BATCH
    # =========================================================

    @staticmethod
    def _normalize_material_codes(
        material_codes: Iterable[str],
    ) -> list[str]:
        """
        Normalize and validate the material-code batch.

        Blank values are removed.

        Duplicates are removed while preserving order.
        """

        seen: set[str] = set()

        normalized: list[str] = []

        for value in material_codes:

            if value is None:
                continue

            code = str(
                value
            ).strip()

            if not code:
                continue

            # Handle Excel-style numeric values.
            if code.endswith(".0"):

                try:

                    number = float(
                        code
                    )

                    if number.is_integer():

                        code = str(
                            int(number)
                        )

                except ValueError:
                    pass

            if code in seen:
                continue

            seen.add(code)

            normalized.append(
                code
            )

        return normalized

    # =========================================================
    # RUN ONE BATCH
    # =========================================================

    def run(
        self,
        batch_number: int,
        material_codes: Iterable[str],
        submit_background: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute one material-code batch through
        ZMAT-FUND_POPR.

        Parameters
        ----------
        batch_number:
            Human-readable batch number.

        material_codes:
            Material codes belonging to this batch.

        submit_background:
            Whether to press the configured background
            submission control after Execute.

            Default is False because the exact real SAP
            background-screen sequence is not yet validated.
        """

        if batch_number <= 0:

            raise ValueError(
                "batch_number must be greater than zero."
            )

        codes = (
            self._normalize_material_codes(
                material_codes
            )
        )

        if not codes:

            raise ValueError(
                "ZMAT-FUND_POPR batch contains "
                "no material codes."
            )

        control_ids = (
            self._get_control_ids()
        )

        result: Dict[str, Any] = {
            "success": False,
            "transaction": self.TRANSACTION,
            "batch_number": batch_number,
            "material_count": len(codes),
            "material_codes": codes,
            "submit_background": (
                submit_background
            ),
            "control_ids": control_ids,
            "operations": [],
        }

        try:

            # -------------------------------------------------
            # 1. CONNECT
            # -------------------------------------------------

            connection = (
                self.controller.connect()
            )

            result["operations"].append(
                {
                    "step": "connect",
                    "result": connection,
                }
            )

            # -------------------------------------------------
            # 2. START TRANSACTION
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 3. PREPARE MATERIAL-CODE INPUT
            # -------------------------------------------------
            #
            # The exact real SAP input mechanism is not yet
            # known. We therefore send the complete batch as
            # newline-separated values to the configured
            # input control.
            #
            # Once real SAP access is available, this is the
            # place where we adapt to the actual screen:
            #
            #   - table control
            #   - multiline field
            #   - paste area
            #   - selection screen
            #   - etc.
            # -------------------------------------------------

            batch_text = "\n".join(
                codes
            )

            input_result = (
                self.controller.set_text(
                    control_ids[
                        "material_input"
                    ],
                    batch_text,
                )
            )

            result["operations"].append(
                {
                    "step": "material_input",
                    "control_id": control_ids[
                        "material_input"
                    ],
                    "material_count": len(
                        codes
                    ),
                    "result": input_result,
                }
            )

            # -------------------------------------------------
            # 4. EXECUTE
            # -------------------------------------------------

            execute_result = (
                self.controller.press(
                    control_ids[
                        "execute"
                    ]
                )
            )

            result["operations"].append(
                {
                    "step": "execute",
                    "control_id": control_ids[
                        "execute"
                    ],
                    "result": execute_result,
                }
            )

            # -------------------------------------------------
            # 5. OPTIONAL BACKGROUND SUBMISSION
            # -------------------------------------------------

            if submit_background:

                background_result = (
                    self.controller.press(
                        control_ids[
                            "background"
                        ]
                    )
                )

                result["operations"].append(
                    {
                        "step": (
                            "background_submission"
                        ),
                        "control_id": control_ids[
                            "background"
                        ],
                        "result": background_result,
                    }
                )

                result[
                    "background_submitted"
                ] = True

            else:

                result[
                    "background_submitted"
                ] = False

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            result["success"] = True

            return result

        finally:

            # -------------------------------------------------
            # ALWAYS DISCONNECT
            # -------------------------------------------------

            self.controller.disconnect()

    # =========================================================
    # RUN BATCH FROM TXT FILE
    # =========================================================

    def run_from_file(
        self,
        batch_number: int,
        batch_file: str | Path,
        submit_background: bool = False,
    ) -> Dict[str, Any]:
        """
        Load one previously-created batch TXT file and
        execute it through ZMAT-FUND_POPR.
        """

        batch_path = Path(
            batch_file
        )

        if not batch_path.exists():

            raise FileNotFoundError(
                "ZMAT-FUND_POPR batch file not found: "
                f"{batch_path}"
            )

        text = batch_path.read_text(
            encoding="utf-8"
        )

        material_codes = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        result = self.run(
            batch_number=batch_number,
            material_codes=material_codes,
            submit_background=submit_background,
        )

        result[
            "batch_file"
        ] = str(batch_path)

        return result