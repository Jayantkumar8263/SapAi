"""
BSP Inventory Report Generator

Generates the final Excel report after:

1. Inventory comparison
2. AI analysis
3. RI / Capital classification
"""

from pathlib import Path

import pandas as pd


# ============================================================
# REPORT GENERATOR
# ============================================================

def generate_inventory_report(
    comparison_df: pd.DataFrame,
    summary: dict,
    output_file: str,
):
    """
    Generate the final BSP inventory Excel report.

    Sheets:
        1. Inventory Comparison
        2. Summary
    """

    # ---------------------------------------------------------
    # Validate input
    # ---------------------------------------------------------

    if comparison_df is None:

        comparison_df = pd.DataFrame()

    comparison_df = comparison_df.copy()

    if summary is None:

        summary = {}

    # ---------------------------------------------------------
    # Prepare output path
    # ---------------------------------------------------------

    output_path = Path(
        output_file
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =========================================================
    # ENSURE CLASSIFICATION COLUMNS EXIST
    # =========================================================

    if "Inventory_Type" not in comparison_df.columns:

        comparison_df[
            "Inventory_Type"
        ] = "UNCLASSIFIED"

    if (
        "Classification_Reason"
        not in comparison_df.columns
    ):

        comparison_df[
            "Classification_Reason"
        ] = (
            "Classification has not "
            "been performed."
        )

    # =========================================================
    # CLASSIFICATION COUNTS
    # =========================================================

    classification_counts = (
        comparison_df[
            "Inventory_Type"
        ]
        .value_counts()
        .to_dict()
    )

    ri_count = int(
        classification_counts.get(
            "RI",
            0,
        )
    )

    capital_count = int(
        classification_counts.get(
            "Capital",
            0,
        )
    )

    normal_count = int(
        classification_counts.get(
            "Normal",
            0,
        )
    )

    unclassified_count = int(
        classification_counts.get(
            "UNCLASSIFIED",
            0,
        )
    )

    conflict_count = int(
        classification_counts.get(
            "CONFLICT",
            0,
        )
    )

    # =========================================================
    # CREATE SUMMARY
    # =========================================================

    summary_data = {

        "Metric": [

            "Previous Records",

            "Current Records",

            "Combined Materials",

            "New Materials",

            "Removed Materials",

            "Existing Materials",

            "Total Previous Quantity",

            "Total Current Quantity",

            "Total Quantity Change",

            "RI Materials",

            "Capital Materials",

            "Normal Materials",

            "Unclassified Materials",

            "Classification Conflicts",

            "Reference Files Available",
        ],

        "Value": [

            summary.get(
                "previous_records",
                0,
            ),

            summary.get(
                "current_records",
                0,
            ),

            summary.get(
                "combined_records",
                0,
            ),

            summary.get(
                "new_materials",
                0,
            ),

            summary.get(
                "removed_materials",
                0,
            ),

            summary.get(
                "existing_materials",
                0,
            ),

            summary.get(
                "total_previous_quantity",
                0,
            ),

            summary.get(
                "total_current_quantity",
                0,
            ),

            summary.get(
                "total_quantity_change",
                0,
            ),

            ri_count,

            capital_count,

            normal_count,

            unclassified_count,

            conflict_count,

            "Yes"
            if summary.get(
                "reference_files_available",
                False,
            )
            else "No",
        ],
    }

    summary_df = pd.DataFrame(
        summary_data
    )

    # =========================================================
    # GENERATE EXCEL
    # =========================================================

    with pd.ExcelWriter(
        output_path,
        engine="openpyxl",
    ) as writer:

        # -----------------------------------------------------
        # Sheet 1
        # -----------------------------------------------------

        comparison_df.to_excel(
            writer,
            sheet_name="Inventory Comparison",
            index=False,
        )

        # -----------------------------------------------------
        # Sheet 2
        # -----------------------------------------------------

        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )

        # -----------------------------------------------------
        # Workbook
        # -----------------------------------------------------

        workbook = writer.book

        comparison_sheet = (
            workbook[
                "Inventory Comparison"
            ]
        )

        summary_sheet = (
            workbook["Summary"]
        )

        # =====================================================
        # FREEZE PANES
        # =====================================================

        comparison_sheet.freeze_panes = (
            "A2"
        )

        summary_sheet.freeze_panes = (
            "A2"
        )

        # =====================================================
        # AUTO FILTER
        # =====================================================

        if (
            comparison_sheet.max_row > 1
            and comparison_sheet.max_column > 0
        ):

            comparison_sheet.auto_filter.ref = (
                comparison_sheet.dimensions
            )

        # =====================================================
        # AUTO COLUMN WIDTH
        # =====================================================

        for sheet in [
            comparison_sheet,
            summary_sheet,
        ]:

            for column in sheet.columns:

                max_length = 0

                column_letter = (
                    column[0]
                    .column_letter
                )

                for cell in column:

                    if cell.value is not None:

                        cell_length = len(
                            str(
                                cell.value
                            )
                        )

                        if (
                            cell_length
                            > max_length
                        ):

                            max_length = (
                                cell_length
                            )

                adjusted_width = (
                    max_length + 2
                )

                adjusted_width = min(
                    adjusted_width,
                    50,
                )

                sheet.column_dimensions[
                    column_letter
                ].width = (
                    adjusted_width
                )

    return str(
        output_path
    )


