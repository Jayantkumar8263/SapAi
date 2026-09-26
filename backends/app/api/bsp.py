from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.agent.state import AgentState
from app.services.bsp_application_service import BSPApplicationService


router = APIRouter(prefix="/bsp")

# Stores active runs while the backend process is running.
_RUNS: dict[str, AgentState] = {}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


async def _save_upload(upload: UploadFile, destination: Path) -> Path:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(
            status_code=400,
            detail=f"Only Excel files are supported: {filename}",
        )

    content = await upload.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file is empty: {filename}",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    return destination


def _run_background(
    state: AgentState,
    previous_path: Path,
    current_path: Path,
    reference_path: Path,
    mode: str,
):
    try:
        service = BSPApplicationService(state)

        if mode == "offline":
            service.run_offline(
                previous_file=previous_path,
                current_file=current_path,
                reference_file=reference_path,
            )
        else:
            raise RuntimeError(
                "Live SAP mode is not enabled yet. "
                "Use offline mode while testing the application pipeline."
            )

    except Exception as exc:
        state.errors.append(str(exc))
        state.finish("failed")


@router.post("/run")
async def run_bsp_automation(
    background_tasks: BackgroundTasks,
    previous_file: UploadFile = File(...),
    current_file: UploadFile = File(...),
    mode: str = Form("offline"),
):
    """
    Upload Previous + Current raw inventory Excel files
    and start the BSP automation pipeline.
    """

    mode = mode.strip().lower()

    if mode not in {"offline", "live"}:
        raise HTTPException(
            status_code=400,
            detail="mode must be 'offline' or 'live'.",
        )

    run_id = str(uuid.uuid4())

    state = AgentState(
        run_id=run_id,
        user_id="web-user",
        plant="1000",
    )

    _RUNS[run_id] = state

    run_input_dir = (
        Path(state.data_directory)
        / "runs"
        / run_id
        / "input"
    )

    previous_path = await _save_upload(
        previous_file,
        run_input_dir / "previous_inventory.xlsx",
    )

    current_path = await _save_upload(
        current_file,
        run_input_dir / "current_inventory.xlsx",
    )

    reference_path = (
        Path(state.data_directory)
        / "config"
        / "references.xlsx"
    )

    if not reference_path.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "references.xlsx was not found at "
                f"{reference_path}"
            ),
        )

    state.status = "queued"

    background_tasks.add_task(
        _run_background,
        state,
        previous_path,
        current_path,
        reference_path,
        mode,
    )

    return {
        "success": True,
        "run_id": run_id,
        "status": state.status,
        "mode": mode,
        "message": "BSP automation started.",
    }


@router.get("/status/{run_id}")
async def bsp_status(run_id: str):
    """
    Return the real status of a BSP automation run.
    """

    state = _RUNS.get(run_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' was not found.",
        )

    return state.to_dict()


@router.get("/files/{run_id}/{filename}")
async def download_bsp_file(
    run_id: str,
    filename: str,
):
    """
    Download generated files from a completed run.
    """

    state = _RUNS.get(run_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' was not found.",
        )

    allowed_files = {
        "BSP_Inventory.xlsx",
        "Inventory PO.xlsx",
        "Inventory_Spool.txt",
        "inventory.db",
        "run_summary.json",
        "MC1_Previous_Standardized.xlsx",
        "MC1_Current_Standardized.xlsx",
    }

    if filename not in allowed_files:
        raise HTTPException(
            status_code=400,
            detail="Requested file is not available.",
        )

    path = (
        Path(state.data_directory)
        / "runs"
        / run_id
        / filename
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Requested artifact is not ready.",
        )

    media_type = "application/octet-stream"

    if path.suffix == ".xlsx":
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    elif path.suffix == ".txt":
        media_type = "text/plain"
    elif path.suffix == ".json":
        media_type = "application/json"
    elif path.suffix == ".db":
        media_type = "application/vnd.sqlite3"

    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=filename,
    )