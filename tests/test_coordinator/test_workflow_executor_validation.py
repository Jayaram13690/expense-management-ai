"""
Test WorkflowExecutor Validation and Runtime Behavior.

This module contains pytest tests for the WorkflowExecutor class to ensure
it correctly executes workflows and handles various scenarios.
"""

from unittest.mock import Mock, patch

import pytest

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from coordinator.decision import ExecutionMode
from coordinator.executor import WorkflowExecutor
from coordinator.workflow import (
    SUBMIT_EXPENSE_CLAIM_WORKFLOW,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowType,
)


class TestWorkflowExecutorInitialization:
    """Test WorkflowExecutor initialization."""

    def test_initialization_requires_all_agents(self):
        """Test that WorkflowExecutor requires all agents to be provided."""
        with pytest.raises(ValueError, match="All specialized agents must be provided"):
            WorkflowExecutor(
                expense_agent=None,
                employee_agent=Mock(),
                policy_agent=Mock(),
                receipt_agent=Mock(),
                approval_agent=Mock(),
            )

    def test_initialization_creates_agent_registry(self):
        """Test that WorkflowExecutor creates agent registry correctly."""
        # Create mock agents
        expense_agent = Mock(spec=ExpenseAgent)
        expense_agent.agent_name = "ExpenseAgent"

        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=PolicyAgent)
        policy_agent.agent_name = "PolicyAgent"

        receipt_agent = Mock(spec=ReceiptAgent)
        receipt_agent.agent_name = "ReceiptAgent"

        approval_agent = Mock(spec=ApprovalAgent)
        approval_agent.agent_name = "ApprovalAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

        # Verify agent registry
        assert len(executor._agent_registry) == 5
        assert executor._agent_registry["ExpenseAgent"] is expense_agent
        assert executor._agent_registry["EmployeeAgent"] is employee_agent


class TestWorkflowExecutorParameterFix:
    """Test that WorkflowExecutor parameter issues are fixed."""

    def test_execute_step_uses_correct_parameters(self):
        """Test that _execute_step uses the correct parameters."""
        # Create mock agents
        expense_agent = Mock(spec=ExpenseAgent)
        expense_agent.agent_name = "ExpenseAgent"

        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=Mock(),
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        # Create a mock step
        step = Mock(spec=WorkflowStep)
        step.stage_name = "test_stage"
        step.agent_name = "EmployeeAgent"

        workflow_context = {"employee_id": "EMP001"}
        previous_results = {"previous": "results"}

        # Mock the AgentRequestBuilder.build method
        with patch("coordinator.executor.AgentRequestBuilder.build") as mock_build:
            mock_build.return_value = "test_request"

            # Mock the agent.invoke method
            employee_agent.invoke.return_value = "test_result"

            # Call _execute_step
            result = executor._execute_step(step, workflow_context, previous_results)

            # Verify AgentRequestBuilder.build was called with correct parameters
            mock_build.assert_called_once_with(
                workflow_step=step,
                workflow_context=workflow_context,
                previous_results=previous_results,
            )

            # Verify agent.invoke was called
            employee_agent.invoke.assert_called_once_with("test_request")

            # Verify result
            assert result == "test_result"


class TestWorkflowExecutorAgentRequestBuilderIntegration:
    """Test WorkflowExecutor integration with AgentRequestBuilder."""

    def test_executor_calls_agent_request_builder_build(self):
        """Test that WorkflowExecutor calls AgentRequestBuilder.build correctly."""
        # Create mock agents
        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=Mock(),
            employee_agent=employee_agent,
            policy_agent=Mock(),
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        # Create a mock step
        step = Mock(spec=WorkflowStep)
        step.stage_name = "employee_retrieval"
        step.agent_name = "EmployeeAgent"

        workflow_context = {"employee_id": "EMP001"}
        previous_results = {}

        # Mock the AgentRequestBuilder.build method
        with patch("coordinator.executor.AgentRequestBuilder.build") as mock_build:
            mock_build.return_value = "retrieve employee EMP001"

            # Mock the agent.invoke method
            employee_agent.invoke.return_value = {"employee_id": "EMP001", "name": "John Doe"}

            # Call _execute_step
            executor._execute_step(step, workflow_context, previous_results)

            # Verify AgentRequestBuilder.build was called once
            mock_build.assert_called_once()

            # Verify agent.invoke was called once
            employee_agent.invoke.assert_called_once()


