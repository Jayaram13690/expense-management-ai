"""
Test WorkflowState Infrastructure.

This module contains pytest tests for the WorkflowState enumeration to ensure
it provides the correct states for workflow progression.
"""

import pytest

from coordinator.state import WorkflowState


class TestWorkflowStateEnum:
    """Test WorkflowState enumeration values and behavior."""

    def test_workflow_state_has_correct_values(self):
        """Test that WorkflowState has all expected values."""
        expected_states = [
            "started",
            "collecting_information",
            "building_request",
            "ready_to_execute",
            "executing",
            "waiting_for_confirmation",
            "waiting_for_receipt",
            "waiting_for_manager",
            "completed",
            "failed",
            "cancelled",
        ]

        actual_states = [state.value for state in WorkflowState]

        assert len(actual_states) == len(expected_states)
        assert set(actual_states) == set(expected_states)

    def test_workflow_state_is_str_enum(self):
        """Test that WorkflowState values are strings."""
        for state in WorkflowState:
            assert isinstance(state, str)
            assert isinstance(state.value, str)

    def test_workflow_state_values_match_enum_names(self):
        """Test that WorkflowState values match their enum names."""
        assert WorkflowState.STARTED == "started"
        assert WorkflowState.COLLECTING_INFORMATION == "collecting_information"
        assert WorkflowState.BUILDING_REQUEST == "building_request"
        assert WorkflowState.READY_TO_EXECUTE == "ready_to_execute"
        assert WorkflowState.EXECUTING == "executing"
        assert WorkflowState.WAITING_FOR_CONFIRMATION == "waiting_for_confirmation"
        assert WorkflowState.WAITING_FOR_RECEIPT == "waiting_for_receipt"
        assert WorkflowState.WAITING_FOR_MANAGER == "waiting_for_manager"
        assert WorkflowState.COMPLETED == "completed"
        assert WorkflowState.FAILED == "failed"
        assert WorkflowState.CANCELLED == "cancelled"

    def test_removed_execution_states_no_longer_exist(self):
        """Test that removed execution states are no longer present."""
        with pytest.raises(AttributeError):
            _ = WorkflowState.EXECUTING_SEQUENTIAL

        with pytest.raises(AttributeError):
            _ = WorkflowState.EXECUTING_PARALLEL

    def test_workflow_state_can_be_used_in_comparisons(self):
        """Test that WorkflowState can be used in comparisons."""
        state = WorkflowState.STARTED

        assert state == "started"
        assert state != "completed"
        assert state == WorkflowState.STARTED
        assert state != WorkflowState.COMPLETED

    def test_workflow_state_iteration(self):
        """Test that WorkflowState can be iterated over."""
        states = list(WorkflowState)
        assert len(states) == 11
        assert all(isinstance(state, WorkflowState) for state in states)


class TestWorkflowStateUsage:
    """Test practical usage of WorkflowState in Coordinator context."""

    def test_workflow_state_transitions(self):
        """Test typical workflow state transitions."""
        # Initial state
        current_state = WorkflowState.STARTED
        assert current_state == WorkflowState.STARTED

        # Transition to collecting information
        current_state = WorkflowState.COLLECTING_INFORMATION
        assert current_state == WorkflowState.COLLECTING_INFORMATION

        # Transition to building request
        current_state = WorkflowState.BUILDING_REQUEST
        assert current_state == WorkflowState.BUILDING_REQUEST

        # Transition to ready to execute
        current_state = WorkflowState.READY_TO_EXECUTE
        assert current_state == WorkflowState.READY_TO_EXECUTE

        # Transition to executing
        current_state = WorkflowState.EXECUTING
        assert current_state == WorkflowState.EXECUTING

        # Transition to waiting for confirmation
        current_state = WorkflowState.WAITING_FOR_CONFIRMATION
        assert current_state == WorkflowState.WAITING_FOR_CONFIRMATION

        # Final transition to completed
        current_state = WorkflowState.COMPLETED
        assert current_state == WorkflowState.COMPLETED

    def test_terminal_states(self):
        """Test that terminal states are distinct and valid."""
        terminal_states = [
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        ]

        # All should be different
        assert len(set(terminal_states)) == 3

        # All should have expected values
        assert WorkflowState.COMPLETED == "completed"
        assert WorkflowState.FAILED == "failed"
        assert WorkflowState.CANCELLED == "cancelled"

    def test_human_in_loop_states(self):
        """Test that human-in-loop checkpoint states are present."""
        human_states = [
            WorkflowState.WAITING_FOR_CONFIRMATION,
            WorkflowState.WAITING_FOR_RECEIPT,
            WorkflowState.WAITING_FOR_MANAGER,
        ]

        # All should be valid states
        for state in human_states:
            assert state in WorkflowState
            assert any(
                state.value.endswith(suffix) for suffix in ["_manager", "_confirmation", "_receipt"]
            )
