from pathlib import Path
from typing import Optional, Any
import uuid
import math


class AgentState:
    """
    Central state object for the SapAi inventory automation agent.

    The state stores:

    - User information
    - SAP configuration
    - Inventory input files
    - Workflow progress
    - Comparison results
    - Generated report
    - Validation results
    - Errors and warnings
    - Agent/tool execution results

    The state also guarantees that data returned to FastAPI
    is JSON serializable.
    """

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        run_id: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tcode: Optional[str] = None,
        variant: Optional[str] = None,
        plant: Optional[str] = None,
        previous_period: Optional[str] = None,
        current_period: Optional[str] = None,
        storage_location: Optional[str] = None,
        preferences: Optional[dict[str, Any]] = None,
    ):

        # =====================================================
        # RUN / USER
        # =====================================================

        self.run_id = run_id or str(uuid.uuid4())

        self.user_id: Optional[str] = user_id

        # =====================================================
        # USER / SAP CONFIGURATION
        # =====================================================

        self.username: Optional[str] = username

        # NEVER expose this through API responses.
        self.password: Optional[str] = password

        self.tcode: str = tcode or "MC.1"

        self.variant: str = variant or "B002159"

        # =====================================================
        # REPORT PERIOD
        # =====================================================

        self.previous_period: Optional[str] = (
            previous_period
        )

        self.current_period: Optional[str] = (
            current_period
        )

        # =====================================================
        # USER / SAP FILTERS
        # =====================================================

        self.plant: Optional[str] = plant

        self.storage_location: Optional[str] = (
            storage_location
        )

        self.preferences: dict[str, Any] = (
            preferences.copy()
            if preferences
            else {}
        )

        # =====================================================
        # PROJECT PATHS
        # =====================================================

        project_root = (
            Path(__file__)
            .resolve()
            .parents[3]
        )

        self.data_directory = (
            project_root / "data"
        )

        self.report_directory = (
            self.data_directory / "reports"
        )

        self.report_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

# -----------------------------------------------------
# Previous inventory
# -----------------------------------------------------

        self.previous_inventory_file: str = str(
            self.data_directory
            / "uploads"
            / "previous_inventory.xlsx"
        )


