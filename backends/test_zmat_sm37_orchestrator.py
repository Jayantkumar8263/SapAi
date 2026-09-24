from app.agent.state import AgentState
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.zmat_sm37_orchestrator import (
    ZMATSM37Orchestrator,
)


def create_state():
    return AgentState(
        user_id="zmat_sm37_test",
        plant="Bhilai",
    )


def create_orchestrator():
    state = create_state()

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    orchestrator = ZMATSM37Orchestrator(
        state=state,
        controller=controller,
    )

    return (
        orchestrator,
        client,
    )


# ============================================================
# ZMAT → SM37 SUCCESS
# ============================================================


def test_zmat_sm37_success():

    orchestrator, client = (
        create_orchestrator()
    )

    # Mock SM37 result.
    client.controls[
        "txt_JOB_STATUS"
    ] = "FINISHED"

    client.controls[
        "txt_JOB_NUMBER"
    ] = "12345678"

    try:

        result = (
            orchestrator.run_batch(
                batch_number=1,
                material_codes=[
                    "15111201000046",
                    "15111301000109",
                ],
                job_name="ZMAT_PO_PR",
                submit_background=True,
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert result["success"] is True

        # ----------------------------------------------------
        # ZMAT
        # ----------------------------------------------------

        assert (
            result["zmat"]["success"]
            is True
        )

        assert (
            result["zmat"][
                "background_submitted"
            ]
            is True
        )

        # ----------------------------------------------------
        # SM37
        # ----------------------------------------------------

        assert (
            result["sm37"]["success"]
            is True
        )

        assert (
            result["sm37"]["job_name"]
            == "ZMAT_PO_PR"
        )

        assert (
            result["sm37"][
                "monitoring"
            ]["status"]
            == "FINISHED"
        )

        assert (
            result["sm37"][
                "monitoring"
            ]["job_number"]
            == "12345678"
        )

        # ----------------------------------------------------
        # SAP HISTORY
        # ----------------------------------------------------

        assert (
            "transaction:ZMAT-FUND_POPR"
            in client.history
        )

        assert (
            "press:btn_BACKGROUND"
            in client.history
        )

        assert (
            "transaction:SM37"
            in client.history
        )

        assert (
            "set_text:txt_JOB_NAME=ZMAT_PO_PR"
            in client.history
        )

        # ----------------------------------------------------
        # DISCONNECTED
        # ----------------------------------------------------

        assert (
            client.connected
            is False
        )

    finally:

        client.detach()


# ============================================================
# BACKGROUND SUBMISSION REQUIRED
# ============================================================


def test_zmat_sm37_requires_background_submission():

    orchestrator, client = (
        create_orchestrator()
    )

    try:

        result = (
            orchestrator.run_batch(
                batch_number=1,
                material_codes=[
                    "15111201000046",
                ],
                job_name="ZMAT_PO_PR",
                submit_background=False,
            )
        )

        assert (
            result["success"]
            is False
        )

        assert (
            "background job was not submitted"
            in result["error"]
        )

        # SM37 must NOT start.
        assert (
            "transaction:SM37"
            not in client.history
        )

    finally:

        client.detach()


# ============================================================
# CANCELLED JOB
# ============================================================


def test_zmat_sm37_cancelled_job_stops_workflow():

    orchestrator, client = (
        create_orchestrator()
    )

    client.controls[
        "txt_JOB_STATUS"
    ] = "CANCELLED"

    client.controls[
        "txt_JOB_NUMBER"
    ] = "12345678"

    try:

        result = (
            orchestrator.run_batch(
                batch_number=1,
                material_codes=[
                    "15111201000046",
                ],
                job_name="ZMAT_PO_PR",
                submit_background=True,
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert (
            result["success"]
            is False
        )

        assert (
            result["sm37"]["success"]
            is False
        )

        assert (
            result["sm37"][
                "monitoring"
            ]["status"]
            == "CANCELLED"
        )

    finally:

        client.detach()


# ============================================================
# MULTIPLE BATCHES
# ============================================================


def test_zmat_sm37_multiple_batches():

    orchestrator, client = (
        create_orchestrator()
    )

    client.controls[
        "txt_JOB_STATUS"
    ] = "FINISHED"

    client.controls[
        "txt_JOB_NUMBER"
    ] = "12345678"

    batches = [
        [
            "15111201000046",
            "15111301000109",
        ],
        [
            "15111401000020",
            "15111401000026",
        ],
    ]

    try:

        result = (
            orchestrator.run_batches(
                batches=batches,
                job_name="ZMAT_PO_PR",
                submit_background=True,
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert (
            result["success"]
            is True
        )

        assert (
            result["batch_count"]
            == 2
        )

        assert (
            result["completed_batches"]
            == 2
        )

        assert (
            len(result["batches"])
            == 2
        )

        assert all(
            batch["success"]
            for batch in result["batches"]
        )

    finally:

        client.detach()


# ============================================================
# EMPTY BATCH LIST
# ============================================================


def test_zmat_sm37_empty_batches():

    orchestrator, client = (
        create_orchestrator()
    )

    result = (
        orchestrator.run_batches(
            batches=[],
        )
    )

    assert (
        result["success"]
        is True
    )

    assert (
        result["batch_count"]
        == 0
    )

    assert (
        result["completed_batches"]
        == 0
    )