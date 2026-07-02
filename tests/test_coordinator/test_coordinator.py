"""
Test Coordinator Infrastructure.

This module contains pytest tests for the Coordinator class to ensure
it functions correctly as the infrastructure layer.
"""

from unittest.mock import Mock

import pytest

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from coordinator import Coordinator, CoordinatorRequestBuilder, WorkflowState


class TestCoordinatorInitialization:
    """Test Coordinator initialization and basic functionality."""

    def test_initialization_with_valid_agents(self):
        """Test that Coordinator initializes correctly with valid agents."""
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

        # Initialize coordinator
        coordinator = Coordinator(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

        # Verify initialization
        assert coordinator.expense_agent == expense_agent
        assert coordinator.employee_agent == employee_agent
        assert coordinator.policy_agent == policy_agent
        assert coordinator.receipt_agent == receipt_agent
        assert coordinator.approval_agent == approval_agent
        assert coordinator.current_state == WorkflowState.STARTED

    def test_initialization_with_none_agents(self):
        """Test that Coordinator raises ValueError when any agent is None."""
        with pytest.raises(ValueError, match="All specialized agents must be provided"):
            Coordinator(
                expense_agent=None,  # type: ignore
                employee_agent=None,  # type: ignore
                policy_agent=None,  # type: ignore
                receipt_agent=None,  # type: ignore
                approval_agent=None,  # type: ignore
            )


class TestCoordinatorMethods:
    """Test Coordinator methods and functionality."""

    @pytest.fixture
    def coordinator(self) -> Coordinator:
        """Fixture providing a Coordinator instance with mock agents."""
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

        return Coordinator(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    def test_run_method_removed(self, coordinator: Coordinator):
        """Test that run method has been removed from Coordinator."""
        # run() method should not exist
        with pytest.raises(AttributeError):
            coordinator.run(test_param="value")

        # Should also work with no parameters
        with pytest.raises(AttributeError):
            coordinator.run()

    def test_status_method_returns_correct_structure(self, coordinator: Coordinator):
        """Test that status method returns expected structure."""
        status = coordinator.status()

        assert "state" in status
        assert "agents_initialized" in status
        assert "request_builder_ready" in status
        assert status["state"] == WorkflowState.STARTED
        assert all(status["agents_initialized"].values())
        assert status["request_builder_ready"] is True

    def test_get_request_builder_returns_builder_instance(self, coordinator: Coordinator):
        """Test that get_request_builder returns CoordinatorRequestBuilder instance."""
        builder = coordinator.get_request_builder()
        assert isinstance(builder, CoordinatorRequestBuilder)

    def test_reset_method(self, coordinator: Coordinator):
        """Test that reset method properly resets coordinator state."""
        # Change state first
        coordinator.shutdown()
        assert coordinator.current_state == WorkflowState.CANCELLED

        # Reset should return to STARTED
        coordinator.reset()
        assert coordinator.current_state == WorkflowState.STARTED

    def test_shutdown_method(self, coordinator: Coordinator):
        """Test that shutdown method sets state to CANCELLED."""
        coordinator.shutdown()
        assert coordinator.current_state == WorkflowState.CANCELLED

    def test_current_state_property(self, coordinator: Coordinator):
        """Test that current_state property returns WorkflowState."""
        assert isinstance(coordinator.current_state, WorkflowState)
        assert coordinator.current_state == WorkflowState.STARTED

    def test_repr_method(self, coordinator: Coordinator):
        """Test that __repr__ method returns expected format."""
        repr_str = repr(coordinator)
        assert "Coordinator" in repr_str
        assert "state=" in repr_str
        assert "started" in repr_str.lower()
