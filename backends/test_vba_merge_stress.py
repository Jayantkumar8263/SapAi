"""
Stress test for the Python equivalent of BSP's VBA GenerateInventory.

The tests are based directly on the documented VBA business rules.

Run:
    python test_vba_merge_stress.py
"""

from __future__ import annotations

import pandas as pd


def normalize_key(value) -> str:
    """Equivalent to VBA Trim(ws.Cells(i, 1).Value)."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def generate_inventory_python(
    previous: pd.DataFrame,
    current: pd.DataFrame,
) -> pd.DataFrame:
    """
    Python equivalent of the employee VBA GenerateInventory macro.

    Expected input columns:
        Concatenate
        Mat Grp
        Mat Grp Desc
        Material Code
        Material Code Desc
        Storage Location
        Storage Location Desc
        Plant
        Prev Qty
        Prev Value
        UOM

    Current uses:
        Pres Qty
        Pres Value
        UOM
    """

    previous = previous.copy()
    current = current.copy()

    previous["Concatenate"] = previous["Concatenate"].apply(normalize_key)
    current["Concatenate"] = current["Concatenate"].apply(normalize_key)

    result = {}

    # ---------------------------------------------------------
    # VBA:
    # For i = 2 To lastPrev
    #     key = Trim(...)
    #     If key <> "" Then
    #         dict.Add key, arr
    # ---------------------------------------------------------

    for _, row in previous.iterrows():

        key = normalize_key(row["Concatenate"])

        if key == "":
            continue

        # IMPORTANT:
        # VBA Dictionary.Add raises an error on duplicate keys.
        if key in result:
            raise ValueError(
                f"Duplicate previous key detected: {key}"
            )

        result[key] = {
            "Mat Grp": row["Mat Grp"],
            "Mat Grp Desc": row["Mat Grp Desc"],
            "Material Code": row["Material Code"],
            "Material Code Desc": row["Material Code Desc"],
            "Storage Location": row["Storage Location"],
            "Storage Location Desc": row["Storage Location Desc"],
            "Plant": row["Plant"],
            "Prev Qty": row["Prev Qty"],
            "Prev Value": row["Prev Value"],
            "UOM": row["UOM"],
            "Pres Qty": "",
            "Pres Value": "",
            "Pres UOM": "",
        }

    # ---------------------------------------------------------
    # VBA:
    # For i = 2 To lastPres
    #     key = Trim(...)
    #     If dict.Exists(key) Then
    #         update current fields
    #     Else
    #         add new current-only record
    # ---------------------------------------------------------

    for _, row in current.iterrows():

        key = normalize_key(row["Concatenate"])

        if key == "":
            continue

        if key in result:

            result[key]["Pres Qty"] = row["Pres Qty"]
            result[key]["Pres Value"] = row["Pres Value"]
            result[key]["Pres UOM"] = row["Pres UOM"]

        else:

            result[key] = {
                "Mat Grp": row["Mat Grp"],
                "Mat Grp Desc": row["Mat Grp Desc"],
                "Material Code": row["Material Code"],
                "Material Code Desc": row["Material Code Desc"],
                "Storage Location": row["Storage Location"],
                "Storage Location Desc": row["Storage Location Desc"],
                "Plant": row["Plant"],
                "Prev Qty": "",
                "Prev Value": "",
                "UOM": "",
                "Pres Qty": row["Pres Qty"],
                "Pres Value": row["Pres Value"],
                "Pres UOM": row["Pres UOM"],
            }

    rows = []

    for key, values in result.items():

        rows.append({
            "Concatenate": key,
            **values,
        })

    return pd.DataFrame(rows)


def base_row(
    key,
    material="MAT001",
    storage="UP03",
    plant="1000",
    prev_qty=100,
    prev_value=1000,
    uom="EA",
):
    return {
        "Concatenate": key,
        "Mat Grp": "151",
        "Mat Grp Desc": "Test Material Group",
        "Material Code": material,
        "Material Code Desc": "Test Material",
        "Storage Location": storage,
        "Storage Location Desc": "Test Storage",
        "Plant": plant,
        "Prev Qty": prev_qty,
        "Prev Value": prev_value,
        "UOM": uom,
    }


def current_row(
    key,
    material="MAT001",
    storage="UP03",
    plant="1000",
    qty=120,
    value=1200,
    uom="EA",
):
    return {
        "Concatenate": key,
        "Mat Grp": "151",
        "Mat Grp Desc": "Test Material Group",
        "Material Code": material,
        "Material Code Desc": "Test Material",
        "Storage Location": storage,
        "Storage Location Desc": "Test Storage",
        "Plant": plant,
        "Pres Qty": qty,
        "Pres Value": value,
        "Pres UOM": uom,
    }


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(
            f"{message}\nExpected: {expected}\nActual: {actual}"
        )


def test_1_same_key_updates_current():

    previous = pd.DataFrame([
        base_row(
            "1000MAT001UP03",
            prev_qty=100,
            prev_value=1000,
        )
    ])

    current = pd.DataFrame([
        current_row(
            "1000MAT001UP03",
            qty=120,
            value=1200,
        )
    ])

    result = generate_inventory_python(previous, current)

    assert_equal(len(result), 1, "Same key should create one row")

    row = result.iloc[0]

    assert_equal(row["Prev Qty"], 100, "Previous quantity incorrect")
    assert_equal(row["Prev Value"], 1000, "Previous value incorrect")
    assert_equal(row["Pres Qty"], 120, "Current quantity incorrect")
    assert_equal(row["Pres Value"], 1200, "Current value incorrect")

    print("PASS 1: Same key → previous + current combined")


def test_2_current_only():

    previous = pd.DataFrame([
        base_row(
            "1000MAT001UP03",
            prev_qty=100,
            prev_value=1000,
        )
    ])

    current = pd.DataFrame([
        current_row(
            "1000MAT001UP03",
            qty=120,
            value=1200,
        ),
        current_row(
            "1000MAT002UP04",
            material="MAT002",
            storage="UP04",
            qty=50,
            value=500,
        ),
    ])

    result = generate_inventory_python(previous, current)

    assert_equal(
        len(result),
        2,
        "Current-only key should be added",
    )

    row = result[
        result["Concatenate"] == "1000MAT002UP04"
    ].iloc[0]

    assert_equal(
        row["Prev Qty"],
        "",
        "Current-only record should have blank previous quantity",
    )

    assert_equal(
        row["Pres Qty"],
        50,
        "Current-only record should contain current quantity",
    )

    print("PASS 2: Current-only key → added with blank previous fields")


def test_3_previous_only():

    previous = pd.DataFrame([
        base_row(
            "1000MAT001UP03",
            prev_qty=100,
            prev_value=1000,
        ),
        base_row(
            "1000MAT002UP04",
            material="MAT002",
            storage="UP04",
            prev_qty=80,
            prev_value=800,
        ),
    ])

    current = pd.DataFrame([
        current_row(
            "1000MAT001UP03",
            qty=120,
            value=1200,
        )
    ])

    result = generate_inventory_python(previous, current)

    assert_equal(
        len(result),
        2,
        "Previous-only key should remain",
    )

    row = result[
        result["Concatenate"] == "1000MAT002UP04"
    ].iloc[0]

    assert_equal(
        row["Prev Qty"],
        80,
        "Previous-only record should preserve previous quantity",
    )

    assert_equal(
        row["Pres Qty"],
        "",
        "Previous-only record should have blank current quantity",
    )

    print("PASS 3: Previous-only key → retained with blank current fields")


def test_4_different_storage_locations():

    previous = pd.DataFrame([
        base_row(
            "1000MAT001UP03",
            storage="UP03",
            prev_qty=100,
        ),
        base_row(
            "1000MAT001UP04",
            storage="UP04",
            prev_qty=200,
        ),
    ])

    current = pd.DataFrame([
        current_row(
            "1000MAT001UP03",
            storage="UP03",
            qty=110,
        ),
        current_row(
            "1000MAT001UP04",
            storage="UP04",
            qty=220,
        ),
    ])

    result = generate_inventory_python(previous, current)

    assert_equal(
        len(result),
        2,
        "Same material in different storage locations must remain separate",
    )

    keys = set(result["Concatenate"])

    assert_equal(
        keys,
        {
            "1000MAT001UP03",
            "1000MAT001UP04",
        },
        "Storage-location keys were incorrectly merged",
    )

    print("PASS 4: Same material + different storage → separate records")


def test_5_blank_key_is_ignored():

    previous = pd.DataFrame([
        base_row(""),
        base_row("1000MAT001UP03"),
    ])

    current = pd.DataFrame([
        current_row(""),
        current_row("1000MAT001UP03"),
    ])

    result = generate_inventory_python(previous, current)

    assert_equal(
        len(result),
        1,
        "Blank Concatenate keys should be ignored",
    )

    assert_equal(
        result.iloc[0]["Concatenate"],
        "1000MAT001UP03",
        "Wrong key survived",
    )

    print("PASS 5: Blank keys → ignored")


def test_6_trim_key():

    previous = pd.DataFrame([
        base_row("   1000MAT001UP03   ")
    ])

    current = pd.DataFrame([
        current_row("1000MAT001UP03", qty=150)
    ])

    result = generate_inventory_python(previous, current)

    assert_equal(
        len(result),
        1,
        "Trimmed key should match current key",
    )

    row = result.iloc[0]

    assert_equal(
        row["Concatenate"],
        "1000MAT001UP03",
        "Key was not trimmed like VBA",
    )

    assert_equal(
        row["Pres Qty"],
        150,
        "Current record did not update trimmed key",
    )

    print("PASS 6: Key whitespace → handled like VBA Trim")


def test_7_duplicate_previous_key_raises_error():

    previous = pd.DataFrame([
        base_row("1000MAT001UP03", prev_qty=100),
        base_row("1000MAT001UP03", prev_qty=200),
    ])

    current = pd.DataFrame(columns=[
    "Concatenate",
    "Mat Grp",
    "Mat Grp Desc",
    "Material Code",
    "Material Code Desc",
    "Storage Location",
    "Storage Location Desc",
    "Plant",
    "Pres Qty",
    "Pres Value",
    "Pres UOM",
    ])

    try:
        generate_inventory_python(previous, current)

    except ValueError as exc:

        assert "Duplicate previous key" in str(exc)

        print(
            "PASS 7: Duplicate previous key → error, "
            "matching VBA Dictionary.Add behavior"
        )

        return

    raise AssertionError(
        "Duplicate previous key should raise an error"
    )


def run_all_tests():

    print("=" * 70)
    print("BSP VBA → Python Inventory Merge Stress Test")
    print("=" * 70)
    print()

    tests = [
        test_1_same_key_updates_current,
        test_2_current_only,
        test_3_previous_only,
        test_4_different_storage_locations,
        test_5_blank_key_is_ignored,
        test_6_trim_key,
        test_7_duplicate_previous_key_raises_error,
    ]

    for test in tests:
        test()

    print()
    print("=" * 70)
    print("ALL STRESS TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()