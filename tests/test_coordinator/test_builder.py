"""
Test CoordinatorRequestBuilder Infrastructure.

This module contains pytest tests for the CoordinatorRequestBuilder class to ensure
it correctly collects and exposes conversation data.
"""

import pytest

from coordinator.builders import CoordinatorRequestBuilder


class TestRequestBuilderInitialization:
    """Test CoordinatorRequestBuilder initialization."""

    def test_initialization_creates_empty_data(self):
        """Test that builder initializes with empty collected data."""
        builder = CoordinatorRequestBuilder()
        assert builder.get_collected_data() == {}
        assert len(builder.get_collected_data()) == 0


class TestRequestBuilderMethods:
    """Test CoordinatorRequestBuilder methods."""

    @pytest.fixture
    def builder(self) -> CoordinatorRequestBuilder:
        """Fixture providing a CoordinatorRequestBuilder instance."""
        return CoordinatorRequestBuilder()

    def test_add_field_stores_data_correctly(self, builder: CoordinatorRequestBuilder):
        """Test that add_field correctly stores field values."""
        builder.add_field("employee_id", "EMP123")
        builder.add_field("trip_name", "AWS Summit")

        collected = builder.get_collected_data()
        assert collected["employee_id"] == "EMP123"
        assert collected["trip_name"] == "AWS Summit"
        assert len(collected) == 2

    def test_add_field_returns_self_for_chaining(self, builder: CoordinatorRequestBuilder):
        """Test that add_field returns self for method chaining."""
        result = builder.add_field("field1", "value1")
        assert result is builder

        # Test chaining works
        chained_result = builder.add_field("field2", "value2").add_field("field3", "value3")
        assert chained_result is builder
        assert len(builder.get_collected_data()) == 3

    def test_has_field_returns_correct_boolean(self, builder: CoordinatorRequestBuilder):
        """Test that has_field correctly identifies collected fields."""
        # Field not present
        assert not builder.has_field("missing_field")

        # Add field
        builder.add_field("present_field", "value")

        # Field now present
        assert builder.has_field("present_field")
        assert not builder.has_field("still_missing")

    def test_get_field_returns_correct_values(self, builder: CoordinatorRequestBuilder):
        """Test that get_field returns correct values for collected fields."""
        # Non-existent field returns None
        assert builder.get_field("missing_field") is None

        # Add fields
        builder.add_field("employee_id", "EMP123")
        builder.add_field("trip_name", "AWS Summit")

        # Retrieve fields
        assert builder.get_field("employee_id") == "EMP123"
        assert builder.get_field("trip_name") == "AWS Summit"
        assert builder.get_field("still_missing") is None

    def test_get_collected_data_returns_copy(self, builder: CoordinatorRequestBuilder):
        """Test that get_collected_data returns a copy, not the original dict."""
        builder.add_field("field1", "value1")

        collected = builder.get_collected_data()
        collected["field2"] = "value2"  # Modify the returned dict

        # Original should be unchanged
        original = builder.get_collected_data()
        assert "field2" not in original
        assert len(original) == 1

    def test_clear_removes_all_collected_data(self, builder: CoordinatorRequestBuilder):
        """Test that clear method removes all collected data."""
        # Add some data
        builder.add_field("field1", "value1")
        builder.add_field("field2", "value2")
        builder.add_field("field3", "value3")

        assert len(builder.get_collected_data()) == 3

        # Clear data
        builder.clear()

        # Should be empty
        assert builder.get_collected_data() == {}
        assert len(builder.get_collected_data()) == 0
        assert not builder.has_field("field1")

    def test_build_method_no_longer_exists(self, builder: CoordinatorRequestBuilder):
        """Test that build method has been removed from the class."""
        assert not hasattr(builder, "build")

        # Should not be able to call build()
        with pytest.raises(AttributeError):
            builder.build()  # type: ignore


class TestRequestBuilderEdgeCases:
    """Test edge cases for CoordinatorRequestBuilder."""

    def test_add_field_with_none_value(self):
        """Test that add_field can store None values."""
        builder = CoordinatorRequestBuilder()
        builder.add_field("optional_field", None)

        assert builder.has_field("optional_field")
        assert builder.get_field("optional_field") is None

    def test_add_field_with_complex_data_types(self):
        """Test that add_field can store complex data types."""
        builder = CoordinatorRequestBuilder()

        complex_data = {"nested": {"list": [1, 2, 3], "dict": {"key": "value"}}}

        builder.add_field("complex_data", complex_data)

        assert builder.get_field("complex_data") == complex_data
        assert builder.get_collected_data()["complex_data"] == complex_data

    def test_multiple_clears_work_correctly(self):
        """Test that multiple clear operations work correctly."""
        builder = CoordinatorRequestBuilder()

        # First cycle
        builder.add_field("field1", "value1")
        builder.clear()
        assert len(builder.get_collected_data()) == 0

        # Second cycle
        builder.add_field("field2", "value2")
        builder.add_field("field3", "value3")
        assert len(builder.get_collected_data()) == 2

        # Clear again
        builder.clear()
        assert len(builder.get_collected_data()) == 0
