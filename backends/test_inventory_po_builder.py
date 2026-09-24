from pathlib import Path

import pandas as pd
import pytest

from app.services.inventory_po_builder import (
    build_inventory_po,
    combine_spool_txt_files,
    normalize_sap_date,
    read_spool_txt,
)


ROOT = Path(
    __file__
).resolve().parent


def test_normalize_sap_date():

    assert (
        normalize_sap_date(
            "24.09.2026"
        )
        == "20260924"
    )

    assert (
        normalize_sap_date(
            "24/09/2026"
        )
        == "20260924"
    )

    assert (
        normalize_sap_date(
            "2026-09-24"
        )
        == "20260924"
    )

    assert (
        normalize_sap_date(
            "20260924"
        )
        == "20260924"
    )

    assert (
        normalize_sap_date("")
        == ""
    )


def test_read_spool_txt():

    file = (
        ROOT
        / "_test_spool_read.txt"
    )

    try:

        file.write_text(
            "Material\tQuantity\tDate\n"
            "15111201000046\t10\t24.09.2026\n",
            encoding="utf-8",
        )

        df = read_spool_txt(
            file
        )

        assert list(
            df.columns
        ) == [
            "Material",
            "Quantity",
            "Date",
        ]

        assert len(df) == 1

        assert (
            df.loc[
                0,
                "Material",
            ]
            == "15111201000046"
        )

    finally:

        file.unlink(
            missing_ok=True
        )


def test_combine_spool_files():

    file1 = (
        ROOT
        / "_spool_001.txt"
    )

    file2 = (
        ROOT
        / "_spool_002.txt"
    )

    try:

        file1.write_text(
            "Material\tQuantity\tDate\n"
            "100\t10\t24.09.2026\n",
            encoding="utf-8",
        )

        file2.write_text(
            "Material\tQuantity\tDate\n"
            "200\t20\t25.09.2026\n",
            encoding="utf-8",
        )

        df = combine_spool_txt_files(
            [
                file1,
                file2,
            ]
        )

        assert len(df) == 2

        assert (
            df.loc[
                0,
                "Material",
            ]
            == "100"
        )

        assert (
            df.loc[
                1,
                "Material",
            ]
            == "200"
        )

    finally:

        file1.unlink(
            missing_ok=True
        )

        file2.unlink(
            missing_ok=True
        )


def test_build_inventory_po():

    file1 = (
        ROOT
        / "_po_001.txt"
    )

    file2 = (
        ROOT
        / "_po_002.txt"
    )

    output = (
        ROOT
        / "_Inventory_PO.xlsx"
    )

    try:

        file1.write_text(
            "Material\tQuantity\tDate\n"
            "100\t10\t24.09.2026\n",
            encoding="utf-8",
        )

        file2.write_text(
            "Material\tQuantity\tDate\n"
            "200\t20\t25.09.2026\n",
            encoding="utf-8",
        )

        result = build_inventory_po(
            [
                file1,
                file2,
            ],
            output,
            date_columns=[
                "Date"
            ],
        )

        assert (
            result
            == str(output)
        )

        assert output.exists()

        df = pd.read_excel(
            output,
            sheet_name="Inventory PO",
            dtype=str,
        )

        assert len(df) == 2

        assert (
            df.loc[
                0,
                "Date",
            ]
            == "20260924"
        )

        assert (
            df.loc[
                1,
                "Date",
            ]
            == "20260925"
        )

    finally:

        file1.unlink(
            missing_ok=True
        )

        file2.unlink(
            missing_ok=True
        )

        output.unlink(
            missing_ok=True
        )


def test_different_spool_structures_fail():

    file1 = (
        ROOT
        / "_bad_spool_001.txt"
    )

    file2 = (
        ROOT
        / "_bad_spool_002.txt"
    )

    try:

        file1.write_text(
            "Material\tQuantity\n"
            "100\t10\n",
            encoding="utf-8",
        )

        file2.write_text(
            "Material\tQuantity\tDate\n"
            "200\t20\t25.09.2026\n",
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError
        ):

            combine_spool_txt_files(
                [
                    file1,
                    file2,
                ]
            )

    finally:

        file1.unlink(
            missing_ok=True
        )

        file2.unlink(
            missing_ok=True
        )