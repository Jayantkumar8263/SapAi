"""
Deterministic RI / Capital classifier for SapAi.

Classification rules:
- Material found in RI reference -> RI
- Material found in Capital reference -> Capital
- Material found in neither -> Normal
- If reference files are unavailable -> UNCLASSIFIED
- If a material exists in both references -> CONFLICT

The classifier never guesses RI/Capital.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

import pandas as pd


# ============================================================
# REFERENCE PATHS
# ============================================================

DEFAULT_REFERENCE_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "reference"
)

DEFAULT_RI_FILE = (
    DEFAULT_REFERENCE_DIR
    / "RI_Materials.xlsx"
)

DEFAULT_CAPITAL_FILE = (
    DEFAULT_REFERENCE_DIR
    / "Capital_Materials.xlsx"
)


# ============================================================
# MATERIAL CODE NORMALIZATION
# ============================================================

def normalize_material_code(value: Any) -> str:
    """
    Normalize material codes so that values such as:

        12345
        12345.0
        "12345"

    are treated consistently.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value).strip()

    # Handle Excel numeric values such as 12345.0
    if text.endswith(".0"):
        try:
            number = float(text)

            if number.is_integer():
                text = str(int(number))

        except ValueError:
            pass

    return text.upper()


# ============================================================
# FIND MATERIAL CODE COLUMN
# ============================================================

def _find_material_column(
    df: pd.DataFrame,
) -> Optional[str]:

    if df.empty:
        return None

    candidates = [
        "Material_Code",
        "Material Code",
        "MaterialCode",
        "Material",
        "Material Number",
        "Material_Number",
        "MATNR",
        "material_code",
        "material",
        "code",
    ]

    normalized = {
        str(column)
        .strip()
        .lower()
        .replace("_", " "): column
        for column in df.columns
    }

    for candidate in candidates:

        key = (
            candidate
            .lower()
            .replace("_", " ")
        )

        if key in normalized:
            return normalized[key]

    # Fallback search
    for column in df.columns:

        name = (
            str(column)
            .strip()
            .lower()
        )

        if (
            "material" in name
            or "matnr" in name
        ):
            return column

    return None


# ============================================================
# LOAD REFERENCE FILE
# ============================================================

def _load_reference_codes(
    file_path: Path,
) -> Tuple[set[str], dict]:

    if not file_path.exists():

        return set(), {
            "available": False,
            "file": str(file_path),
            "count": 0,
            "error": "Reference file not found.",
        }

    try:

        df = pd.read_excel(
            file_path
        )

    except Exception as exc:

        return set(), {
            "available": False,
            "file": str(file_path),
            "count": 0,
            "error": (
                f"Unable to read reference file: {exc}"
            ),
        }

    column = _find_material_column(df)

    if column is None:

        return set(), {
            "available": False,
            "file": str(file_path),
            "count": 0,
            "error": (
                "No material-code column "
                "was found."
            ),
        }

    codes = {
        normalize_material_code(value)
        for value in df[column].tolist()
    }

    codes.discard("")

    return codes, {
        "available": True,
        "file": str(file_path),
        "count": len(codes),
        "column": str(column),
        "error": None,
    }


# ============================================================
# CLASSIFY INVENTORY
# ============================================================

