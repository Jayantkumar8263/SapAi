from pathlib import Path

import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
    create_sqlite_connection,
)

from app.services.inventory_po_database_pipeline import (
    InventoryPODatabasePipeline,
)


ROOT = Path(
    __file__
).resolve().parent


def create_inventory_po_file(
    path: Path,
):
    dataframe = pd.DataFrame(
        {
            "Material Code": [
                "15111201000046",
                "15111301000109",
            ],
            "Quantity": [
                10,
                20,
            ],
            "Date": [
                "20260924",
                "20260925",
            ],
        }
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:

        dataframe.to_excel(
            writer,
            sheet_name="Inventory PO",
            index=False,
        )


def test_read_inventory_po():

    input_file = (
        ROOT
        / "_test_inventory_po_database.xlsx"
    )

    try:

        create_inventory_po_file(
            input_file
        )

        dataframe = (
            InventoryPODatabasePipeline
            .read_inventory_po(
                input_file
            )
        )

        assert len(dataframe) == 2

        assert (
            "Material Code"
            in dataframe.columns
        )

    finally:

        input_file.unlink(
            missing_ok=True
        )


def test_validate_inventory_po():

    dataframe = pd.DataFrame(
        {
            "Material Code": [
                "15111201000046"
            ],
            "Quantity": [
                10
            ],
        }
    )

    result = (
        InventoryPODatabasePipeline
        .validate_inventory_po(
            dataframe
        )
    )

    assert result[
        "valid"
    ] is True

    assert result[
        "rows"
    ] == 1


def test_import_inventory_po():

    connection = (
        create_sqlite_connection()
    )

    try:

        database = InventoryDatabase(
            connection
        )

        pipeline = (
            InventoryPODatabasePipeline(
                database
            )
        )

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "15111201000046",
                    "15111301000109",
                ],
                "Quantity": [
                    10,
                    20,
                ],
            }
        )

        result = (
            pipeline.import_inventory_po(
                dataframe,
                "mminv1_new",
            )
        )

        assert result[
            "success"
        ] is True

        assert result[
            "expected_rows"
        ] == 2

        assert result[
            "imported_rows"
        ] == 2

        assert (
            database.count_rows(
                "mminv1_new"
            )
            == 2
        )

    finally:

        connection.close()


def test_run_inventory_po_to_database():

    input_file = (
        ROOT
        / "_test_inventory_po_database.xlsx"
    )

    connection = (
        create_sqlite_connection()
    )

    try:

        create_inventory_po_file(
            input_file
        )

        database = InventoryDatabase(
            connection
        )

        pipeline = (
            InventoryPODatabasePipeline(
                database
            )
        )

        result = (
            pipeline.run(
                input_file=input_file,
                table_name="mminv1_new",
            )
        )

        assert result[
            "success"
        ] is True

        assert result[
            "input_rows"
        ] == 2

        assert result[
            "database"
        ]["imported_rows"] == 2

        assert (
            database.count_rows(
                "mminv1_new"
            )
            == 2
        )

        stored = (
            database.read_table(
                "mminv1_new"
            )
        )

        assert len(stored) == 2

        assert (
            "Material Code"
            in stored.columns
        )

    finally:

        connection.close()

        input_file.unlink(
            missing_ok=True
        )


def test_invalid_inventory_po_is_rejected():

    connection = (
        create_sqlite_connection()
    )

    try:

        database = InventoryDatabase(
            connection
        )

        pipeline = (
            InventoryPODatabasePipeline(
                database
            )
        )

        dataframe = pd.DataFrame(
            {
                "Quantity": [
                    10
                ]
            }
        )

        result = (
            pipeline.import_inventory_po(
                dataframe,
                "mminv1_new",
            )
        )

        assert result[
            "success"
        ] is False

        assert (
            "Material Code"
            in result["error"]
        )

    finally:

        connection.close()