from pathlib import Path

import pandas as pd

from app.agent.state import AgentState
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.zmmrirep_workflow import (
    ZMMRIREPWorkflow,
)


ROOT = Path(__file__).resolve().parent


def test_zmmrirep_sap_workflow():

    state = AgentState(
        user_id="zmmrirep_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(client)

    workflow = ZMMRIREPWorkflow(
        state,
        controller,
    )

    result = workflow.run()

    assert result["success"] is True

    assert result["transaction"] == "ZMMRIREP"

    assert (
        result["control_ids"]["execute"]
        == "btn_EXECUTE"
    )

    assert "attach" in client.history

    assert (
        "transaction:ZMMRIREP"
        in client.history
    )

    assert (
        "press:btn_EXECUTE"
        in client.history
    )

    controller.disconnect()

    assert client.connected is False


def test_load_ri_material_codes():

    output_file = (
        ROOT
        / "_test_zmmrirep_output.xlsx"
    )

    try:

        df = pd.DataFrame(
            [
                ["20112301000119"],
                ["20112301000610"],
                ["20212401000028"],
                [None],
            ]
        )

        with pd.ExcelWriter(
            output_file,
            engine="openpyxl",
        ) as writer:

            df.to_excel(
                writer,
                header=False,
                index=False,
            )

        codes = (
            ZMMRIREPWorkflow.load_ri_material_codes(
                output_file
            )
        )

        assert codes == {
            "20112301000119",
            "20112301000610",
            "20212401000028",
        }

    finally:

        output_file.unlink(
            missing_ok=True
        )


def test_load_ri_material_codes_with_header():

    output_file = (
        ROOT
        / "_test_zmmrirep_header.xlsx"
    )

    try:

        df = pd.DataFrame(
            [
                ["Material Code"],
                ["20112301000119"],
                ["20112301000610"],
            ]
        )

        with pd.ExcelWriter(
            output_file,
            engine="openpyxl",
        ) as writer:

            df.to_excel(
                writer,
                header=False,
                index=False,
            )

        codes = (
            ZMMRIREPWorkflow.load_ri_material_codes(
                output_file
            )
        )

        assert "Material Code" not in codes

        assert (
            "20112301000119"
            in codes
        )

        assert (
            "20112301000610"
            in codes
        )

    finally:

        output_file.unlink(
            missing_ok=True
        )