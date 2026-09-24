"""
Tests for MC.1 Export Manager.

Run:

    python -m pytest -q test_mc1_export_manager.py
"""

from pathlib import Path

import pandas as pd

from app.services.mc1_export_manager import (
    MC1ExportManager,
)


ROOT = Path(
    __file__
).resolve().parent


def make_raw_mc1(
    path: Path,
):
    """
    Create a realistic small raw MC.1 workbook.
    """

    df = pd.DataFrame(
        {
            "Material Group": [
                "151 KILNS"
            ],
            "Material": [
                "15111201000046 TENSION PULLEY"
            ],
            "Storage location": [
                "1000UP03"
            ],
            "Val. stock": [
                10
            ],
            "ValStckVal": [
                1500
            ],
            "Val. stock.1": [
                "EA"
            ],
        }
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Sheet1",
            index=False,
        )


def test_validate_raw_mc1():

    source = (
        ROOT
        / "_test_manager_raw.xlsx"
    )

    try:

        make_raw_mc1(
            source
        )

        result = (
            MC1ExportManager.validate_file(
                source
            )
        )

        assert result["valid"] is True
        assert result["format"] == "raw_mc1"
        assert result["sheet"] == "Sheet1"

    finally:

        source.unlink(
            missing_ok=True
        )


def test_process_previous_export():

    source = (
        ROOT
        / "_test_manager_previous.xlsx"
    )

    output_dir = (
        ROOT
        / "_test_manager_output"
    )

    try:

        make_raw_mc1(
            source
        )

        manager = MC1ExportManager(
            output_dir
        )

        result = manager.process_export(
            source,
            "previous",
        )

        assert result["success"] is True
        assert result["period"] == "previous"
        assert result["rows"] == 1
        assert result[
            "unique_material_codes"
        ] == 1

        output_file = Path(
            result["standardized_file"]
        )

        assert output_file.exists()

        df = pd.read_excel(
            output_file,
            sheet_name="Inventory",
        )

        assert len(df) == 1

        assert (
            str(
                int(
                    df.loc[
                        0,
                        "Material_Code",
                    ]
                )
            )
            == "15111201000046"
        )

        assert (
            df.loc[
                0,
                "Inventory_Key",
            ]
            == "100015111201000046UP03"
        )

    finally:

        source.unlink(
            missing_ok=True
        )

        output_file = (
            output_dir
            / "mc1_previous_standardized.xlsx"
        )

        output_file.unlink(
            missing_ok=True
        )

        try:
            output_dir.rmdir()
        except OSError:
            pass


def test_process_current_export():

    source = (
        ROOT
        / "_test_manager_current.xlsx"
    )

    output_dir = (
        ROOT
        / "_test_manager_current_output"
    )

    try:

        make_raw_mc1(
            source
        )

        manager = MC1ExportManager(
            output_dir
        )

        result = manager.process_export(
            source,
            "current",
        )

        assert result["success"] is True
        assert result["period"] == "current"
        assert result["rows"] == 1

        output_file = Path(
            result["standardized_file"]
        )

        assert output_file.exists()

    finally:

        source.unlink(
            missing_ok=True
        )

        output_file = (
            output_dir
            / "mc1_current_standardized.xlsx"
        )

        output_file.unlink(
            missing_ok=True
        )

        try:
            output_dir.rmdir()
        except OSError:
            pass


def test_invalid_file():

    result = (
        MC1ExportManager.validate_file(
            ROOT
            / "does_not_exist.xlsx"
        )
    )

    assert result["valid"] is False


def test_both_periods():

    previous = (
        ROOT
        / "_test_manager_previous2.xlsx"
    )

    current = (
        ROOT
        / "_test_manager_current2.xlsx"
    )

    output_dir = (
        ROOT
        / "_test_manager_both_output"
    )

    try:

        make_raw_mc1(
            previous
        )

        make_raw_mc1(
            current
        )

        manager = MC1ExportManager(
            output_dir
        )

        result = (
            manager.process_previous_and_current(
                previous,
                current,
            )
        )

        assert result["success"] is True

        assert (
            result["previous"]["period"]
            == "previous"
        )

        assert (
            result["current"]["period"]
            == "current"
        )

        assert Path(
            result["previous"][
                "standardized_file"
            ]
        ).exists()

        assert Path(
            result["current"][
                "standardized_file"
            ]
        ).exists()

    finally:

        previous.unlink(
            missing_ok=True
        )

        current.unlink(
            missing_ok=True
        )

        for filename in [
            "mc1_previous_standardized.xlsx",
            "mc1_current_standardized.xlsx",
        ]:

            (
                output_dir
                / filename
            ).unlink(
                missing_ok=True
            )

        try:
            output_dir.rmdir()
        except OSError:
            pass