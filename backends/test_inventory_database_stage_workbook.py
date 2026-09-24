from pathlib import Path
import sqlite3
from app.agent.state import AgentState
import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
)

from app.services.inventory_database_stage import (
    InventoryDatabaseStage,
)


def create_bsp_workbook(
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


def test_database_stage_from_bsp_workbook(
    tmp_path: Path,
) -> None:

    workbook = (
        tmp_path
        / "BSP_Final_Inventory.xlsx"
    )

    create_bsp_workbook(
        workbook
    )

    connection = sqlite3.connect(
        tmp_path
        / "inventory.db"
    )

    database = InventoryDatabase(
        connection
    )

    stage = InventoryDatabaseStage(
        database
    )

    result = (
        stage.run_from_workbook(
            workbook_file=workbook,
            batch_size=20_000,
        )
    )

    assert result["success"] is True

    assert (
        result["workbook"]
        == str(workbook)
    )

    assert (
        result["inventory_rows"]
        == 2
    )

    assert (
        result["database"]["table"]
        == "mminv_new"
    )

    assert (
        result["database"]["database_rows"]
        == 2
    )

    assert (
        result["batches"]["unique_material_codes"]
        == 2
    )

    assert (
        result["batches"]["batch_count"]
        == 1
    )


def test_database_stage_rejects_missing_workbook(
    tmp_path: Path,
) -> None:

    connection = sqlite3.connect(
        tmp_path
        / "inventory.db"
    )

    database = InventoryDatabase(
        connection
    )

    stage = InventoryDatabaseStage(
        database
    )

    missing_file = (
        tmp_path
        / "does_not_exist.xlsx"
    )

    try:

        stage.run_from_workbook(
            missing_file
        )

    except FileNotFoundError as exc:

        assert (
            "not found"
            in str(exc)
        )

    else:

        raise AssertionError(
            "Expected FileNotFoundError."
        )