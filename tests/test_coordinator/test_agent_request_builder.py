"""
Test AgentRequestBuilder Infrastructure.

This module contains pytest tests for the AgentRequestBuilder class to ensure
it correctly transforms workflow context into runtime business requests.
"""

from unittest.mock import Mock

import pytest

from coordinator.agent_request_builder import AgentRequestBuilder
from coordinator.workflow import WorkflowStep


class TestAgentRequestBuilderInitialization:
    """Test AgentRequestBuilder initialization and basic functionality."""

    def test_build_method_is_static(self):
        """Test that build method is static and can be called without instance."""
        # Should be callable without creating an instance
        assert hasattr(AgentRequestBuilder, "build")
        assert callable(AgentRequestBuilder.build)


class TestAgentRequestBuilderValidation:
    """Test AgentRequestBuilder input validation."""

    def test_build_raises_value_error_for_none_workflow_step(self):
        """Test that build raises ValueError for None workflow_step."""
        with pytest.raises(ValueError, match="workflow_step cannot be None"):
            AgentRequestBuilder.build(workflow_step=None, workflow_context={}, previous_results={})

    def test_build_raises_value_error_for_none_workflow_context(self):
        """Test that build raises ValueError for None workflow_context."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "test_stage"

        with pytest.raises(ValueError, match="workflow_context cannot be None"):
            AgentRequestBuilder.build(
                workflow_step=step, workflow_context=None, previous_results={}
            )

    def test_build_raises_value_error_for_none_previous_results(self):
        """Test that build raises ValueError for None previous_results."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "test_stage"

        with pytest.raises(ValueError, match="previous_results cannot be None"):
            AgentRequestBuilder.build(
                workflow_step=step, workflow_context={}, previous_results=None
            )


class TestAgentRequestBuilderDispatch:
    """Test AgentRequestBuilder dispatch mechanism."""

    def test_known_stage_uses_specific_builder(self):
        """Test that known stages use specific builders."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "employee_retrieval"
        step.agent_name = "EmployeeAgent"

        workflow_context = {"employee_id": "EMP001"}
        previous_results = {}

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Should contain employee retrieval specific content
        assert "Retrieve employee details" in result
        assert "Employee Information" in result

    def test_unknown_stage_uses_generic_builder(self):
        """Test that unknown stages use generic builder."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "unknown_stage"
        step.agent_name = "UnknownAgent"

        workflow_context = {}
        previous_results = {}

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Should contain generic content
        assert "Execute workflow stage: unknown_stage" in result
        assert "Agent: UnknownAgent" in result


class TestAgentRequestBuilderEmployeeRequest:
    """Test AgentRequestBuilder for employee retrieval requests."""

    def test_employee_retrieval_request_generation(self):
        """Test that employee retrieval request is generated correctly."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "employee_retrieval"
        step.agent_name = "EmployeeAgent"

        workflow_context = {"employee_id": "EMP001", "name": "John Doe"}
        previous_results = {}

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Verify the request structure
        assert "Retrieve employee details" in result
        assert "Employee Information" in result
        assert str(workflow_context) in result


class TestAgentRequestBuilderPolicyRequest:
    """Test AgentRequestBuilder for policy requests."""

    def test_policy_eligibility_request_generation(self):
        """Test that policy eligibility request is generated correctly."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "policy_eligibility_lookup"
        step.agent_name = "PolicyAgent"

        workflow_context = {"expense_category": "HOTEL"}
        previous_results = {
            "employee_retrieval": {
                "employee_id": "EMP001",
                "grade": "G5",
                "department": "Engineering",
            }
        }

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Verify the request structure
        assert "Retrieve the applicable expense policy" in result
        assert "Employee Information" in result
        assert "HOTEL" in result


class TestAgentRequestBuilderExpensePreviewRequest:
    """Test AgentRequestBuilder for expense preview requests."""

    def test_expense_preview_request_generation(self):
        """Test that expense preview request is generated correctly."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "expense_preview"
        step.agent_name = "ExpenseAgent"

        workflow_context = {
            "expense_items": [
                {
                    "category": "HOTEL",
                    "description": "Marriott",
                    "amount": 250.00,
                    "date": "2023-01-15",
                }
            ]
        }
        previous_results = {
            "employee_retrieval": {"employee_id": "EMP001", "name": "John Doe"},
            "policy_eligibility_lookup": {"policy_id": "POL001", "policy_name": "Standard"},
        }

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Verify the request structure
        assert "Generate an expense claim preview" in result
        assert "Employee Information" in result
        assert "Policy Information" in result
        assert "Expense Items" in result


class TestAgentRequestBuilderAllStages:
    """Test AgentRequestBuilder for all supported workflow stages."""

    @pytest.mark.parametrize(
        "stage_name,expected_content",
        [
            ("employee_retrieval", "Retrieve employee details"),
            ("policy_eligibility_lookup", "Retrieve the applicable expense policy"),
            ("category_limit_lookup", "Retrieve the expense category limits"),
            ("expense_preview", "Generate an expense claim preview"),
            ("expense_submission", "Submit this approved expense claim"),
            ("receipt_upload", "Upload and associate this receipt"),
            ("approval", "Approve or reject this expense claim"),
            ("policy_retrieval", "Retrieve expense policy details"),
            ("expense_retrieval", "Retrieve expense claim details"),
            ("receipt_validation", "Validate receipt for upload"),
            ("receipt_processing", "Process validated receipt"),
            ("receipt_association", "Associate processed receipt"),
            ("approval_validation", "Validate expense claim for approval"),
            ("manager_approval", "Request manager approval"),
            ("approval_notification", "Send approval notification"),
            ("rejection_validation", "Validate expense claim for rejection"),
            ("manager_rejection", "Request manager rejection"),
            ("rejection_notification", "Send rejection notification"),
            ("claims_listing", "List employee expense claims"),
            ("category_retrieval", "Retrieve expense category details"),
        ],
    )
    def test_all_known_stages_have_builders(self, stage_name, expected_content):
        """Test that all known workflow stages have corresponding builders."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = stage_name
        step.agent_name = "TestAgent"

        workflow_context = {"test": "data"}
        previous_results = {}

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Verify that the specific content is present
        assert expected_content in result


