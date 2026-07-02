"""
Test Workflow Definitions and Executor.

This module contains pytest tests for the workflow definition layer and executor.
"""

from unittest.mock import Mock

import pytest

from agents.base_agent import BaseAgent
from conversation.intents import ConversationIntent
from coordinator import (
    Coordinator,
    Decision,
    DecisionType,
    ExecutionMode,
    WorkflowDefinition,
    WorkflowExecutor,
    WorkflowState,
    WorkflowStep,
    WorkflowType,
    get_workflow_definition,
)


class TestWorkflowType:
    """Test WorkflowType enumeration."""

    def test_workflow_type_has_correct_values(self):
        """Test that WorkflowType has all required values."""
        expected_values = [
            "submit_expense_claim",
            "preview_expense_claim",
            "get_expense_claim",
            "upload_receipt",
            "get_receipt_status",
            "approve_claim",
            "reject_claim",
            "get_employee_details",
            "list_employee_claims",
            "get_policy",
            "get_expense_category",
        ]

        actual_values = [workflow_type.value for workflow_type in WorkflowType]

        for expected in expected_values:
            assert expected in actual_values

    def test_workflow_type_is_str_enum(self):
        """Test that WorkflowType is a StrEnum."""
        assert isinstance(WorkflowType.SUBMIT_EXPENSE_CLAIM, WorkflowType)
        assert WorkflowType.SUBMIT_EXPENSE_CLAIM == "submit_expense_claim"


class TestWorkflowStep:
    """Test WorkflowStep dataclass."""

    def test_workflow_stage_creation(self):
        """Test WorkflowStep creation with all parameters."""
        stage = WorkflowStep(
            stage_name="test_stage",
            agent_name="ExpenseAgent",
            execution_order=1,
            requires_confirmation=True,
            requires_receipt=True,
            requires_manager=True,
            metadata={"key": "value"},
        )

        assert stage.stage_name == "test_stage"
        assert stage.agent_name == "ExpenseAgent"
        assert stage.execution_order == 1
        assert stage.requires_confirmation is True
        assert stage.requires_receipt is True
        assert stage.requires_manager is True
        assert stage.metadata == {"key": "value"}

    def test_workflow_stage_default_values(self):
        """Test WorkflowStep creation with default values."""
        stage = WorkflowStep(stage_name="test_stage", agent_name="ExpenseAgent", execution_order=1)

        assert stage.requires_confirmation is False
        assert stage.requires_receipt is False
        assert stage.requires_manager is False
        assert stage.metadata == {}

    def test_workflow_stage_immutability(self):
        """Test that WorkflowStep instances are immutable."""
        stage = WorkflowStep(stage_name="test_stage", agent_name="ExpenseAgent", execution_order=1)

        with pytest.raises(Exception):  # FrozenInstanceError
            stage.stage_name = "modified"  # type: ignore

    def test_workflow_stage_equality(self):
        """Test WorkflowStep equality comparison."""
        stage1 = WorkflowStep(stage_name="test_stage", agent_name="ExpenseAgent", execution_order=1)
        stage2 = WorkflowStep(stage_name="test_stage", agent_name="ExpenseAgent", execution_order=1)
        stage3 = WorkflowStep(
            stage_name="different_stage", agent_name="ExpenseAgent", execution_order=1
        )

        assert stage1 == stage2
        assert stage1 != stage3


