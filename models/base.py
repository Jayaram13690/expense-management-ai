"""
Base domain models for the Enterprise AI Travel Expense Management System.

This module defines the foundational domain models shared across all
business entities.

Every domain entity should inherit from BaseEntity.

Author:
    Jayaram Bantumilli

Architecture:
    BaseSchema
        └── AuditEntity
                └── BaseEntity
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """
    Return the current UTC timestamp.

    Returns:
        Timezone-aware UTC datetime.
    """
    return datetime.now(UTC)


class BaseSchema(BaseModel):
    """
    Base Pydantic schema.

    Provides common configuration shared by every domain model.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        frozen=False,
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model into a dictionary.

        Returns:
            Dictionary representation.
        """
        return self.model_dump(mode="python")

    def to_json(self) -> str:
        """
        Convert model into JSON.

        Returns:
            JSON string.
        """
        return self.model_dump_json(indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseSchema:
        """
        Create model from dictionary.

        Args:
            data: Input dictionary.

        Returns:
            Model instance.
        """
        return cls.model_validate(data)


class AuditEntity(BaseSchema):
    """
    Base audit information.

    Every persistent entity should inherit these fields.
    """

    created_at: datetime = Field(default_factory=utc_now)

    updated_at: datetime = Field(default_factory=utc_now)

    created_by: str = Field(
        default="system",
        min_length=1,
        max_length=100,
    )

    updated_by: str = Field(
        default="system",
        min_length=1,
        max_length=100,
    )

    version: int = Field(
        default=1,
        ge=1,
    )

    is_active: bool = True

    def touch(self, updated_by: str = "system") -> None:
        """
        Update audit information.

        Args:
            updated_by:
                User or system performing the update.
        """
        self.updated_at = utc_now()
        self.updated_by = updated_by
        self.version += 1


class BaseEntity(AuditEntity):
    """
    Base business entity.

    Every domain entity inherits from this class.
    """

    id: UUID = Field(default_factory=uuid4)

    def to_dynamodb_item(self) -> dict[str, Any]:
        """
        Convert entity into a DynamoDB-compatible dictionary.

        UUIDs, datetimes, and dates are converted into strings.

        Returns:
            DynamoDB-ready dictionary.
        """
        item = self.model_dump(
            mode="python",
            exclude_computed_fields=True,
        )

        for key, value in item.items():
            if isinstance(value, UUID):
                item[key] = str(value)

            elif isinstance(value, (datetime, date)):
                item[key] = value.isoformat()

        return item
