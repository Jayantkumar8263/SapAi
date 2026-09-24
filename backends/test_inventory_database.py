import pandas as pd
import pytest

from app.services.inventory_database import (
    InventoryDatabase,
    create_sqlite_connection,
)


def create_test_database():

    connection = (
        create_sqlite_connection()
    )

    database = InventoryDatabase(
        connection
    )

    return (
        connection,
        database,
    )


def test_replace_inventory_table():

    connection, database = (
        create_test_database()
    )

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    "15111201000046",
                    "15111301000109",
                    "15111401000020",
                ],
                "Quantity": [
                    10,
                    20,
                    30,
                ],
                "Plant": [
                    "1000",
                    "1000",
                    "1000",
                ],
            }
        )

        result = (
            database.replace_table(
                dataframe,
                "mminv_new",
            )
        )

        assert (
            result["success"]
            is True
        )

        assert (
            result["table"]
            == "mminv_new"
        )

        assert (
            result["rows"]
            == 3
        )

        assert (
            database.table_exists(
                "mminv_new"
            )
            is True
        )

        assert (
            database.count_rows(
                "mminv_new"
            )
            == 3
        )

    finally:

        connection.close()


def test_replace_table_replaces_old_data():

    connection, database = (
        create_test_database()
    )

    try:

        old_data = pd.DataFrame(
            {
                "Material Code": [
                    "OLD001",
                    "OLD002",
                ],
                "Quantity": [
                    1,
                    2,
                ],
            }
        )

        database.replace_table(
            old_data,
            "mminv_new",
        )

        new_data = pd.DataFrame(
            {
                "Material Code": [
                    "NEW001",
                    "NEW002",
                    "NEW003",
                ],
                "Quantity": [
                    10,
                    20,
                    30,
                ],
            }
        )

        result = (
            database.replace_table(
                new_data,
                "mminv_new",
            )
        )

        assert (
            result["rows"]
            == 3
        )

        stored = (
            database.read_table(
                "mminv_new"
            )
        )

        assert len(stored) == 3

        assert set(
            stored["Material Code"]
        ) == {
            "NEW001",
            "NEW002",
            "NEW003",
        }

        assert (
            "OLD001"
            not in set(
                stored["Material Code"]
            )
        )

    finally:

        connection.close()


def test_get_unique_material_codes():

    connection, database = (
        create_test_database()
    )

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
            database.get_unique_material_codes(
                "mminv_new"
            )
        )

        assert codes == [
            "100",
            "200",
            "300",
        ]

    finally:

        connection.close()


def test_unique_material_codes_are_strings():

    connection, database = (
        create_test_database()
    )

    try:

        dataframe = pd.DataFrame(
            {
                "Material Code": [
                    15111201000046,
                    15111301000109,
                ],
            }
        )

        database.replace_table(
            dataframe,
            "mminv_new",
        )

        codes = (
            database.get_unique_material_codes(
                "mminv_new"
            )
        )

        assert (
            codes
            == [
                "15111201000046",
                "15111301000109",
            ]
        )

    finally:

        connection.close()


def test_invalid_table_name_fails():

    connection, database = (
        create_test_database()
    )

    try:

        with pytest.raises(
            ValueError
        ):

            database.replace_table(
                pd.DataFrame(
                    {
                        "A": [1]
                    }
                ),
                "mminv_new;DROP TABLE",
            )

    finally:

        connection.close()


def test_missing_table_fails():

    connection, database = (
        create_test_database()
    )

    try:

        with pytest.raises(
            Exception
        ):

            database.count_rows(
                "mminv_new"
            )

    finally:

        connection.close()