class TestWorkflowExecutorSequentialExecution:
    """Test WorkflowExecutor sequential execution."""

    def test_sequential_execution_follows_correct_order(self):
        """Test that sequential execution follows the correct stage order."""
        # Create mock agents
        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=PolicyAgent)
        policy_agent.agent_name = "PolicyAgent"

        expense_agent = Mock(spec=ExpenseAgent)
        expense_agent.agent_name = "ExpenseAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        # Create a simple workflow definition
        workflow_definition = Mock(spec=WorkflowDefinition)
        workflow_definition.workflow_type = WorkflowType.SUBMIT_EXPENSE_CLAIM
        workflow_definition.steps = [
            Mock(
                spec=WorkflowStep,
                stage_name="employee_retrieval",
                agent_name="EmployeeAgent",
                execution_order=1,
                requires_confirmation=False,
                depends_on=(),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="policy_eligibility_lookup",
                agent_name="PolicyAgent",
                execution_order=2,
                requires_confirmation=False,
                depends_on=("employee_retrieval",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="expense_preview",
                agent_name="ExpenseAgent",
                execution_order=3,
                requires_confirmation=True,
                depends_on=("policy_eligibility_lookup",),
            ),
        ]

        # Mock agent responses
        employee_agent.invoke.return_value = {"employee_id": "EMP001"}
        policy_agent.invoke.return_value = {"policy_id": "POL001"}
        expense_agent.invoke.return_value = {"preview": "data"}

        # Execute workflow
        result = executor.execute_workflow(
            workflow_definition=workflow_definition, execution_mode=ExecutionMode.SEQUENTIAL
        )

        # Verify execution order
        assert employee_agent.invoke.call_count == 1
        assert policy_agent.invoke.call_count == 1
        assert expense_agent.invoke.call_count == 1

        # Verify workflow completed
        assert result["status"] == "completed"
        assert result["completed_stages"] == 3


class TestWorkflowExecutorHumanInTheLoop:
    """Test WorkflowExecutor human-in-the-loop functionality."""

    def test_workflow_pauses_at_confirmation_stage(self):
        """Test that workflow pauses at confirmation stage."""
        # Create mock agents
        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=PolicyAgent)
        policy_agent.agent_name = "PolicyAgent"

        expense_agent = Mock(spec=ExpenseAgent)
        expense_agent.agent_name = "ExpenseAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        # Create a workflow with confirmation stage
        workflow_definition = Mock(spec=WorkflowDefinition)
        workflow_definition.workflow_type = WorkflowType.SUBMIT_EXPENSE_CLAIM
        workflow_definition.steps = [
            Mock(
                spec=WorkflowStep,
                stage_name="employee_retrieval",
                agent_name="EmployeeAgent",
                execution_order=1,
                requires_confirmation=False,
                depends_on=(),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="policy_eligibility_lookup",
                agent_name="PolicyAgent",
                execution_order=2,
                requires_confirmation=False,
                depends_on=("employee_retrieval",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="expense_preview",
                agent_name="ExpenseAgent",
                execution_order=3,
                requires_confirmation=True,
                depends_on=("policy_eligibility_lookup",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="wait_confirmation",
                agent_name=None,
                execution_order=4,
                requires_confirmation=True,
                depends_on=("expense_preview",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="expense_submission",
                agent_name="ExpenseAgent",
                execution_order=5,
                requires_confirmation=False,
                depends_on=("wait_confirmation",),
            ),
        ]

        # Mock agent responses
        employee_agent.invoke.return_value = {"employee_id": "EMP001"}
        policy_agent.invoke.return_value = {"policy_id": "POL001"}
        expense_agent.invoke.return_value = {"preview": "data"}

        # Execute workflow
        result = executor.execute_workflow(
            workflow_definition=workflow_definition, execution_mode=ExecutionMode.SEQUENTIAL
        )

        # Verify workflow paused at confirmation
        assert result["status"] == "waiting_for_confirmation"
        assert result["next_required_action"] == "CONFIRM"
        assert result["completed_stages"] == 3  # Only 3 stages completed before pause

        # Verify expense submission was NOT called
        assert expense_agent.invoke.call_count == 1  # Only preview, not submission

    def test_workflow_resumes_from_paused_state(self):
        """Test that workflow can resume from paused state."""
        # Create mock agents
        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=PolicyAgent)
        policy_agent.agent_name = "PolicyAgent"

        expense_agent = Mock(spec=ExpenseAgent)
        expense_agent.agent_name = "ExpenseAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        # Create a workflow with confirmation stage
        workflow_definition = Mock(spec=WorkflowDefinition)
        workflow_definition.workflow_type = WorkflowType.SUBMIT_EXPENSE_CLAIM
        workflow_definition.steps = [
            Mock(
                spec=WorkflowStep,
                stage_name="employee_retrieval",
                agent_name="EmployeeAgent",
                execution_order=1,
                requires_confirmation=False,
                depends_on=(),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="policy_eligibility_lookup",
                agent_name="PolicyAgent",
                execution_order=2,
                requires_confirmation=False,
                depends_on=("employee_retrieval",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="expense_preview",
                agent_name="ExpenseAgent",
                execution_order=3,
                requires_confirmation=True,
                depends_on=("policy_eligibility_lookup",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="wait_confirmation",
                agent_name=None,
                execution_order=4,
                requires_confirmation=True,
                depends_on=("expense_preview",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="expense_submission",
                agent_name="ExpenseAgent",
                execution_order=5,
                requires_confirmation=False,
                depends_on=("wait_confirmation",),
            ),
        ]

        # Mock agent responses
        employee_agent.invoke.return_value = {"employee_id": "EMP001"}
        policy_agent.invoke.return_value = {"policy_id": "POL001"}
        expense_agent.invoke.return_value = {"preview": "data"}

        # Execute workflow initially (should pause)
        result1 = executor.execute_workflow(
            workflow_definition=workflow_definition, execution_mode=ExecutionMode.SEQUENTIAL
        )

        workflow_id = result1["workflow_id"]

        # Verify workflow paused
        assert result1["status"] == "waiting_for_confirmation"
        assert expense_agent.invoke.call_count == 1  # Only preview

        # Reset the mock to track new calls
        expense_agent.reset_mock()
        expense_agent.invoke.return_value = {"submission": "success"}

        # Resume workflow
        result2 = executor.resume_workflow(workflow_id=workflow_id, employee_decision=True)

        # Verify workflow completed
        assert result2["status"] == "completed"
        assert (
            result2["completed_stages"] == 4
        )  # All stages completed (wait_confirmation has no agent)

        # Verify expense submission was called (only after resume)
        assert expense_agent.invoke.call_count == 1  # Submission call


class TestWorkflowExecutorParallelExecution:
    """Test WorkflowExecutor parallel execution."""

    def test_parallel_execution_runs_independent_stages_concurrently(self):
        """Test that parallel execution runs independent stages concurrently."""
        # Create mock agents
        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=PolicyAgent)
        policy_agent.agent_name = "PolicyAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=Mock(),
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        # Create a workflow with parallel stages
        workflow_definition = Mock(spec=WorkflowDefinition)
        workflow_definition.workflow_type = WorkflowType.SUBMIT_EXPENSE_CLAIM
        workflow_definition.steps = [
            Mock(
                spec=WorkflowStep,
                stage_name="employee_retrieval",
                agent_name="EmployeeAgent",
                execution_order=1,
                requires_confirmation=False,
                depends_on=(),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="policy_eligibility_lookup",
                agent_name="PolicyAgent",
                execution_order=2,
                requires_confirmation=False,
                depends_on=("employee_retrieval",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="category_limit_lookup",
                agent_name="PolicyAgent",
                execution_order=3,
                requires_confirmation=False,
                depends_on=("employee_retrieval",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="merge_policy_results",
                agent_name=None,
                execution_order=4,
                requires_confirmation=False,
                depends_on=("policy_eligibility_lookup", "category_limit_lookup"),
            ),
        ]

        # Mock agent responses
        employee_agent.invoke.return_value = {"employee_id": "EMP001"}
        policy_agent.invoke.side_effect = [
            {"policy_eligibility": "data"},
            {"category_limits": "data"},
        ]

        # Execute workflow in parallel mode
        result = executor.execute_workflow(
            workflow_definition=workflow_definition, execution_mode=ExecutionMode.PARALLEL
        )

        # Verify both policy stages were executed
        assert policy_agent.invoke.call_count == 2

        # Verify workflow completed
        assert result["status"] == "completed"


class TestWorkflowExecutorFailurePropagation:
    """Test WorkflowExecutor failure propagation."""

    def test_failure_in_middle_stage_stops_execution(self):
        """Test that failure in middle stage stops further execution."""
        # Create mock agents
        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=PolicyAgent)
        policy_agent.agent_name = "PolicyAgent"

        expense_agent = Mock(spec=ExpenseAgent)
        expense_agent.agent_name = "ExpenseAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=Mock(),
            approval_agent=Mock(),
        )

        # Create a workflow
        workflow_definition = Mock(spec=WorkflowDefinition)
        workflow_definition.workflow_type = WorkflowType.SUBMIT_EXPENSE_CLAIM
        workflow_definition.steps = [
            Mock(
                spec=WorkflowStep,
                stage_name="employee_retrieval",
                agent_name="EmployeeAgent",
                execution_order=1,
                requires_confirmation=False,
                depends_on=(),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="policy_eligibility_lookup",
                agent_name="PolicyAgent",
                execution_order=2,
                requires_confirmation=False,
                depends_on=("employee_retrieval",),
            ),
            Mock(
                spec=WorkflowStep,
                stage_name="expense_preview",
                agent_name="ExpenseAgent",
                execution_order=3,
                requires_confirmation=False,
                depends_on=("policy_eligibility_lookup",),
            ),
        ]

        # Mock agent responses - policy agent will fail
        employee_agent.invoke.return_value = {"employee_id": "EMP001"}
        policy_agent.invoke.side_effect = RuntimeError("Policy service unavailable")

        # Execute workflow
        with pytest.raises(RuntimeError, match="Policy service unavailable"):
            executor.execute_workflow(
                workflow_definition=workflow_definition, execution_mode=ExecutionMode.SEQUENTIAL
            )

        # Verify expense agent was never called
        assert expense_agent.invoke.call_count == 0


class TestWorkflowExecutorPurity:
    """Test WorkflowExecutor purity (no direct service/repository/tool access)."""

    def test_workflow_executor_does_not_import_services(self):
        """Test that WorkflowExecutor doesn't import any services."""
        # Get the source code
        import inspect

        import coordinator.executor as executor_module

        source = inspect.getsource(executor_module)

        # Check that no service imports are present
        service_imports = ["from services", "import services", "from .services", "from services."]
        for service_import in service_imports:
            assert service_import not in source, "WorkflowExecutor should not import services"

    def test_workflow_executor_does_not_import_repositories(self):
        """Test that WorkflowExecutor doesn't import any repositories."""
        # Get the source code
        import inspect

        import coordinator.executor as executor_module

        source = inspect.getsource(executor_module)

        # Check that no repository imports are present
        repo_imports = [
            "from repositories",
            "import repositories",
            "from .repositories",
            "from repositories.",
        ]
        for repo_import in repo_imports:
            assert repo_import not in source, "WorkflowExecutor should not import repositories"

    def test_workflow_executor_does_not_import_tools(self):
        """Test that WorkflowExecutor doesn't import any tools."""
        # Get the source code
        import inspect

        import coordinator.executor as executor_module

        source = inspect.getsource(executor_module)

        # Check that no tool imports are present
        tool_imports = ["from tools", "import tools", "from .tools", "from tools."]
        for tool_import in tool_imports:
            assert tool_import not in source, "WorkflowExecutor should not import tools"


class TestWorkflowExecutorEndToEnd:
    """Test WorkflowExecutor end-to-end business journey."""

    def test_complete_expense_submission_journey(self):
        """Test complete expense submission journey with confirmation."""
        # Create mock agents
        employee_agent = Mock(spec=EmployeeAgent)
        employee_agent.agent_name = "EmployeeAgent"

        policy_agent = Mock(spec=PolicyAgent)
        policy_agent.agent_name = "PolicyAgent"

        expense_agent = Mock(spec=ExpenseAgent)
        expense_agent.agent_name = "ExpenseAgent"

        receipt_agent = Mock(spec=ReceiptAgent)
        receipt_agent.agent_name = "ReceiptAgent"

        approval_agent = Mock(spec=ApprovalAgent)
        approval_agent.agent_name = "ApprovalAgent"

        # Create executor
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

        # Use the actual SUBMIT_EXPENSE_CLAIM_WORKFLOW
        workflow_definition = SUBMIT_EXPENSE_CLAIM_WORKFLOW

        # Mock agent responses
        employee_agent.invoke.return_value = {
            "employee_id": "EMP001",
            "name": "John Doe",
            "grade": "G5",
            "department": "Engineering",
        }

        policy_agent.invoke.side_effect = [
            {"policy_id": "POL001", "policy_name": "Standard", "daily_limit": 200},
            {"category_limits": {"HOTEL": 250, "MEALS": 50}},
        ]

        expense_agent.invoke.side_effect = [
            {"preview": "expense preview data"},  # Preview stage
            {"submission_id": "EXP001", "status": "submitted"},  # Submission stage
        ]

        receipt_agent.invoke.return_value = {"receipt_id": "REC001", "status": "uploaded"}
        approval_agent.invoke.return_value = {"approval_id": "APP001", "status": "approved"}

        # Execute workflow - should pause at confirmation
        result1 = executor.execute_workflow(
            workflow_definition=workflow_definition,
            execution_mode=ExecutionMode.SEQUENTIAL,
            workflow_context={
                "employee_id": "EMP001",
                "expense_category": "HOTEL",
                "expense_items": [
                    {
                        "category": "HOTEL",
                        "description": "Marriott",
                        "amount": 250.00,
                        "date": "2023-01-15",
                    }
                ],
            },
        )

        workflow_id = result1["workflow_id"]

        # Verify paused at confirmation
        assert result1["status"] == "waiting_for_confirmation"
        assert (
            result1["completed_stages"] == 5
        )  # Up to expense_preview (includes merge_policy_results stage)

        # Verify agents called so far
        assert employee_agent.invoke.call_count == 1
        assert policy_agent.invoke.call_count == 2  # Both policy lookups
        assert expense_agent.invoke.call_count == 1  # Only preview
        assert receipt_agent.invoke.call_count == 0
        assert approval_agent.invoke.call_count == 0

        # Resume workflow
        result2 = executor.resume_workflow(workflow_id=workflow_id, employee_decision=True)

        # Verify completed
        assert result2["status"] == "completed"
        assert (
            result2["completed_stages"] == 6
        )  # All stages except wait_confirmation (skipped on resume)

        # Verify all agents called
        assert employee_agent.invoke.call_count == 1  # No additional calls
        assert policy_agent.invoke.call_count == 2  # No additional calls
        assert expense_agent.invoke.call_count == 2  # Preview + submission
        assert receipt_agent.invoke.call_count == 0  # Not in this workflow
        assert approval_agent.invoke.call_count == 0  # Not in this workflow
