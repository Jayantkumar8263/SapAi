from pathlib import Path
import sqlite3
import json

from app.agent.state import AgentState
from app.services.inventory_database import InventoryDatabase
from app.services.bsp_offline_pipeline import BSPOfflinePipeline


PREVIOUS = Path(r"C:\Jayant\College files\College\Study Material\semester\7thSem\BSP-training\SapAi\data\samples\Inventory Previous 07(month).xlsx")

CURRENT = Path(r"C:\Jayant\College files\College\Study Material\semester\7thSem\BSP-training\SapAi\data\samples\Inventory Previous 25.08.xlsx")

REFERENCE = Path(r"C:\Jayant\College files\College\Study Material\semester\7thSem\BSP-training\SapAi\data\samples\Final output file.xlsx")


def main():
    run_dir = Path("data") / "real_bsp_test"
    run_dir.mkdir(parents=True, exist_ok=True)

    database = InventoryDatabase(
        sqlite3.connect(run_dir / "inventory.db")
)

    state = AgentState(
        run_id="real-bsp-test"
    )

    pipeline = BSPOfflinePipeline(
        state=state,
        database=database,
        run_directory=run_dir,
    )

    result = pipeline.prepare_for_sap(
        previous_export=PREVIOUS,
        current_export=CURRENT,
        reference_file=REFERENCE,
    )

    print("\n==============================")
    print("REAL BSP OFFLINE TEST")
    print("==============================")
    print(json.dumps(result, indent=2, default=str))

    print("\nDatabase rows:")
    print(database.count_rows("mminv_new"))

    print("\nSTATUS:")
    print(result["status"])


if __name__ == "__main__":
    main()