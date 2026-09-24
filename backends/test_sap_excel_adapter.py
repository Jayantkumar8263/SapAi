"""
End-to-end test for the MC.1 raw Excel
-> Sheet2 -> SapAi adapter path.

Run from:

    SapAi\\backends

Commands:

    python test_bsp_mc1_export.py

or:

    python -m pytest -q test_bsp_mc1_export.py
"""

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(
    __file__
).resolve().parent


sys.path.insert(
    0,
    str(ROOT)
)


from app.services.bsp_mc1_export import (
    clean_mc1_sheet1,
    clean_mc1_workbook,
)


from app.services.sap_excel_adapter import (
    load_sap_mc1_raw,
    load_and_adapt_sap_mc1,
)


def sample_raw():

    return pd.DataFrame(
        {
            "Material Group": [
                "151 Material Group Description"
            ],

            "Material": [
                "15111201000046 Example Material"
            ],

            "Storage Location": [
                "1000UP03     Storage Location"
            ],

            "Val. stock": [
                12.5
            ],

            "ValStckVal": [
                1000.0
            ],

            "Val. stock.1": [
                "EA"
            ],
        }
    )


def test_raw_cleaning_logic():

    cleaned = clean_mc1_sheet1(
        sample_raw()
    )

    row = cleaned.iloc[0]

    assert (
        row["Mat Grp"]
        == "151"
    )

    assert (
        row["Mat Grp Desc"]
        == "Material Group Description"
    )

    assert (
        row["Material Code"]
        == "15111201000046"
    )

    assert (
        row["Material Code Desc"]
        == "Example Material"
    )

    assert (
        row["Plant"]
        == "1000"
    )

    assert (
        row["Storage Location"]
        == "UP03"
    )

    assert (
        row["Storage Location Desc"]
        == "Storage Location"
    )

    assert (
        row["Concatenate"]
        == "100015111201000046UP03"
    )


def test_raw_one_sheet_adapter():

    temp = (
        ROOT
        / "_test_mc1_raw.xlsx"
    )

    try:

        with pd.ExcelWriter(
            temp,
            engine="openpyxl",
        ) as writer:

            sample_raw().to_excel(
                writer,
                sheet_name="Sheet1",
                index=False,
            )

        raw_loaded = load_sap_mc1_raw(
            temp
        )

        assert (
            str(
                int(
                    raw_loaded.iloc[0][
                        "Material Code"
                    ]
                )
            )
            == "15111201000046"
        )

        adapted = load_and_adapt_sap_mc1(
            temp
        )

        assert (
            adapted.iloc[0][
                "Inventory_Key"
            ]
            == "100015111201000046UP03"
        )

        assert (
            adapted.iloc[0][
                "Quantity"
            ]
            == 12.5
        )

        assert (
            adapted.iloc[0][
                "Unit"
            ]
            == "EA"
        )

    finally:

        temp.unlink(
            missing_ok=True
        )


def test_cleaned_two_sheet_workbook():

    temp = (
        ROOT
        / "_test_mc1_cleaned.xlsx"
    )

    try:

        with pd.ExcelWriter(
            temp,
            engine="openpyxl",
        ) as writer:

            sample_raw().to_excel(
                writer,
                sheet_name="Sheet1",
                index=False,
            )

            clean_mc1_sheet1(
                sample_raw()
            ).to_excel(
                writer,
                sheet_name="Sheet2",
                index=False,
            )

        raw_loaded = load_sap_mc1_raw(
            temp
        )

        assert (
    str(
        int(
            raw_loaded.iloc[0][
                "Material Code"
            ]
        )
    )
    == "15111201000046"
)

        adapted = load_and_adapt_sap_mc1(
            temp
        )

        assert (
            adapted.iloc[0][
                "Inventory_Key"
            ]
            == "100015111201000046UP03"
        )

    finally:

        temp.unlink(
            missing_ok=True
        )


def test_clean_mc1_workbook_output():

    source = (
        ROOT
        / "_test_mc1_source.xlsx"
    )

    output = (
        ROOT
        / "_test_mc1_output.xlsx"
    )

    try:

        with pd.ExcelWriter(
            source,
            engine="openpyxl",
        ) as writer:

            sample_raw().to_excel(
                writer,
                sheet_name="Sheet1",
                index=False,
            )

        result = clean_mc1_workbook(
            source,
            output,
        )

        assert result.exists()

        with pd.ExcelFile(
            result,
            engine="openpyxl",
        ) as excel_file:

            assert (
                "Sheet1"
                in excel_file.sheet_names
            )

            assert (
                "Sheet2"
                in excel_file.sheet_names
            )

    finally:

        source.unlink(
            missing_ok=True
        )

        output.unlink(
            missing_ok=True
        )


if __name__ == "__main__":

    tests = [
        test_raw_cleaning_logic,
        test_raw_one_sheet_adapter,
        test_cleaned_two_sheet_workbook,
        test_clean_mc1_workbook_output,
    ]

    print("=" * 70)
    print("SapAi BSP MC.1 Export Tests")
    print("=" * 70)

    for test in tests:

        test()

        print(
            f"PASS: {test.__name__}"
        )

    print("=" * 70)
    print("ALL BSP MC.1 EXPORT TESTS PASSED")
    print("=" * 70)