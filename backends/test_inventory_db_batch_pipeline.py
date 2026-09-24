from pathlib import Path

import pandas as pd
import pytest

from app.services.inventory_database import (
    InventoryDatabase,
    create_sqlite_connection,
)

from app.services.inventory_db_batch_pipeline import (
    InventoryDatabaseBatchPipeline,
)


ROOT = Path(
    __file__
).resolve().parent


def create_test_pipeline():

    connection = (
        create_sqlite_connection()
    )

    database = InventoryDatabase(
        connection
    )

    pipeline = (
        InventoryDatabaseBatchPipeline(
            database
        )
    )

    return (
        connection,
        database,
        pipeline,
    )


def test_database_material_codes():

    (
        connection,
        database,
        pipeline,
    ) = create_test_pipeline()

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "100",
                    "200",
                    "100",
                    "300",
                    "200",
                    "",
                    None,
                ],
                "Quantity": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                ],
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        codes = (
            pipeline.get_material_codes()
        )

        assert codes == [
            "100",
            "200",
            "300",
        ]

    finally:

        connection.close()


def test_database_to_batches():

    (
        connection,
        database,
        pipeline,
    ) = create_test_pipeline()

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    str(index)
                    for index in range(
                        1,
                        46_001,
                    )
                ]
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        result = (
            pipeline.create_batches(
                batch_size=20_000,
            )
        )

        assert (
            result["total_input_rows"]
            == 46_000
        )

        assert (
            result[
                "unique_material_codes"
            ]
            == 46_000
        )

        assert (
            result["batch_count"]
            == 3
        )

        assert (
            len(
                result["batches"][0]
            )
            == 20_000
        )

        assert (
            len(
                result["batches"][1]
            )
            == 20_000
        )

        assert (
            len(
                result["batches"][2]
            )
            == 6_000
        )

    finally:

        connection.close()


def test_database_to_batches_preserves_order():

    (
        connection,
        database,
        pipeline,
    ) = create_test_pipeline()

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "500",
                    "100",
                    "300",
                    "500",
                    "200",
                    "100",
                ]
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        result = (
            pipeline.create_batches(
                batch_size=2,
            )
        )

        assert (
            result["batches"]
            == [
                [
                    "500",
                    "100",
                ],
                [
                    "300",
                    "200",
                ],
            ]
        )

    finally:

        connection.close()


def test_database_to_batch_files():

    (
        connection,
        database,
        pipeline,
    ) = create_test_pipeline()

    output_directory = (
        ROOT
        / "_test_db_batches"
    )

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "100",
                    "200",
                    "300",
                    "400",
                    "500",
                ]
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        result = (
            pipeline.create_batch_files(
                output_directory,
                batch_size=2,
            )
        )

        assert (
            result["batch_count"]
            == 3
        )

        assert (
            len(
                result["batch_files"]
            )
            == 3
        )

        first_file = Path(
            result[
                "batch_files"
            ][0]
        )

        second_file = Path(
            result[
                "batch_files"
            ][1]
        )

        third_file = Path(
            result[
                "batch_files"
            ][2]
        )

        assert first_file.exists()
        assert second_file.exists()
        assert third_file.exists()

        assert (
            first_file.read_text(
                encoding="utf-8"
            )
            == "100\n200"
        )

        assert (
            second_file.read_text(
                encoding="utf-8"
            )
            == "300\n400"
        )

        assert (
            third_file.read_text(
                encoding="utf-8"
            )
            == "500"
        )

    finally:

        if output_directory.exists():

            for file in (
                output_directory.glob(
                    "*.txt"
                )
            ):
                file.unlink(
                    missing_ok=True
                )

            output_directory.rmdir()

        connection.close()


def test_missing_material_code_column():

    (
        connection,
        database,
        pipeline,
    ) = create_test_pipeline()

    try:

        dataframe = pd.DataFrame(
            {
                "Wrong Column": [
                    "100",
                    "200",
                ]
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        with pytest.raises(
            ValueError
        ):

            pipeline.create_batches()

    finally:

        connection.close()


def test_empty_database():

    (
        connection,
        database,
        pipeline,
    ) = create_test_pipeline()

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
            pipeline.create_batches()
        )

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

    finally:

        connection.close()