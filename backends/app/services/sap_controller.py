from __future__ import annotations

from typing import Any, Dict

from app.services.sap_interface import SAPClientInterface


class SAPController:
    """
    High-level controller for SAP automation.

    The controller does not know whether it is talking to:

        - MockSAPClient
        - SAPGUIClient

    It only communicates through SAPClientInterface.
    """

    def __init__(
        self,
        client: SAPClientInterface,
    ):
        self.client = client
        self.attached = False

    # =========================================================
    # CONNECT
    # =========================================================

    def connect(self) -> Dict[str, Any]:
        """
        Attach to the SAP client.
        """

        result = self.client.attach()

        self.attached = True

        return {
            "success": True,
            "session": result,
        }

    # =========================================================
    # SESSION INFORMATION
    # =========================================================

    def get_session_info(self) -> Dict[str, Any]:
        """
        Return current SAP session information.
        """

        self._require_connection()

        return self.client.session_info()

    # =========================================================
    # START TRANSACTION
    # =========================================================

    def start_transaction(
        self,
        tcode: str,
    ) -> Dict[str, Any]:
        """
        Start an SAP transaction.
        """

        self._require_connection()

        if not tcode:
            raise ValueError(
                "SAP transaction code cannot be empty."
            )

        return self.client.start_transaction(
            tcode
        )

    # =========================================================
    # SET TEXT
    # =========================================================

    def set_text(
        self,
        control_id: str,
        value: str,
    ) -> Dict[str, Any]:
        """
        Set a value into an SAP text field.
        """

        self._require_connection()

        if not control_id:
            raise ValueError(
                "SAP control ID cannot be empty."
            )

        return self.client.set_text(
            control_id,
            value,
        )
        # =========================================================
    # READ TEXT
    # =========================================================

    def read_text(
        self,
        control_id: str,
    ) -> str:
        """
        Read the current text/value of an SAP control.
        """

        self._require_connection()

        if not control_id:
            raise ValueError(
                "SAP control ID cannot be empty."
            )

        return self.client.read_text(
            control_id
        )

    # =========================================================
    # PRESS BUTTON
    # =========================================================

    def press(
        self,
        control_id: str,
    ) -> Dict[str, Any]:
        """
        Press an SAP button/control.
        """

        self._require_connection()

        if not control_id:
            raise ValueError(
                "SAP control ID cannot be empty."
            )

        return self.client.press(
            control_id
        )

    # =========================================================
    # SELECT COMBO VALUE
    # =========================================================

    def select_combo(
        self,
        control_id: str,
        value: str,
    ) -> Dict[str, Any]:
        """
        Select a value from an SAP combo box.
        """

        self._require_connection()

        return self.client.select_combo_value(
            control_id,
            value,
        )

    # =========================================================
    # SEND VKEY
    # =========================================================

    def send_vkey(
        self,
        key: int,
    ) -> Dict[str, Any]:
        """
        Send an SAP virtual key.
        """

        self._require_connection()

        return self.client.send_vkey(
            key
        )

    # =========================================================
    # SCREEN INFORMATION
    # =========================================================

    def get_screen_info(self) -> Dict[str, Any]:
        """
        Return current SAP screen information.
        """

        self._require_connection()

        return self.client.get_current_screen_info()

    # =========================================================
    # SCREEN INSPECTION
    # =========================================================

    def inspect_screen(self) -> list[Dict[str, Any]]:
        """
        Inspect controls on the current SAP screen.
        """

        self._require_connection()

        return self.client.inspect_screen()

    # =========================================================
    # DISCONNECT
    # =========================================================

    def disconnect(self) -> None:
        """
        Detach from SAP.
        """

        if self.attached:
            self.client.detach()

        self.attached = False

    # =========================================================
    # CONNECTION CHECK
    # =========================================================

    def _require_connection(self) -> None:
        """
        Make sure SAP is connected before executing
        an operation.
        """

        if not self.attached:
            raise RuntimeError(
                "SAP is not connected. "
                "Call connect() first."
            )