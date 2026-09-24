import uuid
from typing import Optional, Dict, Any

from app.agent.state import AgentState
from app.agent.workflow import InventoryWorkflow


# ---------------------------------------------------------
# IN-MEMORY AGENT RUN STORE
# ---------------------------------------------------------

_AGENT_RUNS: Dict[str, AgentState] = {}


# ---------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------

class AgentOrchestrator:
    """
    Controls SapAi agent executions.

    This is intentionally deterministic in v1.

    The LLM reasoning layer will be added later.
    """

    def create_run(
        self,
        user_id: Optional[str] = None,
        tcode: Optional[str] = None,
        variant: Optional[str] = None,
        plant: Optional[str] = None,
        previous_period: Optional[str] = None,
        current_period: Optional[str] = None,
    ) -> AgentState:

        run_id = str(uuid.uuid4())

        state = AgentState(
            run_id=run_id,
            user_id=user_id,
            tcode=tcode,
            variant=variant,
            plant=plant,
            previous_period=previous_period,
            current_period=current_period,
        )

        _AGENT_RUNS[run_id] = state

        return state

    # -----------------------------------------------------
    # RUN
    # -----------------------------------------------------

    def run(
        self,
        user_id: Optional[str] = None,
        tcode: Optional[str] = None,
        variant: Optional[str] = None,
        plant: Optional[str] = None,
        previous_period: Optional[str] = None,
        current_period: Optional[str] = None,
    ) -> Dict[str, Any]:

        state = self.create_run(
            user_id=user_id,
            tcode=tcode,
            variant=variant,
            plant=plant,
            previous_period=previous_period,
            current_period=current_period,
        )

        workflow = InventoryWorkflow(state)

        try:

            return workflow.run()

        except Exception:

            return state.to_dict()

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    def get_status(
        self,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:

        state = _AGENT_RUNS.get(run_id)

        if state is None:
            return None

        return state.to_dict()


# ---------------------------------------------------------
# SINGLE ORCHESTRATOR INSTANCE
# ---------------------------------------------------------

orchestrator = AgentOrchestrator()