from __future__ import annotations

from typing import Any, Dict

from app.services.sap_interface import SAPClientInterface


class MockSAPClient(SAPClientInterface):
    """
    Fake SAP client used during development.

    This does NOT connect to real SAP.

    It simulates the basic operations that SapAi
    will eventually perform on SAP GUI.
    """

    def __init__(
        self,
        connection_index: int = 0,
        session_index: int = 0,
    ):
        self.connection_index = connection_index
        self.session_index = session_index

        self.connected = False
        self.current_transaction = None

        self.controls: Dict[str, Any] = {}

        self.history = []

    # =========================================================
    # ATTACH
    # =========================================================

    def attach(self) -> Dict[str, Any]:

        self.connected = True

        self.history.append("attach")

        return self.session_info()

    # =========================================================
    # SESSION INFO
    # =========================================================

    def session_info(self) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        return {
            "system": "MOCK_SAP",
            "client": "000",
            "user": "MOCK_USER",
            "transaction": self.current_transaction,
            "program": "MOCK_PROGRAM",
            "connection_index": self.connection_index,
            "session_index": self.session_index,
        }

    # =========================================================
    # TRANSACTION
    # =========================================================

    def start_transaction(
        self,
        tcode: str,
    ) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        self.current_transaction = tcode

        self.history.append(
            f"transaction:{tcode}"
        )

        return {
            "success": True,
            "transaction": tcode,
            "message": (
                f"Mock SAP transaction {tcode} started."
            ),
        }

    # =========================================================
    # CURRENT SCREEN
    # =========================================================

    def get_current_screen_info(self) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        return {
            "transaction": self.current_transaction,
            "screen": "MOCK_SCREEN",
            "title": (
                f"Mock SAP - "
                f"{self.current_transaction or 'Home'}"
            ),
        }

    # =========================================================
    # INSPECT SCREEN
    # =========================================================

    def inspect_screen(self) -> list[Dict[str, Any]]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        return [
            {
                "id": "wnd[0]",
                "type": "GuiMainWindow",
                "name": "MainWindow",
                "text": "Mock SAP",
                "tooltip": "",
            },
            {
                "id": "txt_PLANT",
                "type": "GuiTextField",
                "name": "Plant",
                "text": self.controls.get(
                    "txt_PLANT",
                    "",
                ),
                "tooltip": "Plant",
            },
            {
                "id": "txt_PERIOD",
                "type": "GuiTextField",
                "name": "Period",
                "text": self.controls.get(
                    "txt_PERIOD",
                    "",
                ),
                "tooltip": "Period",
            },
            {
                "id": "txt_VARIANT",
                "type": "GuiTextField",
                "name": "Variant",
                "text": self.controls.get(
                    "txt_VARIANT",
                "",
                ),
                "tooltip": "Variant",
            },
            {
                "id": "btn_EXECUTE",
                "type": "GuiButton",
                "name": "Execute",
                "text": "Execute",
                "tooltip": "Execute",
            },
        ]

    # =========================================================
    # SET TEXT
    # =========================================================

    def set_text(
        self,
        control_id: str,
        value: str,
    ) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        self.controls[control_id] = value

        self.history.append(
            f"set_text:{control_id}={value}"
        )

        return {
            "success": True,
            "control_id": control_id,
            "value": value,
        }
        # =========================================================
    # READ TEXT
    # =========================================================

    def read_text(
        self,
        control_id: str,
    ) -> str:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        value = self.controls.get(
            control_id,
            "",
        )

        self.history.append(
            f"read_text:{control_id}"
        )

        return str(
            value
        )

    # =========================================================
    # PRESS
    # =========================================================

    def press(
        self,
        control_id: str,
    ) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        self.history.append(
            f"press:{control_id}"
        )

        return {
            "success": True,
            "control_id": control_id,
            "message": (
                f"Mock control {control_id} pressed."
            ),
        }

    # =========================================================
    # COMBO BOX
    # =========================================================

    def select_combo_value(
        self,
        control_id: str,
        value: str,
    ) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        self.controls[control_id] = value

        self.history.append(
            f"combo:{control_id}={value}"
        )

        return {
            "success": True,
            "control_id": control_id,
            "value": value,
        }

    # =========================================================
    # VKEY
    # =========================================================

    def send_vkey(
        self,
        key: int,
    ) -> Dict[str, Any]:

        if not self.connected:
            raise RuntimeError(
                "Mock SAP session is not attached."
            )

        self.history.append(
            f"vkey:{key}"
        )

        return {
            "success": True,
            "key": key,
        }

    # =========================================================
    # DETACH
    # =========================================================

    def detach(self) -> None:

        self.history.append("detach")

        self.connected = False
        self.current_transaction = None