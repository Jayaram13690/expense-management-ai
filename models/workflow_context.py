"""
Workflow Context.

Represents the shared execution context passed between
multiple AI agents during workflow execution.

Unlike utils.context, this is a business model and may
be persisted or transmitted between services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import Field

from common.identifiers import RequestId, WorkflowId
from models.base import BaseSchema
from models.expense_claim import ExpenseClaim


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class WorkflowStage(StrEnum):
    """
    Workflow execution stages.
    """

    CREATED = "CREATED"

    VALIDATION = "VALIDATION"

    POLICY_VALIDATION = "POLICY_VALIDATION"

    FINANCIAL_REVIEW = "FINANCIAL_REVIEW"

    APPROVAL = "APPROVAL"

    PERSISTENCE = "PERSISTENCE"

    COMPLETED = "COMPLETED"

    FAILED = "FAILED"


class WorkflowContext(BaseSchema):
    """
    Shared workflow context.

    Passed between all AI agents.
    """

    workflow_id: WorkflowId

    request_id: RequestId

    claim: ExpenseClaim

    current_stage: WorkflowStage = WorkflowStage.CREATED

    current_agent: str | None = None

    execution_history: list[str] = Field(default_factory=list)

    metadata: dict[str, str] = Field(default_factory=dict)

    started_at: datetime = Field(default_factory=utc_now)

    completed_at: datetime | None = None

    def move_to_stage(
        self,
        stage: WorkflowStage,
    ) -> None:
        """
        Move workflow to another stage.
        """

        self.current_stage = stage

    def set_current_agent(
        self,
        agent_name: str,
    ) -> None:
        """
        Set currently executing agent.
        """

        self.current_agent = agent_name

    def add_history(
        self,
        event: str,
    ) -> None:
        """
        Record workflow event.
        """

        self.execution_history.append(event)

    def complete(self) -> None:
        """
        Mark workflow completed.
        """

        self.current_stage = WorkflowStage.COMPLETED
        self.completed_at = utc_now()

    def fail(
        self,
        reason: str,
    ) -> None:
        """
        Mark workflow failed.
        """

        self.current_stage = WorkflowStage.FAILED
        self.add_history(reason)
