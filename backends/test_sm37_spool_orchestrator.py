from pathlib import Path

from app.agent.state import AgentState

from app.services.mock_sap import (
    MockSAPClient,
)

from app.services.sap_controller import (
    SAPController,
)

from app.services.sm37_spool_orchestrator import (
    SM37SpoolOrchestrator,
)


ROOT = Path(
    __file__
).resolve().parent


def create_test_orchestrator():

    state = AgentState(
        user_id="sm37_spool_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    orchestrator = (
        SM37SpoolOrchestrator(
            state,
            controller,
        )
    )

    return (
        client,
        orchestrator,
    )


def test_finished_job_extracts_spool():

    (
        client,
        orchestrator,
    ) = create_test_orchestrator()

    output_file = (
        ROOT
        / "_test_sm37_spool_output.txt"
    )

    try:

        # Simulate completed SAP background job.

        client.controls[
            "txt_JOB_STATUS"
        ] = "FINISHED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "12345678"

        # Simulate spool content.

        client.controls[
            "txt_SPOOL"
        ] = (
            "Material\tQuantity\tDate\n"
            "15111201000046\t10\t20260924\n"
        )

        result = (
            orchestrator.run(
                output_file=output_file,
                job_name="ZMAT_PO_PR",
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert result[
            "success"
        ] is True

        assert result[
            "monitoring"
        ]["success"] is True

        assert result[
            "monitoring"
        ]["monitoring"]["status"] == "FINISHED"

        assert result[
            "spool"
        ]["success"] is True

        assert output_file.exists()

        content = output_file.read_text(
            encoding="utf-8"
        )

        assert (
            "15111201000046"
            in content
        )

        assert (
            "20260924"
            in content
        )

    finally:

        output_file.unlink(
            missing_ok=True
        )


def test_cancelled_job_does_not_extract_spool():

    (
        client,
        orchestrator,
    ) = create_test_orchestrator()

    output_file = (
        ROOT
        / "_test_cancelled_spool.txt"
    )

    try:

        client.controls[
            "txt_JOB_STATUS"
        ] = "CANCELLED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "12345678"

        result = (
            orchestrator.run(
                output_file=output_file,
                job_name="ZMAT_PO_PR",
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert result[
            "success"
        ] is False

        assert result[
            "spool"
        ] is None

        assert not output_file.exists()

    finally:

        output_file.unlink(
            missing_ok=True
        )


def test_finished_job_with_spool_failure():

    (
        client,
        orchestrator,
    ) = create_test_orchestrator()

    output_file = (
        ROOT
        / "_test_spool_failure.txt"
    )

    try:

        client.controls[
            "txt_JOB_STATUS"
        ] = "FINISHED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "12345678"

        def failing_extract(
            output_file
        ):

            return {
                "success": False,
                "error": (
                    "Simulated spool failure."
                ),
            }

        orchestrator.spool_workflow.extract = (
            failing_extract
        )

        result = (
            orchestrator.run(
                output_file=output_file,
                job_name="ZMAT_PO_PR",
                timeout_seconds=1,
                poll_interval_seconds=0.01,
            )
        )

        assert result[
            "success"
        ] is False

        assert result[
            "spool"
        ]["success"] is False

        assert (
            result["error"]
            == "Simulated spool failure."
        )

    finally:

        output_file.unlink(
            missing_ok=True
        )