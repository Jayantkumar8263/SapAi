from pathlib import Path

import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
    create_sqlite_connection,
)

from app.services.inventory_db_batch_pipeline import (
    InventoryDatabaseBatchPipeline,
)

from app.services.inventory_zmat_orchestrator import (
    InventoryZMATOrchestrator,
)

from app.services.mock_sap import (
    MockSAPClient,
)

from app.services.sap_controller import (
    SAPController,
)

from app.services.zmat_fund_popr_workflow import (
    ZMATFundPOPRWorkflow,
)

from app.agent.state import AgentState


ROOT = Path(
    __file__
).resolve().parent


def create_test_orchestrator():

    connection = (
        create_sqlite_connection()
    )

    database = InventoryDatabase(
        connection
    )

    batch_pipeline = (
        InventoryDatabaseBatchPipeline(
            database
        )
    )

    state = AgentState(
        user_id="inventory_zmat_test",
        plant="Bhilai",
    )

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    zmat_workflow = (
        ZMATFundPOPRWorkflow(
            state,
            controller,
        )
    )

    orchestrator = (
        InventoryZMATOrchestrator(
            batch_pipeline,
            zmat_workflow,
        )
    )

    return (
        connection,
        database,
        client,
        orchestrator,
    )


def test_database_batches_are_sent_to_zmat():

    (
        connection,
        database,
        client,
        orchestrator,
    ) = create_test_orchestrator()

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "15111201000046",
                    "15111301000109",
                    "15111401000020",
                    "15111201000046",
                    "15111401000026",
                ]
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        result = (
            orchestrator.run(
                batch_size=2,
                submit_background=False,
            )
        )

        assert result["success"] is True

        assert (
            result[
                "unique_material_codes"
            ]
            == 4
        )

        assert (
            result["batch_count"]
            == 2
        )

        assert (
            len(
                result["batches"]
            )
            == 2
        )

        assert (
            result[
                "batches"
            ][0][
                "material_codes"
            ]
            == [
                "15111201000046",
                "15111301000109",
            ]
        )

        assert (
            result[
                "batches"
            ][1][
                "material_codes"
            ]
            == [
                "15111401000020",
                "15111401000026",
            ]
        )

        operations = client.history

        assert (
            "transaction:ZMAT-FUND_POPR"
            in operations
        )

        assert any(
            operation.startswith(
                "set_text:"
            )
            for operation in operations
        )

        assert (
            "press:btn_EXECUTE"
            in operations
        )

    finally:

        connection.close()


def test_empty_database_does_not_call_zmat():

    (
        connection,
        database,
        client,
        orchestrator,
    ) = create_test_orchestrator()

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [],
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        result = (
            orchestrator.run()
        )

        assert result["success"] is True

        assert (
            result[
                "unique_material_codes"
            ]
            == 0
        )

        assert (
            result["batch_count"]
            == 0
        )

        assert (
            result["batches"]
            == []
        )

        assert (
            "transaction:ZMAT-FUND_POPR"
            not in client.history
        )

    finally:

        connection.close()


def test_zmat_failure_stops_following_batches():

    (
        connection,
        database,
        client,
        orchestrator,
    ) = create_test_orchestrator()

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "100",
                    "200",
                    "300",
                    "400",
                ]
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        original_run = (
            orchestrator.zmat_workflow.run
        )

        call_count = {
            "value": 0
        }

        def failing_run(
            batch_number,
            material_codes,
            submit_background=False,
        ):

            call_count[
                "value"
            ] += 1

            if batch_number == 2:

                return {
                    "success": False,
                    "batch_number": 2,
                    "error": (
                        "Simulated SAP failure"
                    ),
                }

            return original_run(
                batch_number=batch_number,
                material_codes=material_codes,
                submit_background=(
                    submit_background
                ),
            )

        orchestrator.zmat_workflow.run = (
            failing_run
        )

        result = (
            orchestrator.run(
                batch_size=2,
            )
        )

        assert result["success"] is False

        assert (
            result[
                "failed_batch"
            ]
            == 2
        )

        assert (
            result["error"]
            == "Simulated SAP failure"
        )

        assert (
            call_count["value"]
            == 2
        )

    finally:

        connection.close()


def test_background_flag_is_forwarded():

    (
        connection,
        database,
        client,
        orchestrator,
    ) = create_test_orchestrator()

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "100",
                    "200",
                ]
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        result = (
            orchestrator.run(
                batch_size=20_000,
                submit_background=True,
            )
        )

        assert result["success"] is True

        assert (
            result[
                "batches"
            ][0][
                "submit_background"
            ]
            is True
        )

        assert (
            result[
                "batches"
            ][0][
                "background_submitted"
            ]
            is True
        )

        assert (
            "press:btn_BACKGROUND"
            in client.history
        )

    finally:

        connection.close()