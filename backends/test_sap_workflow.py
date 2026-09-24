from app.agent.state import AgentState
from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController
from app.services.sap_workflow import SAPWorkflow


def main():

    print("=" * 60)
    print("SapAi MC.1 Workflow Test")
    print("=" * 60)

    # =========================================================
    # CREATE STATE
    # =========================================================

    state = AgentState(
        user_id="test_user",
        username="test_user",
        tcode="MC.1",
        variant="B002159",
        current_period="2026-09",
        plant="Bhilai",
    )

    print("\n1. AgentState created")

    print("T-Code:", state.tcode)
    print("Variant:", state.variant)
    print("Period:", state.current_period)
    print("Plant:", state.plant)

    # =========================================================
    # CREATE MOCK SAP
    # =========================================================

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    workflow = SAPWorkflow(
        state,
        controller,
    )

    # =========================================================
    # RUN MC.1
    # =========================================================

    print("\n2. Running MC.1 workflow...")

    result = workflow.run_mc1()

    print("\nWorkflow result:")

    print(result)

    # =========================================================
    # VALIDATION
    # =========================================================

    print("\n3. Validating result...")

    assert result["success"] is True

    assert result["transaction"] == "MC.1"

    assert (
        result["parameters"]["variant"]
        == "B002159"
    )

    assert (
        result["parameters"]["current_period"]
        == "2026-09"
    )

    assert (
        result["parameters"]["plant"]
        == "Bhilai"
    )

    # =========================================================
    # SCREEN
    # =========================================================

    print("\n4. Final mock SAP screen:")

    for control in client.inspect_screen():
        print(control)

    # =========================================================
    # HISTORY
    # =========================================================

    print("\n5. SAP operation history:")

    for item in client.history:
        print("  >", item)

    # =========================================================
    # CLOSE
    # =========================================================

    print("\n6. Closing SAP connection...")

    workflow.close()

    assert client.connected is False

    print("Connected:", client.connected)

    # =========================================================
    # COMPLETE
    # =========================================================

    print("\n" + "=" * 60)
    print("MC.1 WORKFLOW TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()