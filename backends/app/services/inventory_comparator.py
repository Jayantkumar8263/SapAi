from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = [
    "Material_Code",
    "Material_Name",
    "Quantity",
    "Unit",
    "Plant",
]


def read_inventory_file(file_path: str) -> pd.DataFrame:
    """Read and clean one inventory Excel file."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    df = pd.read_excel(file_path)

    # Remove completely empty rows/columns
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    # Standardize column names
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )

    # Check required columns
    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    # Clean text fields
    text_columns = [
        "Material_Code",
        "Material_Name",
        "Unit",
        "Plant",
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # Quantity must be numeric
    df["Quantity"] = pd.to_numeric(
        df["Quantity"],
        errors="coerce"
    )

    # Remove invalid rows
    df = df.dropna(
        subset=[
            "Material_Code",
            "Quantity",
            "Plant",
        ]
    )

    return df.reset_index(drop=True)


def create_inventory_key(df: pd.DataFrame) -> pd.DataFrame:
    """Create a unique key for inventory comparison."""

    df = df.copy()

    if "Storage_Location" in df.columns:

        df["Storage_Location"] = (
            df["Storage_Location"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["Inventory_Key"] = (
            df["Plant"]
            + "_"
            + df["Material_Code"]
            + "_"
            + df["Storage_Location"]
        )

    else:

        df["Inventory_Key"] = (
            df["Plant"]
            + "_"
            + df["Material_Code"]
        )

    return df


def compare_inventory(
    previous_file: str,
    current_file: str
):
    """
    Compare previous-month inventory with current-month inventory.
    """

    print("\n" + "=" * 60)
    print("BSP INVENTORY COMPARISON")
    print("=" * 60)

    # ---------------------------------------------------------
    # READ FILES
    # ---------------------------------------------------------

    print("\nReading previous month inventory...")
    previous_df = read_inventory_file(previous_file)

    print(
        f"Previous month records: "
        f"{len(previous_df)}"
    )

    print("\nReading current month inventory...")
    current_df = read_inventory_file(current_file)

    print(
        f"Current month records: "
        f"{len(current_df)}"
    )

    # ---------------------------------------------------------
    # CREATE KEYS
    # ---------------------------------------------------------

    previous_df = create_inventory_key(previous_df)
    current_df = create_inventory_key(current_df)

    # ---------------------------------------------------------
    # RENAME QUANTITY COLUMNS
    # ---------------------------------------------------------

    previous_df = previous_df.rename(
        columns={
            "Quantity": "Previous_Quantity"
        }
    )

    current_df = current_df.rename(
        columns={
            "Quantity": "Current_Quantity"
        }
    )

    # ---------------------------------------------------------
    # MERGE PREVIOUS + CURRENT
    # ---------------------------------------------------------

    print("\nCombining previous and current inventory...")

    comparison = pd.merge(
        previous_df[
            [
                "Inventory_Key",
                "Material_Code",
                "Material_Name",
                "Previous_Quantity",
                "Unit",
                "Plant",
            ]
        ],
        current_df[
            [
                "Inventory_Key",
                "Material_Code",
                "Material_Name",
                "Current_Quantity",
                "Unit",
                "Plant",
            ]
        ],
        on="Inventory_Key",
        how="outer",
        suffixes=("_Previous", "_Current"),
        indicator=True,
    )

    # ---------------------------------------------------------
    # HANDLE MATERIAL INFORMATION
    # ---------------------------------------------------------

    comparison["Material_Code"] = (
        comparison["Material_Code_Previous"]
        .fillna(
            comparison["Material_Code_Current"]
        )
    )

    comparison["Material_Name"] = (
        comparison["Material_Name_Previous"]
        .fillna(
            comparison["Material_Name_Current"]
        )
    )

    comparison["Unit"] = (
        comparison["Unit_Previous"]
        .fillna(
            comparison["Unit_Current"]
        )
    )

    comparison["Plant"] = (
        comparison["Plant_Previous"]
        .fillna(
            comparison["Plant_Current"]
        )
    )

    # ---------------------------------------------------------
    # FILL MISSING QUANTITIES
    # ---------------------------------------------------------

    comparison["Previous_Quantity"] = (
        comparison["Previous_Quantity"]
        .fillna(0)
    )

    comparison["Current_Quantity"] = (
        comparison["Current_Quantity"]
        .fillna(0)
    )

    # ---------------------------------------------------------
    # CALCULATE CHANGE
    # ---------------------------------------------------------

    comparison["Quantity_Change"] = (
        comparison["Current_Quantity"]
        - comparison["Previous_Quantity"]
    )

    # ---------------------------------------------------------
    # CLASSIFY RECORD
    # ---------------------------------------------------------

    comparison["Status"] = comparison["_merge"].map(
        {
            "both": "Existing",
            "left_only": "Removed",
            "right_only": "New",
        }
    )

    # ---------------------------------------------------------
    # SELECT FINAL COLUMNS
    # ---------------------------------------------------------

    comparison = comparison[
        [
            "Inventory_Key",
            "Material_Code",
            "Material_Name",
            "Previous_Quantity",
            "Current_Quantity",
            "Quantity_Change",
            "Unit",
            "Plant",
            "Status",
        ]
    ]

    comparison = comparison.sort_values(
        by=["Plant", "Material_Code"]
    )

    comparison = comparison.reset_index(
        drop=True
    )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    summary = {
        "previous_records": len(previous_df),
        "current_records": len(current_df),
        "combined_records": len(comparison),
        "new_materials": int(
            (comparison["Status"] == "New").sum()
        ),
        "removed_materials": int(
            (comparison["Status"] == "Removed").sum()
        ),
        "existing_materials": int(
            (comparison["Status"] == "Existing").sum()
        ),
        "total_previous_quantity": float(
            comparison["Previous_Quantity"].sum()
        ),
        "total_current_quantity": float(
            comparison["Current_Quantity"].sum()
        ),
        "total_quantity_change": float(
            comparison["Quantity_Change"].sum()
        ),
    }

    # ---------------------------------------------------------
    # DISPLAY
    # ---------------------------------------------------------

    print("\n" + "-" * 60)
    print("INVENTORY COMPARISON")
    print("-" * 60)

    print(comparison.to_string(index=False))

    print("\n" + "-" * 60)
    print("COMPARISON SUMMARY")
    print("-" * 60)

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("COMPARISON COMPLETED")
    print("=" * 60)

    return comparison, summary


if __name__ == "__main__":

    project_root = Path(__file__).resolve().parents[3]

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

    comparison, summary = compare_inventory(
        str(previous_file),
        str(current_file)
    )