"""
Test Decision Engine.

This module contains pytest tests for the Decision Engine and related models.
"""

from unittest.mock import Mock

import pytest

from conversation.intents import ConversationIntent
from conversation.requirements import (
    GET_EXPENSE_CLAIM_REQUIREMENTS,
    SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
    UNKNOWN_REQUIREMENTS,
)
from coordinator import (
    Coordinator,
    CoordinatorRequestBuilder,
    Decision,
    DecisionEngine,
    DecisionType,
    ExecutionMode,
    WorkflowState,
)


class TestDecisionType:
    """Test DecisionType enumeration."""

    def test_decision_type_has_correct_values(self):
        """Test that DecisionType has all required values."""
        expected_values = [
            "continue_conversation",
            "execute_workflow",
            "wait_for_confirmation",
            "wait_for_receipt",
            "wait_for_manager",
            "complete",
            "cancel",
            "error",
            "unknown",
        ]

        actual_values = [decision_type.value for decision_type in DecisionType]

        for expected in expected_values:
            assert expected in actual_values

    def test_decision_type_is_str_enum(self):
        """Test that DecisionType is a StrEnum."""
        assert isinstance(DecisionType.CONTINUE_CONVERSATION, DecisionType)
        assert DecisionType.CONTINUE_CONVERSATION == "continue_conversation"


class TestExecutionMode:
    """Test ExecutionMode enumeration."""

    def test_execution_mode_has_correct_values(self):
        """Test that ExecutionMode has all required values."""
        expected_values = ["sequential", "parallel", "none"]

        actual_values = [mode.value for mode in ExecutionMode]

        for expected in expected_values:
            assert expected in actual_values

    def test_execution_mode_is_str_enum(self):
        """Test that ExecutionMode is a StrEnum."""
        assert isinstance(ExecutionMode.SEQUENTIAL, ExecutionMode)
        assert ExecutionMode.SEQUENTIAL == "sequential"


class TestDecisionModel:
    """Test Decision dataclass."""

    def test_decision_creation_with_minimal_params(self):
        """Test Decision creation with minimal required parameters."""
        decision = Decision(decision_type=DecisionType.CONTINUE_CONVERSATION)

        assert decision.decision_type == DecisionType.CONTINUE_CONVERSATION
        assert decision.next_agent is None
        assert decision.reason == ""
        assert decision.execution_mode == ExecutionMode.NONE
        assert decision.requires_confirmation is False
        assert decision.requires_user_input is False
        assert decision.missing_fields == ()
        assert decision.metadata == {}

    def test_decision_creation_with_all_params(self):
        """Test Decision creation with all parameters."""
        decision = Decision(
            decision_type=DecisionType.EXECUTE_WORKFLOW,
            next_agent="ExpenseAgent",
            reason="All requirements met",
            execution_mode=ExecutionMode.SEQUENTIAL,
            requires_confirmation=True,
            requires_user_input=False,
            missing_fields=["field1", "field2"],
            metadata={"key": "value"},
        )

        assert decision.decision_type == DecisionType.EXECUTE_WORKFLOW
        assert decision.next_agent == "ExpenseAgent"
        assert decision.reason == "All requirements met"
        assert decision.execution_mode == ExecutionMode.SEQUENTIAL
        assert decision.requires_confirmation is True
        assert decision.requires_user_input is False
        assert decision.missing_fields == ["field1", "field2"]
        assert decision.metadata == {"key": "value"}

    def test_decision_is_immutable(self):
        """Test that Decision instances are immutable."""
        decision = Decision(decision_type=DecisionType.CONTINUE_CONVERSATION, reason="Test")

        with pytest.raises(Exception):  # FrozenInstanceError
            decision.reason = "Modified"  # type: ignore

    def test_decision_equality(self):
        """Test Decision equality comparison."""
        decision1 = Decision(decision_type=DecisionType.CONTINUE_CONVERSATION, reason="Test")
        decision2 = Decision(decision_type=DecisionType.CONTINUE_CONVERSATION, reason="Test")
        decision3 = Decision(decision_type=DecisionType.EXECUTE_WORKFLOW, reason="Test")

        assert decision1 == decision2
        assert decision1 != decision3