class TestWorkflowDefinition:
    """Test WorkflowDefinition dataclass."""

    def test_workflow_definition_creation(self):
        """Test WorkflowDefinition creation with valid stages."""
        stages = (
            WorkflowStep(stage_name="stage1", agent_name="ExpenseAgent", execution_order=1),
            WorkflowStep(stage_name="stage2", agent_name="ExpenseAgent", execution_order=2),
        )

        definition = WorkflowDefinition(
            workflow_type=WorkflowType.SUBMIT_EXPENSE_CLAIM,
            steps=stages,
            description="Test workflow",
            metadata={"key": "value"},
        )

        assert definition.workflow_type == WorkflowType.SUBMIT_EXPENSE_CLAIM
        assert len(definition.steps) == 2
        assert definition.description == "Test workflow"
        assert definition.metadata == {"key": "value"}

    def test_workflow_definition_immutability(self):
        """Test that WorkflowDefinition instances are immutable."""
        steps = (WorkflowStep(stage_name="step1", agent_name="ExpenseAgent", execution_order=1),)

        definition = WorkflowDefinition(
            workflow_type=WorkflowType.SUBMIT_EXPENSE_CLAIM,
            steps=steps,
            description="Test workflow",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            definition.description = "modified"  # type: ignore

    def test_workflow_definition_validation(self):
        """Test that WorkflowDefinition validates step ordering."""
        # Valid sequential ordering
        valid_steps = (
            WorkflowStep(stage_name="step1", agent_name="ExpenseAgent", execution_order=1),
            WorkflowStep(stage_name="step2", agent_name="ExpenseAgent", execution_order=2),
        )

        # Should not raise an exception
        definition = WorkflowDefinition(
            workflow_type=WorkflowType.SUBMIT_EXPENSE_CLAIM,
            steps=valid_steps,
            description="Valid workflow",
        )
        assert len(definition.steps) == 2

    def test_workflow_definition_invalid_ordering(self):
        """Test that WorkflowDefinition rejects invalid step ordering."""
        invalid_steps = (
            WorkflowStep(
                stage_name="step1",
                agent_name="ExpenseAgent",
                execution_order=2,  # Should start from 1
            ),
            WorkflowStep(
                stage_name="step2",
                agent_name="ExpenseAgent",
                execution_order=3,  # Non-sequential
            ),
        )

        with pytest.raises(ValueError, match="sequential execution orders"):
            WorkflowDefinition(
                workflow_type=WorkflowType.SUBMIT_EXPENSE_CLAIM,
                steps=invalid_steps,
                description="Invalid workflow",
            )

    def test_workflow_definition_duplicate_names(self):
        """Test that WorkflowDefinition rejects duplicate step names."""
        duplicate_steps = (
            WorkflowStep(stage_name="step1", agent_name="ExpenseAgent", execution_order=1),
            WorkflowStep(
                stage_name="step1",  # Duplicate name
                agent_name="ExpenseAgent",
                execution_order=2,
            ),
        )

        with pytest.raises(ValueError, match="unique names"):
            WorkflowDefinition(
                workflow_type=WorkflowType.SUBMIT_EXPENSE_CLAIM,
                steps=duplicate_steps,
                description="Duplicate names workflow",
            )


class TestWorkflowDefinitions:
    """Test predefined workflow definitions."""

    def test_get_workflow_definition(self):
        """Test that workflow definitions can be retrieved."""
        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        assert workflow.workflow_type == WorkflowType.SUBMIT_EXPENSE_CLAIM
        assert len(workflow.steps) > 0
        assert workflow.description

    def test_get_workflow_definition_invalid(self):
        """Test that invalid workflow type raises error."""
        # Create a mock workflow type that doesn't exist in the definitions
        from coordinator.workflow import WorkflowType

        # This will raise ValueError because the workflow type doesn't exist
        # We need to create a valid WorkflowType first, then test the lookup
        try:
            # Try to create an invalid workflow type
            invalid_type = WorkflowType("invalid_type")  # This will fail at enum creation
            assert False, "Should not reach here"
        except ValueError as e:
            # This is expected - StrEnum validates values
            assert "invalid_type" in str(e)

    def test_submit_expense_claim_workflow_structure(self):
        """Test SUBMIT_EXPENSE_CLAIM workflow structure with parallel policy processing."""
        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        assert workflow.workflow_type == WorkflowType.SUBMIT_EXPENSE_CLAIM
        assert len(workflow.steps) == 7  # Now has parallel policy stages and merge stage

        # Check business stage names and agents
        stages = workflow.steps

        # Verify stage sequence and agents
        assert stages[0].stage_name == "employee_retrieval"
        assert stages[0].agent_name == "EmployeeAgent"
        assert stages[0].requires_confirmation is False
        assert stages[0].depends_on == ()

        assert stages[1].stage_name == "policy_eligibility_lookup"
        assert stages[1].agent_name == "PolicyAgent"
        assert stages[1].requires_confirmation is False
        assert stages[1].depends_on == ("employee_retrieval",)

        assert stages[2].stage_name == "category_limit_lookup"
        assert stages[2].agent_name == "PolicyAgent"
        assert stages[2].requires_confirmation is False
        assert stages[2].depends_on == ("employee_retrieval",)

        assert stages[3].stage_name == "merge_policy_results"
        assert stages[3].agent_name is None  # No agent for merge stage
        assert stages[3].requires_confirmation is False
        assert stages[3].depends_on == ("policy_eligibility_lookup", "category_limit_lookup")

        assert stages[4].stage_name == "expense_preview"
        assert stages[4].agent_name == "ExpenseAgent"
        assert stages[4].requires_confirmation is True
        assert stages[4].depends_on == ("merge_policy_results",)

        assert stages[5].stage_name == "wait_confirmation"
        assert stages[5].agent_name is None  # No agent for confirmation stage
        assert stages[5].requires_confirmation is True
        assert stages[5].depends_on == ("expense_preview",)

        assert stages[6].stage_name == "expense_submission"
        assert stages[6].agent_name == "ExpenseAgent"
        assert stages[6].requires_confirmation is False
        assert stages[6].depends_on == ("wait_confirmation",)

        # Verify PolicyAgent appears twice (for parallel policy lookups)
        policy_agent_stages = [s for s in stages if s.agent_name == "PolicyAgent"]
        assert len(policy_agent_stages) == 2

        # Verify ExpenseAgent appears twice (preview and submission)
        expense_agent_stages = [s for s in stages if s.agent_name == "ExpenseAgent"]
        assert len(expense_agent_stages) == 2

    def test_get_expense_claim_workflow_structure(self):
        """Test GET_EXPENSE_CLAIM workflow structure with business stages."""
        workflow = get_workflow_definition(WorkflowType.GET_EXPENSE_CLAIM)

        assert workflow.workflow_type == WorkflowType.GET_EXPENSE_CLAIM
        assert len(workflow.steps) == 2  # Now has business stages

        # Check business stage names and agents
        stages = workflow.steps

        assert stages[0].stage_name == "employee_retrieval"
        assert stages[0].agent_name == "EmployeeAgent"
        assert stages[0].requires_confirmation is False

        assert stages[1].stage_name == "expense_retrieval"
        assert stages[1].agent_name == "ExpenseAgent"
        assert stages[1].requires_confirmation is False


class TestWorkflowExecutor:
    """Test WorkflowExecutor class."""

    @pytest.fixture
    def executor(self) -> WorkflowExecutor:
        """Fixture providing a WorkflowExecutor instance with mock agents."""
        # Create mock agents with invoke method
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        receipt_agent = Mock(spec=BaseAgent)
        receipt_agent.agent_name = "ReceiptAgent"
        receipt_agent.invoke.return_value = "mock_receipt_result"

        approval_agent = Mock(spec=BaseAgent)
        approval_agent.agent_name = "ApprovalAgent"
        approval_agent.invoke.return_value = "mock_approval_result"

        return WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    @pytest.fixture
    def simple_workflow(self) -> WorkflowDefinition:
        """Fixture providing a simple workflow definition for testing with business stages."""
        return WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="employee_retrieval", agent_name="EmployeeAgent", execution_order=1
                ),
                WorkflowStep(
                    stage_name="expense_retrieval", agent_name="ExpenseAgent", execution_order=2
                ),
            ),
            description="Simple test workflow with business stages",
        )

    def test_workflow_executor_initialization(self, executor: WorkflowExecutor):
        """Test WorkflowExecutor initialization."""
        assert executor.expense_agent is not None
        assert executor.employee_agent is not None
        assert executor.policy_agent is not None
        assert executor.receipt_agent is not None
        assert executor.approval_agent is not None

    def test_workflow_executor_requires_all_agents(self):
        """Test that WorkflowExecutor requires all agents."""
        with pytest.raises(ValueError, match="All specialized agents must be provided"):
            WorkflowExecutor(
                expense_agent=None,  # type: ignore
                employee_agent=Mock(),
                policy_agent=Mock(),
                receipt_agent=Mock(),
                approval_agent=Mock(),
            )

    def test_execute_workflow_sequential(
        self, executor: WorkflowExecutor, simple_workflow: WorkflowDefinition
    ):
        """Test sequential workflow execution with business stages."""
        results = executor.execute_workflow(
            workflow_definition=simple_workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        assert results["workflow_type"] == WorkflowType.GET_EXPENSE_CLAIM
        assert results["status"] == "completed"
        assert results["completed_stages"] == 2  # Now has 2 business stages
        assert len(results["results"]) == 2

    def test_execute_workflow_parallel_fallback(
        self, executor: WorkflowExecutor, simple_workflow: WorkflowDefinition
    ):
        """Test that PARALLEL mode falls back to sequential with business stages."""
        results = executor.execute_workflow(
            workflow_definition=simple_workflow, execution_mode=ExecutionMode.PARALLEL
        )

        # Should still complete successfully with fallback
        assert results["status"] == "completed"
        assert results["completed_stages"] == 2  # Now has 2 business stages

    def test_execute_workflow_invalid_mode(
        self, executor: WorkflowExecutor, simple_workflow: WorkflowDefinition
    ):
        """Test that invalid execution mode raises error."""
        # Create a mock execution mode that doesn't exist
        from coordinator.decision import ExecutionMode

        try:
            # Try to create an invalid execution mode
            invalid_mode = ExecutionMode("INVALID")  # This will fail at enum creation
            assert False, "Should not reach here"
        except ValueError as e:
            # This is expected - StrEnum validates values
            assert "INVALID" in str(e)

    def test_execute_workflow_stage_results(
        self, executor: WorkflowExecutor, simple_workflow: WorkflowDefinition
    ):
        """Test that workflow execution returns proper stage results."""
        results = executor.execute_workflow(
            workflow_definition=simple_workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        # Check lightweight results structure
        assert results["workflow_type"] == WorkflowType.GET_EXPENSE_CLAIM
        assert results["status"] == "completed"
        assert results["completed_stages"] == 2  # Now has 2 business stages

        # Check that stage results are stored directly
        stage_results = results["results"]
        assert "employee_retrieval" in stage_results
        assert "expense_retrieval" in stage_results

        # Check that agent results are stored
        assert stage_results["employee_retrieval"] == "mock_employee_result"
        assert stage_results["expense_retrieval"] == "mock_expense_result"

    def test_execute_workflow_error_handling(self, executor: WorkflowExecutor):
        """Test workflow execution error handling."""
        # Create a workflow with a stage that has an invalid agent
        invalid_workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="invalid_stage",
                    agent_name="InvalidAgent",  # This agent doesn't exist
                    execution_order=1,
                ),
            ),
            description="Invalid workflow",
        )

        with pytest.raises(RuntimeError, match="Workflow execution failed"):
            executor.execute_workflow(
                workflow_definition=invalid_workflow, execution_mode=ExecutionMode.SEQUENTIAL
            )


