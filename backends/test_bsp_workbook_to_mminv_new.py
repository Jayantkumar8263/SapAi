from pathlib import Path

from app.agent.state import AgentState
from app.agent.workflow import InventoryWorkflow

from app.services.inventory_database import (
    InventoryDatabase,
    create_sqlite_connection,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLES_DIR = (
    PROJECT_ROOT
    / "data"
    / "samples"
)

PREVIOUS_FILE = (
    SAMPLES_DIR
    / "Inventory Previous 07(month).xlsx"
)

CURRENT_FILE = (
    SAMPLES_DIR
    / "Inventory Previous 25.08.xlsx"
)

REFERENCE_FILE = (
    SAMPLES_DIR
    / "Final output file.xlsx"
)


# ============================================================
# TEST DATABASE
# ============================================================

def create_test_database():

    connection = (
        create_sqlite_connection()
    )

    database = InventoryDatabase(
        connection
    )

    return (
        connection,
        database,
    )


# ============================================================
# INTEGRATION TEST
# ============================================================

def test_bsp_workbook_to_mminv_new(
    tmp_path,
):
    """
    Integration test:

        Previous Inventory
                +
        Current Inventory
                ↓
        BSP Workbook
                ↓
            Inventory
                ↓
            mminv_new
                ↓
        Unique Material Codes
                ↓
        20,000-record batches
    """

    # =========================================================
    # DATABASE
    # =========================================================

    connection, database = (
        create_test_database()
    )

    try:

        # =====================================================
        # VERIFY INPUT FILES
        # =====================================================

        assert PREVIOUS_FILE.exists(), (
            "Previous inventory file not found: "
            f"{PREVIOUS_FILE}"
        )

        assert CURRENT_FILE.exists(), (
            "Current inventory file not found: "
            f"{CURRENT_FILE}"
        )

        assert REFERENCE_FILE.exists(), (
            "BSP RI/Capital reference file not found: "
            f"{REFERENCE_FILE}"
        )

        # =====================================================
        # STATE
        # =====================================================

        state = AgentState(
            user_id="bsp_workbook_db_test",
            plant="Bhilai",
        )

        # -----------------------------------------------------
        # IMPORTANT
        # -----------------------------------------------------
        # InventoryWorkflow.run_bsp_workbook_to_mminv_new()
        # gets Previous and Current files from AgentState.
        #
        # It does NOT accept previous_file/current_file
        # as function arguments.
        # =====================================================

        state.previous_inventory_file = str(
            PREVIOUS_FILE
        )

        state.current_inventory_file = str(
            CURRENT_FILE
        )

        # =====================================================
        # WORKFLOW
        # =====================================================

        workflow = InventoryWorkflow(
            state
        )

        # =====================================================
        # VERIFY REQUIRED METHOD
        # =====================================================

        assert hasattr(
            workflow,
            "run_bsp_workbook_to_mminv_new",
        ), (
            "InventoryWorkflow does not yet expose "
            "run_bsp_workbook_to_mminv_new()."
        )

        # =====================================================
        # RUN
        # =====================================================

        result = (
            workflow.run_bsp_workbook_to_mminv_new(
                database=database,
                reference_file=REFERENCE_FILE,
                output_file=(
                    tmp_path
                    / "BSP_Inventory.xlsx"
                ),
                batch_output_directory=(
                    tmp_path
                    / "batches"
                ),
            )
        )

        # =====================================================
        # TOP-LEVEL SUCCESS
        # =====================================================

        assert (
            result["success"]
            is True
        )

        # =====================================================
        # BSP WORKBOOK
        # =====================================================

        workbook_file = Path(
            result["bsp_workbook_file"]
        )

        assert (
            workbook_file.exists()
        )

        # =====================================================
        # mminv_new
        # =====================================================

        database_result = result[
            "mminv_new"
        ]

        assert (
            database_result["success"]
            is True
        )

        assert (
            database_result["database"]["table"]
            == "mminv_new"
        )

        # =====================================================
        # DATABASE TABLE
        # =====================================================

        assert (
            database.table_exists(
                "mminv_new"
            )
            is True
        )

        # =====================================================
        # ROW COUNT
        # =====================================================

        row_count = (
            database.count_rows(
                "mminv_new"
            )
        )

        assert (
            row_count > 0
        )

        # =====================================================
        # UNIQUE MATERIAL CODES
        # =====================================================

        material_codes = (
            database.get_unique_material_codes(
                "mminv_new"
            )
        )

        assert (
            len(material_codes) > 0
        )

        # =====================================================
        # BATCH RESULT
        # =====================================================

        batch_result = database_result["batches"]

        assert (
            batch_result["success"]
            is True
        )

        assert (
            batch_result[
                "unique_material_codes"
            ]
            == len(material_codes)
        )

        assert (
            batch_result[
                "batch_count"
            ]
            > 0
        )

        # =====================================================
        # BATCH FILES
        # =====================================================

        batch_directory = (
            tmp_path
            / "batches"
        )

        assert (
            batch_directory.exists()
        )

        batch_files = list(
            batch_directory.glob(
                "*.txt"
            )
        )

        assert (
            len(batch_files)
            == batch_result[
                "batch_count"
            ]
        )

        # =====================================================
        # FINAL OUTPUT
        # =====================================================

        print()

        print(
            "=============================================="
        )

        print(
            "BSP WORKBOOK → mminv_new TEST PASSED"
        )

        print(
            "=============================================="
        )

        print(
            f"Workbook : {workbook_file}"
        )

        print(
            f"Inventory rows : {row_count}"
        )

        print(
            "Unique material codes : "
            f"{len(material_codes)}"
        )

        print(
            "Batch size : "
            f"{batch_result['batch_size']}"
        )

        print(
            "Batch count : "
            f"{batch_result['batch_count']}"
        )

        print(
            "=============================================="
        )

    finally:

        connection.close()