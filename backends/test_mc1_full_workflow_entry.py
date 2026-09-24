from pathlib import Path

import pandas as pd

from app.agent.state import AgentState
from app.agent.workflow import InventoryWorkflow


ROOT = Path(
    __file__
).resolve().parent


def create_mc1_export(
    path: Path,
    quantity: int,
):
    """
    Create a small realistic MC.1 export.
    """

    df = pd.DataFrame(
        {
            "Material Group": [
                "151 KILNS"
            ],
            "Material": [
                "15111201000046 TENSION PULLEY"
            ],
            "Storage location": [
                "1000UP03"
            ],
            "Val. stock": [
                quantity
            ],
            "ValStckVal": [
                quantity * 150
            ],
            "Val. stock.1": [
                "EA"
            ],
        }
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Sheet1",
            index=False,
        )


def test_run_from_mc1_exports():

    previous = (
        ROOT
        / "_full_previous.xlsx"
    )

    current = (
        ROOT
        / "_full_current.xlsx"
    )

    try:

        # -----------------------------------------------------
        # CREATE TEST MC.1 EXPORTS
        # -----------------------------------------------------

        create_mc1_export(
            previous,
            10,
        )

        create_mc1_export(
            current,
            20,
        )

        # -----------------------------------------------------
        # CREATE STATE
        # -----------------------------------------------------

        state = AgentState(
            previous_period="2026-08",
            current_period="2026-09",
            plant="Bhilai",
        )

        workflow = InventoryWorkflow(
            state
        )

        # -----------------------------------------------------
        # RUN HIGH-LEVEL ENTRY POINT
        # -----------------------------------------------------

        result = (
            workflow.run_from_mc1_exports(
                previous_export=previous,
                current_export=current,
            )
        )

        # -----------------------------------------------------
        # VERIFY WORKFLOW COMPLETED
        # -----------------------------------------------------

        assert result is not None

        assert (
            state.status
            == "completed"
        )

        # -----------------------------------------------------
        # VERIFY MC.1 HANDOFF
        # -----------------------------------------------------

        assert (
            "mc1_export_handoff"
            in state.results
        )

        # -----------------------------------------------------
        # VERIFY INVENTORY PROCESSING
        # -----------------------------------------------------

        assert (
            "previous_inventory"
            in state.results
        )

        assert (
            "current_inventory"
            in state.results
        )

        # -----------------------------------------------------
        # VERIFY COMPARISON
        # -----------------------------------------------------

        assert (
            "comparison"
            in state.results
        )

        # -----------------------------------------------------
        # VERIFY ANALYSIS
        # -----------------------------------------------------

        assert (
            "analysis"
            in state.results
        )

        # -----------------------------------------------------
        # VERIFY CLASSIFICATION
        # -----------------------------------------------------

        assert (
            "classification"
            in state.results
        )

        # -----------------------------------------------------
        # VERIFY REPORT
        # -----------------------------------------------------

        assert (
            "report"
            in state.results
        )

        # -----------------------------------------------------
        # VERIFY VALIDATION
        # -----------------------------------------------------

        assert (
            "validation"
            in state.results
        )

        # -----------------------------------------------------
        # VERIFY FINAL WORKFLOW SUMMARY
        # -----------------------------------------------------

        summary = (
            state.results.get(
                "workflow_summary",
                {},
            )
        )

        assert (
            summary.get(
                "previous_inventory_processed"
            )
            is True
        )

        assert (
            summary.get(
                "current_inventory_processed"
            )
            is True
        )

        assert (
            summary.get(
                "comparison_completed"
            )
            is True
        )

        assert (
            summary.get(
                "analysis_completed"
            )
            is True
        )

        assert (
            summary.get(
                "classification_completed"
            )
            is True
        )

        assert (
            summary.get(
                "report_validated"
            )
            is True
        )

    finally:

        previous.unlink(
            missing_ok=True
        )

        current.unlink(
            missing_ok=True
        )

        # -----------------------------------------------------
        # CLEAN GENERATED MC.1 FILES
        # -----------------------------------------------------

        if "state" in locals():

            processed_directory = (
                Path(
                    state.data_directory
                )
                / "mc1_processed"
            )

            for filename in [
                "mc1_previous_standardized.xlsx",
                "mc1_current_standardized.xlsx",
            ]:

                (
                    processed_directory
                    / filename
                ).unlink(
                    missing_ok=True
                )

            try:

                processed_directory.rmdir()

            except OSError:

                pass