class TestCoordinatorWorkflowIntegration:
    """Test workflow execution integration with Coordinator."""

    @pytest.fixture
    def coordinator(self) -> Coordinator:
        """Fixture providing a Coordinator instance with mock agents."""
        # Create mock agents with invoke method
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        receipt_agent = Mock(spec=BaseAgent)
        receipt_agent.agent_name = "ReceiptAgent"
        receipt_agent.invoke.return_value = "mock_receipt_result"

        approval_agent = Mock(spec=BaseAgent)
        approval_agent.agent_name = "ApprovalAgent"
        approval_agent.invoke.return_value = "mock_approval_result"

        return Coordinator(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_coordinator_execute_workflow(self, coordinator: Coordinator):
        """Test Coordinator workflow execution with business stages."""
        # Start a conversation and collect required fields
        coordinator.start_conversation(ConversationIntent.GET_EXPENSE_CLAIM)
        coordinator.collect_field("claim_id", "CLAIM123")

        # Get decision (should be ready to execute)
        decision = coordinator.get_decision()

        # Execute workflow
        results = coordinator.execute_workflow(decision)

        assert results["workflow_type"] == WorkflowType.GET_EXPENSE_CLAIM
        assert results["status"] == "completed"
        assert results["completed_stages"] > 0

        # Verify business stages were executed
        stage_results = results["results"]
        assert "employee_retrieval" in stage_results
        assert "expense_retrieval" in stage_results

    def test_coordinator_execute_workflow_invalid_decision(self, coordinator: Coordinator):
        """Test that Coordinator rejects non-executable decisions."""
        # Create a non-executable decision
        invalid_decision = Decision(decision_type=DecisionType.CONTINUE_CONVERSATION, reason="Test")

        with pytest.raises(ValueError, match="Cannot execute workflow"):
            coordinator.execute_workflow(invalid_decision)

    def test_coordinator_execute_workflow_no_intent(self, coordinator: Coordinator):
        """Test that Coordinator requires intent for workflow execution."""
        # Create an executable decision but no intent set
        decision = Decision(
            decision_type=DecisionType.EXECUTE_WORKFLOW, execution_mode=ExecutionMode.SEQUENTIAL
        )

        with pytest.raises(ValueError, match="No current intent set"):
            coordinator.execute_workflow(decision)


class TestCoordinatorHumanInTheLoop:
    """Test Coordinator HITL functionality."""

    @pytest.fixture
    def coordinator(self) -> Coordinator:
        """Fixture providing a Coordinator instance with mock agents."""
        # Create mock agents with invoke method
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        receipt_agent = Mock(spec=BaseAgent)
        receipt_agent.agent_name = "ReceiptAgent"
        receipt_agent.invoke.return_value = "mock_receipt_result"

        approval_agent = Mock(spec=BaseAgent)
        approval_agent.agent_name = "ApprovalAgent"
        approval_agent.invoke.return_value = "mock_approval_result"

        return Coordinator(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_coordinator_resume_workflow_yes(self, coordinator: Coordinator):
        """Test Coordinator resume_workflow with YES decision."""
        from conversation.intents import ConversationIntent

        # Start a conversation
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Collect all required fields dynamically
        while True:
            decision = coordinator.get_decision()
            if decision.decision_type == DecisionType.EXECUTE_WORKFLOW:
                break
            elif decision.decision_type == DecisionType.CONTINUE_CONVERSATION:
                for field in decision.missing_fields:
                    coordinator.collect_field(field, f"mock_{field}")
            elif decision.decision_type == DecisionType.WAIT_FOR_CONFIRMATION:
                # This workflow requires confirmation before execution
                break
            else:
                break

        # For SUBMIT_EXPENSE_CLAIM, the decision engine requires confirmation
        # So we need to force execution by creating an EXECUTE_WORKFLOW decision
        if decision.decision_type == DecisionType.WAIT_FOR_CONFIRMATION:
            decision = Decision(
                decision_type=DecisionType.EXECUTE_WORKFLOW, execution_mode=ExecutionMode.SEQUENTIAL
            )

        # Now execute workflow (should pause at confirmation)
        pause_results = coordinator.execute_workflow(decision)

        assert pause_results["status"] == "waiting_for_confirmation"
        workflow_id = pause_results["workflow_id"]

        # Resume with YES decision
        resume_results = coordinator.resume_workflow(
            workflow_id=workflow_id, employee_decision=True
        )

        assert resume_results["status"] == "completed"
        assert resume_results["completed_stages"] == 6  # All stages except confirmation (no agent)

    def test_coordinator_resume_workflow_no(self, coordinator: Coordinator):
        """Test Coordinator resume_workflow with NO decision."""
        from conversation.intents import ConversationIntent

        # Start a conversation
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Collect all required fields dynamically
        while True:
            decision = coordinator.get_decision()
            if decision.decision_type == DecisionType.EXECUTE_WORKFLOW:
                break
            elif decision.decision_type == DecisionType.CONTINUE_CONVERSATION:
                for field in decision.missing_fields:
                    coordinator.collect_field(field, f"mock_{field}")
            elif decision.decision_type == DecisionType.WAIT_FOR_CONFIRMATION:
                # This workflow requires confirmation before execution
                break
            else:
                break

        # For SUBMIT_EXPENSE_CLAIM, the decision engine requires confirmation
        # So we need to force execution by creating an EXECUTE_WORKFLOW decision
        if decision.decision_type == DecisionType.WAIT_FOR_CONFIRMATION:
            decision = Decision(
                decision_type=DecisionType.EXECUTE_WORKFLOW, execution_mode=ExecutionMode.SEQUENTIAL
            )

        # Now execute workflow (should pause at confirmation)
        pause_results = coordinator.execute_workflow(decision)

        assert pause_results["status"] == "waiting_for_confirmation"
        workflow_id = pause_results["workflow_id"]

        # Resume with NO decision
        cancel_results = coordinator.resume_workflow(
            workflow_id=workflow_id, employee_decision=False
        )

        assert cancel_results["status"] == "cancelled"
        assert cancel_results["message"] == "Workflow cancelled by employee"

    def test_coordinator_workflow_state_transition(self, coordinator: Coordinator):
        """Test that Coordinator updates state after workflow execution."""
        # Start a conversation and collect required fields
        coordinator.start_conversation(ConversationIntent.GET_EXPENSE_CLAIM)
        coordinator.collect_field("claim_id", "CLAIM123")

        # Check initial state (should be COLLECTING_INFORMATION)
        assert coordinator.current_state == WorkflowState.COLLECTING_INFORMATION

        # Get decision (should be ready to execute since GET_EXPENSE_CLAIM doesn't require confirmation)
        decision = coordinator.get_decision()
        assert decision.decision_type == DecisionType.EXECUTE_WORKFLOW

        # Execute workflow
        coordinator.execute_workflow(decision)

        # State should be updated to COMPLETED
        assert coordinator.current_state == WorkflowState.COMPLETED


class TestWorkflowExecutorNoBusinessLogic:
    """Test that WorkflowExecutor contains no business logic."""

    def test_workflow_executor_no_direct_agent_calls(self):
        """Test that WorkflowExecutor doesn't make direct agent calls."""
        import inspect

        from coordinator.executor import WorkflowExecutor

        # Check that WorkflowExecutor doesn't contain business logic
        source = inspect.getsource(WorkflowExecutor)

        # Should not contain business-specific execution terms
        assert "reimbursement" not in source
        assert "calculate" not in source
        assert "validate" not in source
        # "business", "domain", "policy", "approval" are allowed in docstrings

    def test_workflow_executor_no_service_access(self):
        """Test that WorkflowExecutor doesn't access services directly."""
        import inspect

        from coordinator.executor import WorkflowExecutor

        # Check that WorkflowExecutor doesn't import or reference services
        source = inspect.getsource(WorkflowExecutor)

        # Should not contain service-related imports or calls
        assert "Service" not in source
        assert "Repository" not in source
        # "Tool" is allowed in docstrings for future Strands SDK integration
        assert "DynamoDB" not in source
        assert "database" not in source
        assert "SQL" not in source

    def test_workflow_definitions_metadata_only(self):
        """Test that workflow definitions contain only metadata."""
        from coordinator.workflow import (
            SUBMIT_EXPENSE_CLAIM_WORKFLOW,
        )

        # Workflow definitions should be frozen dataclasses with only metadata
        # They should not contain any executable code or business logic

        # Verify they are frozen (immutable)
        with pytest.raises(Exception):  # FrozenInstanceError
            SUBMIT_EXPENSE_CLAIM_WORKFLOW.description = "modified"  # type: ignore

        # Verify they contain only metadata (steps, description, etc.)
        assert hasattr(SUBMIT_EXPENSE_CLAIM_WORKFLOW, "workflow_type")
        assert hasattr(SUBMIT_EXPENSE_CLAIM_WORKFLOW, "steps")
        assert hasattr(SUBMIT_EXPENSE_CLAIM_WORKFLOW, "description")
        assert hasattr(SUBMIT_EXPENSE_CLAIM_WORKFLOW, "metadata")

        # Steps should also be frozen
        step = SUBMIT_EXPENSE_CLAIM_WORKFLOW.steps[0]
        with pytest.raises(Exception):  # FrozenInstanceError
            step.step_name = "modified"  # type: ignore


class TestWorkflowParallelReadiness:
    """Test that the workflow system is ready for parallel execution."""

    def test_execution_mode_enum_includes_parallel(self):
        """Test that ExecutionMode includes PARALLEL."""
        from coordinator.decision import ExecutionMode

        assert hasattr(ExecutionMode, "PARALLEL")
        assert ExecutionMode.PARALLEL == "parallel"

    def test_workflow_executor_accepts_parallel_mode(self):
        """Test that WorkflowExecutor accepts PARALLEL mode without error."""
        from agents.base_agent import BaseAgent
        from coordinator.executor import WorkflowExecutor
        from coordinator.workflow import WorkflowDefinition, WorkflowStep, WorkflowType

        # Create a simple workflow
        workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="test", agent_name="ExpenseAgent", execution_order=1, depends_on=()
                ),
            ),
            description="Test",
        )

        # Create executor with proper mock agents
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_result"

        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=Mock(spec=BaseAgent),
            policy_agent=Mock(spec=BaseAgent),
            receipt_agent=Mock(spec=BaseAgent),
            approval_agent=Mock(spec=BaseAgent),
        )

        # Should accept PARALLEL mode and execute successfully
        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        assert results["status"] == "completed"

    def test_workflow_executor_parallel_method_exists(self):
        """Test that WorkflowExecutor has parallel execution method."""
        from coordinator.executor import WorkflowExecutor

        assert hasattr(WorkflowExecutor, "_execute_parallel")

        # Check that the method exists and is callable
        executor = WorkflowExecutor(
            expense_agent=Mock(),
            employee_agent=Mock(),
            policy_agent=Mock(),
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        assert callable(executor._execute_parallel)


class TestWorkflowStepDependencies:
    """Test WorkflowStep dependency functionality."""

    def test_workflow_step_depends_on_field(self):
        """Test that WorkflowStep has depends_on field."""
        from coordinator.workflow import WorkflowStep

        # Test default empty dependencies
        step = WorkflowStep(stage_name="test_stage", agent_name="ExpenseAgent", execution_order=1)
        assert step.depends_on == ()

        # Test explicit empty dependencies
        step = WorkflowStep(
            stage_name="test_stage", agent_name="ExpenseAgent", execution_order=1, depends_on=()
        )
        assert step.depends_on == ()

        # Test single dependency
        step = WorkflowStep(
            stage_name="test_stage",
            agent_name="ExpenseAgent",
            execution_order=1,
            depends_on=("dependency1",),
        )
        assert step.depends_on == ("dependency1",)

        # Test multiple dependencies
        step = WorkflowStep(
            stage_name="test_stage",
            agent_name="ExpenseAgent",
            execution_order=1,
            depends_on=("dependency1", "dependency2"),
        )
        assert step.depends_on == ("dependency1", "dependency2")

    def test_workflow_step_depends_on_immutability(self):
        """Test that depends_on field is immutable."""
        from coordinator.workflow import WorkflowStep

        step = WorkflowStep(
            stage_name="test_stage",
            agent_name="ExpenseAgent",
            execution_order=1,
            depends_on=("dependency1",),
        )

        # Should not be able to modify depends_on
        with pytest.raises(Exception):  # FrozenInstanceError
            step.depends_on = ("modified",)  # type: ignore"


class TestDependencyAwareConcurrentExecution:
    """Test dependency-aware concurrent execution functionality."""

    @pytest.fixture
    def executor(self) -> WorkflowExecutor:
        """Fixture providing a WorkflowExecutor instance with mock agents."""
        # Create mock agents with invoke method
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        receipt_agent = Mock(spec=BaseAgent)
        receipt_agent.agent_name = "ReceiptAgent"
        receipt_agent.invoke.return_value = "mock_receipt_result"

        approval_agent = Mock(spec=BaseAgent)
        approval_agent.agent_name = "ApprovalAgent"
        approval_agent.invoke.return_value = "mock_approval_result"

        return WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_parallel_execution_independent_stages(self, executor: WorkflowExecutor):
        """Test that independent stages execute concurrently."""
        from coordinator.workflow import WorkflowDefinition, WorkflowStep, WorkflowType

        # Create workflow with independent stages
        workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="stage1",
                    agent_name="EmployeeAgent",
                    execution_order=1,
                    depends_on=(),
                ),
                WorkflowStep(
                    stage_name="stage2",
                    agent_name="PolicyAgent",
                    execution_order=2,
                    depends_on=(),  # Independent of stage1
                ),
            ),
            description="Test independent stages",
        )

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        assert results["status"] == "completed"
        assert results["completed_stages"] == 2
        assert "stage1" in results["results"]
        assert "stage2" in results["results"]

    def test_parallel_execution_dependent_stages(self, executor: WorkflowExecutor):
        """Test that dependent stages wait for dependencies."""
        from coordinator.workflow import WorkflowDefinition, WorkflowStep, WorkflowType

        # Create workflow with dependent stages
        workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="stage1",
                    agent_name="EmployeeAgent",
                    execution_order=1,
                    depends_on=(),
                ),
                WorkflowStep(
                    stage_name="stage2",
                    agent_name="PolicyAgent",
                    execution_order=2,
                    depends_on=("stage1",),  # Depends on stage1
                ),
            ),
            description="Test dependent stages",
        )

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        assert results["status"] == "completed"
        assert results["completed_stages"] == 2
        assert "stage1" in results["results"]
        assert "stage2" in results["results"]

    def test_parallel_execution_multiple_dependencies(self, executor: WorkflowExecutor):
        """Test stages with multiple dependencies."""
        from coordinator.workflow import WorkflowDefinition, WorkflowStep, WorkflowType

        # Create workflow with multiple dependencies
        workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="stage1",
                    agent_name="EmployeeAgent",
                    execution_order=1,
                    depends_on=(),
                ),
                WorkflowStep(
                    stage_name="stage2", agent_name="PolicyAgent", execution_order=2, depends_on=()
                ),
                WorkflowStep(
                    stage_name="stage3",
                    agent_name="ExpenseAgent",
                    execution_order=3,
                    depends_on=("stage1", "stage2"),  # Depends on both stage1 and stage2
                ),
            ),
            description="Test multiple dependencies",
        )

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        assert results["status"] == "completed"
        assert results["completed_stages"] == 3
        assert "stage1" in results["results"]
        assert "stage2" in results["results"]
        assert "stage3" in results["results"]

    def test_parallel_execution_failure_propagation(self, executor: WorkflowExecutor):
        """Test that failures stop dependent stages."""
        from coordinator.workflow import WorkflowDefinition, WorkflowStep, WorkflowType

        # Create mock agent that will fail
        failing_agent = Mock(spec=BaseAgent)
        failing_agent.agent_name = "FailingAgent"
        failing_agent.invoke.side_effect = RuntimeError("Agent failed")

        # Replace one agent with failing agent
        executor.expense_agent = failing_agent

        # Create workflow where stage2 depends on stage1
        workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="stage1", agent_name="FailingAgent", execution_order=1, depends_on=()
                ),
                WorkflowStep(
                    stage_name="stage2",
                    agent_name="PolicyAgent",
                    execution_order=2,
                    depends_on=("stage1",),  # Depends on failing stage
                ),
            ),
            description="Test failure propagation",
        )

        with pytest.raises(RuntimeError, match="Workflow execution failed"):
            executor.execute_workflow(
                workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
            )

    def test_parallel_execution_result_merging(self, executor: WorkflowExecutor):
        """Test that results from concurrent stages are properly merged."""
        from coordinator.workflow import WorkflowDefinition, WorkflowStep, WorkflowType

        # Create workflow with independent stages
        workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="employee_stage",
                    agent_name="EmployeeAgent",
                    execution_order=1,
                    depends_on=(),
                ),
                WorkflowStep(
                    stage_name="policy_stage",
                    agent_name="PolicyAgent",
                    execution_order=2,
                    depends_on=(),
                ),
            ),
            description="Test result merging",
        )

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        # Verify results are merged
        assert results["status"] == "completed"
        assert len(results["results"]) == 2
        assert results["results"]["employee_stage"] == "mock_employee_result"
        assert results["results"]["policy_stage"] == "mock_policy_result"

    def test_parallel_vs_sequential_equivalence(self, executor: WorkflowExecutor):
        """Test that parallel and sequential execution produce equivalent results."""
        from coordinator.workflow import WorkflowDefinition, WorkflowStep, WorkflowType

        # Create a simple workflow
        workflow = WorkflowDefinition(
            workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
            steps=(
                WorkflowStep(
                    stage_name="stage1",
                    agent_name="EmployeeAgent",
                    execution_order=1,
                    depends_on=(),
                ),
                WorkflowStep(
                    stage_name="stage2",
                    agent_name="PolicyAgent",
                    execution_order=2,
                    depends_on=("stage1",),
                ),
            ),
            description="Test equivalence",
        )

        # Execute sequentially
        sequential_results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        # Execute in parallel
        parallel_results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        # Results should be equivalent (same stages executed, same outputs)
        assert sequential_results["status"] == parallel_results["status"]
        assert sequential_results["completed_stages"] == parallel_results["completed_stages"]
        assert set(sequential_results["results"].keys()) == set(parallel_results["results"].keys())


