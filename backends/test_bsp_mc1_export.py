from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.services.bsp_mc1_export import clean_mc1_sheet1, clean_mc1_workbook
from app.services.sap_excel_adapter import load_sap_mc1_raw, load_and_adapt_sap_mc1


def sample_raw():
    return pd.DataFrame({
        "Material Group": ["151 Material Group Description"],
        "Material": ["15111201000046 Example Material"],
        "Storage Location": ["1000UP03     Storage Location"],
        "Val. stock": [12.5],
        "ValStckVal": [1000.0],
        "Val. stock.1": ["EA"],
    })


def main():
    cleaned = clean_mc1_sheet1(sample_raw())
    row = cleaned.iloc[0]
    assert row["Mat Grp"] == "151"
    assert row["Mat Grp Desc"] == "Material Group Description"
    assert row["Material Code"] == "15111201000046"
    assert row["Material Code Desc"] == "Example Material"
    assert row["Plant"] == "1000"
    assert row["Storage Location"] == "UP03"
    assert row["Storage Location Desc"] == "Storage Location"
    assert row["Concatenate"] == "100015111201000046UP03"

    temp = ROOT / "_test_mc1_raw.xlsx"
    cleaned_path = ROOT / "_test_mc1_cleaned.xlsx"
    try:
        with pd.ExcelWriter(temp, engine="openpyxl") as writer:
            sample_raw().to_excel(writer, sheet_name="Sheet1", index=False)
        raw_loaded = load_sap_mc1_raw(temp)
        assert str(int(raw_loaded.iloc[0]["Material Code"])) == "15111201000046"
        adapted = load_and_adapt_sap_mc1(temp)
        assert adapted.iloc[0]["Inventory_Key"] == "100015111201000046UP03"
        assert adapted.iloc[0]["Quantity"] == 12.5
        assert adapted.iloc[0]["Unit"] == "EA"

        output = clean_mc1_workbook(temp, cleaned_path)
        assert output.exists()
        assert "Sheet1" in pd.ExcelFile(output).sheet_names
        assert "Sheet2" in pd.ExcelFile(output).sheet_names

        # Existing Sheet2-style workbooks must remain compatible.
        sheet2_path = ROOT / "_test_mc1_sheet2.xlsx"
        with pd.ExcelWriter(sheet2_path, engine="openpyxl") as writer:
            cleaned.to_excel(writer, sheet_name="Sheet2", index=False)
        try:
            sheet2_loaded = load_sap_mc1_raw(sheet2_path)
            assert str(int(sheet2_loaded.iloc[0]["Material Code"])) == "15111201000046"
        finally:
            sheet2_path.unlink(missing_ok=True)
    finally:
        import gc
        import time

    # Release any remaining Python references to
    # pandas/openpyxl workbook objects.
        gc.collect()

    # Windows can take a short moment to release
    # the underlying file handle.
        if cleaned_path.exists():
            for attempt in range(5):
                try:
                    cleaned_path.unlink()
                    break
                except PermissionError:
                    if attempt == 4:
                        raise

                    time.sleep(0.2)
    print("BSP MC.1 raw Sheet1 -> Sheet2 tests passed")
    print("SAP Excel adapter raw/Sheet2 compatibility tests passed")


if __name__ == "__main__":
    main()
