from pathlib import Path
import sqlite3

import pandas as pd

from app.services.inventory_database import (
    InventoryDatabase,
)

from app.services.inventory_database_stage import (
    InventoryDatabaseStage,
)


def create_test_database(
    path: Path,
) -> InventoryDatabase:

    connection = sqlite3.connect(
        path
    )

    return InventoryDatabase(
        connection
    )


def create_inventory_dataframe(
    count: int = 45_000,
) -> pd.DataFrame:

    rows = []

    for index in range(
        count
    ):

        # Deliberately create duplicates.
        material_code = (
            f"{15100000000000 + (index % 30_000):014d}"
        )

        rows.append(
            {
                "Mat Grp": "151",
                "Mat Grp Desc": "Test Group",
                "Material Code": material_code,
                "Matrial Code Desc": (
                    f"Material {index}"
                ),
                "Storage Location": "UP03",
                "Storage Location Desc": (
                    "Test Location"
                ),
                "Plant": "1000",
                "Inve Prev Quantity": 10,
                "Inve Prev Value": 1000,
                "Inve Pres Quantity": 15,
                "Inve Pres Value": 1500,
                "UOM": "EA",
                "RI Ind": "No",
                "Capital Ind": "No",
            }
        )

    return pd.DataFrame(
        rows
    )


def test_database_stage_creates_zmat_batches(
    tmp_path: Path,
) -> None:

    database = create_test_database(
        tmp_path
        / "inventory.db"
    )

    stage = InventoryDatabaseStage(
        database
    )

    inventory = (
        create_inventory_dataframe()
    )

    result = stage.run(
        inventory_dataframe=inventory,
        batch_size=20_000,
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    assert result["success"] is True

    database_result = (
        result["database"]
    )

    assert (
        database_result["table"]
        == "mminv_new"
    )

    assert (
        database_result["input_rows"]
        == 45_000
    )

    assert (
        database_result["database_rows"]
        == 45_000
    )

    # --------------------------------------------------------
    # BATCHES
    # --------------------------------------------------------

    batch_result = (
        result["batches"]
    )

    assert (
        batch_result["success"]
        is True
    )

    assert (
        batch_result["table"]
        == "mminv_new"
    )

    assert (
        batch_result["total_input_rows"]
        == 45_000
    )

    # 45,000 rows contain only 30,000
    # unique material codes.
    assert (
        batch_result[
            "unique_material_codes"
        ]
        == 30_000
    )

    assert (
        batch_result[
            "batch_size"
        ]
        == 20_000
    )

    assert (
        batch_result[
            "batch_count"
        ]
        == 2
    )

    batches = (
        batch_result["batches"]
    )

    # --------------------------------------------------------
    # VERIFY BATCH SIZES
    # --------------------------------------------------------

    assert (
        len(batches)
        == 2
    )

    assert (
        len(batches[0])
        == 20_000
    )

    assert (
        len(batches[1])
        == 10_000
    )

    # --------------------------------------------------------
    # VERIFY NO MATERIAL CODE IS LOST
    # --------------------------------------------------------

    all_codes = []

    for batch in batches:

        all_codes.extend(
            batch
        )

    assert (
        len(all_codes)
        == 30_000
    )

    assert (
        len(set(all_codes))
        == 30_000
    )


def test_database_stage_rejects_missing_material_code(
    tmp_path: Path,
) -> None:

    database = create_test_database(
        tmp_path
        / "inventory.db"
    )

    stage = InventoryDatabaseStage(
        database
    )

    invalid_inventory = pd.DataFrame(
        {
            "Plant": ["1000"],
            "UOM": ["EA"],
        }
    )

    try:

        stage.run(
            inventory_dataframe=(
                invalid_inventory
            )
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