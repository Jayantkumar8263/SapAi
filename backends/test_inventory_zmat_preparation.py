from pathlib import Path
import sqlite3

import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
)

from app.services.inventory_db_batch_pipeline import (
    InventoryDatabaseBatchPipeline,
)

from app.services.inventory_zmat_orchestrator import (
    InventoryZMATOrchestrator,
)


class DummyZMATWorkflow:
    """
    SAP execution is deliberately not used in Step 15.
    """

    pass


def create_test_database(
    path: Path,
) -> InventoryDatabase:

    connection = sqlite3.connect(
        path
    )

    database = InventoryDatabase(
        connection
    )

    inventory = pd.DataFrame(
        [
            {
                "Material Code": "15100000000001",
                "Plant": "1000",
            },
            {
                "Material Code": "15100000000002",
                "Plant": "1000",
            },
            {
                "Material Code": "15100000000003",
                "Plant": "1000",
            },
        ]
    )

    database.replace_table(
        dataframe=inventory,
        table_name="mminv_new",
    )

    return database


def test_zmat_preparation_creates_batch_files(
    tmp_path: Path,
) -> None:

    database = create_test_database(
        tmp_path / "inventory.db"
    )

    batch_pipeline = (
        InventoryDatabaseBatchPipeline(
            database
        )
    )

    orchestrator = (
        InventoryZMATOrchestrator(
            batch_pipeline=batch_pipeline,
            zmat_workflow=DummyZMATWorkflow(),
        )
    )

    output_directory = (
        tmp_path
        / "zmat_batches"
    )

    result = (
        orchestrator.prepare_batch_files(
            output_directory=output_directory,
            table_name="mminv_new",
            material_code_column="Material Code",
            batch_size=20_000,
        )
    )

    assert result["success"] is True

    assert (
        result["table"]
        == "mminv_new"
    )

    assert (
        result["unique_material_codes"]
        == 3
    )

    assert (
        result["batch_size"]
        == 20_000
    )

    assert (
        result["batch_count"]
        == 1
    )

    assert (
        result["preparation_only"]
        is True
    )

    assert (
        result["sap_execution"]
        is False
    )

    assert (
        len(result["batch_files"])
        == 1
    )

    batch_file = Path(
        result["batch_files"][0]
    )

    assert batch_file.exists()

    contents = (
        batch_file.read_text(
            encoding="utf-8"
        )
    )

    material_codes = [
        line.strip()
        for line in contents.splitlines()
        if line.strip()
    ]

    assert material_codes == [
        "15100000000001",
        "15100000000002",
        "15100000000003",
    ]


def test_zmat_preparation_does_not_execute_sap(
    tmp_path: Path,
) -> None:

    database = create_test_database(
        tmp_path / "inventory.db"
    )

    batch_pipeline = (
        InventoryDatabaseBatchPipeline(
            database
        )
    )

    orchestrator = (
        InventoryZMATOrchestrator(
            batch_pipeline=batch_pipeline,
            zmat_workflow=DummyZMATWorkflow(),
        )
    )

    result = (
        orchestrator.prepare_batch_files(
            output_directory=(
                tmp_path
                / "zmat_batches"
            ),
        )
    )

    assert result["success"] is True

    assert (
        result["sap_execution"]
        is False
    )