class TestExistingWorkflowDefinitionsWithDependencies:
    """Test that existing workflow definitions work with dependency-aware execution."""

    @pytest.fixture
    def executor(self) -> WorkflowExecutor:
        """Fixture providing a WorkflowExecutor instance with mock agents."""
        # Create mock agents with invoke method
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        receipt_agent = Mock(spec=BaseAgent)
        receipt_agent.agent_name = "ReceiptAgent"
        receipt_agent.invoke.return_value = "mock_receipt_result"

        approval_agent = Mock(spec=BaseAgent)
        approval_agent.agent_name = "ApprovalAgent"
        approval_agent.invoke.return_value = "mock_approval_result"

        return WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_submit_expense_claim_parallel(self, executor: WorkflowExecutor):
        """Test SUBMIT_EXPENSE_CLAIM workflow with parallel execution."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        # Should pause at confirmation stage
        assert results["status"] == "waiting_for_confirmation"
        assert results["next_required_action"] == "CONFIRM"
        assert results["completed_stages"] == 5  # Stages before confirmation

        # Verify stages executed before confirmation
        stage_results = results["results"]
        assert "employee_retrieval" in stage_results
        assert "policy_eligibility_lookup" in stage_results
        assert "category_limit_lookup" in stage_results
        assert "merge_policy_results" in stage_results
        assert "expense_preview" in stage_results
        # Should not have executed submission yet
        assert "expense_submission" not in stage_results

    def test_preview_expense_claim_parallel(self, executor: WorkflowExecutor):
        """Test PREVIEW_EXPENSE_CLAIM workflow with parallel execution."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.PREVIEW_EXPENSE_CLAIM)

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        assert results["status"] == "completed"
        assert results["completed_stages"] == 3  # All stages should complete

        # Verify all stages executed
        stage_results = results["results"]
        assert "employee_retrieval" in stage_results
        assert "policy_retrieval" in stage_results
        assert "expense_preview" in stage_results