# -----------------------------------------------------
# Current inventory
# -----------------------------------------------------

        self.current_inventory_file: str = str(
            self.data_directory
            / "uploads"
            / "current_inventory.xlsx"
        )

        self.previous_cleaned_file: Optional[str] = None

        self.current_cleaned_file: Optional[str] = None

        # =====================================================
        # INVENTORY DATA
        # =====================================================

        self.previous_inventory: Optional[Any] = None

        self.current_inventory: Optional[Any] = None

        # =====================================================
        # COMPARISON
        # =====================================================

        self.comparison: Optional[Any] = None

        self.summary: dict[str, Any] = {}

        # =====================================================
        # WORKFLOW STATE
        # =====================================================

        self.status: str = "idle"

        self.current_step: Optional[str] = None

        self.steps: list[dict[str, Any]] = []

        self.completed_steps: list[str] = []

        self.errors: list[str] = []

        self.warnings: list[str] = []

        # =====================================================
        # RESULTS
        # =====================================================

        self.results: dict[str, Any] = {}

        self.inspection_result: Optional[Any] = None

        self.comparison_result: Optional[Any] = None

        self.validation_result: Optional[Any] = None

        # =====================================================
        # REPORT
        # =====================================================

        self.report_path: Optional[str] = None

        self.report_file: Optional[str] = None

        # =====================================================
        # METADATA
        # =====================================================

        self.metadata: dict[str, Any] = {}

    # =========================================================
    # PERIOD COMPATIBILITY
    # =========================================================

    @property
    def previous_month(self) -> Optional[str]:
        """
        Backward-compatible alias for previous_period.
        """

        return self.previous_period

    @previous_month.setter
    def previous_month(
        self,
        value: Optional[str],
    ):
        self.previous_period = value

    # ---------------------------------------------------------

    @property
    def current_month(self) -> Optional[str]:
        """
        Backward-compatible alias for current_period.
        """

        return self.current_period

    @current_month.setter
    def current_month(
        self,
        value: Optional[str],
    ):
        self.current_period = value

    # =========================================================
    # REPORT PATH
    # =========================================================

    def set_report_path(
        self,
        path: Optional[str],
    ):
        """
        Keep report_path and report_file synchronized.
        """

        if path is None:

            self.report_path = None
            self.report_file = None

            return

        path_string = str(path)

        self.report_path = path_string

        self.report_file = path_string

    # =========================================================
    # JSON SAFE CONVERSION
    # =========================================================

    @staticmethod
    def _make_json_safe(
        value: Any,
    ) -> Any:
        """
        Recursively convert values into JSON-safe Python objects.

        Handles:

        - numpy integers
        - numpy floats
        - numpy booleans
        - pandas DataFrames
        - pandas Series
        - pandas timestamps
        - pathlib.Path
        - dictionaries
        - lists
        - tuples
        - sets
        - NaN / Infinity
        """

        # -----------------------------------------------------
        # None
        # -----------------------------------------------------

        if value is None:
            return None

        # -----------------------------------------------------
        # Basic JSON-compatible types
        # -----------------------------------------------------

        if isinstance(
            value,
            (
                str,
                int,
                bool,
            ),
        ):
            return value

        # -----------------------------------------------------
        # Float safety
        # -----------------------------------------------------

        if isinstance(
            value,
            float,
        ):

            if not math.isfinite(value):
                return None

            return value

        # -----------------------------------------------------
        # pathlib.Path
        # -----------------------------------------------------

        if isinstance(
            value,
            Path,
        ):
            return str(value)

        # -----------------------------------------------------
        # NumPy
        # -----------------------------------------------------

        try:

            import numpy as np

            if isinstance(
                value,
                np.generic,
            ):

                python_value = value.item()

                return AgentState._make_json_safe(
                    python_value
                )

            if isinstance(
                value,
                np.ndarray,
            ):

                return [
                    AgentState._make_json_safe(item)
                    for item in value.tolist()
                ]

        except ImportError:

            pass

        # -----------------------------------------------------
        # Pandas DataFrame
        # -----------------------------------------------------

        try:

            import pandas as pd

            if isinstance(
                value,
                pd.DataFrame,
            ):

                records = value.to_dict(
                    orient="records"
                )

                return AgentState._make_json_safe(
                    records
                )

            # -------------------------------------------------
            # Pandas Series
            # -------------------------------------------------

            if isinstance(
                value,
                pd.Series,
            ):

                return AgentState._make_json_safe(
                    value.tolist()
                )

            # -------------------------------------------------
            # Pandas Timestamp
            # -------------------------------------------------

            if isinstance(
                value,
                pd.Timestamp,
            ):

                if pd.isna(value):
                    return None

                return value.isoformat()

            # -------------------------------------------------
            # Pandas NA
            # -------------------------------------------------

            try:

                if pd.isna(value):
                    return None

            except (
                TypeError,
                ValueError,
            ):

                pass

        except ImportError:

            pass

        # -----------------------------------------------------
        # Dictionaries
        # -----------------------------------------------------

        if isinstance(
            value,
            dict,
        ):

            return {
                str(key): AgentState._make_json_safe(
                    item
                )
                for key, item in value.items()
            }

        # -----------------------------------------------------
        # Lists / tuples / sets
        # -----------------------------------------------------

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            return [
                AgentState._make_json_safe(
                    item
                )
                for item in value
            ]

        # -----------------------------------------------------
        # Objects with to_dict()
        # -----------------------------------------------------

        if hasattr(
            value,
            "to_dict",
        ) and callable(
            value.to_dict
        ):

            try:

                converted = value.to_dict()

                return AgentState._make_json_safe(
                    converted
                )

            except Exception:

                pass

        # -----------------------------------------------------
        # Objects with dict()
        # -----------------------------------------------------

        if hasattr(
            value,
            "dict",
        ) and callable(
            value.dict
        ):

            try:

                converted = value.dict()

                return AgentState._make_json_safe(
                    converted
                )

            except Exception:

                pass

        # -----------------------------------------------------
        # Fallback
        # -----------------------------------------------------

        return str(value)

    # =========================================================
    # STEP MANAGEMENT
    # =========================================================

    def start_step(
        self,
        step_name: str,
    ):

        self.current_step = step_name

        step = {
            "step": step_name,
            "status": "running",
        }

        self.steps.append(step)

        print()
        print("=" * 70)
        print(
            f"STARTING STEP: {step_name}"
        )
        print("=" * 70)

    # ---------------------------------------------------------

    def complete_step(
        self,
        step_name: str,
        result: Any = None,
    ):

        for step in reversed(self.steps):

            if (
                step["step"] == step_name
                and step["status"] == "running"
            ):

                step["status"] = "completed"

                if result is not None:
                    step["result"] = result

                break

        if step_name not in self.completed_steps:

            self.completed_steps.append(
                step_name
            )

        self.current_step = step_name

        print()
        print("=" * 70)
        print(
            f"STEP COMPLETED: {step_name}"
        )
        print("=" * 70)

        return result

    # ---------------------------------------------------------

    def fail_step(
        self,
        step_name: str,
        error_message: str,
    ):

        for step in reversed(self.steps):

            if (
                step["step"] == step_name
                and step["status"] == "running"
            ):

                step["status"] = "failed"

                step["error"] = (
                    str(error_message)
                )

                break

        self.errors.append(
            str(error_message)
        )

        self.current_step = step_name

        print()
        print("=" * 70)
        print(
            f"STEP FAILED: {step_name}"
        )
        print(
            f"ERROR: {error_message}"
        )
        print("=" * 70)

        return error_message

    # =========================================================
    # BACKWARD COMPATIBILITY
    # =========================================================

    def mark_completed(
        self,
        step_name: str,
        result: Any = None,
    ):

        has_running_step = any(
            step["step"] == step_name
            and step["status"] == "running"
            for step in self.steps
        )

        if has_running_step:

            return self.complete_step(
                step_name,
                result,
            )

        self.current_step = step_name

        if step_name not in self.completed_steps:

            self.completed_steps.append(
                step_name
            )

        step = {
            "step": step_name,
            "status": "completed",
        }

        if result is not None:

            step["result"] = result

        self.steps.append(step)

        return result

    # ---------------------------------------------------------

    def mark_failed(
        self,
        step_name: str,
        error_message: str,
    ):

        return self.fail_step(
            step_name,
            error_message,
        )

    # =========================================================
    # RESULT MANAGEMENT
    # =========================================================

    def add_result(
        self,
        name: str,
        result: Any = None,
    ):

        self.results[name] = result

        return result

    # ---------------------------------------------------------

    def get_result(
        self,
        name: str,
        default: Any = None,
    ):

        return self.results.get(
            name,
            default,
        )

    # =========================================================
    # ERROR MANAGEMENT
    # =========================================================

    def add_error(
        self,
        error_message: str,
    ):

        self.errors.append(
            str(error_message)
        )

        return error_message

    # ---------------------------------------------------------

    def add_warning(
        self,
        warning_message: str,
    ):

        self.warnings.append(
            str(warning_message)
        )

        return warning_message

    # =========================================================
    # WORKFLOW FINISH
    # =========================================================

    def finish(
        self,
        status: str = "completed",
    ):

        self.status = status

        self.current_step = None

        print()
        print("=" * 70)
        print(
            f"WORKFLOW FINISHED: {status.upper()}"
        )
        print("=" * 70)

        return status

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.status = "idle"

        self.current_step = None

        self.steps = []

        self.completed_steps = []

        self.errors = []

        self.warnings = []

        self.results = {}

        self.inspection_result = None

        self.comparison_result = None

        self.validation_result = None

        self.previous_inventory = None

        self.current_inventory = None

        self.comparison = None

        self.summary = {}

        self.previous_cleaned_file = None

        self.current_cleaned_file = None

        self.report_path = None

        self.report_file = None

        self.metadata = {}

        return self

    # =========================================================
    # SAFE DICTIONARY
    # =========================================================

    def safe_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return a completely JSON-safe representation
        of the agent state.

        Password is never included.
        """

        data = self.to_dict()

        data.pop(
            "password",
            None,
        )

        return self._make_json_safe(
            data
        )

    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Convert the complete agent state into a dictionary.

        All values are converted into JSON-safe Python types.
        """

        data = {

            # -------------------------------------------------
            # RUN / USER
            # -------------------------------------------------

            "run_id": self.run_id,

            "user_id": self.user_id,

            # -------------------------------------------------
            # STATUS
            # -------------------------------------------------

            "status": self.status,

            "current_step": self.current_step,

            "completed_steps": (
                self.completed_steps
            ),

            # -------------------------------------------------
            # SAP CONFIGURATION
            # -------------------------------------------------

            "sap_configuration": {

                "username": self.username,

                "tcode": self.tcode,

                "variant": self.variant,

                "previous_period": (
                    self.previous_period
                ),

                "current_period": (
                    self.current_period
                ),

                # Backward-compatible names
                "previous_month": (
                    self.previous_month
                ),

                "current_month": (
                    self.current_month
                ),

                "plant": self.plant,

                "storage_location": (
                    self.storage_location
                ),

                "preferences": (
                    self.preferences
                ),
            },

            # -------------------------------------------------
            # INVENTORY FILES
            # -------------------------------------------------

            "inventory_files": {

                "previous_inventory_file": (
                    self.previous_inventory_file
                ),

                "current_inventory_file": (
                    self.current_inventory_file
                ),

                "previous_cleaned_file": (
                    self.previous_cleaned_file
                ),

                "current_cleaned_file": (
                    self.current_cleaned_file
                ),
            },

            # -------------------------------------------------
            # WORKFLOW
            # -------------------------------------------------

            "steps": self.steps,

            # -------------------------------------------------
            # RESULTS
            # -------------------------------------------------

            "results": self.results,

            # -------------------------------------------------
            # INDIVIDUAL RESULTS
            # -------------------------------------------------

            "inspection_result": (
                self.inspection_result
            ),

            "comparison_result": (
                self.comparison_result
            ),

            "validation_result": (
                self.validation_result
            ),

            # -------------------------------------------------
            # COMPARISON
            # -------------------------------------------------

            "comparison": self.comparison,

            "summary": self.summary,

            # -------------------------------------------------
            # REPORT
            # -------------------------------------------------

            "report_path": self.report_path,

            "report_file": self.report_file,

            # -------------------------------------------------
            # ERRORS
            # -------------------------------------------------

            "errors": self.errors,

            # -------------------------------------------------
            # WARNINGS
            # -------------------------------------------------

            "warnings": self.warnings,

            # -------------------------------------------------
            # METADATA
            # -------------------------------------------------

            "metadata": self.metadata,
        }

        # =====================================================
        # FINAL JSON-SAFE CONVERSION
        # =====================================================

        return self._make_json_safe(
            data
        )

    # =========================================================
    # STRING REPRESENTATION
    # =========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            "AgentState("
            f"run_id={self.run_id!r}, "
            f"user_id={self.user_id!r}, "
            f"status={self.status!r}, "
            f"tcode={self.tcode!r}, "
            f"variant={self.variant!r}, "
            f"previous_period="
            f"{self.previous_period!r}, "
            f"current_period="
            f"{self.current_period!r}, "
            f"previous_inventory_file="
            f"{self.previous_inventory_file!r}, "
            f"current_inventory_file="
            f"{self.current_inventory_file!r}, "
            f"steps={len(self.steps)}"
            ")"
        )