class TestAgentRequestBuilderPurity:
    """Test AgentRequestBuilder purity (no external dependencies)."""

    def test_agent_request_builder_has_no_agent_imports(self):
        """Test that AgentRequestBuilder doesn't import any agents."""
        # Check that the module doesn't import any agent classes
        import coordinator.agent_request_builder as builder_module

        # Get all attributes from the module
        module_attrs = dir(builder_module)

        # Check that no agent classes are imported
        agent_classes = [
            "EmployeeAgent",
            "PolicyAgent",
            "ExpenseAgent",
            "ReceiptAgent",
            "ApprovalAgent",
        ]
        for agent_class in agent_classes:
            assert agent_class not in module_attrs, (
                "AgentRequestBuilder should not import " + agent_class
            )

    def test_agent_request_builder_has_no_service_imports(self):
        """Test that AgentRequestBuilder doesn't import any services."""
        # Get the source code
        import inspect

        import coordinator.agent_request_builder as builder_module

        source = inspect.getsource(builder_module)

        # Check that no service imports are present
        service_imports = ["from services", "import services", "from .services", "from services."]
        for service_import in service_imports:
            assert service_import not in source, "AgentRequestBuilder should not import services"

    def test_agent_request_builder_has_no_repository_imports(self):
        """Test that AgentRequestBuilder doesn't import any repositories."""
        # Get the source code
        import inspect

        import coordinator.agent_request_builder as builder_module

        source = inspect.getsource(builder_module)

        # Check that no repository imports are present
        repo_imports = [
            "from repositories",
            "import repositories",
            "from .repositories",
            "from repositories.",
        ]
        for repo_import in repo_imports:
            assert repo_import not in source, "AgentRequestBuilder should not import repositories"

    def test_agent_request_builder_has_no_tool_imports(self):
        """Test that AgentRequestBuilder doesn't import any tools."""
        # Get the source code
        import inspect

        import coordinator.agent_request_builder as builder_module

        source = inspect.getsource(builder_module)

        # Check that no tool imports are present
        tool_imports = ["from tools", "import tools", "from .tools", "from tools."]
        for tool_import in tool_imports:
            assert tool_import not in source, "AgentRequestBuilder should not import tools"


class TestAgentRequestBuilderSimplifiedStructure:
    """Test that AgentRequestBuilder uses simplified structured context."""

    def test_employee_request_uses_structured_context(self):
        """Test that employee request uses structured context instead of manual field extraction."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "employee_retrieval"
        step.agent_name = "EmployeeAgent"

        workflow_context = {
            "employee_id": "EMP001",
            "name": "John Doe",
            "department": "Engineering",
        }
        previous_results = {}

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Should contain the entire structured context, not manually extracted fields
        assert str(workflow_context) in result
        # Should not contain manual field extraction patterns
        assert "Employee ID:\nEMP001" not in result  # Old manual extraction pattern

    def test_policy_request_uses_structured_context(self):
        """Test that policy request uses structured context instead of manual field extraction."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "policy_eligibility_lookup"
        step.agent_name = "PolicyAgent"

        workflow_context = {"expense_category": "HOTEL"}
        previous_results = {
            "employee_retrieval": {
                "employee_id": "EMP001",
                "grade": "G5",
                "department": "Engineering",
                "name": "John Doe",
            }
        }

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Should contain the entire structured context, not manually extracted fields
        assert str(previous_results.get("employee_retrieval")) in result
        # Should not contain manual field extraction patterns
        assert "Employee ID: EMP001" not in result  # Old manual extraction pattern
        assert "Grade: G5" not in result  # Old manual extraction pattern

    def test_expense_preview_uses_structured_context(self):
        """Test that expense preview request uses structured
        context instead of manual field extraction."""
        step = Mock(spec=WorkflowStep)
        step.stage_name = "expense_preview"
        step.agent_name = "ExpenseAgent"

        workflow_context = {
            "expense_items": [
                {
                    "category": "HOTEL",
                    "description": "Marriott",
                    "amount": 250.00,
                    "date": "2023-01-15",
                }
            ]
        }
        previous_results = {
            "employee_retrieval": {"employee_id": "EMP001", "name": "John Doe"},
            "policy_eligibility_lookup": {"policy_id": "POL001", "policy_name": "Standard"},
        }

        result = AgentRequestBuilder.build(step, workflow_context, previous_results)

        # Should contain the entire structured context, not manually extracted fields
        assert str(previous_results.get("employee_retrieval")) in result
        assert str(previous_results.get("policy_eligibility_lookup")) in result
        assert str(workflow_context.get("expense_items")) in result
        # Should not contain manual field extraction patterns
        assert "Employee ID: EMP001" not in result  # Old manual extraction pattern
        assert "Employee Name: John Doe" not in result  # Old manual extraction pattern
