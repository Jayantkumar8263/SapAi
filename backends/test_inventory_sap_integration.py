from app.agent.state import AgentState
from app.agent.workflow import InventoryWorkflow

from app.services.mock_sap import MockSAPClient
from app.services.sap_controller import SAPController


def main():

    print("=" * 65)
    print("SapAi Inventory + SAP Integration Test")
    print("=" * 65)

    # =========================================================
    # 1. CREATE AGENT STATE
    # =========================================================

    state = AgentState(
        user_id="integration_test",
        username="test_user",
        tcode="MC.1",
        variant="B002159",
        previous_period="2026-08",
        current_period="2026-09",
        plant="Bhilai",
    )

    print("\n1. AgentState")

    print("Run ID:", state.run_id)
    print("T-Code:", state.tcode)
    print("Variant:", state.variant)
    print("Previous Period:", state.previous_period)
    print("Current Period:", state.current_period)
    print("Plant:", state.plant)

    # =========================================================
    # 2. CREATE MOCK SAP
    # =========================================================

    print("\n2. Creating Mock SAP...")

    client = MockSAPClient()

    controller = SAPController(
        client
    )

    # =========================================================
    # 3. CREATE INVENTORY WORKFLOW
    # =========================================================

    print("\n3. Creating InventoryWorkflow...")

    workflow = InventoryWorkflow(
        state,
        controller,
    )

    # =========================================================
    # 4. RUN SAP MC.1
    # =========================================================

    print("\n4. Running SAP MC.1...")

    result = workflow.run_sap_mc1()

    print("\nSAP result:")

    print(result)

    # =========================================================
    # 5. VALIDATE
    # =========================================================

    print("\n5. Validating...")

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
    # 6. CHECK STATE
    # =========================================================

    print("\n6. Checking AgentState...")

    assert "sap_mc1" in state.results

    assert "sap_mc1" in state.metadata

    print("SAP result stored in state.results")

    print("SAP result stored in state.metadata")

    # =========================================================
    # 7. CHECK WORKFLOW STEP
    # =========================================================

    print("\n7. Workflow steps:")

    for step in state.steps:
        print(step)

    assert any(
        step.get("step") == "SAP MC.1"
        and step.get("status") == "completed"
        for step in state.steps
    )

    # =========================================================
    # 8. CHECK SAP HISTORY
    # =========================================================

    print("\n8. SAP operation history:")

    for item in client.history:
        print("  >", item)

    # =========================================================
    # 9. CHECK CONNECTION
    # =========================================================

    print("\n9. SAP connection status:")

    print(
        "Connected:",
        client.connected,
    )

    assert client.connected is False

    # =========================================================
    # SUCCESS
    # =========================================================

    print("\n" + "=" * 65)
    print("INVENTORY + SAP INTEGRATION TEST PASSED")
    print("=" * 65)


if __name__ == "__main__":
    main()