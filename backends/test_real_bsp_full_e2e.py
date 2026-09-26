from pathlib import Path
import sqlite3

import pandas as pd

from app.agent.state import AgentState
from app.services.inventory_database import InventoryDatabase
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.zmat_sm37_orchestrator import ZMATSM37Orchestrator
from app.services.spool_inventory_po_orchestrator import (
    SpoolInventoryPOOrchestrator,
)
from app.services.final_inventory_database_stage import (
    FinalInventoryDatabaseStage,
)
from app.services.zmat_sm37_orchestrator import ZMATSM37Orchestrator
from app.services.sm37_spool_orchestrator import (
    SM37SpoolOrchestrator,
)

ROOT = Path(__file__).resolve().parent
REAL_RUN = ROOT / "data" / "real_bsp_test"
BATCH_DIR = REAL_RUN / "zmat_batches"


EXPECTED_MATERIALS = 142154
EXPECTED_BATCHES = 8


def test_real_bsp_full_offline_e2e(tmp_path: Path):

    # =========================================================
    # 1. VERIFY REAL BSP ARTIFACTS
    # =========================================================

    batch_files = sorted(
        BATCH_DIR.glob("zmat_batch_*.txt")
    )

    assert len(batch_files) == EXPECTED_BATCHES

    batch_sizes = []

    for batch_file in batch_files:
        lines = batch_file.read_text(
            encoding="utf-8"
        ).splitlines()

        assert len(lines) > 0

        batch_sizes.append(len(lines))

    assert sum(batch_sizes) == EXPECTED_MATERIALS

    assert batch_sizes[:7] == [20000] * 7
    assert batch_sizes[7] == 2154

    # =========================================================
    # 2. CREATE MOCK SAP
    # =========================================================

    state = AgentState(
        user_id="real_bsp_e2e",
        plant="Bhilai",
    )

    client = MockSAPClient()

    # Every mocked background job immediately finishes.
    client.controls["txt_JOB_STATUS"] = "FINISHED"
    client.controls["txt_JOB_NUMBER"] = "90000001"

    controller = SAPController(client)

    zmat_sm37 = ZMATSM37Orchestrator(
        state=state,
        controller=controller,
    )

    # =========================================================
    # 3. RUN ALL 8 REAL BATCHES THROUGH MOCK SAP
    # =========================================================

    batches = []

    for index, batch_file in enumerate(
        batch_files,
        start=1,
    ):

        material_codes = [
            line.strip()
            for line in batch_file.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        batches.append(
            {
                "batch_number": index,
                "material_codes": material_codes,
            }
        )

    result = zmat_sm37.run_batches(
        batches=batches,
        job_name="ZMAT_PO_PR",
        submit_background=True,
        timeout_seconds=1,
        poll_interval_seconds=0.01,
    )

    assert result["success"] is True

    assert result["batch_count"] == 8

    assert result["completed_batches"] == 8

    assert len(result["batches"]) == 8

    assert all(
        batch["success"]
        for batch in result["batches"]
    )

    # =========================================================
    # 4. CREATE DETERMINISTIC MOCK SPOOL FILES
    # =========================================================

    spool_dir = (
        tmp_path
        / "spool"
    )

    spool_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    spool_files = []

    for index, batch_file in enumerate(
        batch_files,
        start=1,
    ):

        material_codes = [
            line.strip()
            for line in batch_file.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        spool_file = (
            spool_dir
            / f"Inventory_{index}.txt"
        )

        with spool_file.open(
            "w",
            encoding="utf-8",
        ) as f:

            f.write(
                "Material\tQuantity\tDate\n"
            )

            for material_code in material_codes:

                f.write(
                    f"{material_code}\t1\t20260925\n"
                )

        spool_files.append(
            spool_file
        )

    # Verify all spool files exist.
    assert len(spool_files) == 8

    assert all(
        file.exists()
        for file in spool_files
    )

    # =========================================================
    # 5. BUILD INVENTORY PO
    # =========================================================

    inventory_po_file = (
        tmp_path
        / "Inventory PO.xlsx"
    )

    sm37_spool = SM37SpoolOrchestrator(
    state,
    controller,
    )

    spool_po = SpoolInventoryPOOrchestrator(
    sm37_spool
    )

    po_result = (
        spool_po.build_from_txt_files(
            input_files=spool_files,
            output_file=inventory_po_file,
        )
    )

    assert po_result["success"] is True

    assert inventory_po_file.exists()

    # =========================================================
    # 6. VERIFY INVENTORY PO
    # =========================================================

    inventory_po = pd.read_excel(
        inventory_po_file,
        sheet_name="Inventory PO",
    )

    assert len(inventory_po) == EXPECTED_MATERIALS

    assert "Material Code" in inventory_po.columns

    assert "Quantity" in inventory_po.columns

    assert "Date" in inventory_po.columns

    # =========================================================
    # 7. UPDATE mminv1_new
    # =========================================================

    database_path = (
        tmp_path
        / "final_inventory.db"
    )

    connection = sqlite3.connect(
        database_path
    )

    database = InventoryDatabase(
        connection
    )

    final_stage = FinalInventoryDatabaseStage(
        database
    )

    final_result = final_stage.run(
        inventory_po_file=inventory_po_file,
        table_name="mminv1_new",
        sheet_name="Inventory PO",
)

    print("\n================ FINAL DATABASE RESULT ================")
    print(final_result)
    print("========================================================")

    assert final_result.get("success") is True

    assert final_result["success"] is True

    assert (
        final_result["rows_imported"]
        == EXPECTED_MATERIALS
    )

    # =========================================================
    # 8. VERIFY FINAL DATABASE
    # =========================================================

    final_rows = database.count_rows(
        "mminv1_new"
    )

    assert final_rows == EXPECTED_MATERIALS

    # =========================================================
    # 9. FINAL STATUS
    # =========================================================

    print()
    print("=" * 70)
    print("REAL BSP OFFLINE E2E")
    print("=" * 70)
    print(
        f"Real material codes : {EXPECTED_MATERIALS}"
    )
    print(
        f"Real ZMAT batches   : {EXPECTED_BATCHES}"
    )
    print(
        f"Inventory PO rows   : {len(inventory_po)}"
    )
    print(
        f"mminv1_new rows     : {final_rows}"
    )
    print(
        "STATUS              : COMPLETE"
    )
    print("=" * 70)