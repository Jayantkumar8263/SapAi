from pathlib import Path

from app.services.bsp_workbook_builder import build_bsp_workbook


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Change these filenames if you use different sample files.
PREVIOUS_FILE = DATA_DIR / "samples" / "Inventory Previous 07(month).xlsx"
PRESENT_FILE = DATA_DIR / "samples" / "Inventory Previous 25.08.xlsx"

# Your final output workbook contains the RI and Capital reference sheets.
REFERENCE_FILE = DATA_DIR / "samples" / "Final output file.xlsx"

OUTPUT_FILE = DATA_DIR / "reports" / "BSP_Automated_Inventory_Test.xlsx"


def main():
    print("=" * 70)
    print("BSP INVENTORY WORKBOOK BUILDER TEST")
    print("=" * 70)

    print("\nPrevious file:")
    print(PREVIOUS_FILE)

    print("\nPresent file:")
    print(PRESENT_FILE)

    print("\nReference file:")
    print(REFERENCE_FILE)

    print("\nOutput file:")
    print(OUTPUT_FILE)

    for file_path in [
        PREVIOUS_FILE,
        PRESENT_FILE,
        REFERENCE_FILE,
    ]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"\nFile not found:\n{file_path}"
                "\n\nPut the sample files inside:\n"
                f"{DATA_DIR / 'samples'}"
            )

    result = build_bsp_workbook(
        previous_file=PREVIOUS_FILE,
        present_file=PRESENT_FILE,
        reference_file=REFERENCE_FILE,
        output_file=OUTPUT_FILE,
    )

    print("\n" + "=" * 70)
    print("BUILD COMPLETED")
    print("=" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("\nGenerated file:")
    print(OUTPUT_FILE)

    print("\nBSP WORKBOOK BUILDER TEST PASSED")


if __name__ == "__main__":
    main()