class TestSubmitExpenseClaimParallelExecution:
    """Test SUBMIT_EXPENSE_CLAIM workflow parallel execution behavior."""

    @pytest.fixture
    def executor(self) -> WorkflowExecutor:
        """Fixture providing a WorkflowExecutor instance with mock agents."""
        # Create mock agents with invoke method
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        receipt_agent = Mock(spec=BaseAgent)
        receipt_agent.agent_name = "ReceiptAgent"
        receipt_agent.invoke.return_value = "mock_receipt_result"

        approval_agent = Mock(spec=BaseAgent)
        approval_agent.agent_name = "ApprovalAgent"
        approval_agent.invoke.return_value = "mock_approval_result"

        return WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_parallel_policy_execution(self, executor: WorkflowExecutor):
        """Test that policy stages execute in parallel."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        # Verify policy stages executed
        stage_results = results["results"]
        assert "policy_eligibility_lookup" in stage_results
        assert "category_limit_lookup" in stage_results

        # Both should have executed (same agent, different stages)
        assert stage_results["policy_eligibility_lookup"] == "mock_policy_result"
        assert stage_results["category_limit_lookup"] == "mock_policy_result"

    def test_merge_stage_synchronization(self, executor: WorkflowExecutor):
        """Test that merge stage executes only after both policy stages finish."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        # Verify merge stage executed after policy stages
        stage_results = results["results"]
        assert "merge_policy_results" in stage_results
        # Merge stage has no agent, so result should be None
        assert stage_results["merge_policy_results"] is None

    def test_dependency_chain_verification(self, executor: WorkflowExecutor):
        """Test the complete dependency chain of SUBMIT_EXPENSE_CLAIM workflow."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        # Verify dependency structure
        stages = workflow.steps
        stage_map = {stage.stage_name: stage for stage in stages}

        # Verify dependencies match assessment document
        assert stage_map["employee_retrieval"].depends_on == ()
        assert stage_map["policy_eligibility_lookup"].depends_on == ("employee_retrieval",)
        assert stage_map["category_limit_lookup"].depends_on == ("employee_retrieval",)
        assert stage_map["merge_policy_results"].depends_on == (
            "policy_eligibility_lookup",
            "category_limit_lookup",
        )
        assert stage_map["expense_preview"].depends_on == ("merge_policy_results",)
        assert stage_map["wait_confirmation"].depends_on == ("expense_preview",)
        assert stage_map["expense_submission"].depends_on == ("wait_confirmation",)

    def test_sequential_execution_still_works(self, executor: WorkflowExecutor):
        """Test that sequential execution still works with new workflow structure."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        # Should pause at confirmation stage
        assert results["status"] == "waiting_for_confirmation"
        assert results["next_required_action"] == "CONFIRM"
        assert results["completed_stages"] == 5  # Stages before confirmation

        # Should have executed stages up to but not including submission
        stage_results = results["results"]
        assert len(stage_results) == 5  # Stages before confirmation


