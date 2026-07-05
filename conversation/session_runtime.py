from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from agents.approval_agent import ApprovalAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from conversation.context_repository import ConversationContextRepository
from conversation.conversation_context import ConversationContext
from conversation.conversation_state import ConversationState
from conversation.orchestrator import ConversationOrchestrator

CoordinatorFactory = Callable[[ConversationContext], CoordinatorAgent]


@dataclass
class ConversationRuntime:
    """Load, process, and persist conversational state outside the orchestrator."""

    repository: ConversationContextRepository
    coordinator_factory: CoordinatorFactory

    def process_request(
        self,
        session_id: str | None,
        message: str,
        extracted_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        snapshot = self.repository.load(session_id) if session_id else None
        context = (
            ConversationContext.from_snapshot(snapshot)
            if snapshot is not None
            else ConversationContext()
        )
        coordinator = self.coordinator_factory(context)
        response = coordinator.route_message(message, extracted_data=extracted_data)

        if context.execution_stage in {
            ConversationState.COMPLETED,
            ConversationState.CANCELLED,
        }:
            self.repository.delete(session_id)
        else:
            self.repository.save(session_id, context.snapshot())

        return response


def build_default_runtime(
    repository: ConversationContextRepository | None = None,
) -> ConversationRuntime:
    employee_agent = EmployeeAgent()
    expense_agent = ExpenseAgent()
    policy_agent = PolicyAgent()
    approval_agent = ApprovalAgent()
    receipt_agent = ReceiptAgent()

    def _coordinator_factory(context: ConversationContext) -> CoordinatorAgent:
        orchestrator = ConversationOrchestrator(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            policy_agent=policy_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
            context=context,
        )
        return CoordinatorAgent(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            policy_agent=policy_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
            conversation_orchestrator=orchestrator,
        )

    return ConversationRuntime(
        repository=repository or ConversationContextRepository(),
        coordinator_factory=_coordinator_factory,
    )


__all__ = ["ConversationRuntime", "build_default_runtime"]
