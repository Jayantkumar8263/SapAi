"""
SapAi - Inventory Intelligence Service

Purpose:
    Analyze the deterministic inventory comparison produced by
    the existing Pandas-based inventory pipeline.

Important:
    - This service does NOT calculate inventory quantities.
    - The comparison engine remains the source of truth.
    - This service interprets changes and produces insights.
    - It is designed so a real LLM reasoning provider can be
      added later without changing the deterministic pipeline.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

# Percentage change considered significant.
SIGNIFICANT_CHANGE_PERCENT = 20.0


# ============================================================
# JSON-SAFE VALUE
# ============================================================

def safe_value(value: Any) -> Any:
    """
    Convert Pandas / NumPy values into JSON-safe Python values.
    """

    if value is None:
        return None

    if hasattr(value, "item"):

        try:
            value = value.item()

        except Exception:
            pass

    if isinstance(value, float):

        if pd.isna(value):
            return None

    return value


# ============================================================
# DATAFRAME NORMALIZATION
# ============================================================

def normalize_comparison(
    comparison: Any,
) -> pd.DataFrame:
    """
    Convert the comparison result into a DataFrame.

    Supports:
        - pandas DataFrame
        - list of dictionaries
        - dictionary
    """

    if comparison is None:

        return pd.DataFrame()

    if isinstance(comparison, pd.DataFrame):

        return comparison.copy()

    if isinstance(comparison, list):

        return pd.DataFrame(comparison)

    if isinstance(comparison, dict):

        # Single comparison row
        return pd.DataFrame([comparison])

    raise TypeError(
        "Unsupported comparison result type: "
        f"{type(comparison).__name__}"
    )


# ============================================================
# COLUMN RESOLUTION
# ============================================================

def find_column(
    df: pd.DataFrame,
    *possible_names: str,
) -> str | None:
    """
    Find a column using multiple possible names.
    """

    if df.empty:
        return None

    columns = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for name in possible_names:

        key = name.strip().lower()

        if key in columns:
            return columns[key]

    return None


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_inventory_changes(
    comparison: Any,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Analyze inventory changes.

    The deterministic comparison remains the source of truth.

    Returns:
        Structured inventory insights suitable for:
            - FastAPI
            - React
            - reports
            - future LLM reasoning
    """

    df = normalize_comparison(comparison)

    summary = summary or {}

    # --------------------------------------------------------
    # EMPTY RESULT
    # --------------------------------------------------------

    if df.empty:

        return {
            "success": True,
            "message": "No inventory comparison records available.",
            "analysis": {
                "total_materials": 0,
                "new_materials": 0,
                "removed_materials": 0,
                "existing_materials": 0,
                "zero_stock_materials": [],
                "zero_stock_materials_count": 0,
                "significant_changes": [],
                "top_increases": [],
                "top_decreases": [],
                "recommendations": [],
                "risk_level": "low",
            },
        }

    # --------------------------------------------------------
    # RESOLVE COLUMNS
    # --------------------------------------------------------

    material_code_col = find_column(
        df,
        "Material_Code",
        "material_code",
        "Material Code",
        "material",
    )

    material_name_col = find_column(
        df,
        "Material_Name",
        "material_name",
        "Material Name",
        "name",
    )

    previous_qty_col = find_column(
        df,
        "Previous_Quantity",
        "previous_quantity",
        "Previous Quantity",
        "previous_qty",
    )

    current_qty_col = find_column(
        df,
        "Current_Quantity",
        "current_quantity",
        "Current Quantity",
        "current_qty",
    )

    change_col = find_column(
        df,
        "Quantity_Change",
        "quantity_change",
        "Quantity Change",
        "change",
    )

    status_col = find_column(
        df,
        "Status",
        "status",
    )

    unit_col = find_column(
        df,
        "Unit",
        "unit",
    )

    # --------------------------------------------------------
    # REQUIRED QUANTITY COLUMNS
    # --------------------------------------------------------

    if previous_qty_col is None:

        raise ValueError(
            "Previous inventory quantity column was not found."
        )

    if current_qty_col is None:

        raise ValueError(
            "Current inventory quantity column was not found."
        )

    # --------------------------------------------------------
    # NORMALIZE NUMERIC VALUES
    # --------------------------------------------------------

    df[previous_qty_col] = pd.to_numeric(
        df[previous_qty_col],
        errors="coerce",
    ).fillna(0)

    df[current_qty_col] = pd.to_numeric(
        df[current_qty_col],
        errors="coerce",
    ).fillna(0)

    if change_col is not None:

        df[change_col] = pd.to_numeric(
            df[change_col],
            errors="coerce",
        ).fillna(
            df[current_qty_col] -
            df[previous_qty_col]
        )

    else:

        change_col = "__calculated_change__"

        df[change_col] = (
            df[current_qty_col] -
            df[previous_qty_col]
        )

    # --------------------------------------------------------
    # MATERIAL STATUS
    # --------------------------------------------------------

    if status_col is not None:

        status_series = (
            df[status_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

    else:

        status_series = pd.Series(
            ["existing"] * len(df),
            index=df.index,
        )

    # --------------------------------------------------------
    # BASIC COUNTS
    # --------------------------------------------------------

    total_materials = len(df)

    new_materials = int(
        (status_series == "new").sum()
    )

    removed_materials = int(
        (
            status_series.isin(
                [
                    "removed",
                    "missing",
                ]
            )
        ).sum()
    )

    existing_materials = int(
        (
            ~status_series.isin(
                [
                    "new",
                    "removed",
                    "missing",
                ]
            )
        ).sum()
    )

    # --------------------------------------------------------
    # ZERO STOCK
    # --------------------------------------------------------

    zero_stock_df = df[
        df[current_qty_col] == 0
    ]

    zero_stock_materials = []

    for _, row in zero_stock_df.iterrows():

        material_code = (
            safe_value(row[material_code_col])
            if material_code_col
            else None
        )

        material_name = (
            safe_value(row[material_name_col])
            if material_name_col
            else None
        )

        zero_stock_materials.append(
            {
                "material_code": material_code,
                "material_name": material_name,
                "previous_quantity": safe_value(
                    row[previous_qty_col]
                ),
            }
        )

    # --------------------------------------------------------
    # PERCENTAGE CHANGE
    # --------------------------------------------------------

    df["__change_percent__"] = 0.0

    non_zero_previous = (
        df[previous_qty_col] != 0
    )

    df.loc[
        non_zero_previous,
        "__change_percent__",
    ] = (
        (
            df.loc[
                non_zero_previous,
                current_qty_col,
            ]
            -
            df.loc[
                non_zero_previous,
                previous_qty_col,
            ]
        )
        /
        df.loc[
            non_zero_previous,
            previous_qty_col,
        ]
        * 100
    )

    # --------------------------------------------------------
    # NEW MATERIALS WITH STOCK
    # --------------------------------------------------------

    new_stock_df = df[
        (
            status_series == "new"
        )
        &
        (
            df[current_qty_col] > 0
        )
    ]

    # --------------------------------------------------------
    # SIGNIFICANT CHANGES
    # --------------------------------------------------------

    significant_df = df[
        (
            df["__change_percent__"].abs()
            >= SIGNIFICANT_CHANGE_PERCENT
        )
        |
        (
            (
                df[previous_qty_col] == 0
            )
            &
            (
                df[current_qty_col] != 0
            )
        )
    ]

    significant_changes = []

    for _, row in significant_df.iterrows():

        previous_qty = float(
            row[previous_qty_col]
        )

        current_qty = float(
            row[current_qty_col]
        )

        change = float(
            row[change_col]
        )

        if previous_qty == 0:

            percentage = None

        else:

            percentage = (
                (change / previous_qty)
                * 100
            )

        significant_changes.append(
            {
                "material_code": (
                    safe_value(
                        row[material_code_col]
                    )
                    if material_code_col
                    else None
                ),

                "material_name": (
                    safe_value(
                        row[material_name_col]
                    )
                    if material_name_col
                    else None
                ),

                "previous_quantity": (
                    safe_value(previous_qty)
                ),

                "current_quantity": (
                    safe_value(current_qty)
                ),

                "quantity_change": (
                    safe_value(change)
                ),

                "change_percent": (
                    safe_value(percentage)
                ),

                "unit": (
                    safe_value(row[unit_col])
                    if unit_col
                    else None
                ),

                "direction": (
                    "increase"
                    if change > 0
                    else "decrease"
                    if change < 0
                    else "no_change"
                ),
            }
        )

    # --------------------------------------------------------
    # TOP INCREASES
    # --------------------------------------------------------

    top_increase_df = (
        df[df[change_col] > 0]
        .sort_values(
            by=change_col,
            ascending=False,
        )
        .head(5)
    )

    top_increases = []

    for _, row in top_increase_df.iterrows():

        top_increases.append(
            {
                "material_code": (
                    safe_value(
                        row[material_code_col]
                    )
                    if material_code_col
                    else None
                ),

                "material_name": (
                    safe_value(
                        row[material_name_col]
                    )
                    if material_name_col
                    else None
                ),

                "quantity_change": safe_value(
                    row[change_col]
                ),
            }
        )

    # --------------------------------------------------------
    # TOP DECREASES
    # --------------------------------------------------------

    top_decrease_df = (
        df[df[change_col] < 0]
        .sort_values(
            by=change_col,
            ascending=True,
        )
        .head(5)
    )

    top_decreases = []

    for _, row in top_decrease_df.iterrows():

        top_decreases.append(
            {
                "material_code": (
                    safe_value(
                        row[material_code_col]
                    )
                    if material_code_col
                    else None
                ),

                "material_name": (
                    safe_value(
                        row[material_name_col]
                    )
                    if material_name_col
                    else None
                ),

                "quantity_change": safe_value(
                    row[change_col]
                ),
            }
        )

    # --------------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------------

    recommendations = []

    if len(zero_stock_materials) > 0:

        recommendations.append(
            (
                f"Review {len(zero_stock_materials)} "
                "material(s) with zero current stock."
            )
        )

    if len(significant_changes) > 0:

        recommendations.append(
            (
                f"Review {len(significant_changes)} "
                "material(s) with significant inventory changes."
            )
        )

    if new_materials > 0:

        recommendations.append(
            (
                f"Verify {new_materials} new material(s) "
                "against recent procurement or production activity."
            )
        )

    if removed_materials > 0:

        recommendations.append(
            (
                f"Investigate {removed_materials} removed "
                "material(s) to confirm stock depletion or "
                "master-data changes."
            )
        )

    if not recommendations:

        recommendations.append(
            "No major inventory anomalies were detected."
        )

    # --------------------------------------------------------
    # RISK LEVEL
    # --------------------------------------------------------

    risk_score = 0

    risk_score += len(
        zero_stock_materials
    )

    risk_score += len(
        significant_changes
    )

    risk_score += removed_materials

    if risk_score >= 10:

        risk_level = "high"

    elif risk_score >= 3:

        risk_level = "medium"

    else:

        risk_level = "low"

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    analysis = {

        "total_materials": total_materials,

        "new_materials": new_materials,

        "removed_materials": removed_materials,

        "existing_materials": existing_materials,

        "zero_stock_materials": zero_stock_materials,

        # Numeric count for dashboard/API consumers.
        # Keep the detailed list above for drill-down views.
        "zero_stock_materials_count": len(
            zero_stock_materials
        ),

        "significant_changes": significant_changes,

        "top_increases": top_increases,

        "top_decreases": top_decreases,

        "recommendations": recommendations,

        "risk_level": risk_level,

        "source_summary": {
            key: safe_value(value)
            for key, value in summary.items()
        },
    }

    return {

        "success": True,

        "message": (
            "Inventory intelligence analysis "
            "completed successfully."
        ),

        "analysis": analysis,

    }