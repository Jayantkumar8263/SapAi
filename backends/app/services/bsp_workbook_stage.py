"""
BSP Workbook Stage
==================

Builds the official BSP five-sheet inventory workbook from
the standardized Previous and Current MC.1 inventory files.

Flow:

    Previous MC.1 standardized file
                    +
    Current MC.1 standardized file
                    +
    RI / Capital reference
                    ↓
        BSP five-sheet workbook
                    ↓
              Inventory sheet
                    ↓
              mminv_new

This stage does NOT:
- connect to SAP
- update the database
- execute ZMAT-FUND_POPR
- monitor SM37
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.bsp_workbook_builder import (
    build_bsp_workbook,
)


DEFAULT_WORKBOOK_NAME = "BSP_Inventory_Workbook.xlsx"


class BSPWorkbookStage:
    """
    Builds the BSP-format inventory workbook.
    """

    def __init__(self) -> None:
        pass

    def run(
        self,
        previous_file: str | Path,
        present_file: str | Path,
        reference_file: str | Path,
        output_file: str | Path,
    ) -> dict[str, Any]:
        """
        Build the BSP five-sheet workbook.

        Parameters
        ----------
        previous_file:
            Standardized Previous MC.1 inventory file.

        present_file:
            Standardized Current MC.1 inventory file.

        reference_file:
            Workbook containing RI and Capital sheets.

        output_file:
            Destination BSP workbook.
        """

        # =====================================================
        # VALIDATION
        # =====================================================

        if previous_file is None:
            raise ValueError(
                "previous_file is required."
            )

        if present_file is None:
            raise ValueError(
                "present_file is required."
            )

        if reference_file is None:
            raise ValueError(
                "reference_file is required."
            )

        if output_file is None:
            raise ValueError(
                "output_file is required."
            )

        previous_path = Path(previous_file)
        present_path = Path(present_file)
        reference_path = Path(reference_file)
        output_path = Path(output_file)

        if not previous_path.exists():
            raise FileNotFoundError(
                f"Previous inventory file not found: "
                f"{previous_path}"
            )

        if not present_path.exists():
            raise FileNotFoundError(
                f"Present inventory file not found: "
                f"{present_path}"
            )

        if not reference_path.exists():
            raise FileNotFoundError(
                f"Reference workbook not found: "
                f"{reference_path}"
            )

        if previous_path.suffix.lower() != ".xlsx":
            raise ValueError(
                "Previous inventory file must be .xlsx."
            )

        if present_path.suffix.lower() != ".xlsx":
            raise ValueError(
                "Present inventory file must be .xlsx."
            )

        if reference_path.suffix.lower() != ".xlsx":
            raise ValueError(
                "Reference workbook must be .xlsx."
            )

        if output_path.suffix.lower() != ".xlsx":
            raise ValueError(
                "Output workbook must be .xlsx."
            )

        # =====================================================
        # OUTPUT DIRECTORY
        # =====================================================

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # =====================================================
        # BUILD BSP WORKBOOK
        # =====================================================

        result = build_bsp_workbook(
            previous_file=previous_path,
            present_file=present_path,
            reference_file=reference_path,
            output_file=output_path,
        )

        # =====================================================
        # VALIDATE RESULT
        # =====================================================

        if not isinstance(result, dict):
            raise RuntimeError(
                "BSP workbook builder returned "
                "an invalid result."
            )

        if not result.get("success", False):
            raise RuntimeError(
                result.get(
                    "message",
                    "BSP workbook generation failed.",
                )
            )

        if not output_path.exists():
            raise RuntimeError(
                "BSP workbook builder reported success, "
                "but the output workbook was not created."
            )

        # =====================================================
        # RETURN
        # =====================================================

        return {
            "success": True,
            "output_file": str(output_path),
            "previous_rows": result.get(
                "previous_rows"
            ),
            "present_rows": result.get(
                "present_rows"
            ),
            "ri_materials": result.get(
                "ri_materials"
            ),
            "capital_materials": result.get(
                "capital_materials"
            ),
            "final_inventory_rows": result.get(
                "final_inventory_rows"
            ),
        }