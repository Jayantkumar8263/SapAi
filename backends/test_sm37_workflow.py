from app.agent.state import AgentState
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.sm37_workflow import (
    SM37Workflow,
)


def create_state():

    return AgentState(
        user_id="sm37_test",
        plant="Bhilai",
    )


def create_workflow():

    state = create_state()

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = SM37Workflow(
        state,
        controller,
    )

    return (
        workflow,
        client,
    )


def test_sm37_open_and_search():

    workflow, client = (
        create_workflow()
    )

    try:

        result = (
            workflow.open_sm37()
        )

        assert (
            result["success"]
            is True
        )

        search = (
            workflow.search_job(
                "ZMAT_FUND_001"
            )
        )

        assert (
            search["success"]
            is True
        )

        assert (
            "transaction:SM37"
            in client.history
        )

        assert (
            "set_text:txt_JOB_NAME="
            "ZMAT_FUND_001"
            in client.history
        )

        assert (
            "press:btn_EXECUTE"
            in client.history
        )

    finally:

        client.detach()


def test_sm37_read_finished_job():

    workflow, client = (
        create_workflow()
    )

    try:

        workflow.open_sm37()

        client.controls[
            "txt_JOB_STATUS"
        ] = "FINISHED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "12345678"

        status = (
            workflow.read_job_status()
        )

        assert (
            status
            == "FINISHED"
        )

        job_number = (
            workflow.read_job_number()
        )

        assert (
            job_number
            == "12345678"
        )

    finally:

        client.detach()


def test_sm37_monitor_finished_job():

    workflow, client = (
        create_workflow()
    )

    try:

        workflow.open_sm37()

        client.controls[
            "txt_JOB_STATUS"
        ] = "FINISHED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "12345678"

        result = (
            workflow.wait_until_finished(
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert (
            result["success"]
            is True
        )

        assert (
            result["status"]
            == "FINISHED"
        )

        assert (
            result["job_number"]
            == "12345678"
        )

    finally:

        client.detach()


def test_sm37_monitor_cancelled_job():

    workflow, client = (
        create_workflow()
    )

    try:

        workflow.open_sm37()

        client.controls[
            "txt_JOB_STATUS"
        ] = "CANCELLED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "12345678"

        result = (
            workflow.wait_until_finished(
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert (
            result["success"]
            is False
        )

        assert (
            result["status"]
            == "CANCELLED"
        )

        assert (
            "failed"
            in result["message"].lower()
        )

    finally:

        client.detach()


def test_sm37_monitor_timeout():

    workflow, client = (
        create_workflow()
    )

    try:

        workflow.open_sm37()

        client.controls[
            "txt_JOB_STATUS"
        ] = "RUNNING"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "12345678"

        result = (
            workflow.wait_until_finished(
                timeout_seconds=0.05,
                poll_interval_seconds=0.01,
            )
        )

        assert (
            result["success"]
            is False
        )

        assert (
            "timed out"
            in result["message"].lower()
        )

    finally:

        client.detach()


def test_sm37_monitor_full_flow():

    workflow, client = (
        create_workflow()
    )

    try:

        client.controls[
            "txt_JOB_STATUS"
        ] = "FINISHED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "87654321"

        result = (
            workflow.monitor_job(
                "ZMAT_FUND_002",
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert (
            result["success"]
            is True
        )

        assert (
            result["job_name"]
            == "ZMAT_FUND_002"
        )

        assert (
            result["monitoring"]["status"]
            == "FINISHED"
        )

        assert (
            result["monitoring"]["job_number"]
            == "87654321"
        )

        assert (
            client.connected
            is False
        )

    finally:

        client.detach()