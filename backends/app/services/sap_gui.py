"""
SAP GUI Scripting Adapter
==========================

This module provides a small Python wrapper around SAP GUI Scripting.

Purpose:
    - Connect to an already-open SAP GUI session
    - Inspect the active SAP screen
    - Execute SAP transactions
    - Provide control IDs that can later be automated

Important:
    - SAP GUI must already be installed.
    - SAP GUI Scripting must be enabled.
    - The user should normally log into SAP manually first.
    - This module does NOT store or print SAP passwords.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import win32com.client

from app.services.sap_interface import SAPClientInterface


class SAPGUIError(Exception):
    """Raised when SAP GUI automation fails."""


class SAPGUIClient:
    """
    Lightweight SAP GUI Scripting client.

    The client attaches to an existing SAP GUI session instead
    of opening SAP or handling credentials.
    """

    def __init__(
        self,
        connection_index: int = 0,
        session_index: int = 0,
    ):
        self.connection_index = connection_index
        self.session_index = session_index

        self.sap_gui = None
        self.application = None
        self.connection = None
        self.session = None

    # =========================================================
    # CONNECT TO SAP GUI
    # =========================================================

    def attach(self) -> Dict[str, Any]:
        """
        Attach to an already-running SAP GUI session.

        Returns basic information about the SAP session.
        """

        try:
            self.sap_gui = win32com.client.GetObject(
                "SAPGUI"
            )

            self.application = (
                self.sap_gui.GetScriptingEngine()
            )

        except Exception as exc:
            raise SAPGUIError(
                "Unable to connect to SAP GUI. "
                "Make sure SAP Logon is running and "
                "SAP GUI Scripting is enabled."
            ) from exc

        try:
            self.connection = (
                self.application.Children(
                    self.connection_index
                )
            )
        except Exception as exc:
            raise SAPGUIError(
                f"SAP connection index "
                f"{self.connection_index} was not found."
            ) from exc

        try:
            self.session = (
                self.connection.Children(
                    self.session_index
                )
            )
        except Exception as exc:
            raise SAPGUIError(
                f"SAP session index "
                f"{self.session_index} was not found."
            ) from exc

        return self.session_info()

    # =========================================================
    # SESSION INFORMATION
    # =========================================================

    def session_info(self) -> Dict[str, Any]:
        """
        Return safe information about the current SAP session.

        Passwords and sensitive authentication information are
        never returned.
        """

        if self.session is None:
            raise SAPGUIError(
                "SAP session is not attached."
            )

        info: Dict[str, Any] = {}

        attributes = {
            "system": "Info.SystemName",
            "client": "Info.Client",
            "user": "Info.User",
            "transaction": "Info.Transaction",
            "program": "Info.Program",
        }

        for key, attribute_path in attributes.items():

            try:
                value = self._get_nested_attribute(
                    self.session,
                    attribute_path,
                )
                info[key] = value
            except Exception:
                info[key] = None

        return info

    # =========================================================
    # RUN TRANSACTION
    # =========================================================

    def start_transaction(
        self,
        tcode: str,
    ) -> Dict[str, Any]:
        """
        Start an SAP transaction.

        Example:

            client.start_transaction("MC.1")
        """

        if self.session is None:
            raise SAPGUIError(
                "SAP session is not attached."
            )

        if not tcode:
            raise SAPGUIError(
                "SAP transaction code is required."
            )

        tcode = tcode.strip()

        try:
            self.session.StartTransaction(
                tcode
            )
        except Exception as exc:
            raise SAPGUIError(
                f"Unable to start SAP transaction "
                f"{tcode}."
            ) from exc

        return {
            "success": True,
            "tcode": tcode,
            "session": self.session_info(),
        }

    # =========================================================
    # CURRENT SCREEN
    # =========================================================

    def get_current_screen_info(
        self,
    ) -> Dict[str, Any]:
        """
        Return information about the current SAP window.
        """

        if self.session is None:
            raise SAPGUIError(
                "SAP session is not attached."
            )

        try:
            window = self.session.FindById(
                "wnd[0]"
            )

            return {
                "id": "wnd[0]",
                "type": getattr(
                    window,
                    "Type",
                    None,
                ),
                "text": getattr(
                    window,
                    "Text",
                    None,
                ),
                "transaction": getattr(
                    self.session.Info,
                    "Transaction",
                    None,
                ),
                "program": getattr(
                    self.session.Info,
                    "Program",
                    None,
                ),
            }

        except Exception as exc:
            raise SAPGUIError(
                "Unable to inspect the current "
                "SAP screen."
            ) from exc

    # =========================================================
    # CONTROL TREE
    # =========================================================

    def inspect_screen(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Inspect controls available on the current SAP screen.

        This is extremely useful while developing the
        automation because SAP GUI control IDs differ
        between screens/configurations.
        """

        if self.session is None:
            raise SAPGUIError(
                "SAP session is not attached."
            )

        controls: List[Dict[str, Any]] = []

        try:
            root = self.session.FindById(
                "wnd[0]"
            )
        except Exception as exc:
            raise SAPGUIError(
                "Unable to access SAP main window."
            ) from exc

        self._walk_controls(
            root,
            controls,
        )

        return controls

    # =========================================================
    # FIND CONTROL
    # =========================================================

    def find_control(
        self,
        control_id: str,
    ):
        """
        Find a SAP GUI control by its ID.

        Example:

            control = client.find_control(
                "wnd[0]/usr/..."
            )
        """

        if self.session is None:
            raise SAPGUIError(
                "SAP session is not attached."
            )

        if not control_id:
            raise SAPGUIError(
                "SAP control ID is required."
            )

        try:
            return self.session.FindById(
                control_id
            )
        except Exception as exc:
            raise SAPGUIError(
                f"SAP control was not found: "
                f"{control_id}"
            ) from exc

    # =========================================================
    # SET CONTROL TEXT
    # =========================================================

    def set_text(
        self,
        control_id: str,
        value: str,
    ) -> Dict[str, Any]:
        """
        Set text/value of an SAP GUI input control.
        """

        control = self.find_control(
            control_id
        )

        try:
            control.Text = value
        except Exception as exc:
            raise SAPGUIError(
                f"Unable to set text for "
                f"{control_id}."
            ) from exc

        return {
            "success": True,
            "control_id": control_id,
        }
        # =========================================================
    # READ CONTROL TEXT
    # =========================================================

    def read_text(
        self,
        control_id: str,
    ) -> str:
        """
        Read the Text property of an SAP GUI control.

        The actual control ID must come from the real
        SAP screen inspection.
        """

        control = self.find_control(
            control_id
        )

        try:

            value = getattr(
                control,
                "Text",
                "",
            )

        except Exception as exc:

            raise SAPGUIError(
                f"Unable to read text from "
                f"{control_id}."
            ) from exc

        return str(
            value
        )
    # =========================================================
    # PRESS BUTTON
    # =========================================================

    def press(
        self,
        control_id: str,
    ) -> Dict[str, Any]:
        """
        Press an SAP GUI button/control.
        """

        control = self.find_control(
            control_id
        )

        try:
            control.Press()
        except Exception as exc:
            raise SAPGUIError(
                f"Unable to press SAP control "
                f"{control_id}."
            ) from exc

        return {
            "success": True,
            "control_id": control_id,
        }

    # =========================================================
    # SELECT COMBOBOX VALUE
    # =========================================================

    def select_combo_value(
        self,
        control_id: str,
        value: str,
    ) -> Dict[str, Any]:
        """
        Select a value from an SAP combo box.
        """

        control = self.find_control(
            control_id
        )

        try:
            control.Key = value
        except Exception as exc:
            raise SAPGUIError(
                f"Unable to select value '{value}' "
                f"from {control_id}."
            ) from exc

        return {
            "success": True,
            "control_id": control_id,
            "value": value,
        }

    # =========================================================
    # ENTER / SEND VKEY
    # =========================================================

    def send_vkey(
        self,
        key: int = 0,
    ) -> Dict[str, Any]:
        """
        Send an SAP GUI virtual key.

        key=0 normally corresponds to Enter.
        """

        if self.session is None:
            raise SAPGUIError(
                "SAP session is not attached."
            )

        try:
            self.session.SendVKey(key)
        except Exception as exc:
            raise SAPGUIError(
                f"Unable to send SAP virtual key "
                f"{key}."
            ) from exc

        return {
            "success": True,
            "key": key,
        }

    # =========================================================
    # SAFE DETACH
    # =========================================================

    def detach(self) -> None:
        """
        Release local references to SAP objects.

        This does not close SAP.
        """

        self.session = None
        self.connection = None
        self.application = None
        self.sap_gui = None

    # =========================================================
    # INTERNAL ATTRIBUTE HELPER
    # =========================================================

    @staticmethod
    def _get_nested_attribute(
        obj,
        path: str,
    ):
        """
        Resolve an attribute path such as:

            Info.SystemName
        """

        current = obj

        for part in path.split("."):
            current = getattr(
                current,
                part,
            )

        return current

    # =========================================================
    # INTERNAL CONTROL TREE WALKER
    # =========================================================

    def _walk_controls(
        self,
        control,
        result: List[Dict[str, Any]],
    ) -> None:
        """
        Recursively walk SAP GUI controls.
        """

        try:
            children = control.Children
        except Exception:
            children = None

        try:
            control_id = getattr(
                control,
                "Id",
                None,
            )
        except Exception:
            control_id = None

        try:
            control_type = getattr(
                control,
                "Type",
                None,
            )
        except Exception:
            control_type = None

        try:
            control_text = getattr(
                control,
                "Text",
                None,
            )
        except Exception:
            control_text = None

        try:
            name = getattr(
                control,
                "Name",
                None,
            )
        except Exception:
            name = None

        try:
            tooltip = getattr(
                control,
                "Tooltip",
                None,
            )
        except Exception:
            tooltip = None

        result.append(
            {
                "id": control_id,
                "type": control_type,
                "name": name,
                "text": control_text,
                "tooltip": tooltip,
            }
        )

        if children is None:
            return

        try:
            count = children.Count
        except Exception:
            return

        for index in range(count):

            try:
                child = children.Item(index)

                self._walk_controls(
                    child,
                    result,
                )

            except Exception:
                # One inaccessible control should
                # not stop the entire inspection.
                continue


# =============================================================
# CONVENIENCE FUNCTION
# =============================================================

def connect_to_sap(
    connection_index: int = 0,
    session_index: int = 0,
) -> SAPGUIClient:
    """
    Create and attach an SAP GUI client.

    Example:

        client = connect_to_sap()

        print(
            client.session_info()
        )
    """

    client = SAPGUIClient(
        connection_index=connection_index,
        session_index=session_index,
    )

    client.attach()

    return client