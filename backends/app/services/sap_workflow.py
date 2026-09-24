from __future__ import annotations

from typing import Any, Dict

from app.agent.state import AgentState
from app.services.sap_controller import SAPController


class SAPWorkflow:
    """
    High-level deterministic SAP workflow.

    This class works with both:

        - MockSAPClient
        - SAPGUIClient

    The actual SAP control IDs are configurable through
    AgentState.preferences.

    Default IDs are the IDs used by MockSAPClient.

    Real SAP IDs can later be supplied after inspecting
    the real SAP MC.1 screen.
    """

    DEFAULT_CONTROL_IDS = {
        "variant": "txt_VARIANT",
        "period": "txt_PERIOD",
        "plant": "txt_PLANT",
        "execute": "btn_EXECUTE",
    }

    def __init__(
        self,
        state: AgentState,
        controller: SAPController,
    ):
        self.state = state
        self.controller = controller

    # =========================================================
    # CONTROL ID CONFIGURATION
    # =========================================================

    def get_control_ids(self) -> Dict[str, str]:
        """
        Return SAP control IDs.

        State preferences can override the defaults:

            state.preferences = {
                "sap_control_ids": {
                    "variant": "...",
                    "period": "...",
                    "plant": "...",
                    "execute": "...",
                }
            }

        This allows real SAP IDs to be configured without
        changing the workflow code.
        """

        configured = {}

        preferences = getattr(
            self.state,
            "preferences",
            {},
        )

        if isinstance(
            preferences,
            dict,
        ):

            configured = preferences.get(
                "sap_control_ids",
                {},
            )

        if not isinstance(
            configured,
            dict,
        ):

            configured = {}

        control_ids = dict(
            self.DEFAULT_CONTROL_IDS
        )

        for name, value in configured.items():

            if value:

                control_ids[
                    str(name)
                ] = str(value)

        return control_ids

    # =========================================================
    # MC.1 WORKFLOW
    # =========================================================

    def run_mc1(self) -> Dict[str, Any]:
        """
        Execute the deterministic MC.1 workflow.

        Sequence:

            1. Connect
            2. Start MC.1
            3. Set variant
            4. Set reporting period
            5. Set plant
            6. Execute

        This method does NOT guess real SAP control IDs.
        """

        result: Dict[str, Any] = {
            "success": False,
            "transaction": None,
            "parameters": {},
            "control_ids": {},
            "operations": [],
        }

        control_ids = (
            self.get_control_ids()
        )

        result["control_ids"] = dict(
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

        try:

            # -------------------------------------------------
            # 2. START TRANSACTION
            # -------------------------------------------------

            tcode = getattr(
                self.state,
                "tcode",
                "MC.1",
            )

            if not tcode:
                tcode = "MC.1"

            transaction = (
                self.controller.start_transaction(
                    tcode
                )
            )

            result["transaction"] = tcode

            result["operations"].append(
                {
                    "step": "start_transaction",
                    "result": transaction,
                }
            )

            # -------------------------------------------------
            # 3. SET VARIANT
            # -------------------------------------------------

            variant = getattr(
                self.state,
                "variant",
                None,
            )

            if variant:

                variant_result = (
                    self.controller.set_text(
                        control_ids["variant"],
                        str(variant),
                    )
                )

                result["operations"].append(
                    {
                        "step": "set_variant",
                        "result": variant_result,
                    }
                )

                result["parameters"][
                    "variant"
                ] = str(variant)

            # -------------------------------------------------
            # 4. SET PERIOD
            # -------------------------------------------------

            current_period = getattr(
                self.state,
                "current_period",
                None,
            )

            if current_period:

                period_result = (
                    self.controller.set_text(
                        control_ids["period"],
                        str(current_period),
                    )
                )

                result["operations"].append(
                    {
                        "step": "set_period",
                        "result": period_result,
                    }
                )

                result["parameters"][
                    "current_period"
                ] = str(current_period)

            # -------------------------------------------------
            # 5. SET PLANT
            # -------------------------------------------------

            plant = getattr(
                self.state,
                "plant",
                None,
            )

            if plant:

                plant_result = (
                    self.controller.set_text(
                        control_ids["plant"],
                        str(plant),
                    )
                )

                result["operations"].append(
                    {
                        "step": "set_plant",
                        "result": plant_result,
                    }
                )

                result["parameters"][
                    "plant"
                ] = str(plant)

            # -------------------------------------------------
            # 6. EXECUTE
            # -------------------------------------------------

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

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            result["success"] = True

            return result

        except Exception as exc:

            result["success"] = False

            result["message"] = (
                f"SAP MC.1 workflow failed: {exc}"
            )

            result["error"] = str(exc)

            raise

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self) -> None:
        """
        Safely disconnect from SAP.

        This only releases the automation connection.
        It does not close SAP itself.
        """

        self.controller.disconnect()