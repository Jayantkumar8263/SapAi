from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from app.services.inventory_database import (
    InventoryDatabase,
)

from app.services.final_inventory_database_stage import (
    FinalInventoryDatabaseStage,
)


# ============================================================
# TEST DATA
# ============================================================


def create_test_inventory_po(
    path: Path,
) -> Path:

    dataframe = pd.DataFrame(
        [
            {
                "Material Code": "15111201000046",
                "Quantity": 10,
                "Date": "20260924",
            },
            {
                "Material Code": "15111301000109",
                "Quantity": 20,
                "Date": "20260925",
            },
            {
                "Material Code": "15111401000020",
                "Quantity": 30,
                "Date": "20260926",
            },
        ]
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

    return path


# ============================================================
# DATABASE
# ============================================================


def create_test_database(
    path: Path,
) -> InventoryDatabase:

    connection = sqlite3.connect(
        path
    )

    return InventoryDatabase(
        connection
    )


# ============================================================
# TEST 1
# ============================================================


def test_final_database_stage_updates_mminv1_new(
    tmp_path: Path,
) -> None:

    inventory_po_file = (
        tmp_path
        / "Inventory PO.xlsx"
    )

    create_test_inventory_po(
        inventory_po_file
    )

    database = create_test_database(
        tmp_path
        / "inventory.db"
    )

    stage = FinalInventoryDatabaseStage(
        database
    )

    result = stage.run(
        inventory_po_file=inventory_po_file,
        table_name="mminv1_new",
        sheet_name="Inventory PO",
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    assert result["success"] is True

    assert (
        result["table_name"]
        == "mminv1_new"
    )

    assert (
        result["sheet_name"]
        == "Inventory PO"
    )

    assert (
        result["inventory_po_file"]
        == str(inventory_po_file)
    )

    # --------------------------------------------------------
    # ROW COUNT
    # --------------------------------------------------------

    assert (
        result["rows_imported"]
        == 3
    )

    # --------------------------------------------------------
    # DATABASE VERIFICATION
    # --------------------------------------------------------

    dataframe = database.read_table(
        "mminv1_new"
    )

    assert len(dataframe) == 3

    assert (
        dataframe[
            "Material Code"
        ].astype(str).tolist()
        == [
            "15111201000046",
            "15111301000109",
            "15111401000020",
        ]
    )


# ============================================================
# TEST 2
# ============================================================


def test_final_database_stage_replaces_old_mminv1_new(
    tmp_path: Path,
) -> None:

    inventory_po_file = (
        tmp_path
        / "Inventory PO.xlsx"
    )

    create_test_inventory_po(
        inventory_po_file
    )

    database = create_test_database(
        tmp_path
        / "inventory.db"
    )

    # --------------------------------------------------------
    # Create OLD mminv1_new data
    # --------------------------------------------------------

    old_data = pd.DataFrame(
        [
            {
                "Material Code": "OLD001",
                "Quantity": 999,
                "Date": "20260101",
            },
        ]
    )

    database.replace_table(
        dataframe=old_data,
        table_name="mminv1_new",
    )

    assert (
        database.count_rows(
            "mminv1_new"
        )
        == 1
    )

    # --------------------------------------------------------
    # Run final database stage
    # --------------------------------------------------------

    stage = FinalInventoryDatabaseStage(
        database
    )

    result = stage.run(
        inventory_po_file=inventory_po_file,
        table_name="mminv1_new",
    )

    assert result["success"] is True

    # --------------------------------------------------------
    # Verify OLD data was replaced
    # --------------------------------------------------------

    dataframe = database.read_table(
        "mminv1_new"
    )

    assert len(dataframe) == 3

    assert (
        "OLD001"
        not in dataframe[
            "Material Code"
        ].astype(str).tolist()
    )


# ============================================================
# TEST 3
# ============================================================


def test_final_database_stage_rejects_missing_file(
    tmp_path: Path,
) -> None:

    database = create_test_database(
        tmp_path
        / "inventory.db"
    )

    stage = FinalInventoryDatabaseStage(
        database
    )

    missing_file = (
        tmp_path
        / "does_not_exist.xlsx"
    )

    with pytest.raises(
        FileNotFoundError
    ):

        stage.run(
            inventory_po_file=missing_file,
            table_name="mminv1_new",
        )


# ============================================================
# TEST 4
# ============================================================


def test_final_database_stage_rejects_non_excel_file(
    tmp_path: Path,
) -> None:

    database = create_test_database(
        tmp_path
        / "inventory.db"
    )

    stage = FinalInventoryDatabaseStage(
        database
    )

    text_file = (
        tmp_path
        / "Inventory PO.txt"
    )

    text_file.write_text(
        "test",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError
    ):

        stage.run(
            inventory_po_file=text_file,
            table_name="mminv1_new",
        )