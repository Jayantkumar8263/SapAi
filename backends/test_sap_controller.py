from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController


def main():

    print("=" * 60)
    print("SapAi SAP Controller Test")
    print("=" * 60)

    # =========================================================
    # CREATE MOCK SAP
    # =========================================================

    client = MockSAPClient()

    # =========================================================
    # CREATE CONTROLLER
    # =========================================================

    controller = SAPController(client)

    # =========================================================
    # CONNECT
    # =========================================================

    print("\n1. Connecting to SAP...")

    result = controller.connect()

    print(result)

    assert result["success"] is True

    # =========================================================
    # SESSION
    # =========================================================

    print("\n2. Getting session information...")

    session = controller.get_session_info()

    print(session)

    assert session["system"] == "MOCK_SAP"

    # =========================================================
    # TRANSACTION
    # =========================================================

    print("\n3. Starting MC.1...")

    result = controller.start_transaction(
        "MC.1"
    )

    print(result)

    assert result["success"] is True

    # =========================================================
    # PLANT
    # =========================================================

    print("\n4. Setting plant...")

    result = controller.set_text(
        "txt_PLANT",
        "Bhilai",
    )

    print(result)

    assert result["success"] is True

    # =========================================================
    # PERIOD
    # =========================================================

    print("\n5. Setting period...")

    result = controller.set_text(
        "txt_PERIOD",
        "2026-09",
    )

    print(result)

    assert result["success"] is True

    # =========================================================
    # SCREEN
    # =========================================================

    print("\n6. Inspecting SAP screen...")

    screen = controller.inspect_screen()

    for control in screen:
        print(control)

    assert len(screen) > 0

    # =========================================================
    # EXECUTE
    # =========================================================

    print("\n7. Executing...")

    result = controller.press(
        "btn_EXECUTE"
    )

    print(result)

    assert result["success"] is True

    # =========================================================
    # SCREEN INFO
    # =========================================================

    print("\n8. Current screen...")

    screen_info = controller.get_screen_info()

    print(screen_info)

    # =========================================================
    # DISCONNECT
    # =========================================================

    print("\n9. Disconnecting...")

    controller.disconnect()

    print(
        "Controller attached:",
        controller.attached,
    )

    assert controller.attached is False

    # =========================================================
    # HISTORY
    # =========================================================

    print("\n10. SAP operation history...")

    for item in client.history:
        print("  >", item)

    print("\n" + "=" * 60)
    print("SAP CONTROLLER TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()