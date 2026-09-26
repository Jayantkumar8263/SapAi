from pathlib import Path
import sqlite3
import pandas as pd

from app.services.bsp_mc1_export import clean_mc1_workbook
from app.services.bsp_workbook_builder import build_bsp_workbook
from app.services.inventory_database import InventoryDatabase
from app.services.inventory_database_stage import InventoryDatabaseStage
from app.services.inventory_zmat_orchestrator import InventoryZMATOrchestrator
from app.services.zmat_fund_popr_workflow import ZMATFundPOPRWorkflow
from app.services.zmat_sm37_orchestrator import ZMATSM37Orchestrator
from app.services.sm37_spool_orchestrator import SM37SpoolOrchestrator
from app.services.spool_inventory_po_orchestrator import SpoolInventoryPOOrchestrator
from app.services.final_inventory_database_stage import FinalInventoryDatabaseStage
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.agent.state import AgentState

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "demo_output"
RAW = OUT / "raw"
REF = OUT / "references.xlsx"


def make_raw(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(path, sheet_name="Sheet1", index=False)


def raw_row(group, material, loc, qty, value, uom):
    return {
        "Material Group": group,
        "Material": material,
        "Storage Location": loc,
        "Val. stock": qty,
        "ValStckVal": value,
        "Val. stock.1": uom,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    # Strings are shaped like the documented MC.1 export fields.
    prev_rows = [
        raw_row("151 Bearing", "15111201000046 Material A", "1000UP03 Stores", 10, 1000, "EA"),
        raw_row("151 Bearing", "15111301000109 Material B", "1000UP04 Stores", 20, 2000, "EA"),
        raw_row("152 Motor", "15211401000020 Material C", "1000UP03 Stores", 5, 1500, "EA"),
        raw_row("153 Pump", "15311501000031 Material D", "1000UP05 Stores", 8, 3200, "EA"),
        raw_row("154 Valve", "15411601000042 Material E", "1000UP06 Stores", 12, 2400, "EA"),
    ]
    curr_rows = [
        raw_row("151 Bearing", "15111201000046 Material A", "1000UP03 Stores", 15, 1500, "EA"),
        raw_row("151 Bearing", "15111301000109 Material B", "1000UP04 Stores", 18, 1800, "EA"),
        raw_row("152 Motor", "15211401000020 Material C", "1000UP03 Stores", 5, 1500, "EA"),
        raw_row("153 Pump", "15311501000031 Material D", "1000UP05 Stores", 10, 4000, "EA"),
        raw_row("155 New Item", "15511701000053 Material F", "1000UP07 Stores", 7, 2100, "EA"),
    ]

    prev_raw = RAW / "MC1_Previous_Raw.xlsx"
    curr_raw = RAW / "MC1_Current_Raw.xlsx"
    make_raw(prev_raw, prev_rows)
    make_raw(curr_raw, curr_rows)

    # RI/Capital reference lists emulate ZMMRIREP and the desktop Capital file.
    with pd.ExcelWriter(REF, engine="openpyxl") as writer:
        pd.DataFrame({"Material Code": ["15111201000046", "15211401000020"]}).to_excel(writer, sheet_name="RI", index=False)
        pd.DataFrame({"Material Code": ["15311501000031", "15511701000053"]}).to_excel(writer, sheet_name="Capital", index=False)

    prev_std = OUT / "MC1_Previous_Standardized.xlsx"
    curr_std = OUT / "MC1_Current_Standardized.xlsx"
    clean_mc1_workbook(prev_raw, prev_std)
    clean_mc1_workbook(curr_raw, curr_std)

    bsp_workbook = OUT / "BSP_Inventory.xlsx"
    wb_result = build_bsp_workbook(prev_std, curr_std, REF, bsp_workbook)

    conn = sqlite3.connect(OUT / "demo.db")
    db = InventoryDatabase(conn)
    state = AgentState(user_id="demo", plant="1000")

    db_stage = InventoryDatabaseStage(db)
    db_result = db_stage.run_from_workbook(
        workbook_file=bsp_workbook,
        output_directory=OUT / "zmat_batches",
    )

    # Simulated SAP ZMAT -> background -> SM37 for each batch.
    client = MockSAPClient()
    client.controls["txt_JOB_STATUS"] = "FINISHED"
    client.controls["txt_JOB_NUMBER"] = "DEMO-0001"
    controller = SAPController(client)
    zmat_workflow = ZMATFundPOPRWorkflow(state, controller)
    zmat_sm37 = ZMATSM37Orchestrator(state, controller)
    batch_results = []
    for i, batch in enumerate(db_result["batches"]["batches"], start=1):
        batch_results.append(zmat_sm37.run_batch(
            batch_number=i,
            material_codes=batch,
            job_name="ZMAT_PO_PR",
            submit_background=True,
            timeout_seconds=1,
            poll_interval_seconds=0.01,
        ))
    zmat_result = {"success": all(r.get("success") for r in batch_results), "batches": batch_results}

    # For a full demo, simulate the SAP background/SM37/spool path.
    client2 = MockSAPClient()
    client2.controls["txt_JOB_STATUS"] = "FINISHED"
    client2.controls["txt_JOB_NUMBER"] = "DEMO-0001"
    client2.controls["txt_SPOOL"] = (
        "Material\tQuantity\tDate\n"
        "15111201000046\t15\t25.09.2026\n"
        "15111301000109\t18\t25.09.2026\n"
        "15211401000020\t5\t25.09.2026\n"
        "15311501000031\t10\t25.09.2026\n"
        "15511701000053\t7\t25.09.2026\n"
    )
    controller2 = SAPController(client2)
    state2 = AgentState(user_id="demo-sm37", plant="1000")
    sm37_spool = SM37SpoolOrchestrator(state2, controller2)
    spool_po = SpoolInventoryPOOrchestrator(sm37_spool)
    spool_file = OUT / "Inventory_Spool.txt"
    po_file = OUT / "Inventory PO.xlsx"
    po_result = spool_po.run(
        spool_output_file=spool_file,
        inventory_po_file=po_file,
        job_name="ZMAT_PO_PR",
        timeout_seconds=1,
        poll_interval_seconds=0.01,
    )

    # Final mminv1_new import.
    final_stage = FinalInventoryDatabaseStage(db)
    final_result = final_stage.run(po_file)

    summary = {
        "success": bool(wb_result.get("success")) and bool(db_result.get("success")) and bool(po_result.get("success")) and bool(final_result.get("success")),
        "raw_previous": str(prev_raw),
        "raw_current": str(curr_raw),
        "bsp_workbook": str(bsp_workbook),
        "mminv_new_rows": db_result.get("database", {}).get("database_rows", db_result.get("database_rows")),
        "unique_material_codes": db_result.get("batches", {}).get("unique_material_codes"),
        "zmat_batch_count": db_result.get("batches", {}).get("batch_count"),
        "zmat_demo_preparation": zmat_result,
        "inventory_po": str(po_file),
        "inventory_po_rows": po_result.get("inventory_po", {}).get("rows") if isinstance(po_result.get("inventory_po"), dict) else None,
        "mminv1_new": final_result,
    }
    pd.DataFrame([{
        "Material Code": "15111201000046",
        "Quantity": 15,
        "Date": "20260925",
    }]).to_excel(OUT / "demo_expected_sample.xlsx", index=False)
    import json
    (OUT / "demo_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("DEMO BSP AUTOMATION")
    print("STATUS:", "COMPLETE" if summary["success"] else "FAILED")
    print("BSP workbook:", bsp_workbook)
    print("mminv_new rows:", summary["mminv_new_rows"])
    print("Unique material codes:", summary["unique_material_codes"])
    print("ZMAT batches:", summary["zmat_batch_count"])
    print("Inventory PO:", po_file)
    print("mminv1_new:", final_result)
    print("Summary:", OUT / "demo_summary.json")
    conn.close()


if __name__ == "__main__":
    main()
