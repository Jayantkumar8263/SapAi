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

from app.services.spool_inventory_po_orchestrator import (
    SpoolInventoryPOOrchestrator,
)


ROOT = Path(
    __file__
).resolve().parent


def create_test_orchestrator():

    state = AgentState(
        user_id="spool_inventory_po_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    sm37_spool = (
        SM37SpoolOrchestrator(
            state,
            controller,
        )
    )

    orchestrator = (
        SpoolInventoryPOOrchestrator(
            sm37_spool
        )
    )

    return (
        client,
        orchestrator,
    )


def test_build_inventory_po_from_txt_files():

    txt_file = (
        ROOT
        / "_test_inventory_po_input.txt"
    )

    output_file = (
        ROOT
        / "_test_inventory_po_output.xlsx"
    )

    try:

        txt_file.write_text(
            "Material\tQuantity\tDate\n"
            "15111201000046\t10\t24.09.2026\n"
            "15111301000109\t20\t2026-09-25\n",
            encoding="utf-8",
        )

        (
            client,
            orchestrator,
        ) = create_test_orchestrator()

        result = (
            orchestrator.build_from_txt_files(
                input_files=[
                    txt_file
                ],
                output_file=(
                    output_file
                ),
            )
        )

        assert result[
            "success"
        ] is True

        assert output_file.exists()

        import pandas as pd

        df = pd.read_excel(
            output_file,
            sheet_name="Inventory PO",
        )

        assert len(df) == 2

        assert (
            str(
                df.loc[
                    0,
                    "Date",
                ]
            )
            == "20260924"
        )

        assert (
            str(
                df.loc[
                    1,
                    "Date",
                ]
            )
            == "20260925"
        )

    finally:

        txt_file.unlink(
            missing_ok=True
        )

        output_file.unlink(
            missing_ok=True
        )


def test_extract_and_build_inventory_po():

    (
        client,
        orchestrator,
    ) = create_test_orchestrator()

    spool_file = (
        ROOT
        / "_test_spool_inventory_po.txt"
    )

    output_file = (
        ROOT
        / "_test_spool_inventory_po.xlsx"
    )

    try:

        client.controls[
            "txt_SPOOL"
        ] = (
            "Material\tQuantity\tDate\n"
            "15111201000046\t10\t24.09.2026\n"
        )

        result = (
            orchestrator.extract_and_build(
                spool_output_file=(
                    spool_file
                ),
                inventory_po_file=(
                    output_file
                ),
            )
        )

        assert result[
            "success"
        ] is True

        assert spool_file.exists()

        assert output_file.exists()

        assert (
            result[
                "inventory_po"
            ]["success"]
            is True
        )

    finally:

        spool_file.unlink(
            missing_ok=True
        )

        output_file.unlink(
            missing_ok=True
        )


def test_run_requires_finished_job():

    (
        client,
        orchestrator,
    ) = create_test_orchestrator()

    spool_file = (
        ROOT
        / "_test_failed_spool.txt"
    )

    output_file = (
        ROOT
        / "_test_failed_inventory_po.xlsx"
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
                spool_output_file=(
                    spool_file
                ),
                inventory_po_file=(
                    output_file
                ),
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

        assert result[
            "inventory_po"
        ] is None

        assert not output_file.exists()

    finally:

        spool_file.unlink(
            missing_ok=True
        )

        output_file.unlink(
            missing_ok=True
        )


def test_complete_sm37_to_inventory_po():

    (
        client,
        orchestrator,
    ) = create_test_orchestrator()

    spool_file = (
        ROOT
        / "_test_complete_spool.txt"
    )

    output_file = (
        ROOT
        / "_test_complete_inventory_po.xlsx"
    )

    try:

        client.controls[
            "txt_JOB_STATUS"
        ] = "FINISHED"

        client.controls[
            "txt_JOB_NUMBER"
        ] = "87654321"

        client.controls[
            "txt_SPOOL"
        ] = (
            "Material\tQuantity\tDate\n"
            "15111201000046\t10\t20260924\n"
            "15111301000109\t20\t25.09.2026\n"
        )

        result = (
            orchestrator.run(
                spool_output_file=(
                    spool_file
                ),
                inventory_po_file=(
                    output_file
                ),
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

        assert result[
            "inventory_po"
        ]["success"] is True

        assert output_file.exists()

        import pandas as pd

        df = pd.read_excel(
            output_file,
            sheet_name="Inventory PO",
        )

        assert len(df) == 2

        assert (
            str(
                df.loc[
                    0,
                    "Date",
                ]
            )
            == "20260924"
        )

        assert (
            str(
                df.loc[
                    1,
                    "Date",
                ]
            )
            == "20260925"
        )

    finally:

        spool_file.unlink(
            missing_ok=True
        )

        output_file.unlink(
            missing_ok=True
        )