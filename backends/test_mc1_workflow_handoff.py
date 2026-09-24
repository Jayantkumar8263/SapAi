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
    Create a small realistic raw MC.1 export.
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


def test_mc1_workflow_handoff():

    previous = (
        ROOT
        / "_handoff_previous.xlsx"
    )

    current = (
        ROOT
        / "_handoff_current.xlsx"
    )

    try:

        create_mc1_export(
            previous,
            10,
        )

        create_mc1_export(
            current,
            20,
        )

        state = AgentState(
            previous_period="2026-08",
            current_period="2026-09",
            plant="Bhilai",
        )

        workflow = InventoryWorkflow(
            state
        )

        result = (
            workflow.prepare_mc1_inventory_files(
                previous,
                current,
            )
        )

        # -----------------------------------------------------
        # Handoff succeeded
        # -----------------------------------------------------

        assert result["success"] is True

        # -----------------------------------------------------
        # AgentState now points to standardized files
        # -----------------------------------------------------

        assert (
            state.previous_inventory_file
            is not None
        )

        assert (
            state.current_inventory_file
            is not None
        )

        assert Path(
            state.previous_inventory_file
        ).exists()

        assert Path(
            state.current_inventory_file
        ).exists()

        # -----------------------------------------------------
        # Verify previous output
        # -----------------------------------------------------

        previous_df = pd.read_excel(
            state.previous_inventory_file
        )

        assert len(previous_df) == 1

        assert (
            str(
                int(
                    previous_df.loc[
                        0,
                        "Material_Code",
                    ]
                )
            )
            == "15111201000046"
        )

        assert (
            previous_df.loc[
                0,
                "Quantity",
            ]
            == 10
        )

        # -----------------------------------------------------
        # Verify current output
        # -----------------------------------------------------

        current_df = pd.read_excel(
            state.current_inventory_file
        )

        assert len(current_df) == 1

        assert (
            current_df.loc[
                0,
                "Quantity",
            ]
            == 20
        )

        # -----------------------------------------------------
        # Verify state result
        # -----------------------------------------------------

        assert (
            "mc1_export_handoff"
            in state.results
        )

        assert (
            "mc1_export_handoff"
            in state.metadata
        )

        # -----------------------------------------------------
        # Verify workflow step
        # -----------------------------------------------------

        assert any(
            step["step"]
            == "Prepare MC.1 Inventory Files"
            and step["status"]
            == "completed"
            for step in state.steps
        )

    finally:

        previous.unlink(
            missing_ok=True
        )

        current.unlink(
            missing_ok=True
        )

        processed_directory = (
            Path(
                state.data_directory
            )
            / "mc1_processed"
        ) if "state" in locals() else None

        if processed_directory:

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