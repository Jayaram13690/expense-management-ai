from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from agents.approval_agent import ApprovalAgent
from agents.base_agent import BaseAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from conversation.conversation_state import ConversationState
from conversation.orchestrator import ConversationOrchestrator


class CoordinatorAgent(BaseAgent):
    """Single conversational entry point that routes by user intent."""

    _INTENT_LABELS = {
        "SUBMIT_EXPENSE_CLAIM",
        "CHECK_CLAIM_STATUS",
        "POLICY_QUERY",
        "EMPLOYEE_QUERY",
        "APPROVAL_QUERY",
        "RECEIPT_QUERY",
        "UNKNOWN",
    }

    def __init__(
        self,
        employee_agent: EmployeeAgent,
        expense_agent: ExpenseAgent,
        policy_agent: PolicyAgent,
        approval_agent: ApprovalAgent,
        receipt_agent: ReceiptAgent,
        conversation_orchestrator: ConversationOrchestrator | None = None,
        model: str | Any | None = None,
    ) -> None:
        if None in (
            employee_agent,
            expense_agent,
            policy_agent,
            approval_agent,
            receipt_agent,
        ):
            raise ValueError("All specialized agents must be provided")

        super().__init__(
            model=model,
            system_prompt=self._build_system_prompt(),
            tools=None,
            name="CoordinatorAgent",
            description="Classifies user intent and routes requests.",
        )

        self.employee_agent = employee_agent
        self.expense_agent = expense_agent
        self.policy_agent = policy_agent
        self.approval_agent = approval_agent
        self.receipt_agent = receipt_agent
        self.conversation_orchestrator = conversation_orchestrator or ConversationOrchestrator(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            policy_agent=policy_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
        )

    def route_message(
        self,
        message: str,
        extracted_data: Mapping[str, Any] | None = None,
    ) -> Any:
        """Route a user message to the appropriate conversational path."""

        if self._has_active_conversation():
            return self.conversation_orchestrator.process_turn(
                message, extracted_data=extracted_data
            )

        intent = self.classify_intent(message)

        if intent == "SUBMIT_EXPENSE_CLAIM":
            self.conversation_orchestrator.reset()
            return self.conversation_orchestrator.process_turn(
                message, extracted_data=extracted_data
            )
        if intent == "CHECK_CLAIM_STATUS":
            return self.expense_agent.invoke(message)
        if intent == "POLICY_QUERY":
            return self.policy_agent.invoke(message)
        if intent == "EMPLOYEE_QUERY":
            return self.employee_agent.invoke(message)
        if intent == "APPROVAL_QUERY":
            return self.approval_agent.invoke(message)
        if intent == "RECEIPT_QUERY":
            return self.receipt_agent.invoke(message)

        return self._clarification_response()

    def classify_intent(self, message: str) -> str:
        """Classify the user's request into a supported intent label."""

        prompt = self._classification_prompt(message)
        raw_response = self.invoke(prompt)
        return self._normalize_intent(raw_response)

    def _has_active_conversation(self) -> bool:
        state = self.conversation_orchestrator.state
        if state in {
            ConversationState.WAITING_USER,
            ConversationState.COLLECTING_EXPENSES,
            ConversationState.COLLECTING_RECEIPTS,
            ConversationState.EXECUTING,
        }:
            return True
        if state != ConversationState.ACTIVE:
            return False
        return self._has_conversation_data()

    def _has_conversation_data(self) -> bool:
        context = self.conversation_orchestrator.context
        fields = (
            context.employee_id,
            context.trip_name,
            context.business_purpose,
            context.destination,
            context.trip_start_date,
            context.trip_end_date,
            context.expense_items,
            context.claim_preview,
            context.confirmation,
            context.claim_id,
            context.execution_results,
        )
        return any(value not in (None, "", [], {}) for value in fields)

    def _build_system_prompt(self) -> str:
        return (
            "You are a routing agent. Classify user intent only.\n"
            "Return a JSON object with keys intent and confidence.\n"
            "Return exactly one intent from:\n"
            "SUBMIT_EXPENSE_CLAIM, CHECK_CLAIM_STATUS, POLICY_QUERY, EMPLOYEE_QUERY,\n"
            "APPROVAL_QUERY, RECEIPT_QUERY, UNKNOWN.\n"
            "Do not answer the user's question. Do not perform business reasoning."
        )

    def _classification_prompt(self, message: str) -> str:
        return (
            "Classify the user's intent from the message below.\n"
            "Return a JSON object with keys intent and confidence.\n\n"
            f"Message: {message}"
        )

    def _normalize_intent(self, raw_response: Any) -> str:
        payload = self._extract_payload(raw_response)
        if payload is not None:
            intent = payload.get("intent")
            if isinstance(intent, str):
                normalized = intent.strip().upper()
                if normalized in self._INTENT_LABELS:
                    return normalized

        text = self._extract_text(raw_response).strip().upper()
        if text in self._INTENT_LABELS:
            return text

        for label in self._INTENT_LABELS:
            if label in text:
                return label

        return "UNKNOWN"

    def _extract_payload(self, response: Any) -> dict[str, Any] | None:
        if isinstance(response, Mapping):
            return dict(response)
        if isinstance(response, str):
            text = response.strip()
            if not text:
                return None
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                return None
            if isinstance(payload, Mapping):
                return dict(payload)
        return None

    def _extract_text(self, response: Any) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, Mapping):
            for key in ("intent", "label", "output", "content", "text", "response"):
                value = response.get(key)
                if isinstance(value, str):
                    return value
        return str(response)

    def _clarification_response(self) -> dict[str, str]:
        return {
            "intent": "UNKNOWN",
            "response": (
                "I can help with submitting expense claims, claim status, policy questions, "
                "employee details, approvals, and receipt summaries. What would you like to do?"
            ),
        }


__all__ = ["CoordinatorAgent"]
