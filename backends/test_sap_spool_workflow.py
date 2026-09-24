from pathlib import Path

from app.agent.state import AgentState
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.sap_spool_workflow import (
    SAPSpoolWorkflow,
)


ROOT = Path(
    __file__
).resolve().parent


def test_open_spool():

    state = AgentState(
        user_id="spool_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = SAPSpoolWorkflow(
        state,
        controller,
    )

    try:

        controller.connect()

        result = (
            workflow.open_spool()
        )

        assert (
            result["success"]
            is True
        )

        assert (
            "press:btn_SPOOL"
            in client.history
        )

    finally:

        controller.disconnect()


def test_read_spool():

    state = AgentState(
        user_id="spool_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = SAPSpoolWorkflow(
        state,
        controller,
    )

    try:

        controller.connect()

        client.controls[
            "txt_SPOOL"
        ] = (
            "Material | Quantity | Date\n"
            "15111201000046 | 10 | 20260924\n"
        )

        text = (
            workflow.read_spool()
        )

        assert (
            "15111201000046"
            in text
        )

        assert (
            "Quantity"
            in text
        )

        assert (
            "read_text:txt_SPOOL"
            in client.history
        )

    finally:

        controller.disconnect()


def test_save_spool():

    output_file = (
        ROOT
        / "_test_spool.txt"
    )

    state = AgentState(
        user_id="spool_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = SAPSpoolWorkflow(
        state,
        controller,
    )

    try:

        result = (
            workflow.save_spool(
                "Material\tQuantity\n"
                "100\t20\n",
                output_file,
            )
        )

        assert (
            result["success"]
            is True
        )

        assert output_file.exists()

        assert (
            output_file.read_text(
                encoding="utf-8"
            )
            == (
                "Material\tQuantity\n"
                "100\t20\n"
            )
        )

    finally:

        output_file.unlink(
            missing_ok=True
        )


def test_empty_spool_fails():

    state = AgentState(
        user_id="spool_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = SAPSpoolWorkflow(
        state,
        controller,
    )

    try:

        workflow.save_spool(
            "",
            ROOT / "_empty_spool.txt",
        )

    except ValueError as exc:

        assert (
            "empty"
            in str(exc).lower()
        )

    else:

        raise AssertionError(
            "Expected ValueError."
        )


def test_complete_spool_extraction():

    output_file = (
        ROOT
        / "_test_complete_spool.txt"
    )

    state = AgentState(
        user_id="spool_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = SAPSpoolWorkflow(
        state,
        controller,
    )

    try:

        client.controls[
            "txt_SPOOL"
        ] = (
            "Material\tQuantity\tDate\n"
            "15111201000046\t10\t20260924\n"
        )

        result = (
            workflow.extract(
                output_file
            )
        )

        assert (
            result["success"]
            is True
        )

        assert output_file.exists()

        text = (
            output_file.read_text(
                encoding="utf-8"
            )
        )

        assert (
            "15111201000046"
            in text
        )

        assert (
            client.connected
            is False
        )

    finally:

        output_file.unlink(
            missing_ok=True
        )