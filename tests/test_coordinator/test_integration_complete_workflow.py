"""
Integration Test for Complete Workflow Execution.

This module contains integration tests that verify the complete end-to-end workflow
execution from Coordinator to real specialized agents, ensuring that all components
are properly integrated and no simulated execution paths remain.
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
    WorkflowType,
)


class TestCompleteWorkflowIntegration:
    """Test complete workflow integration with real agent invocations."""

    def test_complete_expense_submission_workflow_integration(self):
        """Test that the complete expense submission workflow integrates all agents correctly."""
        # Create real agent instances (they will be mocked for testing purposes)
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
        
        # Create executor with all agents
        executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )
        
        # Mock the AgentRequestBuilder to return specific requests for each stage
        with patch("coordinator.executor.AgentRequestBuilder.build") as mock_builder:
            # Set up the builder to return different requests for each stage
            def builder_side_effect(workflow_step, workflow_context, previous_results):
                stage_requests = {
                    "employee_retrieval": "Retrieve employee EMP001 details",
                    "policy_eligibility_lookup": "Check policy eligibility for travel expenses",
                    "category_limit_lookup": "Get category limits for travel",
                    "expense_preview": "Generate preview for travel expense claim",
                    "expense_submission": "Submit approved travel expense claim",
                }
                return stage_requests.get(workflow_step.stage_name, "Generic request")
            
            mock_builder.side_effect = builder_side_effect
            
            # Mock agent responses
            employee_agent.invoke.return_value = {
                "employee_id": "EMP001",
                "name": "John Doe",
                "grade": "G5",
                "department": "Engineering"
            }
            
            policy_agent.invoke.side_effect = [
                {"policy_id": "POL001", "reimbursement_rate": 0.8, "max_limit": 5000},
                {"category_id": "CAT001", "daily_limit": 200, "require_receipt": True}
            ]
            
            expense_agent.invoke.side_effect = [
                {"preview_id": "PREV001", "estimated_reimbursement": 1500.0, "currency": "USD"},
                {"claim_id": "CLAIM001", "status": "SUBMITTED", "amount": 1875.0}
            ]
            
            # Execute the workflow
            workflow_context = {
                "employee_id": "EMP001",
                "expense_category": "TRAVEL",
                "expense_items": [
                    {"date": "2023-01-01", "description": "Flight", "amount": 1200.0},
                    {"date": "2023-01-02", "description": "Hotel", "amount": 675.0}
                ]
            }
            
            # Execute sequentially (for easier testing)
            result = executor.execute_workflow(
                workflow_definition=SUBMIT_EXPENSE_CLAIM_WORKFLOW,
                execution_mode=ExecutionMode.SEQUENTIAL,
                **workflow_context
            )
            
            # Verify the workflow paused at confirmation stage
            assert result["status"] == "waiting_for_confirmation"
            assert result["next_required_action"] == "CONFIRM"
            assert result["completed_stages"] == 5  # Should have completed 5 stages before confirmation
            
            # Verify AgentRequestBuilder was called for each agent stage
            assert mock_builder.call_count == 4  # employee_retrieval, policy_eligibility_lookup, category_limit_lookup, expense_preview
            
            # Verify employee agent was invoked
            employee_agent.invoke.assert_called_once_with("Retrieve employee EMP001 details")
            
            # Verify policy agent was invoked twice (for parallel stages)
            assert policy_agent.invoke.call_count == 2
            policy_agent.invoke.assert_any_call("Check policy eligibility for travel expenses")
            policy_agent.invoke.assert_any_call("Get category limits for travel")
            
            # Verify expense agent was invoked once for preview
            expense_agent.invoke.assert_called_once_with("Generate preview for travel expense claim")
            
            # Verify results contain all stage outputs
            assert "employee_retrieval" in result["results"]
            assert "policy_eligibility_lookup" in result["results"]
            assert "category_limit_lookup" in result["results"]
            assert "expense_preview" in result["results"]
            
            # Verify employee retrieval result
            assert result["results"]["employee_retrieval"]["employee_id"] == "EMP001"
            assert result["results"]["employee_retrieval"]["name"] == "John Doe"
            
            # Verify policy results
            assert result["results"]["policy_eligibility_lookup"]["policy_id"] == "POL001"
            assert result["results"]["category_limit_lookup"]["category_id"] == "CAT001"
            
            # Verify expense preview result
            assert result["results"]["expense_preview"]["preview_id"] == "PREV001"
            assert result["results"]["expense_preview"]["estimated_reimbursement"] == 1500.0

    def test_workflow_resume_integration(self):
        """Test that workflow resume properly continues execution after confirmation."""
        # Create real agent instances
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
        
        # First, execute until confirmation (mocking the initial stages)
        with patch("coordinator.executor.AgentRequestBuilder.build") as mock_builder:
            mock_builder.side_effect = lambda workflow_step, workflow_context, previous_results: f"Request for {workflow_step.stage_name}"
            
            employee_agent.invoke.return_value = {"employee_id": "EMP001", "name": "John Doe"}
            policy_agent.invoke.side_effect = [
                {"policy_id": "POL001"},
                {"category_id": "CAT001"}
            ]
            expense_agent.invoke.return_value = {"preview_id": "PREV001"}
            
            workflow_context = {"employee_id": "EMP001", "expense_category": "TRAVEL"}
            
            # Execute until confirmation
            result = executor.execute_workflow(
                workflow_definition=SUBMIT_EXPENSE_CLAIM_WORKFLOW,
                execution_mode=ExecutionMode.SEQUENTIAL,
                **workflow_context
            )
            
            # Verify workflow is paused
            assert result["status"] == "waiting_for_confirmation"
            workflow_id = result["workflow_id"]
            
            # Now resume the workflow
            expense_agent.invoke.return_value = {"claim_id": "CLAIM001", "status": "SUBMITTED"}
            
            resume_result = executor.resume_workflow(
                workflow_id=workflow_id,
                employee_decision=True,
                execution_mode=ExecutionMode.SEQUENTIAL
            )
            
            # Verify workflow completed
            assert resume_result["status"] == "completed"
            assert resume_result["completed_stages"] == 6  # 4 agent stages + 1 merge + 1 submission
            assert "expense_submission" in resume_result["results"]
            
            # Verify expense agent was called for submission
            expense_agent.invoke.assert_any_call("Request for expense_submission")

    def test_parallel_execution_integration(self):
        """Test that parallel execution properly invokes multiple agents concurrently."""
        # Create agents
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
        
        with patch("coordinator.executor.AgentRequestBuilder.build") as mock_builder:
            mock_builder.side_effect = lambda workflow_step, workflow_context, previous_results: f"Request for {workflow_step.stage_name}"
            
            # Mock agent responses
            employee_agent.invoke.return_value = {"employee_id": "EMP001"}
            policy_agent.invoke.side_effect = [
                {"policy_id": "POL001"},
                {"category_id": "CAT001"}
            ]
            expense_agent.invoke.return_value = {"preview_id": "PREV001"}
            
            workflow_context = {"employee_id": "EMP001", "expense_category": "TRAVEL"}
            
            # Execute in parallel mode
            result = executor.execute_workflow(
                workflow_definition=SUBMIT_EXPENSE_CLAIM_WORKFLOW,
                execution_mode=ExecutionMode.PARALLEL,
                **workflow_context
            )
            
            # Verify parallel execution worked
            assert result["status"] == "waiting_for_confirmation"
            
            # Verify both policy stages were executed (in parallel)
            assert policy_agent.invoke.call_count == 2
            
            # Verify all stages completed up to confirmation
            assert result["completed_stages"] == 5


class TestAgentIntegrationVerification:
    """Verify that all agents are properly integrated and no simulated paths remain."""

    def test_no_simulated_execution_paths_remain(self):
        """Verify that WorkflowExecutor uses real agent invocations, not simulations."""
        # Create agents
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
        
        # Verify that _execute_step calls agent.invoke (not simulated execution)
        from coordinator.workflow import WorkflowStep
        
        step = Mock(spec=WorkflowStep)
        step.stage_name = "employee_retrieval"
        step.agent_name = "EmployeeAgent"
        
        workflow_context = {"employee_id": "EMP001"}
        previous_results = {}
        
        with patch("coordinator.executor.AgentRequestBuilder.build") as mock_builder:
            mock_builder.return_value = "test request"
            employee_agent.invoke.return_value = {"employee_id": "EMP001"}
            
            result = executor._execute_step(step, workflow_context, previous_results)
            
            # Verify that AgentRequestBuilder.build was called
            mock_builder.assert_called_once()
            
            # Verify that agent.invoke was called (not simulated execution)
            employee_agent.invoke.assert_called_once_with("test request")
            
            # Verify that the agent's result was returned
            assert result == {"employee_id": "EMP001"}

    def test_all_agent_types_are_integrated(self):
        """Verify that all agent types are properly integrated in the executor."""
        # Create all agent types
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
        
        # Verify all agents are in the registry
        assert len(executor._agent_registry) == 5
        assert executor._agent_registry["EmployeeAgent"] is employee_agent
        assert executor._agent_registry["PolicyAgent"] is policy_agent
        assert executor._agent_registry["ExpenseAgent"] is expense_agent
        assert executor._agent_registry["ReceiptAgent"] is receipt_agent
        assert executor._agent_registry["ApprovalAgent"] is approval_agent

    def test_agent_request_builder_integration(self):
        """Verify that AgentRequestBuilder is properly integrated with all workflow stages."""
        from coordinator.agent_request_builder import AgentRequestBuilder
        from coordinator.workflow import WorkflowStep
        
        # Test that all workflow stages have corresponding builders
        workflow_steps = [
            "employee_retrieval",
            "policy_eligibility_lookup", 
            "category_limit_lookup",
            "expense_preview",
            "expense_submission",
            "receipt_upload",
            "approval",
            "policy_retrieval",
            "expense_retrieval",
            "receipt_validation",
            "receipt_processing",
            "receipt_association",
            "approval_validation",
            "manager_approval",
            "approval_notification",
            "rejection_validation",
            "manager_rejection",
            "rejection_notification",
            "claims_listing",
            "category_retrieval"
        ]
        
        # Verify each stage has a builder
        for stage_name in workflow_steps:
            step = Mock(spec=WorkflowStep)
            step.stage_name = stage_name
            step.agent_name = "TestAgent"
            
            workflow_context = {}
            previous_results = {}
            
            # This should not raise an exception (builder exists)
            try:
                request = AgentRequestBuilder.build(step, workflow_context, previous_results)
                assert isinstance(request, str)
                assert len(request) > 0
            except Exception as e:
                pytest.fail(f"Stage {stage_name} should have a builder: {e}")