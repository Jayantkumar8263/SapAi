from pathlib import Path
import tempfile
from tempfile import NamedTemporaryFile
from turtle import pd
from app.services.inventory_cleaner import clean_inventory_file
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.inventory_comparator import compare_inventory
from app.services.inventory_processor import process_inventory_file
from app.services.inventory_report import generate_inventory_report


router = APIRouter()


# ============================================================
# PATHS
# ============================================================

# Project root:
# SapAi/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
REPORT_DIR = DATA_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = REPORT_DIR / "BSP_Inventory_Report.xlsx"


# ============================================================
# BASIC INVENTORY ROUTE
# ============================================================

@router.get("/")
async def inventory_root():
    return {
        "message": "BSP Inventory API is running",
        "status": "ready",
    }


# ============================================================
# INSPECT INVENTORY FILE
# ============================================================

@router.post("/inspect")
async def inspect_inventory(
    file: UploadFile = File(...)
):
    """
    Inspect an uploaded inventory Excel file.

    Used for:
    - validating the uploaded Excel file
    - reading inventory data
    - generating basic inventory statistics
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was provided."
        )

    allowed_extensions = [".xlsx", ".xls"]

    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx and .xls files are supported."
        )

    temp_path = None

    try:
        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        with NamedTemporaryFile(
            delete=False,
            suffix=file_extension
        ) as temp_file:

            temp_file.write(file_content)
            temp_path = Path(temp_file.name)

        result = process_inventory_file(str(temp_path))

        return {
            "success": True,
            "filename": file.filename,
            "data": result,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Inventory inspection failed: {str(exc)}"
        )

    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


# ============================================================
# COMPARE TWO INVENTORY FILES
# ============================================================

@router.post("/compare")
async def compare_inventory_files(
    previous_file: UploadFile = File(...),
    current_file: UploadFile = File(...)
):
    """
    Compare previous inventory with current inventory.

    Expected request:

    multipart/form-data

    previous_file = previous inventory Excel
    current_file  = current inventory Excel
    """

    if not previous_file.filename:
        raise HTTPException(
            status_code=400,
            detail="Previous inventory file is required."
        )

    if not current_file.filename:
        raise HTTPException(
            status_code=400,
            detail="Current inventory file is required."
        )

    allowed_extensions = [".xlsx", ".xls"]

    previous_extension = Path(
        previous_file.filename
    ).suffix.lower()

    current_extension = Path(
        current_file.filename
    ).suffix.lower()

    if previous_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Previous inventory must be an Excel file."
        )

    if current_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Current inventory must be an Excel file."
        )

    previous_temp_path = None
    current_temp_path = None

    try:
        # ----------------------------------------------------
        # Read previous file
        # ----------------------------------------------------

        previous_content = await previous_file.read()

        if not previous_content:
            raise HTTPException(
                status_code=400,
                detail="Previous inventory file is empty."
            )

        with NamedTemporaryFile(
            delete=False,
            suffix=previous_extension
        ) as temp_file:

            temp_file.write(previous_content)
            previous_temp_path = Path(temp_file.name)

        # ----------------------------------------------------
        # Read current file
        # ----------------------------------------------------

        current_content = await current_file.read()

        if not current_content:
            raise HTTPException(
                status_code=400,
                detail="Current inventory file is empty."
            )

        with NamedTemporaryFile(
            delete=False,
            suffix=current_extension
        ) as temp_file:

            temp_file.write(current_content)
            current_temp_path = Path(temp_file.name)

        # ----------------------------------------------------
        # Run comparison engine
        # ----------------------------------------------------

        comparison_result = compare_inventory(
            previous_temp_path,
            current_temp_path
        )

        # The comparator returns:
        #
        # comparison_result = (
        #     comparison,
        #     summary
        # )

        if isinstance(comparison_result, tuple):
            comparison_data, summary = comparison_result
        else:
            comparison_data = comparison_result
            summary = {}

        # ----------------------------------------------------
        # Convert DataFrame to JSON-compatible data
        # ----------------------------------------------------

        if hasattr(comparison_data, "to_dict"):
            comparison_records = comparison_data.to_dict(
                orient="records"
            )
        elif isinstance(comparison_data, list):
            comparison_records = comparison_data
        else:
            comparison_records = []

        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return {
            "success": True,
            "previous_file": previous_file.filename,
            "current_file": current_file.filename,
            "comparison": comparison_records,
            "summary": summary,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Inventory comparison failed: {str(exc)}"
        )

    finally:

        if previous_temp_path and previous_temp_path.exists():
            try:
                previous_temp_path.unlink()
            except Exception:
                pass

        if current_temp_path and current_temp_path.exists():
            try:
                current_temp_path.unlink()
            except Exception:
                pass


# ============================================================
# COMPARE LOCAL INVENTORY FILES
# ============================================================

@router.post("/compare-local")
async def compare_local_inventory():
    """
    Compare the standard inventory files stored in:

    data/previous_inventory.xlsx
    data/current_inventory.xlsx
    """

    previous_path = DATA_DIR / "previous_inventory.xlsx"
    current_path = DATA_DIR / "current_inventory.xlsx"

    if not previous_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Previous inventory file not found."
        )

    if not current_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Current inventory file not found."
        )

    try:

        comparison_result = compare_inventory(
            previous_path,
            current_path
        )

        if isinstance(comparison_result, tuple):
            comparison_data, summary = comparison_result
        else:
            comparison_data = comparison_result
            summary = {}

        if hasattr(comparison_data, "to_dict"):
            comparison_records = comparison_data.to_dict(
                orient="records"
            )
        elif isinstance(comparison_data, list):
            comparison_records = comparison_data
        else:
            comparison_records = []

        return {
            "success": True,
            "previous_file": str(previous_path),
            "current_file": str(current_path),
            "comparison": comparison_records,
            "summary": summary,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Local inventory comparison failed: {str(exc)}"
        )


# ============================================================
# GENERATE INVENTORY REPORT
# ============================================================

@router.post("/report")
async def generate_report(
    previous_file: UploadFile = File(...),
    current_file: UploadFile = File(...)
):
    """
    Generate the final BSP Inventory Excel report.

    Workflow:

    Upload previous/current files
            ↓
    Compare inventory
            ↓
    Generate report
            ↓
    Save:
    data/reports/BSP_Inventory_Report.xlsx
    """

    if not previous_file.filename:
        raise HTTPException(
            status_code=400,
            detail="Previous inventory file is required."
        )

    if not current_file.filename:
        raise HTTPException(
            status_code=400,
            detail="Current inventory file is required."
        )

    allowed_extensions = [".xlsx", ".xls"]

    previous_extension = Path(
        previous_file.filename
    ).suffix.lower()

    current_extension = Path(
        current_file.filename
    ).suffix.lower()

    if previous_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Previous inventory must be an Excel file."
        )

    if current_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Current inventory must be an Excel file."
        )

    previous_temp_path = None
    current_temp_path = None

    try:

        # ----------------------------------------------------
        # Save previous file temporarily
        # ----------------------------------------------------

        previous_content = await previous_file.read()

        if not previous_content:
            raise HTTPException(
                status_code=400,
                detail="Previous inventory file is empty."
            )

        with NamedTemporaryFile(
            delete=False,
            suffix=previous_extension
        ) as temp_file:

            temp_file.write(previous_content)
            previous_temp_path = Path(temp_file.name)

        # ----------------------------------------------------
        # Save current file temporarily
        # ----------------------------------------------------

        current_content = await current_file.read()

        if not current_content:
            raise HTTPException(
                status_code=400,
                detail="Current inventory file is empty."
            )

        with NamedTemporaryFile(
            delete=False,
            suffix=current_extension
        ) as temp_file:

            temp_file.write(current_content)
            current_temp_path = Path(temp_file.name)

        # ----------------------------------------------------
        # Compare
        # ----------------------------------------------------

        comparison_result = compare_inventory(
            previous_temp_path,
            current_temp_path
        )

        if isinstance(comparison_result, tuple):
            comparison_data, summary = comparison_result
        else:
            comparison_data = comparison_result
            summary = {}

        # ----------------------------------------------------
        # Generate Excel report
        # ----------------------------------------------------

        generated_file = generate_inventory_report(
            comparison_data,
            summary,
            REPORT_FILE
        )

        # Some report implementations return the output path.
        # If they don't, use REPORT_FILE.
        if generated_file:
            generated_path = Path(generated_file)
        else:
            generated_path = REPORT_FILE

        if not generated_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Report generation completed but the Excel file was not created."
            )

        return {
            "success": True,
            "message": "Inventory report generated successfully.",
            "filename": "BSP_Inventory_Report.xlsx",
            "report_path": str(generated_path),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Inventory report generation failed: {str(exc)}"
        )

    finally:

        if previous_temp_path and previous_temp_path.exists():
            try:
                previous_temp_path.unlink()
            except Exception:
                pass

        if current_temp_path and current_temp_path.exists():
            try:
                current_temp_path.unlink()
            except Exception:
                pass


# ============================================================
# DOWNLOAD GENERATED REPORT
# ============================================================

@router.get("/report/download")
async def download_report():
    """
    Download the latest generated BSP inventory report.
    """

    if not REPORT_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Report not found. Generate the report first."
        )

    return FileResponse(
        path=REPORT_FILE,
        filename="BSP_Inventory_Report.xlsx",
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

# ============================================================
# CLEAN INVENTORY FILE
# ============================================================

@router.post("/clean")
async def clean_inventory(
    file: UploadFile = File(...)
):
    """
    Clean and standardize an SAP inventory Excel file.
    """

    temp_path = None

    try:
        # -------------------------------------------------
        # Validate filename
        # -------------------------------------------------

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file was uploaded."
            )

        filename = file.filename.lower()

        if not filename.endswith(
            (".xlsx", ".xls")
        ):
            raise HTTPException(
                status_code=400,
                detail="Only .xlsx and .xls files are supported."
            )

        # -------------------------------------------------
        # Create temporary directory
        # -------------------------------------------------

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(temp_dir) / file.filename

            # ---------------------------------------------
            # Save uploaded file
            # ---------------------------------------------

            contents = await file.read()

            if not contents:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty."
                )

            temp_path.write_bytes(contents)

            print(
                f"Cleaning uploaded file: "
                f"{temp_path}"
            )

            # ---------------------------------------------
            # Clean inventory
            # ---------------------------------------------

            result = clean_inventory_file(
                temp_path
            )

            # ---------------------------------------------
            # Return result
            # ---------------------------------------------

            return {
                "status": "success",
                "message": "Inventory cleaned successfully.",
                "result": result,
            }

    except HTTPException:
        raise

    except Exception as exc:

        print(
            "Inventory cleaning error:",
            repr(exc)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Inventory cleaning failed: {exc}"
        )
        # ============================================================
# UPLOAD INVENTORY FILES FOR AGENT
# ============================================================

from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"

UPLOAD_DIR = DATA_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ALLOWED_INVENTORY_EXTENSIONS = {
    ".xlsx",
    ".xls",
}


def validate_inventory_upload(
    file: UploadFile,
) -> None:

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file name provided.",
        )

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_INVENTORY_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only Excel files are supported "
                "(.xlsx or .xls)."
            ),
        )


async def save_inventory_upload(
    upload_file: UploadFile,
    destination: Path,
) -> Path:

    validate_inventory_upload(
        upload_file
    )

    try:

        with destination.open("wb") as buffer:

            shutil.copyfileobj(
                upload_file.file,
                buffer,
            )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save uploaded inventory file: "
                f"{exc}"
            ),
        )

    return destination


@router.post("/upload")
async def upload_inventory_files(
    previous_file: UploadFile = File(...),
    current_file: UploadFile = File(...),
):
    """
    Upload the previous and current inventory Excel files.

    The uploaded files are stored using stable filenames so
    the existing agent workflow can process them.

    Previous:
        data/uploads/previous_inventory.xlsx

    Current:
        data/uploads/current_inventory.xlsx
    """

    validate_inventory_upload(
        previous_file
    )

    validate_inventory_upload(
        current_file
    )

    previous_extension = Path(
        previous_file.filename
    ).suffix.lower()

    current_extension = Path(
        current_file.filename
    ).suffix.lower()

    previous_destination = (
        UPLOAD_DIR
        / f"previous_inventory{previous_extension}"
    )

    current_destination = (
        UPLOAD_DIR
        / f"current_inventory{current_extension}"
    )

    # Remove old uploaded versions.
    for old_file in UPLOAD_DIR.glob(
        "previous_inventory.*"
    ):
        try:
            old_file.unlink()
        except OSError:
            pass

    for old_file in UPLOAD_DIR.glob(
        "current_inventory.*"
    ):
        try:
            old_file.unlink()
        except OSError:
            pass

    await save_inventory_upload(
        previous_file,
        previous_destination,
    )

    await save_inventory_upload(
        current_file,
        current_destination,
    )

    return {
        "status": "success",

        "message": (
            "Previous and current inventory "
            "files uploaded successfully."
        ),

        "previous_file": {
            "original_name": previous_file.filename,
            "saved_path": str(
                previous_destination
            ),
        },

        "current_file": {
            "original_name": current_file.filename,
            "saved_path": str(
                current_destination
            ),
        },
    }