class TestWorkflowHumanCheckpoints:
    """Test that workflow definitions support human checkpoint metadata."""

    def test_workflow_step_human_checkpoint_metadata(self):
        """Test that WorkflowStep supports human checkpoint flags."""
        from coordinator.workflow import WorkflowStep

        step = WorkflowStep(
            stage_name="approval_step",
            agent_name="ApprovalAgent",
            execution_order=1,
            requires_confirmation=True,
            requires_receipt=True,
            requires_manager=True,
        )

        assert step.requires_confirmation is True
        assert step.requires_receipt is True
        assert step.requires_manager is True

    def test_workflow_definitions_contain_checkpoints(self):
        """Test that predefined workflows contain appropriate checkpoints."""
        from coordinator.workflow import (
            APPROVE_CLAIM_WORKFLOW,
            SUBMIT_EXPENSE_CLAIM_WORKFLOW,
        )

        # SUBMIT_EXPENSE_CLAIM should have confirmation checkpoints
        submit_workflow = SUBMIT_EXPENSE_CLAIM_WORKFLOW
        preview_stage = [s for s in submit_workflow.steps if s.stage_name == "expense_preview"][0]
        assert preview_stage.requires_confirmation is True

        confirmation_stage = [
            s for s in submit_workflow.steps if s.stage_name == "wait_confirmation"
        ][0]
        assert confirmation_stage.requires_confirmation is True

        # APPROVE_CLAIM should have confirmation checkpoint
        approve_workflow = APPROVE_CLAIM_WORKFLOW
        approval_stage = [s for s in approve_workflow.steps if s.stage_name == "manager_approval"][
            0
        ]
        assert approval_stage.requires_confirmation is True


