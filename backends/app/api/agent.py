from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent.orchestrator import orchestrator


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/agent",
)


# =========================================================
# REQUEST MODEL
# =========================================================

class AgentRunRequest(BaseModel):
    """
    Configuration supplied by the user before starting
    an SapAi agent run.
    """

    user_id: Optional[str] = Field(
        default=None,
        description="Employee/user identifier",
    )

    tcode: Optional[str] = Field(
        default=None,
        description="SAP transaction code",
    )

    variant: Optional[str] = Field(
        default=None,
        description="SAP report variant",
    )

    plant: Optional[str] = Field(
        default=None,
        description="Plant identifier",
    )

    previous_period: Optional[str] = Field(
        default=None,
        description="Previous reporting period",
    )

    current_period: Optional[str] = Field(
        default=None,
        description="Current reporting period",
    )


# =========================================================
# ROOT
# =========================================================

@router.get("/")
async def agent_root():
    """
    Check whether the SapAi Agent API is available.
    """

    return {
        "message": "SapAi Agent API is running",
        "version": "1.0",
        "mode": "deterministic-workflow",
    }


# =========================================================
# RUN AGENT
# =========================================================

@router.post("/run")
async def run_agent(request: AgentRunRequest):
    """
    Start the SapAi inventory automation workflow.

    Flow:

        User Configuration
                ↓
            AgentState
                ↓
        Inventory Workflow
                ↓
        Process Previous Inventory
                ↓
        Process Current Inventory
                ↓
        Compare Inventory
                ↓
        Generate Report
                ↓
        Validate Report
    """

    try:

        result = orchestrator.run(
            user_id=request.user_id,
            tcode=request.tcode,
            variant=request.variant,
            plant=request.plant,
            previous_period=request.previous_period,
            current_period=request.current_period,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(exc)}",
        )


# =========================================================
# GET AGENT STATUS
# =========================================================

@router.get("/status/{run_id}")
async def get_agent_status(run_id: str):
    """
    Retrieve the current status/result of an agent run.
    """

    result = orchestrator.get_status(run_id)

    if result is None:

        raise HTTPException(
            status_code=404,
            detail=f"Agent run '{run_id}' was not found.",
        )

    return result


# =========================================================
# DOWNLOAD GENERATED REPORT
# =========================================================

@router.get("/report/download")
async def download_report():
    """
    Download the latest generated BSP inventory report.
    """

    project_root = Path(__file__).resolve().parents[3]

    report_file = (
        project_root
        / "data"
        / "reports"
        / "BSP_Inventory_Report.xlsx"
    )

    if not report_file.exists():

        raise HTTPException(
            status_code=404,
            detail="Inventory report has not been generated yet.",
        )

    return FileResponse(
        path=str(report_file),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        filename="BSP_Inventory_Report.xlsx",
    )