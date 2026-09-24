from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class SAPClientInterface(ABC):
    """
    Common interface for SAP automation clients.

    Implementations:
        - SAPGUIClient -> real SAP GUI
        - MockSAPClient -> local development/testing
    """

    @abstractmethod
    def attach(self) -> Dict[str, Any]:
        """Attach/connect to SAP."""
        raise NotImplementedError

    @abstractmethod
    def session_info(self) -> Dict[str, Any]:
        """Return safe SAP session information."""
        raise NotImplementedError

    @abstractmethod
    def start_transaction(self, tcode: str) -> Dict[str, Any]:
        """Start an SAP transaction."""
        raise NotImplementedError

    @abstractmethod
    def get_current_screen_info(self) -> Dict[str, Any]:
        """Return information about the current screen."""
        raise NotImplementedError

    @abstractmethod
    def inspect_screen(self) -> list[Dict[str, Any]]:
        """Inspect controls on the current SAP screen."""
        raise NotImplementedError
    
    @abstractmethod
    def read_text(
        self,
        control_id: str,
    ) -> str:
        """Read text/value from an SAP control."""
        raise NotImplementedError

    @abstractmethod
    def set_text(self, control_id: str, value: str) -> Dict[str, Any]:
        """Set text into an SAP control."""
        raise NotImplementedError

    @abstractmethod
    def press(self, control_id: str) -> Dict[str, Any]:
        """Press an SAP control."""
        raise NotImplementedError

    @abstractmethod
    def select_combo_value(
        self,
        control_id: str,
        value: str,
    ) -> Dict[str, Any]:
        """Select a value from an SAP combo box."""
        raise NotImplementedError

    @abstractmethod
    def send_vkey(self, key: int) -> Dict[str, Any]:
        """Send an SAP virtual key."""
        raise NotImplementedError

    @abstractmethod
    def detach(self) -> None:
        """Detach from SAP."""
        raise NotImplementedError