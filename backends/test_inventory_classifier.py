import pandas as pd
import tempfile
from pathlib import Path

from app.services.inventory_classifier import classify_inventory


def create_reference_files(temp_dir: Path):

    ri_file = temp_dir / "RI.xlsx"
    capital_file = temp_dir / "Capital.xlsx"

    pd.DataFrame({
        "Material Code": [
            "RI001",
            "RI002",
            "12345",
            "BOTH001",
        ]
    }).to_excel(
        ri_file,
        index=False
    )

    pd.DataFrame({
        "Material Code": [
            "CAP001",
            "CAP002",
            "67890",
            "BOTH001",
        ]
    }).to_excel(
        capital_file,
        index=False
    )

    return ri_file, capital_file


def main():

    print("=" * 70)
    print("BSP RI / CAPITAL CLASSIFIER TEST")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_dir = Path(temp_dir)

        ri_file, capital_file = create_reference_files(
            temp_dir
        )

        inventory = pd.DataFrame({
            "Material Code": [
                "RI001",
                "CAP001",
                "NORMAL001",
                "BOTH001",
                "12345.0",
                "",
            ]
        })

        result, summary = classify_inventory(
            inventory,
            ri_file=ri_file,
            capital_file=capital_file,
        )

        print()
        print("Classification results:")
        print(
            result[
                [
                    "Material Code",
                    "Inventory_Type",
                    "Classification_Reason",
                ]
            ].to_string(index=False)
        )

        print()
        print("Summary:")
        print(summary)

        classifications = dict(
            zip(
                result["Material Code"],
                result["Inventory_Type"]
            )
        )

        assert classifications["RI001"] == "RI"
        assert classifications["CAP001"] == "Capital"
        assert classifications["NORMAL001"] == "Normal"
        assert classifications["BOTH001"] == "CONFLICT"
        assert classifications["12345.0"] == "RI"
        assert classifications[""] == "UNCLASSIFIED"

        assert summary["reference_files_available"] is True

        print()
        print("=" * 70)
        print("ALL RI / CAPITAL CLASSIFIER TESTS PASSED")
        print("=" * 70)


if __name__ == "__main__":
    main()