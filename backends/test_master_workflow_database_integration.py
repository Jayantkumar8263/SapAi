from pathlib import Path
import sqlite3

import pandas as pd

from app.agent.state import AgentState
from app.agent.workflow import InventoryWorkflow

from app.services.inventory_database import (
    InventoryDatabase,
)


def create_test_bsp_workbook(
    path: Path,
) -> None:

    inventory = pd.DataFrame(
        [
            {
                "Mat Grp": "151",
                "Mat Grp Desc": "Test",
                "Material Code": "15111201000046",
                "Matrial Code Desc": "Material A",
                "Storage Location": "UP03",
                "Storage Location Desc": "Location A",
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
                "Mat Grp Desc": "Test",
                "Material Code": "15111301000109",
                "Matrial Code Desc": "Material B",
                "Storage Location": "UP04",
                "Storage Location Desc": "Location B",
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


def test_master_database_stage_integration(
    tmp_path: Path,
) -> None:

    # --------------------------------------------------------
    # CREATE TEST BSP WORKBOOK
    # --------------------------------------------------------

    workbook = (
        tmp_path
        / "BSP_Final_Inventory.xlsx"
    )

    create_test_bsp_workbook(
        workbook
    )

    # --------------------------------------------------------
    # CREATE TEST DATABASE
    # --------------------------------------------------------

    connection = sqlite3.connect(
        tmp_path
        / "master.db"
    )

    database = InventoryDatabase(
        connection
    )

    # --------------------------------------------------------
    # CREATE AGENT STATE
    # --------------------------------------------------------

    state = AgentState()

    # --------------------------------------------------------
    # CREATE WORKFLOW
    # --------------------------------------------------------

    workflow = InventoryWorkflow(
        state
    )

    # --------------------------------------------------------
    # RUN MASTER DATABASE STAGE
    # --------------------------------------------------------

    result = (
        workflow.run_master_database_stage(
            database=database,
            workbook_file=workbook,
        )
    )

    # --------------------------------------------------------
    # VERIFY SUCCESS
    # --------------------------------------------------------

    assert (
        result["success"]
        is True
    )

    # --------------------------------------------------------
    # VERIFY mminv_new
    # --------------------------------------------------------

    assert (
        result["database"]["table"]
        == "mminv_new"
    )

    assert (
        result["database"]["database_rows"]
        == 2
    )

    # --------------------------------------------------------
    # VERIFY UNIQUE MATERIAL CODES
    # --------------------------------------------------------

    assert (
        result["batches"][
            "unique_material_codes"
        ]
        == 2
    )

    # --------------------------------------------------------
    # VERIFY BATCH COUNT
    # --------------------------------------------------------

    assert (
        result["batches"][
            "batch_count"
        ]
        == 1
    )

    # --------------------------------------------------------
    # VERIFY WORKFLOW STATE
    # --------------------------------------------------------

    assert (
        "master_database_stage"
        in workflow.state.results
    )

    assert (
        "master_database_stage"
        in workflow.state.metadata
    )