# =============================================================
# TESTING
# =============================================================

if __name__ == "__main__":

    print("=" * 60)

    print(
        "BSP INVENTORY REPORT GENERATOR"
    )

    print("=" * 60)

    print()

    print(
        "Reading inventory files..."
    )

    # ---------------------------------------------------------
    # Import comparator
    # ---------------------------------------------------------

    from app.services.inventory_comparator import (
        compare_inventory,
    )

    # ---------------------------------------------------------
    # Find project root
    # ---------------------------------------------------------

    project_root = (
        Path(__file__)
        .resolve()
        .parents[3]
    )

    # ---------------------------------------------------------
    # Input files
    # ---------------------------------------------------------

    previous_file = (
        project_root
        / "data"
        / "previous_inventory.xlsx"
    )

    current_file = (
        project_root
        / "data"
        / "current_inventory.xlsx"
    )

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    output_file = (
        project_root
        / "data"
        / "reports"
        / "BSP_Inventory_Report.xlsx"
    )

    # ---------------------------------------------------------
    # Check files
    # ---------------------------------------------------------

    if not previous_file.exists():

        raise FileNotFoundError(
            f"Previous inventory file not found: "
            f"{previous_file}"
        )

    if not current_file.exists():

        raise FileNotFoundError(
            f"Current inventory file not found: "
            f"{current_file}"
        )

    # ---------------------------------------------------------
    # Compare
    # ---------------------------------------------------------

    print()

    print(
        "Comparing previous and current inventory..."
    )

    comparison, summary = (
        compare_inventory(
            str(previous_file),
            str(current_file),
        )
    )

    # ---------------------------------------------------------
    # Classify
    # ---------------------------------------------------------

    print()

    print(
        "Classifying RI / Capital materials..."
    )

    from app.services.inventory_classifier import (
        classify_inventory,
    )

    comparison, classification_summary = (
        classify_inventory(
            comparison
        )
    )

    # Add classification information
    # into report summary.

    summary.update(
        classification_summary
    )

    # ---------------------------------------------------------
    # Generate
    # ---------------------------------------------------------

    print()

    print(
        "Generating Excel report..."
    )

    report_path = (
        generate_inventory_report(
            comparison,
            summary,
            str(output_file),
        )
    )

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    print()

    print("=" * 60)

    print(
        "REPORT GENERATED SUCCESSFULLY"
    )

    print("=" * 60)

    print()

    print(
        "Report file:"
    )

    print(
        report_path
    )

    print()

    print(
        "Sheets created:"
    )

    print(
        "1. Inventory Comparison"
    )

    print(
        "2. Summary"
    )

    print()

    print(
        "Classification:"
    )

    print(
        f"RI: {classification_summary.get('ri_materials', 0)}"
    )

    print(
        f"Capital: {classification_summary.get('capital_materials', 0)}"
    )

    print(
        f"Normal: {classification_summary.get('normal_materials', 0)}"
    )

    print(
        "Unclassified: "
        f"{classification_summary.get('unclassified_materials', 0)}"
    )

    print(
        "Conflicts: "
        f"{classification_summary.get('conflict_materials', 0)}"
    )

    print()

    print("=" * 60)

    print("DONE")

    print("=" * 60)