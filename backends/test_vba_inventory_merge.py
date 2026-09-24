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

REFERENCE_FILE = SAMPLES_DIR / "Final output file.xlsx"

OUTPUT_FILE = (
    REPORT_DIR /
    "python_vba_inventory_merge_test.xlsx"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_value(value):
    """
    Equivalent to the VBA:

        Trim(...)

    for key handling.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_dataframe(df):

    df = df.copy()

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# LOAD SHEET 2
# ============================================================

def load_sheet2(file_path):

    df = pd.read_excel(
        file_path,
        sheet_name="Sheet2"
    )

    df = normalize_dataframe(df)

    required_columns = [
        "Concatenate",
        "Mat Grp",
        "Mat Grp Desc",
        "Material Code",
        "Material Code Desc",
        "Storage Location",
        "Storage Location Desc",
        "Plant",
        "UOM",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{file_path.name} is missing columns:\n"
            f"{missing}\n\n"
            f"Available columns:\n"
            f"{list(df.columns)}"
        )

    return df


# ============================================================
# LOAD REFERENCE INVENTORY
# ============================================================

def load_reference_inventory():

    df = pd.read_excel(
        REFERENCE_FILE,
        sheet_name="Inventory",
        header=1
    )

    df = normalize_dataframe(df)

    return df


# ============================================================
# PYTHON VERSION OF VBA GENERATEINVENTORY
# ============================================================

def generate_inventory(
    previous_df,
    present_df
):
    """
    Python implementation of the employee VBA:

        Sub GenerateInventory()

    Important:
    The VBA uses column A / Concatenate as the dictionary key.
    """

    inventory = {}

    # ========================================================
    # LOAD PREVIOUS INVENTORY
    # ========================================================

    for _, row in previous_df.iterrows():

        key = normalize_value(
            row["Concatenate"]
        )

        # VBA:
        #
        # If key <> "" Then
        #

        if key == "":
            continue

        # VBA stores:
        #
        # columns B:J
        # plus UOM
        #

        inventory[key] = {
            "Mat Grp":
                row["Mat Grp"],

            "Mat Grp Desc":
                row["Mat Grp Desc"],

            "Material Code":
                row["Material Code"],

            "Material Code Desc":
                row["Material Code Desc"],

            "Storage Location":
                row["Storage Location"],

            "Storage Location Desc":
                row["Storage Location Desc"],

            "Plant":
                row["Plant"],

            "Prev Qty":
                row["Inve Prev Quantity"],

            "Prev Value":
                row["Inve Prev Value"],

            "UOM":
                row["UOM"],

            "Pres Qty":
                "",

            "Pres Value":
                "",

            "Pres UOM":
                "",
        }

    # ========================================================
    # MERGE PRESENT INVENTORY
    # ========================================================

    for _, row in present_df.iterrows():

        key = normalize_value(
            row["Concatenate"]
        )

        if key == "":
            continue

        # ====================================================
        # EXISTING KEY
        # ====================================================

        if key in inventory:

            inventory[key]["Pres Qty"] = (
                row["Inve Pres Quantity"]
                if "Inve Pres Quantity" in row.index
                else row.get(
                    "Inve Prev Quantity",
                    ""
                )
            )

            inventory[key]["Pres Value"] = (
                row["Inve Pres Value"]
                if "Inve Pres Value" in row.index
                else row.get(
                    "Inve Prev Value",
                    ""
                )
            )

            inventory[key]["Pres UOM"] = (
                row["UOM"]
            )

        # ====================================================
        # NEW KEY
        # ====================================================

        else:

            inventory[key] = {
                "Mat Grp":
                    row["Mat Grp"],

                "Mat Grp Desc":
                    row["Mat Grp Desc"],

                "Material Code":
                    row["Material Code"],

                "Material Code Desc":
                    row["Material Code Desc"],

                "Storage Location":
                    row["Storage Location"],

                "Storage Location Desc":
                    row["Storage Location Desc"],

                "Plant":
                    row["Plant"],

                "Prev Qty":
                    "",

                "Prev Value":
                    "",

                "UOM":
                    row["UOM"],

                "Pres Qty":
                    row["Inve Pres Quantity"]
                    if "Inve Pres Quantity" in row.index
                    else row.get(
                        "Inve Prev Quantity",
                        ""
                    ),

                "Pres Value":
                    row["Inve Pres Value"]
                    if "Inve Pres Value" in row.index
                    else row.get(
                        "Inve Prev Value",
                        ""
                    ),

                "Pres UOM":
                    row["UOM"],
            }

    # ========================================================
    # CONVERT DICTIONARY TO DATAFRAME
    # ========================================================

    rows = []

    for key, values in inventory.items():

        rows.append(
            {
                "Concatenate":
                    key,

                **values,
            }
        )

    result = pd.DataFrame(
        rows
    )

    return result


# ============================================================
# COMPARE WITH REFERENCE
# ============================================================

def compare_with_reference(
    generated,
    reference
):
    print("\n" + "=" * 70)
    print("COMPARING PYTHON OUTPUT WITH EMPLOYEE FINAL INVENTORY")
    print("=" * 70)

    print(
        f"\nPython rows: {len(generated)}"
    )

    print(
        f"Reference rows: {len(reference)}"
    )

    # ========================================================
    # RECONSTRUCT VBA KEY IN FINAL WORKBOOK
    # ========================================================
    #
    # The employee's VBA used column A = Concatenate.
    #
    # The final workbook no longer contains that column,
    # so reconstruct it from:
    #
    # Plant + Material Code + Storage Location
    #
    # This matches the Concatenate formula used earlier.
    # ========================================================

    def build_final_key(row):

        plant = normalize_value(
            row["Plant"]
        )

        material_code = normalize_value(
            row["Material Code"]
        )

        storage_location = normalize_value(
            row["Storage Location"]
        )

        return (
            plant
            + material_code
            + storage_location
        )

    reference = reference.copy()

    reference["_VBA_Key"] = reference.apply(
        build_final_key,
        axis=1
    )

    generated = generated.copy()

    generated["_VBA_Key"] = (
        generated["Concatenate"]
        .apply(normalize_value)
    )

    # ========================================================
    # KEY COMPARISON
    # ========================================================

    generated_keys = set(
        generated["_VBA_Key"]
    )

    reference_keys = set(
        reference["_VBA_Key"]
    )

    common_keys = (
        generated_keys &
        reference_keys
    )

    python_only = (
        generated_keys -
        reference_keys
    )

    reference_only = (
        reference_keys -
        generated_keys
    )

    print(
        f"\nPython unique keys: "
        f"{len(generated_keys)}"
    )

    print(
        f"Reference unique keys: "
        f"{len(reference_keys)}"
    )

    print(
        f"Common keys: "
        f"{len(common_keys)}"
    )

    print(
        f"Python-only keys: "
        f"{len(python_only)}"
    )

    print(
        f"Reference-only keys: "
        f"{len(reference_only)}"
    )

    # ========================================================
    # SHOW KEY DIFFERENCES
    # ========================================================

    if python_only:

        print(
            "\nFirst 20 Python-only keys:"
        )

        for key in list(
            python_only
        )[:20]:

            print(
                f"  {key}"
            )

    if reference_only:

        print(
            "\nFirst 20 Reference-only keys:"
        )

        for key in list(
            reference_only
        )[:20]:

            print(
                f"  {key}"
            )

    # ========================================================
    # CELL COMPARISON
    # ========================================================

    if (
        not python_only
        and
        not reference_only
    ):

        print(
            "\nAll keys match."
        )

        generated_compare = (
            generated
            .set_index("_VBA_Key")
            .sort_index()
        )

        reference_compare = (
            reference
            .set_index("_VBA_Key")
            .sort_index()
        )

        # ----------------------------------------------------
        # Map Python names to final workbook names
        # ----------------------------------------------------

        column_mapping = {
            "Mat Grp":
                "Mat Grp",

            "Mat Grp Desc":
                "Mat Grp Desc",

            "Material Code":
                "Material Code",

            "Material Code Desc":
                "Matrial Code Desc",

            "Storage Location":
                "Storage Location",

            "Storage Location Desc":
                "Storage Location Desc",

            "Plant":
                "Plant",

            "Prev Qty":
                "Inve Prev Quantity",

            "Prev Value":
                "Inve Prev Value",

            "Pres Qty":
                "Inve Pres Quantity",

            "Pres Value":
                "Inve Pres Value",

            "UOM":
                "UOM",
        }

        python_columns = []
        reference_columns = []

        for python_column, reference_column in (
            column_mapping.items()
        ):

            if (
                python_column
                in generated_compare.columns
                and
                reference_column
                in reference_compare.columns
            ):

                python_columns.append(
                    python_column
                )

                reference_columns.append(
                    reference_column
                )

        generated_compare = (
            generated_compare[
                python_columns
            ]
        )

        reference_compare = (
            reference_compare[
                reference_columns
            ]
        )

        # Make both use identical column names
        generated_compare.columns = (
            reference_columns
        )

        # ----------------------------------------------------
        # Normalize values
        # ----------------------------------------------------

        generated_compare = (
            generated_compare
            .fillna("")
            .astype(str)
        )

        reference_compare = (
            reference_compare
            .fillna("")
            .astype(str)
        )

        # ----------------------------------------------------
        # Compare
        # ----------------------------------------------------

        differences = (
            generated_compare
            !=
            reference_compare
        )

        total_differences = (
            differences
            .sum()
            .sum()
        )

        print(
            f"\nColumns compared: "
            f"{len(reference_columns)}"
        )

        print(
            f"Total cell differences: "
            f"{total_differences}"
        )

        if total_differences == 0:

            print(
                "\n" + "=" * 70
            )

            print(
                "SUCCESS!"
            )

            print(
                "Python VBA merge exactly matches "
                "the employee final Inventory."
            )

            print(
                "=" * 70
            )

        else:

            print(
                "\nWARNING:"
            )

            print(
                "Keys match, but some values differ."
            )

            print(
                "\nDifferences by column:"
            )

            difference_counts = (
                differences
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            print(
                difference_counts[
                    difference_counts > 0
                ]
                .to_string()
            )

            # ------------------------------------------------
            # First 20 differences
            # ------------------------------------------------

            print(
                "\nFirst 20 cell differences:"
            )

            diff_rows = []

            for key in generated_compare.index:

                for column in reference_columns:

                    python_value = (
                        generated_compare
                        .loc[key, column]
                    )

                    reference_value = (
                        reference_compare
                        .loc[key, column]
                    )

                    if (
                        python_value
                        !=
                        reference_value
                    ):

                        diff_rows.append(
                            {
                                "Key":
                                    key,

                                "Column":
                                    column,

                                "Python":
                                    python_value,

                                "Reference":
                                    reference_value,
                            }
                        )

                    if len(diff_rows) >= 20:
                        break

                if len(diff_rows) >= 20:
                    break

            if diff_rows:

                print(
                    pd.DataFrame(
                        diff_rows
                    ).to_string(
                        index=False
                    )
                )

    return {
        "python_rows":
            len(generated),

        "reference_rows":
            len(reference),

        "python_keys":
            len(generated_keys),

        "reference_keys":
            len(reference_keys),

        "common_keys":
            len(common_keys),

        "python_only":
            len(python_only),

        "reference_only":
            len(reference_only),
    }

    # --------------------------------------------------------
    # KEY COMPARISON
    # --------------------------------------------------------

    generated_keys = set(
        generated["Concatenate"]
        .apply(normalize_value)
    )

    reference_keys = set(
        reference["Concatenate"]
        .apply(normalize_value)
    )

    common_keys = (
        generated_keys &
        reference_keys
    )

    python_only = (
        generated_keys -
        reference_keys
    )

    reference_only = (
        reference_keys -
        generated_keys
    )

    print(
        f"\nPython unique keys: "
        f"{len(generated_keys)}"
    )

    print(
        f"Reference unique keys: "
        f"{len(reference_keys)}"
    )

    print(
        f"Common keys: "
        f"{len(common_keys)}"
    )

    print(
        f"Python-only keys: "
        f"{len(python_only)}"
    )

    print(
        f"Reference-only keys: "
        f"{len(reference_only)}"
    )

    # --------------------------------------------------------
    # CELL COMPARISON
    # --------------------------------------------------------

    if (
        len(python_only) == 0
        and
        len(reference_only) == 0
    ):

        generated_compare = (
            generated
            .set_index("Concatenate")
            .sort_index()
        )

        reference_compare = (
            reference
            .set_index("Concatenate")
            .sort_index()
        )

        common_columns = [
            column
            for column in generated_compare.columns
            if column in reference_compare.columns
        ]

        generated_compare = (
            generated_compare[
                common_columns
            ]
        )

        reference_compare = (
            reference_compare[
                common_columns
            ]
        )

        # Normalize NaN / blank
        generated_compare = (
            generated_compare
            .fillna("")
        )

        reference_compare = (
            reference_compare
            .fillna("")
        )

        generated_compare = (
            generated_compare
            .astype(str)
        )

        reference_compare = (
            reference_compare
            .astype(str)
        )

        differences = (
            generated_compare
            != reference_compare
        )

        total_differences = (
            differences.sum().sum()
        )

        print(
            f"\nColumns compared: "
            f"{len(common_columns)}"
        )

        print(
            f"Total cell differences: "
            f"{total_differences}"
        )

        if total_differences == 0:

            print(
                "\nSUCCESS!"
            )

            print(
                "Python merge matches the "
                "employee VBA output."
            )

        else:

            print(
                "\nWARNING!"
            )

            print(
                "Keys match, but some cell "
                "values are different."
            )

            print(
                "\nDifferences by column:"
            )

            difference_counts = (
                differences.sum()
                .sort_values(
                    ascending=False
                )
            )

            print(
                difference_counts[
                    difference_counts > 0
                ]
                .to_string()
            )

            # Show first few differences
            print(
                "\nFirst 20 differences:"
            )

            diff_rows = []

            for key in generated_compare.index:

                for column in common_columns:

                    generated_value = (
                        generated_compare
                        .loc[key, column]
                    )

                    reference_value = (
                        reference_compare
                        .loc[key, column]
                    )

                    if (
                        generated_value
                        !=
                        reference_value
                    ):

                        diff_rows.append(
                            {
                                "Concatenate":
                                    key,

                                "Column":
                                    column,

                                "Python":
                                    generated_value,

                                "Reference":
                                    reference_value,
                            }
                        )

                    if len(diff_rows) >= 20:
                        break

                if len(diff_rows) >= 20:
                    break

            if diff_rows:

                print(
                    pd.DataFrame(
                        diff_rows
                    ).to_string(
                        index=False
                    )
                )

    else:

        print(
            "\nWARNING:"
        )

        print(
            "Python and reference do not "
            "contain the same keys."
        )

        if python_only:

            print(
                "\nFirst Python-only keys:"
            )

            print(
                list(
                    python_only
                )[:20]
            )

        if reference_only:

            print(
                "\nFirst Reference-only keys:"
            )

            print(
                list(
                    reference_only
                )[:20]
            )

    return {
        "python_rows":
            len(generated),

        "reference_rows":
            len(reference),

        "python_keys":
            len(generated_keys),

        "reference_keys":
            len(reference_keys),

        "common_keys":
            len(common_keys),

        "python_only":
            len(python_only),

        "reference_only":
            len(reference_only),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("STEP 5A - VBA → PYTHON INVENTORY MERGE TEST")
    print("=" * 70)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # LOAD JULY
    # --------------------------------------------------------

    print("\nLoading July Sheet 2...")

    july = load_sheet2(
        JULY_FILE
    )

    print(
        f"July rows: {len(july)}"
    )

    # --------------------------------------------------------
    # LOAD AUGUST
    # --------------------------------------------------------

    print("\nLoading August Sheet 2...")

    august = load_sheet2(
        AUGUST_FILE
    )

    print(
        f"August rows: {len(august)}"
    )

    # --------------------------------------------------------
    # RENAME CURRENT COLUMNS
    # --------------------------------------------------------

    august = august.rename(
        columns={
            "Inve Prev Quantity":
                "Inve Pres Quantity",

            "Inve Prev Value":
                "Inve Pres Value",
        }
    )

    # --------------------------------------------------------
    # GENERATE INVENTORY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("GENERATING INVENTORY")
    print("=" * 70)

    generated = generate_inventory(
        july,
        august
    )

    print(
        f"\nGenerated rows: "
        f"{len(generated)}"
    )

    # --------------------------------------------------------
    # LOAD EMPLOYEE OUTPUT
    # --------------------------------------------------------

    print("\nLoading employee Inventory sheet...")

    reference = load_reference_inventory()

    print(
        f"Reference rows: "
        f"{len(reference)}"
    )

    # --------------------------------------------------------
    # COMPARE
    # --------------------------------------------------------

    result = compare_with_reference(
        generated,
        reference
    )

    # --------------------------------------------------------
    # SAVE SMALL GENERATED RESULT
    # --------------------------------------------------------

    generated.to_excel(
        OUTPUT_FILE,
        sheet_name="Python_Output",
        index=False
    )

    print(
        f"\nPython output saved to:"
    )

    print(
        OUTPUT_FILE
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("STEP 5A SUMMARY")
    print("=" * 70)

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )

    print("\n" + "=" * 70)
    print("STEP 5A COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()