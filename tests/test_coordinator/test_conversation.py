"""
Test Coordinator Conversation Integration.

This module contains pytest tests for the conversation management capabilities
added to the Coordinator.
"""

from unittest.mock import Mock

import pytest

from conversation.intents import ConversationIntent
from coordinator import ConversationManager, Coordinator, WorkflowState
from coordinator.builders import CoordinatorRequestBuilder


class TestFieldMappings:
    """Test the conversation field mappings."""

    def test_field_mappings_has_prompts_for_common_fields(self):
        """Test that field mappings has prompts for common field names."""
        from conversation.field_mappings import get_prompt_for_field, has_prompt_for_field

        # Test employee fields
        assert has_prompt_for_field("employee_id")
        assert get_prompt_for_field("employee_id") == "What is your employee ID?"

        # Test trip fields
        assert has_prompt_for_field("trip_name")
        assert get_prompt_for_field("trip_name") == "What is the name of your business trip?"

        # Test expense fields
        assert has_prompt_for_field("expense_items")
        assert get_prompt_for_field("expense_items") == "Please list the expenses you incurred."

    def test_field_mappings_returns_none_for_unknown_fields(self):
        """Test that field mappings returns None for unknown field names."""
        from conversation.field_mappings import get_prompt_for_field, has_prompt_for_field

        assert get_prompt_for_field("unknown_field") is None
        assert not has_prompt_for_field("unknown_field")

    def test_field_mappings_handles_all_defined_fields(self):
        """Test that field mappings can handle all defined field mappings."""
        from conversation.field_mappings import get_prompt_for_field, has_prompt_for_field

        # This tests that the mapping is comprehensive
        test_fields = [
            "employee_id",
            "trip_name",
            "business_purpose",
            "destination",
            "trip_start_date",
            "trip_end_date",
            "expense_items",
            "expense_category",
            "expense_amount",
            "expense_date",
            "expense_description",
            "claim_id",
            "comments",
            "receipt",
            "receipt_type",
            "receipt_id",
            "notes",
            "approver_id",
            "approver_name",
            "approval_notes",
            "reason",
            "manager_id",
            "policy_category",
            "employee_grade",
        ]

        for field in test_fields:
            assert has_prompt_for_field(field)
            assert get_prompt_for_field(field) is not None


