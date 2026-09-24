from pathlib import Path
import sqlite3

import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
)

from app.services.sap_inventory_database import (
    SAPInventoryDatabase,
)


def create_test_workbook(
    path: Path,
) -> None:

    inventory = pd.DataFrame(
        [
            {
                "Mat Grp": "151",
                "Mat Grp Desc": "Test Group",
                "Material Code": "15111201000046",
                "Matrial Code Desc": "Material A",
                "Storage Location": "UP03",
                "Storage Location Desc": "Test Location",
                "Plant": "1000",
                "Inve Prev Quantity": 10,
                "Inve Prev Value": 1000,
                "Inve Pres Quantity": 15,
                "Inve Pres Value": 1500,
                "UOM": "EA",
                "RI Ind": "Yes",
                "Capital Ind": "No",
            },
            {
                "Mat Grp": "151",
                "Mat Grp Desc": "Test Group",
                "Material Code": "15111301000109",
                "Matrial Code Desc": "Material B",
                "Storage Location": "UP04",
                "Storage Location Desc": "Test Location",
                "Plant": "1000",
                "Inve Prev Quantity": 20,
                "Inve Prev Value": 2000,
                "Inve Pres Quantity": 25,
                "Inve Pres Value": 2500,
                "UOM": "EA",
                "RI Ind": "No",
                "Capital Ind": "Yes",
            },
            {
                "Mat Grp": "151",
                "Mat Grp Desc": "Test Group",
                "Material Code": "15111201000046",
                "Matrial Code Desc": "Material A",
                "Storage Location": "UP05",
                "Storage Location Desc": "Another Location",
                "Plant": "1000",
                "Inve Prev Quantity": 5,
                "Inve Prev Value": 500,
                "Inve Pres Quantity": 7,
                "Inve Pres Value": 700,
                "UOM": "EA",
                "RI Ind": "Yes",
                "Capital Ind": "No",
            },
        ]
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:

        inventory.to_excel(
            writer,
            sheet_name="Inventory",
            index=False,
        )


def create_test_database(
    database_path: Path,
) -> InventoryDatabase:
    """
    Create the existing InventoryDatabase abstraction
    using a SQLite DB-API connection.

    SQLite is used only for testing.
    It is NOT the production SAP database.
    """

    connection = sqlite3.connect(
        database_path
    )

    return InventoryDatabase(
        connection
    )


def test_inventory_database_adapter(
    tmp_path: Path,
) -> None:

    workbook = (
        tmp_path
        / "BSP_Final_Inventory.xlsx"
    )

    create_test_workbook(
        workbook
    )

    # ---------------------------------------------------------
    # TEST DATABASE
    # ---------------------------------------------------------

    database = create_test_database(
        tmp_path
        / "test_inventory.db"
    )

    # ---------------------------------------------------------
    # SAP INVENTORY DATABASE ADAPTER
    # ---------------------------------------------------------

    adapter = SAPInventoryDatabase(
        database
    )

    # ---------------------------------------------------------
    # IMPORT INVENTORY → mminv_new
    # ---------------------------------------------------------

    result = (
        adapter.prepare_material_codes(
            workbook
        )
    )

    # ---------------------------------------------------------
    # VALIDATE IMPORT
    # ---------------------------------------------------------

    assert result["success"] is True

    assert (
        result["database"]["table"]
        == "mminv_new"
    )

    assert (
        result["database"]["rows_imported"]
        == 3
    )

    # ---------------------------------------------------------
    # VALIDATE UNIQUE MATERIAL CODES
    # ---------------------------------------------------------

    assert (
        result["material_code_count"]
        == 2
    )

    assert set(
        result["material_codes"]
    ) == {
        "15111201000046",
        "15111301000109",
    }


def test_inventory_sheet_requires_material_code(
    tmp_path: Path,
) -> None:

    workbook = (
        tmp_path
        / "invalid.xlsx"
    )

    invalid = pd.DataFrame(
        {
            "Plant": ["1000"],
            "UOM": ["EA"],
        }
    )

    with pd.ExcelWriter(
        workbook,
        engine="openpyxl",
    ) as writer:

        invalid.to_excel(
            writer,
            sheet_name="Inventory",
            index=False,
        )

    # ---------------------------------------------------------
    # TEST DATABASE
    # ---------------------------------------------------------

    database = create_test_database(
        tmp_path
        / "test_inventory.db"
    )

    # ---------------------------------------------------------
    # SAP INVENTORY DATABASE ADAPTER
    # ---------------------------------------------------------

    adapter = SAPInventoryDatabase(
        database
    )

    # ---------------------------------------------------------
    # EXPECT VALIDATION ERROR
    # ---------------------------------------------------------

    try:

        adapter.load_inventory_sheet(
            workbook
        )

    except ValueError as exc:

        assert (
            "Material Code"
            in str(exc)
        )

    else:

        raise AssertionError(
            "Expected Material Code "
            "validation error."
        )