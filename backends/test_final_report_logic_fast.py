from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
REPORT_DIR = DATA_DIR / "reports"

JULY_FILE = SAMPLES_DIR / "Inventory Previous 07(month).xlsx"
AUGUST_FILE = SAMPLES_DIR / "Inventory Previous 25.08.xlsx"
FINAL_FILE = SAMPLES_DIR / "Final output file.xlsx"

OUTPUT_FILE = (
    REPORT_DIR /
    "step4b_fast_investigation.xlsx"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_value(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_dataframe(df):

    df = df.copy()

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    for column in df.columns:
        df[column] = df[column].apply(
            normalize_value
        )

    return df


# ============================================================
# KEY
# ============================================================

def make_key(
    material_code,
    storage_location,
    plant
):

    return (
        normalize_value(material_code)
        + "|"
        + normalize_value(storage_location)
        + "|"
        + normalize_value(plant)
    )


def add_key(df):

    df = df.copy()

    df["_Key"] = [
        make_key(
            material_code,
            storage_location,
            plant
        )
        for material_code,
        storage_location,
        plant
        in zip(
            df["Material Code"],
            df["Storage Location"],
            df["Plant"]
        )
    ]

    return df


# ============================================================
# LOAD MONTH SHEET 2
# ============================================================

def load_month(file_path):

    df = pd.read_excel(
        file_path,
        sheet_name="Sheet2"
    )

    df = normalize_dataframe(df)

    return add_key(df)


# ============================================================
# LOAD FINAL SHEET
# ============================================================

def find_header_row(
    sheet_name,
    required_header="Material Code"
):

    preview = pd.read_excel(
        FINAL_FILE,
        sheet_name=sheet_name,
        header=None,
        nrows=10
    )

    for row_number in range(
        len(preview)
    ):

        values = [
            normalize_value(value)
            for value in preview.iloc[row_number]
        ]

        if required_header in values:
            return row_number

    raise ValueError(
        f"Could not find header in {sheet_name}"
    )


def load_final_sheet(sheet_name):

    header_row = find_header_row(
        sheet_name
    )

    print(
        f"{sheet_name}: header row = "
        f"{header_row}"
    )

    df = pd.read_excel(
        FINAL_FILE,
        sheet_name=sheet_name,
        header=header_row
    )

    df = normalize_dataframe(df)

    # Normalize known header variations

    rename_map = {}

    for column in df.columns:

        normalized = (
            str(column)
            .strip()
            .lower()
        )

        if normalized == "storage location":
            rename_map[column] = "Storage Location"

        elif normalized == "material code":
            rename_map[column] = "Material Code"

        elif normalized == "material code desc":
            rename_map[column] = "Material Code Desc"

        elif normalized == "matrial code desc":
            rename_map[column] = "Material Code Desc"

        elif normalized == "plant":
            rename_map[column] = "Plant"

    df = df.rename(
        columns=rename_map
    )

    return add_key(df)


# ============================================================
# LOAD DATA
# ============================================================

def main():

    print("=" * 70)
    print("STEP 4B - FAST FINAL REPORT INVESTIGATION")
    print("=" * 70)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # JULY
    # --------------------------------------------------------

    print("\nLoading July Sheet 2...")

    july = load_month(
        JULY_FILE
    )

    print(
        f"July rows: {len(july)}"
    )

    # --------------------------------------------------------
    # AUGUST
    # --------------------------------------------------------

    print("\nLoading August Sheet 2...")

    august = load_month(
        AUGUST_FILE
    )

    print(
        f"August rows: {len(august)}"
    )

    # --------------------------------------------------------
    # FINAL INVENTORY
    # --------------------------------------------------------

    print("\nLoading Final Inventory...")

    inventory = load_final_sheet(
        "Inventory"
    )

    print(
        f"Final Inventory rows: "
        f"{len(inventory)}"
    )

    # --------------------------------------------------------
    # KEY SETS
    # --------------------------------------------------------

    july_keys = set(
        july["_Key"]
    )

    august_keys = set(
        august["_Key"]
    )

    final_keys = set(
        inventory["_Key"]
    )

    union_keys = (
        july_keys |
        august_keys
    )

    # --------------------------------------------------------
    # DIFFERENCES
    # --------------------------------------------------------

    final_only_keys = (
        final_keys -
        union_keys
    )

    missing_final_keys = (
        union_keys -
        final_keys
    )

    july_only_keys = (
        july_keys -
        august_keys
    )

    august_only_keys = (
        august_keys -
        july_keys
    )

    # --------------------------------------------------------
    # EXTRACT RECORDS
    # --------------------------------------------------------

    final_only = inventory[
        inventory["_Key"].isin(
            final_only_keys
        )
    ].copy()

    missing_from_final = pd.concat(
        [
            july[
                july["_Key"].isin(
                    missing_final_keys
                )
            ],
            august[
                august["_Key"].isin(
                    missing_final_keys
                )
            ]
        ],
        ignore_index=True
    )

    july_only = july[
        july["_Key"].isin(
            july_only_keys
        )
    ].copy()

    august_only = august[
        august["_Key"].isin(
            august_only_keys
        )
    ].copy()

    # ========================================================
    # BASIC COUNTS
    # ========================================================

    print("\n" + "=" * 70)
    print("DIFFERENCE COUNTS")
    print("=" * 70)

    print(
        f"\nFinal-only: "
        f"{len(final_only_keys)}"
    )

    print(
        f"Missing from final: "
        f"{len(missing_final_keys)}"
    )

    print(
        f"July-only: "
        f"{len(july_only_keys)}"
    )

    print(
        f"August-only: "
        f"{len(august_only_keys)}"
    )

    # ========================================================
    # ANALYSIS 1 — BLANK STORAGE LOCATION
    # ========================================================

    print("\n" + "=" * 70)
    print("FINAL-ONLY STORAGE LOCATION")
    print("=" * 70)

    blank_storage = (
        final_only[
            "Storage Location"
        ] == ""
    )

    print(
        f"\nBlank Storage Location: "
        f"{blank_storage.sum()}"
    )

    print(
        f"Non-blank Storage Location: "
        f"{(~blank_storage).sum()}"
    )

    # ========================================================
    # ANALYSIS 2 — PLANT
    # ========================================================

    print("\n" + "=" * 70)
    print("FINAL-ONLY PLANT")
    print("=" * 70)

    print(
        final_only[
            "Plant"
        ]
        .value_counts()
        .head(20)
        .to_string()
    )

    # ========================================================
    # ANALYSIS 3 — RI
    # ========================================================

    if "RI Ind" in final_only.columns:

        print("\n" + "=" * 70)
        print("FINAL-ONLY RI")
        print("=" * 70)

        print(
            final_only[
                "RI Ind"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    # ========================================================
    # ANALYSIS 4 — CAPITAL
    # ========================================================

    if "Capital Ind" in final_only.columns:

        print("\n" + "=" * 70)
        print("FINAL-ONLY CAPITAL")
        print("=" * 70)

        print(
            final_only[
                "Capital Ind"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    # ========================================================
    # ANALYSIS 5 — QUANTITY PATTERN
    # ========================================================

    print("\n" + "=" * 70)
    print("FINAL-ONLY QUANTITY PATTERN")
    print("=" * 70)

    if (
        "Inve Prev Quantity"
        in final_only.columns
        and
        "Inve Pres Quantity"
        in final_only.columns
    ):

        prev_zero = (
            pd.to_numeric(
                final_only[
                    "Inve Prev Quantity"
                ],
                errors="coerce"
            ).fillna(0) == 0
        )

        pres_zero = (
            pd.to_numeric(
                final_only[
                    "Inve Pres Quantity"
                ],
                errors="coerce"
            ).fillna(0) == 0
        )

        print(
            "\nPrevious = 0 AND Present > 0:"
        )

        print(
            (
                prev_zero &
                (~pres_zero)
            ).sum()
        )

        print(
            "\nPrevious = 0 AND Present = 0:"
        )

        print(
            (
                prev_zero &
                pres_zero
            ).sum()
        )

    # ========================================================
    # ANALYSIS 6 — MATERIAL CODES
    # ========================================================

    print("\n" + "=" * 70)
    print("FINAL-ONLY MATERIAL ANALYSIS")
    print("=" * 70)

    material_counts = (
        final_only[
            "Material Code"
        ]
        .value_counts()
    )

    print(
        "\nFinal-only records per material:"
    )

    print(
        material_counts
        .head(30)
        .to_string()
    )

    # ========================================================
    # ANALYSIS 7 — DO FINAL-ONLY MATERIALS EXIST
    #                 IN MONTHLY DATA?
    # ========================================================

    july_materials = set(
        july["Material Code"]
    )

    august_materials = set(
        august["Material Code"]
    )

    final_only[
        "_Material_Exists_In_July"
    ] = final_only[
        "Material Code"
    ].isin(
        july_materials
    )

    final_only[
        "_Material_Exists_In_August"
    ] = final_only[
        "Material Code"
    ].isin(
        august_materials
    )

    print("\n" + "=" * 70)
    print(
        "FINAL-ONLY MATERIAL EXISTENCE"
    )
    print("=" * 70)

    print(
        "\nMaterial exists in July:"
    )

    print(
        final_only[
            "_Material_Exists_In_July"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nMaterial exists in August:"
    )

    print(
        final_only[
            "_Material_Exists_In_August"
        ]
        .value_counts()
        .to_string()
    )

    # ========================================================
    # ANALYSIS 8 — EXAMPLE FINAL-ONLY RECORDS
    # ========================================================

    print("\n" + "=" * 70)
    print("FIRST 30 FINAL-ONLY RECORDS")
    print("=" * 70)

    display_columns = [
        "Mat Grp",
        "Mat Grp Desc",
        "Material Code",
        "Material Code Desc",
        "Storage Location",
        "Storage Location Desc",
        "Plant",
        "Inve Prev Quantity",
        "Inve Prev Value",
        "Inve Pres Quantity",
        "Inve Pres Value",
        "UOM",
        "RI Ind",
        "Capital Ind",
        "_Key",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in final_only.columns
    ]

    print(
        final_only[
            display_columns
        ]
        .head(30)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # SAVE ONLY SMALL DATASETS
    # ========================================================

    print("\n" + "=" * 70)
    print("SAVING SMALL INVESTIGATION FILE")
    print("=" * 70)

    summary = pd.DataFrame(
        {
            "Metric": [
                "July rows",
                "August rows",
                "Final Inventory rows",
                "July unique keys",
                "August unique keys",
                "July + August unique keys",
                "Final unique keys",
                "Final-only keys",
                "Missing from Final",
                "July-only",
                "August-only",
                "Final-only blank storage",
                "Final-only nonblank storage",
            ],
            "Value": [
                len(july),
                len(august),
                len(inventory),
                len(july_keys),
                len(august_keys),
                len(union_keys),
                len(final_keys),
                len(final_only_keys),
                len(missing_final_keys),
                len(july_only_keys),
                len(august_only_keys),
                int(blank_storage.sum()),
                int((~blank_storage).sum()),
            ],
        }
    )

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:

        summary.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

        final_only.to_excel(
            writer,
            sheet_name="Final_Only",
            index=False
        )

        missing_from_final.to_excel(
            writer,
            sheet_name="Missing_Final",
            index=False
        )

        july_only.to_excel(
            writer,
            sheet_name="July_Only",
            index=False
        )

        august_only.to_excel(
            writer,
            sheet_name="August_Only",
            index=False
        )

    print(
        f"\nSaved investigation file:\n"
        f"{OUTPUT_FILE}"
    )

    print("\n" + "=" * 70)
    print("STEP 4B COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()