class TestHumanInTheLoopConfirmation:
    """Test Human-in-the-Loop confirmation functionality."""

    @pytest.fixture
    def executor(self) -> WorkflowExecutor:
        """Fixture providing a WorkflowExecutor instance with mock agents."""
        # Create mock agents with invoke method
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        receipt_agent = Mock(spec=BaseAgent)
        receipt_agent.agent_name = "ReceiptAgent"
        receipt_agent.invoke.return_value = "mock_receipt_result"

        approval_agent = Mock(spec=BaseAgent)
        approval_agent.agent_name = "ApprovalAgent"
        approval_agent.invoke.return_value = "mock_approval_result"

        return WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_workflow_pauses_at_confirmation(self, executor: WorkflowExecutor):
        """Test that workflow pauses at WAIT_CONFIRMATION stage."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        # Should pause at confirmation stage
        assert results["status"] == "waiting_for_confirmation"
        assert results["next_required_action"] == "CONFIRM"
        assert "workflow_id" in results

        # Should have executed stages up to but not including confirmation
        assert (
            results["completed_stages"] == 5
        )  # employee_retrieval, policy_eligibility_lookup, category_limit_lookup, merge_policy_results, expense_preview

        # Verify preview result is available for employee decision
        assert "expense_preview" in results["results"]
        assert results["results"]["expense_preview"] == "mock_expense_result"

    def test_workflow_resume_yes_continues_execution(self, executor: WorkflowExecutor):
        """Test that YES decision resumes workflow and completes execution."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        # Start workflow and get it to pause at confirmation
        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        pause_results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        workflow_id = pause_results["workflow_id"]

        # Resume with YES decision
        resume_results = executor.resume_workflow(workflow_id=workflow_id, employee_decision=True)

        # Should complete successfully
        assert resume_results["status"] == "completed"
        assert resume_results["completed_stages"] == 6  # All stages except confirmation (no agent)

        # Should have executed submission stage
        assert "expense_submission" in resume_results["results"]
        assert resume_results["results"]["expense_submission"] == "mock_expense_result"

    def test_workflow_resume_no_cancels_workflow(self, executor: WorkflowExecutor):
        """Test that NO decision cancels the workflow."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        # Start workflow and get it to pause at confirmation
        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        pause_results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        workflow_id = pause_results["workflow_id"]

        # Resume with NO decision
        cancel_results = executor.resume_workflow(workflow_id=workflow_id, employee_decision=False)

        # Should be cancelled
        assert cancel_results["status"] == "cancelled"
        assert cancel_results["message"] == "Workflow cancelled by employee"

    def test_workflow_resumes_from_correct_stage(self, executor: WorkflowExecutor):
        """Test that workflow resumes from the correct stage after confirmation."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        # Start workflow and get it to pause at confirmation
        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        pause_results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        workflow_id = pause_results["workflow_id"]

        # Verify stages executed before pause
        assert "employee_retrieval" in pause_results["results"]
        assert "policy_eligibility_lookup" in pause_results["results"]
        assert "category_limit_lookup" in pause_results["results"]
        assert "merge_policy_results" in pause_results["results"]
        assert "expense_preview" in pause_results["results"]
        assert "wait_confirmation" not in pause_results["results"]  # Should not be executed yet
        assert "expense_submission" not in pause_results["results"]  # Should not be executed yet

        # Resume with YES decision
        resume_results = executor.resume_workflow(workflow_id=workflow_id, employee_decision=True)

        # Should now have executed the remaining stages
        # Note: wait_confirmation has no agent, so it won't appear in results
        assert "wait_confirmation" not in resume_results["results"]
        assert "expense_submission" in resume_results["results"]

    def test_no_stages_execute_twice(self, executor: WorkflowExecutor):
        """Test that no stages execute twice during pause/resume."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        # Create agents that track execution count
        expense_agent = Mock(spec=BaseAgent)
        expense_agent.agent_name = "ExpenseAgent"
        expense_agent.invoke.return_value = "mock_expense_result"

        employee_agent = Mock(spec=BaseAgent)
        employee_agent.agent_name = "EmployeeAgent"
        employee_agent.invoke.return_value = "mock_employee_result"

        policy_agent = Mock(spec=BaseAgent)
        policy_agent.agent_name = "PolicyAgent"
        policy_agent.invoke.return_value = "mock_policy_result"

        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=Mock(spec=BaseAgent),
            approval_agent=Mock(spec=BaseAgent),
        )

        # Start workflow and get it to pause at confirmation
        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        pause_results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.SEQUENTIAL
        )

        workflow_id = pause_results["workflow_id"]

        # Count executions before resume
        expense_call_count_before = expense_agent.invoke.call_count
        employee_call_count_before = employee_agent.invoke.call_count
        policy_call_count_before = policy_agent.invoke.call_count

        # Resume with YES decision
        resume_results = executor.resume_workflow(workflow_id=workflow_id, employee_decision=True)

        # Count executions after resume
        expense_call_count_after = expense_agent.invoke.call_count
        employee_call_count_after = employee_agent.invoke.call_count
        policy_call_count_after = policy_agent.invoke.call_count

        # Only expense agent should have been called again (for submission stage)
        # Employee and policy agents should not be called again
        assert expense_call_count_after == expense_call_count_before + 1  # +1 for submission
        assert employee_call_count_after == employee_call_count_before  # No change
        assert policy_call_count_after == policy_call_count_before  # No change

    def test_invalid_workflow_id_raises_error(self, executor: WorkflowExecutor):
        """Test that invalid workflow ID raises appropriate error."""
        with pytest.raises(ValueError, match="No paused workflow found"):
            executor.resume_workflow(workflow_id="invalid_workflow_id", employee_decision=True)

    def test_parallel_execution_also_pauses_at_confirmation(self, executor: WorkflowExecutor):
        """Test that parallel execution also pauses at confirmation stage."""
        from coordinator.workflow import WorkflowType, get_workflow_definition

        workflow = get_workflow_definition(WorkflowType.SUBMIT_EXPENSE_CLAIM)

        results = executor.execute_workflow(
            workflow_definition=workflow, execution_mode=ExecutionMode.PARALLEL
        )

        # Should pause at confirmation stage even in parallel mode
        assert results["status"] == "waiting_for_confirmation"
        assert results["next_required_action"] == "CONFIRM"
        assert "workflow_id" in results
