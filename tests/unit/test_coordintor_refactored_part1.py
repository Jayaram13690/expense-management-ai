"""
Test Refactored Coordinator Infrastructure.

This test verifies that the refactored Coordinator infrastructure works correctly
after removing NotImplementedError, simplifying methods, and reducing complexity.
"""

from unittest.mock import Mock

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from coordinator import Coordinator, CoordinatorRequestBuilder, WorkflowState


def test_refactored_coordinator():
    """Test that refactored Coordinator works correctly."""

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

    # Test Coordinator initialization
    coordinator = Coordinator(
        expense_agent=expense_agent,
        employee_agent=employee_agent,
        policy_agent=policy_agent,
        receipt_agent=receipt_agent,
        approval_agent=approval_agent,
    )

    # Verify initial state
    assert coordinator.current_state == WorkflowState.STARTED

    # Test run method (should not raise NotImplementedError)
    coordinator.run(test_param="value")  # Should execute without error

    # Test status method
    status = coordinator.status()
    assert status["state"] == WorkflowState.STARTED
    assert all(status["agents_initialized"].values())

    # Test request builder
    request_builder = coordinator.get_request_builder()
    assert isinstance(request_builder, CoordinatorRequestBuilder)

    # Test reset functionality
    coordinator.reset()
    assert coordinator.current_state == WorkflowState.STARTED

    # Test shutdown functionality
    coordinator.shutdown()
    assert coordinator.current_state == WorkflowState.CANCELLED

    print("Coordinator refactored test passed!")


def test_refactored_request_builder():
    """Test that refactored CoordinatorRequestBuilder works correctly."""

    builder = CoordinatorRequestBuilder()

    # Test adding fields
    builder.add_field("employee_id", "EMP123")
    builder.add_field("trip_name", "AWS Summit")

    # Test field retrieval
    assert builder.has_field("employee_id")
    assert builder.get_field("employee_id") == "EMP123"

    # Test method chaining
    result = builder.add_field("business_purpose", "Attend conference")
    assert result is builder

    # Test collected data
    collected = builder.get_collected_data()
    assert len(collected) == 3

    # Test clear functionality
    builder.clear()
    assert builder.get_collected_data() == {}

    # Test that build method no longer exists
    assert not hasattr(builder, "build")

    print("Request builder refactored test passed!")


def test_simplified_workflow_state():
    """Test that WorkflowState has been simplified correctly."""

    # Test that only essential states remain
    essential_states = [
        WorkflowState.STARTED,
        WorkflowState.COLLECTING_INFORMATION,
        WorkflowState.BUILDING_REQUEST,
        WorkflowState.READY_TO_EXECUTE,
        WorkflowState.EXECUTING,
        WorkflowState.WAITING_FOR_CONFIRMATION,
        WorkflowState.WAITING_FOR_RECEIPT,
        WorkflowState.WAITING_FOR_MANAGER,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    ]

    assert (
        len(essential_states) == 11
    )  # Should be 11 states now (removed EXECUTING_SEQUENTIAL and EXECUTING_PARALLEL)

    # Test that removed states no longer exist
    try:
        _ = WorkflowState.EXECUTING_SEQUENTIAL
        assert False, "EXECUTING_SEQUENTIAL should not exist"
    except AttributeError:
        pass  # Expected

    try:
        _ = WorkflowState.EXECUTING_PARALLEL
        assert False, "EXECUTING_PARALLEL should not exist"
    except AttributeError:
        pass  # Expected

    print("Workflow state simplified test passed!")


if __name__ == "__main__":
    test_refactored_coordinator()
    test_refactored_request_builder()
    test_simplified_workflow_state()
    print("\nAll Coordinator refactored tests passed!")
