from pathlib import Path
import sqlite3

import pandas as pd

from app.agent.state import AgentState
from app.services.bsp_offline_pipeline import BSPOfflinePipeline
from app.services.inventory_database import InventoryDatabase


def create_raw_mc1(path: Path, quantity: int, value: int):
    df = pd.DataFrame({
        "Material Group": ["151 KILNS"],
        "Material": ["15111201000046 TENSION PULLEY"],
        "Storage Location": ["1000UP03 PSS-SMS1_Gr"],
        "Val. stock": [quantity],
        "ValStckVal": [value],
        "Val. stock.1": ["EA"],
    })
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)


def create_reference(path: Path):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"Material Code": ["15111201000046"]}).to_excel(
            writer, sheet_name="RI", index=False
        )
        pd.DataFrame({"Material Code": ["99999999999999"]}).to_excel(
            writer, sheet_name="Capital", index=False
        )


def test_prepare_for_sap_stops_at_explicit_boundary(tmp_path: Path):
    previous = tmp_path / "previous.xlsx"
    current = tmp_path / "current.xlsx"
    reference = tmp_path / "reference.xlsx"

    create_raw_mc1(previous, 10, 1000)
    create_raw_mc1(current, 15, 1500)
    create_reference(reference)

    db = InventoryDatabase(sqlite3.connect(tmp_path / "inventory.db"))
    state = AgentState(run_id="offline-test")
    pipeline = BSPOfflinePipeline(state, db, tmp_path / "run")

    result = pipeline.prepare_for_sap(previous, current, reference)

    assert result["success"] is True
    assert result["status"] == "waiting_for_sap"
    assert result["batches"]["unique_material_codes"] == 1
    assert result["batches"]["batch_count"] == 1
    assert Path(result["bsp_workbook_file"]).exists()
    assert pipeline.manifest_file.exists()
    assert db.count_rows("mminv_new") == 1
    assert "ZMAT-FUND_POPR" in result["next_sap_steps"]


def test_finalize_from_spool_updates_mminv1_new(tmp_path: Path):
    db = InventoryDatabase(sqlite3.connect(tmp_path / "inventory.db"))
    state = AgentState(run_id="offline-finalize-test")
    pipeline = BSPOfflinePipeline(state, db, tmp_path / "run")

    spool = tmp_path / "Inventory 1.txt"
    spool.write_text(
        "Material Code\tQuantity\tDate\n"
        "15111201000046\t10\t24.09.2026\n",
        encoding="utf-8",
    )

    result = pipeline.finalize_from_spool([spool])

    assert result["success"] is True
    assert result["status"] == "completed"
    assert Path(result["inventory_po_file"]).exists()
    assert db.count_rows("mminv1_new") == 1
