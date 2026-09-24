"""
SAP Automation API
==================

FastAPI endpoints for interacting with an existing
SAP GUI session.

Current stage:
    - Attach to SAP GUI
    - Inspect SAP session
    - Start transactions
    - Inspect current screen

Future stages:
    - Select MC.1
    - Select B002159
    - Select periods
    - Plant Analysis
    - Key Figures
    - Valuated Stock
    - Valuated Stock Value
    - Export Excel
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from app.core.security import verify_api_key
from pydantic import BaseModel

from app.services.sap_gui import (
    SAPGUIClient,
    SAPGUIError,
)
from app.core.security import verify_api_key
from fastapi import Depends

router = APIRouter(
    prefix="/sap",
    tags=["SAP"],
    dependencies=[Depends(verify_api_key)],
)


# ============================================================
# REQUEST MODELS
# ============================================================


class SAPSessionRequest(BaseModel):
    connection_index: int = 0
    session_index: int = 0


class SAPTransactionRequest(BaseModel):
    connection_index: int = 0
    session_index: int = 0
    tcode: str = "MC.1"


class SAPControlTextRequest(BaseModel):
    connection_index: int = 0
    session_index: int = 0
    control_id: str
    value: str


class SAPControlRequest(BaseModel):
    connection_index: int = 0
    session_index: int = 0
    control_id: str


class SAPComboRequest(BaseModel):
    connection_index: int = 0
    session_index: int = 0
    control_id: str
    value: str


class SAPVKeyRequest(BaseModel):
    connection_index: int = 0
    session_index: int = 0
    key: int = 0


# ============================================================
# CREATE CLIENT
# ============================================================


def create_sap_client(
    connection_index: int,
    session_index: int,
) -> SAPGUIClient:

    client = SAPGUIClient(
        connection_index=connection_index,
        session_index=session_index,
    )

    client.attach()

    return client


# ============================================================
# ATTACH
# ============================================================


@router.post("/attach")
async def attach_to_sap(
    request: SAPSessionRequest,
):
    """
    Attach SapAi to an already-running SAP GUI session.
    """

    client: Optional[SAPGUIClient] = None

    try:

        client = create_sap_client(
            request.connection_index,
            request.session_index,
        )

        return {
            "status": "success",
            "message": (
                "Successfully attached to SAP GUI."
            ),
            "session": client.session_info(),
        }

    except SAPGUIError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unexpected SAP connection error: "
                f"{exc}"
            ),
        )

    finally:

        if client:
            client.detach()


# ============================================================
# START TRANSACTION
# ============================================================


@router.post("/transaction")
async def start_sap_transaction(
    request: SAPTransactionRequest,
):
    """
    Start an SAP transaction.

    Default:

        MC.1
    """

    client: Optional[SAPGUIClient] = None

    try:

        client = create_sap_client(
            request.connection_index,
            request.session_index,
        )

        result = client.start_transaction(
            request.tcode
        )

        return {
            "status": "success",
            "message": (
                f"SAP transaction "
                f"{request.tcode} started."
            ),
            "result": result,
        }

    except SAPGUIError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unexpected SAP transaction error: "
                f"{exc}"
            ),
        )

    finally:

        if client:
            client.detach()


# ============================================================
# INSPECT SCREEN
# ============================================================


@router.post("/inspect-screen")
async def inspect_sap_screen(
    request: SAPSessionRequest,
):
    """
    Inspect the controls on the current SAP screen.

    This endpoint is used during development to discover
    SAP GUI control IDs.
    """

    client: Optional[SAPGUIClient] = None

    try:

        client = create_sap_client(
            request.connection_index,
            request.session_index,
        )

        screen = (
            client.get_current_screen_info()
        )

        controls = (
            client.inspect_screen()
        )

        return {
            "status": "success",
            "screen": screen,
            "control_count": len(
                controls
            ),
            "controls": controls,
        }

    except SAPGUIError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to inspect SAP screen: "
                f"{exc}"
            ),
        )

    finally:

        if client:
            client.detach()


# ============================================================
# SET TEXT
# ============================================================


@router.post("/set-text")
async def set_sap_text(
    request: SAPControlTextRequest,
):
    """
    Set the text of an SAP GUI input control.
    """

    client: Optional[SAPGUIClient] = None

    try:

        client = create_sap_client(
            request.connection_index,
            request.session_index,
        )

        result = client.set_text(
            request.control_id,
            request.value,
        )

        return {
            "status": "success",
            "message": (
                "SAP control value updated."
            ),
            "result": result,
        }

    except SAPGUIError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to set SAP control value: "
                f"{exc}"
            ),
        )

    finally:

        if client:
            client.detach()


# ============================================================
# PRESS CONTROL
# ============================================================


@router.post("/press")
async def press_sap_control(
    request: SAPControlRequest,
):
    """
    Press an SAP GUI button/control.
    """

    client: Optional[SAPGUIClient] = None

    try:

        client = create_sap_client(
            request.connection_index,
            request.session_index,
        )

        result = client.press(
            request.control_id
        )

        return {
            "status": "success",
            "message": (
                "SAP control pressed."
            ),
            "result": result,
        }

    except SAPGUIError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to press SAP control: "
                f"{exc}"
            ),
        )

    finally:

        if client:
            client.detach()


# ============================================================
# SELECT COMBOBOX VALUE
# ============================================================


@router.post("/select-combo")
async def select_sap_combo(
    request: SAPComboRequest,
):
    """
    Select a value from an SAP combo box.
    """

    client: Optional[SAPGUIClient] = None

    try:

        client = create_sap_client(
            request.connection_index,
            request.session_index,
        )

        result = client.select_combo_value(
            request.control_id,
            request.value,
        )

        return {
            "status": "success",
            "message": (
                "SAP combo-box value selected."
            ),
            "result": result,
        }

    except SAPGUIError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to select SAP combo value: "
                f"{exc}"
            ),
        )

    finally:

        if client:
            client.detach()


# ============================================================
# SEND VKEY
# ============================================================


@router.post("/vkey")
async def send_sap_vkey(
    request: SAPVKeyRequest,
):
    """
    Send an SAP GUI virtual key.

    Default key:

        0 = Enter
    """

    client: Optional[SAPGUIClient] = None

    try:

        client = create_sap_client(
            request.connection_index,
            request.session_index,
        )

        result = client.send_vkey(
            request.key
        )

        return {
            "status": "success",
            "message": (
                "SAP virtual key sent."
            ),
            "result": result,
        }

    except SAPGUIError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to send SAP virtual key: "
                f"{exc}"
            ),
        )

    finally:

        if client:
            client.detach()