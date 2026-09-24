from pathlib import Path

from app.agent.state import AgentState
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.zmat_fund_popr_workflow import (
    ZMATFundPOPRWorkflow,
)


ROOT = Path(
    __file__
).resolve().parent


def create_state():
    return AgentState(
        user_id="zmat_test",
        plant="Bhilai",
    )


def create_workflow(
    state=None,
):
    if state is None:
        state = create_state()

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = ZMATFundPOPRWorkflow(
        state,
        controller,
    )

    return (
        workflow,
        client,
    )


# ============================================================
# NORMAL EXECUTION
# ============================================================


def test_zmat_fund_popr_workflow():

    workflow, client = create_workflow()

    material_codes = [
        "15111201000046",
        "15111301000109",
        "15111401000020",
    ]

    result = workflow.run(
        batch_number=1,
        material_codes=material_codes,
    )

    # ---------------------------------------------------------
    # RESULT
    # ---------------------------------------------------------

    assert result["success"] is True

    assert (
        result["transaction"]
        == "ZMAT-FUND_POPR"
    )

    assert (
        result["batch_number"]
        == 1
    )

    assert (
        result["material_count"]
        == 3
    )

    assert (
        result["material_codes"]
        == material_codes
    )

    assert (
        result["background_submitted"]
        is False
    )

    # ---------------------------------------------------------
    # SAP HISTORY
    # ---------------------------------------------------------

    assert (
        "attach"
        in client.history
    )

    assert (
        "transaction:ZMAT-FUND_POPR"
        in client.history
    )

    assert (
        "set_text:txt_MATERIAL="
        "15111201000046\n"
        "15111301000109\n"
        "15111401000020"
        in client.history
    )

    assert (
        "press:btn_EXECUTE"
        in client.history
    )

    # Background must NOT be pressed.
    assert (
        "press:btn_BACKGROUND"
        not in client.history
    )

    # ---------------------------------------------------------
    # DISCONNECT
    # ---------------------------------------------------------

    assert (
        client.connected
        is False
    )


# ============================================================
# BACKGROUND SUBMISSION
# ============================================================


def test_zmat_fund_popr_background_submission():

    workflow, client = create_workflow()

    result = workflow.run(
        batch_number=2,
        material_codes=[
            "100",
            "200",
        ],
        submit_background=True,
    )

    assert result["success"] is True

    assert (
        result["background_submitted"]
        is True
    )

    assert (
        result["submit_background"]
        is True
    )

    assert (
        "press:btn_BACKGROUND"
        in client.history
    )

    assert (
        client.connected
        is False
    )


# ============================================================
# DUPLICATE / BLANK MATERIAL CODES
# ============================================================


def test_zmat_fund_popr_removes_duplicates():

    workflow, client = create_workflow()

    result = workflow.run(
        batch_number=3,
        material_codes=[
            "100",
            "100",
            "200",
            "",
            "200",
            None,
        ],
    )

    assert result["success"] is True

    assert (
        result["material_codes"]
        == [
            "100",
            "200",
        ]
    )

    assert (
        result["material_count"]
        == 2
    )

    assert (
        "set_text:txt_MATERIAL=100\n200"
        in client.history
    )

    assert (
        client.connected
        is False
    )


# ============================================================
# RUN FROM TXT FILE
# ============================================================


def test_zmat_fund_popr_from_file():

    batch_file = (
        ROOT
        / "_test_zmat_batch.txt"
    )

    try:

        batch_file.write_text(
            "15111201000046\n"
            "15111301000109\n"
            "15111401000020\n",
            encoding="utf-8",
        )

        workflow, client = create_workflow()

        result = workflow.run_from_file(
            batch_number=4,
            batch_file=batch_file,
        )

        assert (
            result["success"]
            is True
        )

        assert (
            result["batch_file"]
            == str(batch_file)
        )

        assert (
            result["material_count"]
            == 3
        )

        assert (
            result["batch_number"]
            == 4
        )

        assert (
            result["material_codes"]
            == [
                "15111201000046",
                "15111301000109",
                "15111401000020",
            ]
        )

        assert (
            client.connected
            is False
        )

    finally:

        batch_file.unlink(
            missing_ok=True
        )


# ============================================================
# EMPTY BATCH
# ============================================================


def test_empty_batch_fails():

    workflow, client = create_workflow()

    try:

        workflow.run(
            batch_number=1,
            material_codes=[],
        )

    except ValueError as exc:

        assert (
            "no material codes"
            in str(exc)
        )

    else:

        raise AssertionError(
            "Expected ValueError for empty batch."
        )

    # No SAP connection should happen because
    # validation occurs before controller.connect().
    assert client.connected is False

    assert client.history == []


# ============================================================
# INVALID BATCH NUMBER
# ============================================================


def test_invalid_batch_number_fails_before_sap():

    workflow, client = create_workflow()

    try:

        workflow.run(
            batch_number=0,
            material_codes=[
                "100",
            ],
        )

    except ValueError as exc:

        assert (
            "batch_number"
            in str(exc)
        )

    else:

        raise AssertionError(
            "Expected ValueError for invalid batch number."
        )

    # Validation happens before SAP connection.
    assert client.connected is False

    assert client.history == []


# ============================================================
# CUSTOM SAP CONTROL IDS
# ============================================================


def test_custom_zmat_control_ids():

    state = create_state()

    state.preferences[
        "zmat_fund_popr_control_ids"
    ] = {
        "material_input": "custom_material",
        "execute": "custom_execute",
        "background": "custom_background",
    }

    workflow, client = create_workflow(
        state
    )

    result = workflow.run(
        batch_number=5,
        material_codes=[
            "100",
            "200",
        ],
        submit_background=True,
    )

    assert result["success"] is True

    assert (
        result["control_ids"][
            "material_input"
        ]
        == "custom_material"
    )

    assert (
        result["control_ids"][
            "execute"
        ]
        == "custom_execute"
    )

    assert (
        result["control_ids"][
            "background"
        ]
        == "custom_background"
    )

    assert (
        "set_text:custom_material=100\n200"
        in client.history
    )

    assert (
        "press:custom_execute"
        in client.history
    )

    assert (
        "press:custom_background"
        in client.history
    )

    assert (
        client.connected
        is False
    )


# ============================================================
# EXCEL-STYLE NUMERIC MATERIAL CODE
# ============================================================


def test_excel_numeric_material_code_is_normalized():

    workflow, client = create_workflow()

    result = workflow.run(
        batch_number=6,
        material_codes=[
            "100.0",
            "200.0",
            "300",
        ],
    )

    assert result["success"] is True

    assert (
        result["material_codes"]
        == [
            "100",
            "200",
            "300",
        ]
    )

    assert (
        result["material_count"]
        == 3
    )

    assert (
        "set_text:txt_MATERIAL=100\n200\n300"
        in client.history
    )

    assert (
        client.connected
        is False
    )