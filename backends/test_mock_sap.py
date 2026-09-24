from app.services.mock_sap import MockSAPClient


def main():

    print("=" * 50)
    print("SapAi Mock SAP Test")
    print("=" * 50)

    sap = MockSAPClient()

    # ---------------------------------------------------------
    # 1. ATTACH
    # ---------------------------------------------------------

    print("\n1. Attaching...")

    result = sap.attach()

    print(result)

    # ---------------------------------------------------------
    # 2. START TRANSACTION
    # ---------------------------------------------------------

    print("\n2. Starting MC.1...")

    result = sap.start_transaction("MC.1")

    print(result)

    # ---------------------------------------------------------
    # 3. SET PLANT
    # ---------------------------------------------------------

    print("\n3. Setting plant...")

    result = sap.set_text(
        "txt_PLANT",
        "Bhilai",
    )

    print(result)

    # ---------------------------------------------------------
    # 4. SET PERIOD
    # ---------------------------------------------------------

    print("\n4. Setting period...")

    result = sap.set_text(
        "txt_PERIOD",
        "2026-09",
    )

    print(result)

    # ---------------------------------------------------------
    # 5. INSPECT SCREEN
    # ---------------------------------------------------------

    print("\n5. Inspecting screen...")

    screen = sap.inspect_screen()

    for control in screen:
        print(control)

    # ---------------------------------------------------------
    # 6. EXECUTE
    # ---------------------------------------------------------

    print("\n6. Pressing execute...")

    result = sap.press("btn_EXECUTE")

    print(result)

    # ---------------------------------------------------------
    # 7. SESSION INFO
    # ---------------------------------------------------------

    print("\n7. Session information...")

    print(sap.session_info())

    # ---------------------------------------------------------
    # 8. HISTORY
    # ---------------------------------------------------------

    print("\n8. Operation history...")

    for item in sap.history:
        print("  >", item)

    # ---------------------------------------------------------
    # 9. DETACH
    # ---------------------------------------------------------

    print("\n9. Detaching...")

    sap.detach()

    print("Connected:", sap.connected)

    print("\n" + "=" * 50)
    print("MOCK SAP TEST PASSED")
    print("=" * 50)


if __name__ == "__main__":
    main()