from pathlib import Path

import pandas as pd
import pytest

from app.services.zmat_fund_popr_batcher import (
    create_material_batches,
    extract_unique_material_codes,
    prepare_zmat_fund_popr_batches,
    save_material_batches,
)


ROOT = Path(
    __file__
).resolve().parent


def test_extract_unique_material_codes():

    df = pd.DataFrame(
        {
            "Material Code": [
                "15111201000046",
                "15111201000046",
                "20112301000119",
                "20112301000610",
                None,
                "",
                20212401000028.0,
            ]
        }
    )

    codes = (
        extract_unique_material_codes(
            df
        )
    )

    assert codes == [
        "15111201000046",
        "20112301000119",
        "20112301000610",
        "20212401000028",
    ]


def test_create_material_batches():

    codes = [
        f"M{i:05d}"
        for i in range(45_000)
    ]

    batches = (
        create_material_batches(
            codes,
            batch_size=20_000,
        )
    )

    assert len(batches) == 3

    assert len(
        batches[0]
    ) == 20_000

    assert len(
        batches[1]
    ) == 20_000

    assert len(
        batches[2]
    ) == 5_000

    # ---------------------------------------------------------
    # Nothing lost
    # ---------------------------------------------------------

    flattened = [
        code
        for batch in batches
        for code in batch
    ]

    assert flattened == codes


def test_prepare_zmat_fund_popr_batches():

    df = pd.DataFrame(
        {
            "Material Code": [
                "100",
                "100",
                "200",
                "300",
                "400",
            ]
        }
    )

    result = (
        prepare_zmat_fund_popr_batches(
            df,
            batch_size=2,
        )
    )

    assert result["success"] is True

    assert (
        result["total_input_rows"]
        == 5
    )

    assert (
        result["unique_material_codes"]
        == 4
    )

    assert (
        result["batch_size"]
        == 2
    )

    assert (
        result["batch_count"]
        == 2
    )

    assert result["batches"] == [
        [
            "100",
            "200",
        ],
        [
            "300",
            "400",
        ],
    ]


def test_save_material_batches():

    output_directory = (
        ROOT
        / "_test_zmat_batches"
    )

    batches = [
        [
            "100",
            "200",
        ],
        [
            "300",
        ],
    ]

    try:

        files = (
            save_material_batches(
                batches,
                output_directory,
            )
        )

        assert len(files) == 2

        first = Path(
            files[0]
        )

        second = Path(
            files[1]
        )

        assert first.exists()
        assert second.exists()

        assert (
            first.read_text(
                encoding="utf-8"
            )
            == "100\n200"
        )

        assert (
            second.read_text(
                encoding="utf-8"
            )
            == "300"
        )

    finally:

        if output_directory.exists():

            for file in (
                output_directory.iterdir()
            ):

                file.unlink(
                    missing_ok=True
                )

            output_directory.rmdir()


def test_invalid_batch_size():

    with pytest.raises(
        ValueError
    ):

        create_material_batches(
            ["100"],
            batch_size=0,
        )