class TestConversationManager:
    """Test the ConversationManager class."""

    @pytest.fixture
    def manager(self) -> ConversationManager:
        """Fixture providing a ConversationManager instance."""

        builder = CoordinatorRequestBuilder()
        return ConversationManager(request_builder=builder)

    def test_start_conversation_with_valid_intent(self, manager: ConversationManager):
        """Test starting conversation with a valid intent."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        assert manager.current_intent() == ConversationIntent.SUBMIT_EXPENSE_CLAIM
        assert manager.current_requirements() is not None
        assert manager.current_requirements().intent == ConversationIntent.SUBMIT_EXPENSE_CLAIM

    def test_start_conversation_with_unknown_intent(self, manager: ConversationManager):
        """Test that starting conversation with unknown intent is handled gracefully."""
        # Should not raise an error, but should result in no requirements
        manager.start_conversation(ConversationIntent.UNKNOWN)  # type: ignore

        # Should have no current requirements
        assert manager.current_requirements() is None
        assert manager.current_intent() == ConversationIntent.UNKNOWN

        # Should have no missing fields and be ready to execute
        assert len(manager.get_missing_required_fields()) == 0
        assert manager.is_ready_to_execute()

    def test_collect_field_marks_field_as_collected(self, manager: ConversationManager):
        """Test that collect_field properly marks fields as collected."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Initially should have missing fields
        missing_fields = manager.get_missing_required_fields()
        assert len(missing_fields) > 0
        assert "employee_id" in missing_fields

        # Collect a field
        manager.collect_field("employee_id", "EMP123")

        # employee_id should no longer be missing
        missing_fields_after = manager.get_missing_required_fields()
        assert "employee_id" not in missing_fields_after
        assert len(missing_fields_after) == len(missing_fields) - 1

    def test_get_missing_required_fields_returns_correct_list(self, manager: ConversationManager):
        """Test that get_missing_required_fields returns correct missing fields."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Get initial missing fields
        missing_fields = manager.get_missing_required_fields()

        # Should include all required fields for SUBMIT_EXPENSE_CLAIM
        expected_fields = [
            "employee_id",
            "trip_name",
            "business_purpose",
            "destination",
            "trip_start_date",
            "trip_end_date",
            "expense_items",
        ]
        assert set(missing_fields) == set(expected_fields)

    def test_get_next_prompt_returns_correct_prompts(self, manager: ConversationManager):
        """Test that get_next_prompt returns appropriate prompts in sequence."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # First prompt should be for employee_id
        first_prompt = manager.get_next_prompt()
        assert first_prompt == "What is your employee ID?"

        # Collect employee_id
        manager.collect_field("employee_id", "EMP123")

        # Next prompt should be for trip_name
        second_prompt = manager.get_next_prompt()
        assert second_prompt == "What is the name of your business trip?"

    def test_is_ready_to_execute_when_all_fields_collected(self, manager: ConversationManager):
        """Test that is_ready_to_execute returns True when all required fields are collected."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Initially should not be ready
        assert not manager.is_ready_to_execute()

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
            manager.collect_field(field, f"value_{field}")

        # Now should be ready
        assert manager.is_ready_to_execute()

    def test_is_ready_to_execute_when_only_some_fields_collected(
        self, manager: ConversationManager
    ):
        """Test that is_ready_to_execute returns False when only some fields are collected."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Collect only some fields
        manager.collect_field("employee_id", "EMP123")
        manager.collect_field("trip_name", "AWS Summit")

        # Should not be ready yet
        assert not manager.is_ready_to_execute()
        assert len(manager.get_missing_required_fields()) > 0

    def test_reset_clears_conversation_state(self, manager: ConversationManager):
        """Test that reset method properly clears conversation state."""
        # Start a conversation
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)
        manager.collect_field("employee_id", "EMP123")

        assert manager.current_intent() == ConversationIntent.SUBMIT_EXPENSE_CLAIM
        assert len(manager.get_missing_required_fields()) < 7  # Some collected

        # Reset
        manager.reset()

        # Should be back to initial state
        assert manager.current_intent() is None
        assert manager.current_requirements() is None
        assert len(manager.get_missing_required_fields()) == 0

    def test_get_next_prompt_returns_none_when_ready(self, manager: ConversationManager):
        """Test that get_next_prompt returns None when all fields are collected."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

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
            manager.collect_field(field, f"value_{field}")

        # Should return None when ready
        assert manager.is_ready_to_execute()
        assert manager.get_next_prompt() is None

    def test_different_intents_have_different_requirements(self, manager: ConversationManager):
        """Test that different intents have different field requirements."""
        # Test SUBMIT_EXPENSE_CLAIM
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)
        submit_fields = manager.get_missing_required_fields()

        # Test GET_EXPENSE_CLAIM (should have different requirements)
        manager.start_conversation(ConversationIntent.GET_EXPENSE_CLAIM)
        get_fields = manager.get_missing_required_fields()

        # Should be different
        assert set(submit_fields) != set(get_fields)
        assert len(get_fields) < len(submit_fields)  # GET should require fewer fields


class TestCoordinatorConversationIntegration:
    """Test conversation integration with Coordinator class."""

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

    def test_coordinator_start_conversation(self, coordinator: Coordinator):
        """Test that Coordinator can start conversations."""
        initial_state = coordinator.current_state
        assert initial_state == WorkflowState.STARTED

        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        assert coordinator.current_state == WorkflowState.COLLECTING_INFORMATION
        assert coordinator.current_intent() == ConversationIntent.SUBMIT_EXPENSE_CLAIM
        assert coordinator.current_requirements() is not None

    def test_coordinator_collect_field_and_store_in_builder(self, coordinator: Coordinator):
        """Test that Coordinator collects fields and stores them in request builder."""
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Collect a field
        coordinator.collect_field("employee_id", "EMP123")

        # Should be stored in request builder
        builder = coordinator.get_request_builder()
        assert builder.has_field("employee_id")
        assert builder.get_field("employee_id") == "EMP123"

        # Should also be tracked by conversation manager
        missing_fields = coordinator.get_missing_fields()
        assert "employee_id" not in missing_fields

    def test_coordinator_get_next_prompt(self, coordinator: Coordinator):
        """Test that Coordinator can get next prompts."""
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Get first prompt
        first_prompt = coordinator.get_next_prompt()
        assert first_prompt == "What is your employee ID?"

        # Collect employee_id
        coordinator.collect_field("employee_id", "EMP123")

        # Get next prompt
        second_prompt = coordinator.get_next_prompt()
        assert second_prompt == "What is the name of your business trip?"

    def test_coordinator_is_ready_to_execute_state_transition(self, coordinator: Coordinator):
        """Test that Coordinator transitions to READY_TO_EXECUTE when all fields collected."""
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Initially should be COLLECTING_INFORMATION
        assert coordinator.current_state == WorkflowState.COLLECTING_INFORMATION
        assert not coordinator.is_ready_to_execute()

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

        # Should now be ready and state should transition
        assert coordinator.is_ready_to_execute()
        assert coordinator.current_state == WorkflowState.READY_TO_EXECUTE

    def test_coordinator_missing_fields_tracking(self, coordinator: Coordinator):
        """Test that Coordinator can track missing fields."""
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Initially all required fields should be missing
        initial_missing = coordinator.get_missing_fields()
        expected_fields = [
            "employee_id",
            "trip_name",
            "business_purpose",
            "destination",
            "trip_start_date",
            "trip_end_date",
            "expense_items",
        ]
        assert set(initial_missing) == set(expected_fields)

        # Collect some fields
        coordinator.collect_field("employee_id", "EMP123")
        coordinator.collect_field("trip_name", "AWS Summit")

        # Should have fewer missing fields
        updated_missing = coordinator.get_missing_fields()
        assert len(updated_missing) == len(expected_fields) - 2
        assert "employee_id" not in updated_missing
        assert "trip_name" not in updated_missing

    def test_coordinator_conversation_reset(self, coordinator: Coordinator):
        """Test that Coordinator conversation can be reset."""
        # Start conversation and collect some fields
        coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)
        coordinator.collect_field("employee_id", "EMP123")

        # Reset coordinator
        coordinator.reset()

        # Should be back to initial state
        assert coordinator.current_state == WorkflowState.STARTED
        assert coordinator.current_intent() is None
        assert len(coordinator.get_missing_fields()) == 0

        # Request builder should also be cleared
        builder = coordinator.get_request_builder()
        assert builder.get_collected_data() == {}


class TestConversationEdgeCases:
    """Test edge cases in conversation management."""

    @pytest.fixture
    def manager(self) -> ConversationManager:
        """Fixture providing a ConversationManager instance."""

        builder = CoordinatorRequestBuilder()
        return ConversationManager(request_builder=builder)

    def test_conversation_with_no_required_fields(self, manager: ConversationManager):
        """Test conversation with intent that has no required fields."""
        # This is a hypothetical case, but should be handled gracefully
        # For now, test with a real intent
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Collect all fields
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
            manager.collect_field(field, f"value_{field}")

        # Should be ready and no more prompts
        assert manager.is_ready_to_execute()
        assert manager.get_next_prompt() is None
        assert len(manager.get_missing_required_fields()) == 0

    def test_collecting_optional_fields(self, manager: ConversationManager):
        """Test that optional fields don't affect ready-to-execute status."""
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # Collect only required fields (not optional ones like comments)
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
            manager.collect_field(field, f"value_{field}")

        # Should be ready even without optional fields
        assert manager.is_ready_to_execute()

    def test_collecting_fields_before_starting_conversation(self, manager: ConversationManager):
        """Test that collecting fields before starting conversation is handled."""
        # Try to collect field before starting conversation
        manager.collect_field("employee_id", "EMP123")

        # Should not cause errors, but field shouldn't be tracked (no requirements yet)
        assert len(manager.get_missing_required_fields()) == 0

        # Start conversation
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)

        # With the new architecture, fields collected before starting conversation are tracked
        # This is correct behavior since the request builder is now the single source of truth
        missing_fields = manager.get_missing_required_fields()
        assert "employee_id" not in missing_fields  # Field was already collected
        assert len(missing_fields) == 6  # Only 6 fields remaining (7 total - 1 collected)

    def test_multiple_conversations_in_sequence(self, manager: ConversationManager):
        """Test that multiple conversations can be conducted in sequence."""
        # First conversation
        manager.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)
        manager.collect_field("employee_id", "EMP123")
        first_missing = manager.get_missing_required_fields()

        # Reset and start second conversation
        manager.reset()
        manager.start_conversation(ConversationIntent.GET_EXPENSE_CLAIM)

        # Should have different requirements
        second_missing = manager.get_missing_required_fields()
        assert set(first_missing) != set(second_missing)

        # First conversation's collected fields should not affect second
        # GET_EXPENSE_CLAIM only requires claim_id, so employee_id won't be in the list
        assert "claim_id" in second_missing  # Should have the correct requirements for GET
