"""
Coordinator Request Builders.

This module provides the infrastructure for building request DTOs from
collected conversation data. This is infrastructure only - actual DTO
building will be implemented in later phases.

Design Principles:
------------------
- Infrastructure only - no actual DTO creation
- No business logic
- No service/repository/tool dependencies
- Designed for future conversation data collection
- Clean separation from business layer
"""

from __future__ import annotations

from typing import Any


class CoordinatorRequestBuilder:
    """Infrastructure for collecting conversation data."""

    def __init__(self) -> None:
        """
        Initialize the request builder with empty collected data.
        """
        self._collected_data: dict[str, Any] = {}

    def add_field(self, field_name: str, value: Any) -> CoordinatorRequestBuilder:
        """Add a collected field to the builder."""
        self._collected_data[field_name] = value
        return self

    def get_collected_data(self) -> dict[str, Any]:
        """Get the currently collected data."""
        return self._collected_data.copy()

    def has_field(self, field_name: str) -> bool:
        """Check if a specific field has been collected."""
        return field_name in self._collected_data

    def get_field(self, field_name: str) -> Any | None:
        """Get the value of a specific collected field."""
        return self._collected_data.get(field_name)

    def clear(self) -> None:
        """Clear all collected data to prepare for a new request."""
        self._collected_data.clear()


__all__ = ["CoordinatorRequestBuilder"]
