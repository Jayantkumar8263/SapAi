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


# ============================================================
# HELPERS
# ============================================================

def normalize_value(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        try:
            number = float(text)
            if number.is_integer():
                return str(int(number))
        except Exception:
            pass

    return text


def build_vba_key(row):
    plant = normalize_value(row["Plant"])
    material = normalize_value(row["Material Code"])
    storage = normalize_value(row["Storage Location"])

    return plant + material + storage


def load_sheet2(path):
    df = pd.read_excel(
        path,
        sheet_name="Sheet2"
    )

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# START
# ============================================================

print("=" * 70)
print("STEP 5C - TRACE VBA MERGE MISMATCHES")
print("=" * 70)


# ============================================================
# LOAD JULY
# ============================================================

print("\nLoading July Sheet 2...")

july = load_sheet2(JULY_FILE)

print(f"July rows: {len(july)}")


# ============================================================
# LOAD AUGUST
# ============================================================

print("\nLoading August Sheet 2...")

august = load_sheet2(AUGUST_FILE)

print(f"August rows: {len(august)}")


# ============================================================
# LOAD EMPLOYEE FINAL INVENTORY
# ============================================================

print("\nLoading employee final Inventory...")

reference = pd.read_excel(
    FINAL_FILE,
    sheet_name="Inventory",
    header=1
)

reference.columns = [
    str(column).strip()
    for column in reference.columns
]

print(f"Reference rows: {len(reference)}")


# ============================================================
# BUILD KEYS
# ============================================================

print("\nBuilding keys...")

july["_VBA_Key"] = july["Concatenate"].apply(
    normalize_value
)

august["_VBA_Key"] = august["Concatenate"].apply(
    normalize_value
)

reference["_VBA_Key"] = reference.apply(
    build_vba_key,
    axis=1
)


# ============================================================
# KEY SETS
# ============================================================

july_keys = set(
    july["_VBA_Key"]
)

august_keys = set(
    august["_VBA_Key"]
)

python_keys = (
    july_keys |
    august_keys
)

reference_keys = set(
    reference["_VBA_Key"]
)

python_only = sorted(
    python_keys - reference_keys
)

reference_only = sorted(
    reference_keys - python_keys
)


print("\n" + "=" * 70)
print("KEY SUMMARY")
print("=" * 70)

print(f"\nJuly unique keys:       {len(july_keys)}")
print(f"August unique keys:     {len(august_keys)}")
print(f"Python union keys:      {len(python_keys)}")
print(f"Reference keys:         {len(reference_keys)}")
print(f"Common keys:            {len(python_keys & reference_keys)}")
print(f"Python-only:            {len(python_only)}")
print(f"Reference-only:         {len(reference_only)}")


# ============================================================
# CREATE SOURCE LOOKUPS
# ============================================================

july_by_key = (
    july
    .drop_duplicates("_VBA_Key")
    .set_index("_VBA_Key")
)

august_by_key = (
    august
    .drop_duplicates("_VBA_Key")
    .set_index("_VBA_Key")
)

reference_by_key = (
    reference
    .drop_duplicates("_VBA_Key")
    .set_index("_VBA_Key")
)


# ============================================================
# MATERIAL CODE LOOKUPS
# ============================================================

july_by_material = (
    july
    .assign(
        _Material_Code=july["Material Code"]
        .apply(normalize_value)
    )
)

august_by_material = (
    august
    .assign(
        _Material_Code=august["Material Code"]
        .apply(normalize_value)
    )
)

reference_by_material = (
    reference
    .assign(
        _Material_Code=reference["Material Code"]
        .apply(normalize_value)
    )
)


# ============================================================
# TRACE PYTHON-ONLY
# ============================================================

print("\n" + "=" * 70)
print("TRACING PYTHON-ONLY RECORDS")
print("=" * 70)


python_trace = []

for key in python_only:

    source_rows = []

    if key in july_by_key.index:
        row = july_by_key.loc[key]

        source_rows.append({
            "Source": "July",
            "Plant": normalize_value(
                row["Plant"]
            ),
            "Material_Code": normalize_value(
                row["Material Code"]
            ),
            "Storage_Location": normalize_value(
                row["Storage Location"]
            ),
            "Material_Description": normalize_value(
                row["Material Code Desc"]
            ),
            "Mat_Grp": normalize_value(
                row["Mat Grp"]
            ),
        })

    if key in august_by_key.index:
        row = august_by_key.loc[key]

        source_rows.append({
            "Source": "August",
            "Plant": normalize_value(
                row["Plant"]
            ),
            "Material_Code": normalize_value(
                row["Material Code"]
            ),
            "Storage_Location": normalize_value(
                row["Storage Location"]
            ),
            "Material_Description": normalize_value(
                row["Material Code Desc"]
            ),
            "Mat_Grp": normalize_value(
                row["Mat Grp"]
            ),
        })

    for source in source_rows:

        material = source["Material_Code"]

        # Find same material in employee reference
        matching_reference = reference_by_material[
            reference_by_material["_Material_Code"]
            == material
        ]

        reference_storage = []

        for _, ref_row in matching_reference.iterrows():

            reference_storage.append(
                normalize_value(
                    ref_row["Storage Location"]
                )
            )

        python_trace.append({
            "Python_Key": key,
            "Source": source["Source"],
            "Plant": source["Plant"],
            "Material_Code": material,
            "Python_Storage": source[
                "Storage_Location"
            ],
            "Reference_Storages_For_Material": " | ".join(
                sorted(set(reference_storage))
            ),
            "Material_Description": source[
                "Material_Description"
            ],
            "Mat_Grp": source["Mat_Grp"],
        })


python_trace_df = pd.DataFrame(
    python_trace
)


# ============================================================
# TRACE REFERENCE-ONLY
# ============================================================

print("\n" + "=" * 70)
print("TRACING REFERENCE-ONLY RECORDS")
print("=" * 70)


reference_trace = []

for key in reference_only:

    if key not in reference_by_key.index:
        continue

    row = reference_by_key.loc[key]

    material = normalize_value(
        row["Material Code"]
    )

    # Find same material in July
    july_matches = july_by_material[
        july_by_material["_Material_Code"]
        == material
    ]

    # Find same material in August
    august_matches = august_by_material[
        august_by_material["_Material_Code"]
        == material
    ]

    july_storages = sorted(
        set(
            july_matches["Storage Location"]
            .apply(normalize_value)
        )
    )

    august_storages = sorted(
        set(
            august_matches["Storage Location"]
            .apply(normalize_value)
        )
    )

    reference_trace.append({
        "Reference_Key": key,
        "Plant": normalize_value(
            row["Plant"]
        ),
        "Material_Code": material,
        "Reference_Storage": normalize_value(
            row["Storage Location"]
        ),
        "July_Storages_For_Material": " | ".join(
            july_storages
        ),
        "August_Storages_For_Material": " | ".join(
            august_storages
        ),
        "Material_Description": normalize_value(
            row["Matrial Code Desc"]
        ),
        "Mat_Grp": normalize_value(
            row["Mat Grp"]
        ),
    })


reference_trace_df = pd.DataFrame(
    reference_trace
)


# ============================================================
# PRINT IMPORTANT EXAMPLES
# ============================================================

print("\n" + "=" * 70)
print("PYTHON-ONLY TRACE - FIRST 30")
print("=" * 70)

if len(python_trace_df) > 0:

    print(
        python_trace_df
        .head(30)
        .to_string(index=False)
    )

else:

    print("No Python-only records.")


print("\n" + "=" * 70)
print("REFERENCE-ONLY TRACE - FIRST 30")
print("=" * 70)

if len(reference_trace_df) > 0:

    print(
        reference_trace_df
        .head(30)
        .to_string(index=False)
    )

else:

    print("No reference-only records.")


# ============================================================
# CLASSIFY MISMATCHES
# ============================================================

print("\n" + "=" * 70)
print("MISMATCH CLASSIFICATION")
print("=" * 70)


# ------------------------------------------------------------
# Python-only records where same material exists in reference
# ------------------------------------------------------------

python_same_material_count = 0

for _, row in python_trace_df.iterrows():

    reference_storages = str(
        row["Reference_Storages_For_Material"]
    )

    if reference_storages.strip():
        python_same_material_count += 1


# ------------------------------------------------------------
# Reference-only records where same material exists in source
# ------------------------------------------------------------

reference_same_material_count = 0

for _, row in reference_trace_df.iterrows():

    july_storages = str(
        row["July_Storages_For_Material"]
    )

    august_storages = str(
        row["August_Storages_For_Material"]
    )

    if (
        july_storages.strip()
        or august_storages.strip()
    ):
        reference_same_material_count += 1


print(
    "\nPython-only records whose material exists "
    "in employee Inventory:"
)

print(
    python_same_material_count
)


print(
    "\nReference-only records whose material exists "
    "in July/August Sheet2:"
)

print(
    reference_same_material_count
)


# ============================================================
# SAVE COMPLETE DIAGNOSTIC
# ============================================================

OUTPUT_FILE = (
    REPORT_DIR /
    "vba_merge_mismatch_trace.xlsx"
)


with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="openpyxl"
) as writer:

    python_trace_df.to_excel(
        writer,
        sheet_name="Python Only Trace",
        index=False
    )

    reference_trace_df.to_excel(
        writer,
        sheet_name="Reference Only Trace",
        index=False
    )


print("\n" + "=" * 70)
print("STEP 5C COMPLETE")
print("=" * 70)

print(
    f"\nDiagnostic saved to:\n{OUTPUT_FILE}"
)