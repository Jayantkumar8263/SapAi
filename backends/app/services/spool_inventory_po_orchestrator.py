"""
SM37 Spool → Inventory PO Orchestrator
=======================================

Connects the existing SAP spool output to the existing
Inventory PO builder.

BSP process:

    SM37
      ↓
    FINISHED
      ↓
    Spool
      ↓
    TXT files
      ↓
    Combine TXT files
      ↓
    Normalize dates
      ↓
    Inventory PO.xlsx

This module does NOT implement:
- SAP GUI operations
- spool extraction logic
- TXT parsing logic
- Excel generation logic

Those responsibilities remain in the existing workflows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from app.services.inventory_po_builder import (
    build_inventory_po,
)

from app.services.sm37_spool_orchestrator import (
    SM37SpoolOrchestrator,
)


class SpoolInventoryPOOrchestrator:
    """
    Connects SM37/spool output to Inventory PO generation.
    """

    def __init__(
        self,
        sm37_spool_orchestrator: SM37SpoolOrchestrator,
    ):
        if sm37_spool_orchestrator is None:
            raise ValueError(
                "sm37_spool_orchestrator cannot be None."
            )

        self.sm37_spool_orchestrator = (
            sm37_spool_orchestrator
        )

    # ========================================================
    # BUILD INVENTORY PO FROM TXT FILES
    # ========================================================

    def build_from_txt_files(
        self,
        input_files: Iterable[str | Path],
        output_file: str | Path,
        date_columns: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """
        Build Inventory PO directly from existing spool TXT files.

        This is useful when the spool files have already been
        extracted by a previous step.
        """

        files = [
            Path(file)
            for file in input_files
        ]

        if not files:
            raise ValueError(
                "No spool TXT files were supplied."
            )

        for file in files:

            if not file.exists():
                raise FileNotFoundError(
                    f"Spool TXT file not found: {file}"
                )

            if file.suffix.lower() != ".txt":
                raise ValueError(
                    f"Expected a .txt spool file: {file}"
                )

        output_path = Path(
            output_file
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        inventory_po_file = build_inventory_po(
            input_files=files,
            output_file=output_path,
            date_columns=date_columns,
        )

        result = {
            "success": True,
            "input_files": [
                str(file)
                for file in files
            ],
            "input_file_count": len(files),
            "inventory_po_file": str(
                inventory_po_file
            ),
        }

        if not output_path.exists():

            result["success"] = False

            result["error"] = (
                "Inventory PO builder reported success, "
                "but the output file was not created."
            )

            return result

        return result

    # ========================================================
    # EXTRACT ONE SPOOL AND BUILD INVENTORY PO
    # ========================================================

    def extract_and_build(
        self,
        spool_output_file: str | Path,
        inventory_po_file: str | Path,
        date_columns: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """
        Extract one completed SAP spool and immediately
        convert it into Inventory PO.xlsx.

        Process:

            SM37
              ↓
            FINISHED
              ↓
            Spool TXT
              ↓
            Inventory PO.xlsx
        """

        spool_path = Path(
            spool_output_file
        )

        inventory_po_path = Path(
            inventory_po_file
        )

        # ----------------------------------------------------
        # STEP 1 — Extract spool
        # ----------------------------------------------------

        spool_result = (
            self.sm37_spool_orchestrator.extract_spool(
                spool_path
            )
        )

        if not spool_result.get(
            "success",
            False,
        ):

            return {
                "success": False,
                "spool": spool_result,
                "inventory_po": None,
                "error": (
                    spool_result.get(
                        "error"
                    )
                    or
                    "Spool extraction failed."
                ),
            }

        # ----------------------------------------------------
        # STEP 2 — Build Inventory PO
        # ----------------------------------------------------

        try:

            inventory_po_result = (
                self.build_from_txt_files(
                    input_files=[
                        spool_path
                    ],
                    output_file=(
                        inventory_po_path
                    ),
                    date_columns=(
                        date_columns
                    ),
                )
            )

        except Exception as exc:

            return {
                "success": False,
                "spool": spool_result,
                "inventory_po": None,
                "error": str(exc),
            }

        if not inventory_po_result.get(
            "success",
            False,
        ):

            return {
                "success": False,
                "spool": spool_result,
                "inventory_po": (
                    inventory_po_result
                ),
                "error": (
                    inventory_po_result.get(
                        "error"
                    )
                    or
                    "Inventory PO generation failed."
                ),
            }

        # ----------------------------------------------------
        # STEP 3 — Final validation
        # ----------------------------------------------------

        if not inventory_po_path.exists():

            return {
                "success": False,
                "spool": spool_result,
                "inventory_po": (
                    inventory_po_result
                ),
                "error": (
                    "Inventory PO output file "
                    "was not created."
                ),
            }

        return {
            "success": True,
            "spool": spool_result,
            "inventory_po": (
                inventory_po_result
            ),
            "inventory_po_file": str(
                inventory_po_path
            ),
        }

    # ========================================================
    # COMPLETE SM37 → SPOOL → INVENTORY PO
    # ========================================================

    def run(
        self,
        spool_output_file: str | Path,
        inventory_po_file: str | Path,
        job_name: str = "ZMAT_PO_PR",
        timeout_seconds: float = 300,
        poll_interval_seconds: float = 5,
        date_columns: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """
        Complete:

            SM37
              ↓
            FINISHED
              ↓
            Spool TXT
              ↓
            Inventory PO.xlsx
        """

        spool_path = Path(
            spool_output_file
        )

        inventory_po_path = Path(
            inventory_po_file
        )

        # ----------------------------------------------------
        # STEP 1 — SM37 → FINISHED
        # ----------------------------------------------------

        monitoring = (
            self.sm37_spool_orchestrator.monitor_job(
                job_name=job_name,
                timeout_seconds=(
                    timeout_seconds
                ),
                poll_interval_seconds=(
                    poll_interval_seconds
                ),
            )
        )

        if not monitoring.get(
            "success",
            False,
        ):

            return {
                "success": False,
                "monitoring": monitoring,
                "spool": None,
                "inventory_po": None,
                "error": (
                    monitoring.get(
                        "monitoring",
                        {},
                    ).get(
                        "message"
                    )
                    or
                    "SAP background job did not finish successfully."
                ),
            }

        # ----------------------------------------------------
        # STEP 2 — Spool → TXT → Inventory PO
        # ----------------------------------------------------

        result = (
            self.extract_and_build(
                spool_output_file=(
                    spool_path
                ),
                inventory_po_file=(
                    inventory_po_path
                ),
                date_columns=(
                    date_columns
                ),
            )
        )

        result[
            "monitoring"
        ] = monitoring

        return result