class TestDecisionEngine:
    """Test DecisionEngine class."""

    @pytest.fixture
    def engine(self) -> DecisionEngine:
        """Fixture providing a DecisionEngine instance."""
        return DecisionEngine()

    @pytest.fixture
    def builder(self) -> CoordinatorRequestBuilder:
        """Fixture providing a CoordinatorRequestBuilder instance."""
        return CoordinatorRequestBuilder()

    def test_decision_engine_unknown_intent(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine with unknown intent."""
        decision = engine.decide(
            intent=ConversationIntent.UNKNOWN,
            requirements=None,
            request_builder=builder,
            current_state=WorkflowState.STARTED,
        )

        assert decision.decision_type == DecisionType.UNKNOWN
        assert decision.requires_user_input is True
        assert "unknown" in decision.metadata.get("context", "")

    def test_decision_engine_missing_requirements(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine with missing requirements."""
        decision = engine.decide(
            intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
            requirements=None,
            request_builder=builder,
            current_state=WorkflowState.STARTED,
        )

        assert decision.decision_type == DecisionType.ERROR
        assert "No requirements defined" in decision.reason

    def test_decision_engine_missing_fields(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine when fields are missing."""
        decision = engine.decide(
            intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
            requirements=SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
            request_builder=builder,
            current_state=WorkflowState.COLLECTING_INFORMATION,
        )

        assert decision.decision_type == DecisionType.CONTINUE_CONVERSATION
        assert decision.requires_user_input is True
        assert len(decision.missing_fields) > 0
        assert "employee_id" in decision.missing_fields

    def test_decision_engine_ready_to_execute(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine when all requirements are met."""
        # Add all required fields
        for field in SUBMIT_EXPENSE_CLAIM_REQUIREMENTS.required_fields:
            builder.add_field(field, f"value_{field}")

        decision = engine.decide(
            intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
            requirements=SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
            request_builder=builder,
            current_state=WorkflowState.READY_TO_EXECUTE,
        )

        # SUBMIT_EXPENSE_CLAIM requires confirmation, so it should wait for confirmation
        assert decision.decision_type == DecisionType.WAIT_FOR_CONFIRMATION
        assert decision.execution_mode == ExecutionMode.NONE
        assert decision.requires_confirmation is True

    def test_decision_engine_confirmation_required(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine when confirmation is required."""
        # Add all required fields for an intent that requires confirmation
        for field in SUBMIT_EXPENSE_CLAIM_REQUIREMENTS.required_fields:
            builder.add_field(field, f"value_{field}")

        decision = engine.decide(
            intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
            requirements=SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
            request_builder=builder,
            current_state=WorkflowState.READY_TO_EXECUTE,
        )

        # SUBMIT_EXPENSE_CLAIM requires confirmation
        assert decision.decision_type == DecisionType.WAIT_FOR_CONFIRMATION
        assert decision.requires_confirmation is True

    def test_decision_engine_no_confirmation_required(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine when no confirmation is required."""
        # Add all required fields for an intent that doesn't require confirmation
        for field in GET_EXPENSE_CLAIM_REQUIREMENTS.required_fields:
            builder.add_field(field, f"value_{field}")

        decision = engine.decide(
            intent=ConversationIntent.GET_EXPENSE_CLAIM,
            requirements=GET_EXPENSE_CLAIM_REQUIREMENTS,
            request_builder=builder,
            current_state=WorkflowState.READY_TO_EXECUTE,
        )

        # GET_EXPENSE_CLAIM doesn't require confirmation
        assert decision.decision_type == DecisionType.EXECUTE_WORKFLOW
        assert decision.requires_confirmation is False

    def test_decision_engine_partial_fields(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine with partially collected fields."""
        # Add only some fields
        builder.add_field("employee_id", "EMP123")
        builder.add_field("trip_name", "Business Trip")

        decision = engine.decide(
            intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
            requirements=SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
            request_builder=builder,
            current_state=WorkflowState.COLLECTING_INFORMATION,
        )

        assert decision.decision_type == DecisionType.CONTINUE_CONVERSATION
        assert len(decision.missing_fields) == 5  # 7 total - 2 collected
        assert "business_purpose" in decision.missing_fields

    def test_decision_engine_requires_request_builder(self, engine: DecisionEngine):
        """Test that DecisionEngine requires a request builder."""
        with pytest.raises(ValueError, match="request_builder cannot be None"):
            engine.decide(
                intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
                requirements=SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
                request_builder=None,  # type: ignore
                current_state=WorkflowState.STARTED,
            )


class TestCoordinatorDecisionIntegration:
    """Test DecisionEngine integration with Coordinator."""

    @pytest.fixture
    def coordinator(self) -> Coordinator:
        """Fixture providing a Coordinator instance with mock agents."""
        # Create mock agents
        expense_agent = Mock(spec=Coordinator)
        expense_agent.agent_name = "ExpenseAgent"

        employee_agent = Mock(spec=Coordinator)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=Coordinator)
        policy_agent.agent_name = "PolicyAgent"

        receipt_agent = Mock(spec=Coordinator)
        receipt_agent.agent_name = "ReceiptAgent"

        approval_agent = Mock(spec=Coordinator)
        approval_agent.agent_name = "ApprovalAgent"

        return Coordinator(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_coordinator_get_decision_initial_state(self, coordinator: Coordinator):
        """Test Coordinator decision in initial state."""
        decision = coordinator.get_decision()

        # No intent set initially
        assert decision.decision_type == DecisionType.UNKNOWN

    def test_coordinator_get_decision_with_conversation(self, coordinator: Coordinator):
        """Test Coordinator decision during conversation."""
        # Start a conversation
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Should need to continue conversation
        decision = coordinator.get_decision()
        assert decision.decision_type == DecisionType.CONTINUE_CONVERSATION
        assert len(decision.missing_fields) > 0

    def test_coordinator_get_decision_ready_to_execute(self, coordinator: Coordinator):
        """Test Coordinator decision when ready to execute."""
        coordinator.start_conversation(ConversationIntent.GET_EXPENSE_CLAIM)

        # Collect the required field
        coordinator.collect_field("claim_id", "CLAIM123")

        # Should be ready to execute
        decision = coordinator.get_decision()
        assert decision.decision_type == DecisionType.EXECUTE_WORKFLOW
        assert decision.execution_mode == ExecutionMode.SEQUENTIAL

    def test_coordinator_get_decision_confirmation_required(self, coordinator: Coordinator):
        """Test Coordinator decision when confirmation is required."""
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Collect all required fields
        required_fields = [
            "employee_id",
            "trip_name",
            "business_purpose",
            "destination",
            "trip_start_date",
            "trip_end_date",
            "expense_items",
        ]
        for field in required_fields:
            coordinator.collect_field(field, f"value_{field}")

        # Should wait for confirmation
        decision = coordinator.get_decision()
        assert decision.decision_type == DecisionType.WAIT_FOR_CONFIRMATION
        assert decision.requires_confirmation is True

    def test_coordinator_decision_state_transitions(self, coordinator: Coordinator):
        """Test Coordinator decision through state transitions."""
        # Initial state
        decision1 = coordinator.get_decision()
        assert decision1.decision_type == DecisionType.UNKNOWN

        # Start conversation
        coordinator.start_conversation(ConversationIntent.GET_EXPENSE_CLAIM)
        decision2 = coordinator.get_decision()
        assert decision2.decision_type == DecisionType.CONTINUE_CONVERSATION

        # Collect field
        coordinator.collect_field("claim_id", "CLAIM123")
        decision3 = coordinator.get_decision()
        assert decision3.decision_type == DecisionType.EXECUTE_WORKFLOW


class TestDecisionEngineEdgeCases:
    """Test edge cases in DecisionEngine."""

    @pytest.fixture
    def engine(self) -> DecisionEngine:
        """Fixture providing a DecisionEngine instance."""
        return DecisionEngine()

    @pytest.fixture
    def builder(self) -> CoordinatorRequestBuilder:
        """Fixture providing a CoordinatorRequestBuilder instance."""
        return CoordinatorRequestBuilder()

    def test_decision_engine_with_empty_requirements(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine with intent that has no required fields."""
        # Use UNKNOWN_REQUIREMENTS which has no required fields
        decision = engine.decide(
            intent=ConversationIntent.UNKNOWN,
            requirements=UNKNOWN_REQUIREMENTS,
            request_builder=builder,
            current_state=WorkflowState.STARTED,
        )

        # Should still be unknown since intent is UNKNOWN
        assert decision.decision_type == DecisionType.UNKNOWN

    def test_decision_engine_with_optional_fields_only(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test DecisionEngine when only optional fields are missing."""
        # Create a mock requirements with only optional fields
        from conversation.requirements import IntentRequirements

        mock_requirements = IntentRequirements(
            intent=ConversationIntent.GET_EXPENSE_CLAIM,
            required_fields=(),
            optional_fields=("comments",),
            confirmation_required=False,
            success_message="Test",
        )

        decision = engine.decide(
            intent=ConversationIntent.GET_EXPENSE_CLAIM,
            requirements=mock_requirements,
            request_builder=builder,
            current_state=WorkflowState.COLLECTING_INFORMATION,
        )

        # Should be ready to execute since no required fields
        assert decision.decision_type == DecisionType.EXECUTE_WORKFLOW

    def test_decision_engine_metadata_content(
        self, engine: DecisionEngine, builder: CoordinatorRequestBuilder
    ):
        """Test that DecisionEngine includes proper metadata."""
        decision = engine.decide(
            intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
            requirements=SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
            request_builder=builder,
            current_state=WorkflowState.COLLECTING_INFORMATION,
        )

        assert "intent" in decision.metadata
        assert "missing_count" in decision.metadata
        assert "total_required" in decision.metadata
        assert decision.metadata["intent"] == "submit_expense_claim"
        assert decision.metadata["missing_count"] == "7"
        assert decision.metadata["total_required"] == "7"


class TestDecisionEngineNoExecution:
    """Test that DecisionEngine contains no execution logic."""

    def test_decision_engine_no_agent_invocations(self):
        """Test that DecisionEngine doesn't invoke any agents."""
        import inspect

        from coordinator.decision import DecisionEngine

        # Check that DecisionEngine doesn't import or reference any agent classes
        source = inspect.getsource(DecisionEngine)

        # Should not contain any agent-related imports or method calls
        assert "ExpenseAgent" not in source
        assert "EmployeeAgent" not in source
        assert "PolicyAgent" not in source
        assert "ReceiptAgent" not in source
        assert "ApprovalAgent" not in source
        assert ".execute(" not in source
        assert ".run(" not in source

    def test_decision_engine_no_service_calls(self):
        """Test that DecisionEngine doesn't make any service calls."""
        import inspect

        from coordinator.decision import DecisionEngine

        # Check that DecisionEngine doesn't import or reference any service classes
        source = inspect.getsource(DecisionEngine)

        # Should not contain any service-related imports or method calls
        assert "Service" not in source
        assert "Repository" not in source
        assert "Tool" not in source
        assert "Bedrock" not in source
        assert "Nova" not in source
        assert "Claude" not in source
        # LLM is allowed in docstrings for future compatibility
        assert "import LLM" not in source
        assert "from LLM" not in source

    def test_decision_only_returns_decisions(self):
        """Test that DecisionEngine methods only return Decision objects."""
        import inspect

        from coordinator.decision import Decision, DecisionEngine

        # Check that the decide method returns Decision
        decide_method = DecisionEngine.decide
        sig = inspect.signature(decide_method)

        # The return annotation should be Decision
        assert "Decision" in str(sig.return_annotation)

        # Test that it actually returns a Decision
        engine = DecisionEngine()
        builder = CoordinatorRequestBuilder()

        decision = engine.decide(
            intent=ConversationIntent.UNKNOWN,
            requirements=None,
            request_builder=builder,
            current_state=WorkflowState.STARTED,
        )

        assert isinstance(decision, Decision)
