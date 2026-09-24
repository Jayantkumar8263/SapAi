from pathlib import Path

import pandas as pd

from app.services.bsp_workbook_stage import (
    BSPWorkbookStage,
)


ROOT = Path(__file__).resolve().parent


def create_test_inventory_file(
    path: Path,
    quantity_column: str,
):
    df = pd.DataFrame(
        [
            {
                "Concatenate": "100015111201000046UP03",
                "Mat Grp": "151",
                "Mat Grp Desc": "Test Group",
                "Material Code": "15111201000046",
                "Material Code Desc": "Test Material",
                "Storage Location": "UP03",
                "Storage Location Desc": "Test Location",
                "Plant": "1000",
                quantity_column: 10,
                (
                    "Inve Prev Value"
                    if quantity_column
                    == "Inve Prev Quantity"
                    else "Inve Pres Value"
                ): 1000,
                "UOM": "EA",
            }
        ]
    )

    df.to_excel(
        path,
        sheet_name="Sheet2",
        index=False,
    )


def create_reference_file(path: Path):
    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:

        pd.DataFrame(
            ["15111201000046"]
        ).to_excel(
            writer,
            sheet_name="RI",
            index=False,
            header=False,
        )

        pd.DataFrame(
            ["15111301000109"]
        ).to_excel(
            writer,
            sheet_name="Capital",
            index=False,
            header=False,
        )


def test_bsp_workbook_stage(tmp_path: Path):

    previous_file = (
        tmp_path / "previous.xlsx"
    )

    present_file = (
        tmp_path / "present.xlsx"
    )

    reference_file = (
        tmp_path / "reference.xlsx"
    )

    output_file = (
        tmp_path / "BSP_Inventory_Workbook.xlsx"
    )

    create_test_inventory_file(
        previous_file,
        "Inve Prev Quantity",
    )

    create_test_inventory_file(
        present_file,
        "Inve Prev Quantity",
    )

    create_reference_file(
        reference_file
    )

    stage = BSPWorkbookStage()

    result = stage.run(
        previous_file=previous_file,
        present_file=present_file,
        reference_file=reference_file,
        output_file=output_file,
    )

    assert result["success"] is True

    assert output_file.exists()

    workbook = pd.ExcelFile(
        output_file
    )

    assert workbook.sheet_names == [
        "Inventory Prev",
        "Inventory Pres",
        "RI",
        "Capital",
        "Inventory",
    ]

    inventory = pd.read_excel(
        output_file,
        sheet_name="Inventory",
    )

    assert len(inventory) == 1

    assert (
        str(
            inventory.loc[
                0,
                "Material Code",
            ]
        )
        == "15111201000046"
    )