def classify_inventory(
    comparison_df: pd.DataFrame,
    ri_file: Optional[str | Path] = None,
    capital_file: Optional[str | Path] = None,
) -> Tuple[pd.DataFrame, dict]:
    """
    Classify inventory materials.

    Possible classifications:

        RI
        Capital
        Normal
        UNCLASSIFIED
        CONFLICT
    """

    df = (
        comparison_df.copy()
        if comparison_df is not None
        else pd.DataFrame()
    )

    ri_path = (
        Path(ri_file)
        if ri_file
        else DEFAULT_RI_FILE
    )

    capital_path = (
        Path(capital_file)
        if capital_file
        else DEFAULT_CAPITAL_FILE
    )

    # --------------------------------------------------------
    # Load references
    # --------------------------------------------------------

    ri_codes, ri_info = (
        _load_reference_codes(
            ri_path
        )
    )

    capital_codes, capital_info = (
        _load_reference_codes(
            capital_path
        )
    )

    ri_available = ri_info["available"]
    capital_available = (
        capital_info["available"]
    )

    references_available = (
        ri_available
        and capital_available
    )

    # --------------------------------------------------------
    # Find material column
    # --------------------------------------------------------

    material_column = _find_material_column(
        df
    )

    if material_column is None:

        df["Inventory_Type"] = (
            "UNCLASSIFIED"
        )

        df["Classification_Reason"] = (
            "Material code column not found."
        )

    else:

        def classify(value):

            code = normalize_material_code(
                value
            )

            # No material code
            if not code:

                return (
                    "UNCLASSIFIED",
                    "Material code is missing.",
                )

            # ------------------------------------------------
            # References unavailable
            # ------------------------------------------------

            if not references_available:

                return (
                    "UNCLASSIFIED",
                    (
                        "RI / Capital reference "
                        "files are unavailable."
                    ),
                )

            # ------------------------------------------------
            # Conflict
            # ------------------------------------------------

            in_ri = code in ri_codes
            in_capital = (
                code in capital_codes
            )

            if in_ri and in_capital:

                return (
                    "CONFLICT",
                    (
                        "Material code exists in "
                        "both RI and Capital "
                        "reference lists."
                    ),
                )

            # ------------------------------------------------
            # RI
            # ------------------------------------------------

            if in_ri:

                return (
                    "RI",
                    (
                        "Material code found in "
                        "RI reference list."
                    ),
                )

            # ------------------------------------------------
            # Capital
            # ------------------------------------------------

            if in_capital:

                return (
                    "Capital",
                    (
                        "Material code found in "
                        "Capital reference list."
                    ),
                )

            # ------------------------------------------------
            # Normal
            # ------------------------------------------------

            return (
                "Normal",
                (
                    "Material code not found "
                    "in RI or Capital "
                    "reference lists."
                ),
            )

        pairs = df[
            material_column
        ].map(classify)

        df["Inventory_Type"] = pairs.map(
            lambda x: x[0]
        )

        df[
            "Classification_Reason"
        ] = pairs.map(
            lambda x: x[1]
        )

    # ========================================================
    # COUNTS
    # ========================================================

    counts = (
        df["Inventory_Type"]
        .value_counts()
        .to_dict()
    )

    summary = {

        "total_materials": int(
            len(df)
        ),

        "ri_materials": int(
            counts.get("RI", 0)
        ),

        "capital_materials": int(
            counts.get("Capital", 0)
        ),

        "normal_materials": int(
            counts.get("Normal", 0)
        ),

        "unclassified_materials": int(
            counts.get(
                "UNCLASSIFIED",
                0
            )
        ),

        "conflict_materials": int(
            counts.get(
                "CONFLICT",
                0
            )
        ),

        "reference_files_available": bool(
            references_available
        ),

        "reference_files": {
            "ri": ri_info,
            "capital": capital_info,
        },

        "warnings": [],
    }

    # ========================================================
    # WARNINGS
    # ========================================================

    if not ri_available:

        summary["warnings"].append(
            (
                "RI reference file is "
                "unavailable. RI classification "
                "cannot be confirmed."
            )
        )

    if not capital_available:

        summary["warnings"].append(
            (
                "Capital reference file is "
                "unavailable. Capital "
                "classification cannot be confirmed."
            )
        )

    if counts.get(
        "CONFLICT",
        0
    ) > 0:

        summary["warnings"].append(
            (
                "Some material codes exist "
                "in both RI and Capital "
                "reference lists."
            )
        )

    return df, summary


# ============================================================
# RECORD-BASED CLASSIFICATION
# ============================================================

def classify_inventory_records(
    records: list[dict],
    ri_file: Optional[str | Path] = None,
    capital_file: Optional[str | Path] = None,
) -> Tuple[list[dict], dict]:

    df = pd.DataFrame(
        records
    )

    classified, summary = (
        classify_inventory(
            df,
            ri_file,
            capital_file,
        )
    )

    return (
        classified.to_dict(
            orient="records"
        ),
        summary,
    )