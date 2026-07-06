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
    _NOTIFICATION_RETRY_COMMANDS = {"retry", "resend", "continue"}

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

        print("\nCoordinator State")
        print(self.conversation_orchestrator.state)
        print(self._has_active_conversation())
        print("===================================================")

        if self._has_active_conversation():
            return self.conversation_orchestrator.process_turn(
                message, extracted_data=extracted_data
            )

        if self._has_pending_notification() and self._is_notification_retry(message):
            return self.receipt_agent.retry_pending_notification()

        approval_command = self.approval_agent.parse_decision_command(message)
        if self.approval_agent.has_pending_rejection() or approval_command is not None:
            return self._route_approval_message(message)

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
            return self._route_approval_message(message)
        if intent == "RECEIPT_QUERY":
            return self.receipt_agent.invoke(message)

        return self._clarification_response()

    def classify_intent(self, message: str) -> str:
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

    def _route_approval_message(self, message: str) -> dict[str, Any] | Any:
        if self.approval_agent.has_pending_rejection():
            return self._continue_pending_rejection(message)

        command = self.approval_agent.parse_decision_command(message)
        if command is None:
            if self._has_pending_notification() and self._is_notification_retry(message):
                return self.receipt_agent.retry_pending_notification()
            return self.approval_agent.invoke(message)

        claim_id = str(command["claim_id"])
        claim_status = self._resolve_claim_status(claim_id)
        if claim_status.get("success") is False:
            return claim_status

        employee_id = claim_status.get("employee_id")
        if not isinstance(employee_id, str) or not employee_id.strip():
            return self._structured_error(
                error_code="EMPLOYEE_NOT_FOUND",
                assistant_message="I couldn't resolve the employee for that claim.",
                recoverable=False,
            )

        employee_profile = self._resolve_employee_profile(employee_id)
        if isinstance(employee_profile, Mapping) and employee_profile.get("success") is False:
            return employee_profile

        manager_id = employee_profile.manager_id
        if not manager_id:
            return self._structured_error(
                error_code="MANAGER_NOT_FOUND",
                assistant_message="Unable to locate the employee's manager.",
                recoverable=True,
            )

        manager_profile = self._resolve_employee_profile(manager_id)
        if isinstance(manager_profile, Mapping) and manager_profile.get("success") is False:
            return manager_profile

        decision_result = self.approval_agent.process_decision(
            claim_id=claim_id,
            decision=str(command["decision"]),
            approver_id=manager_profile.employee_id,
            approver_name=manager_profile.employee_name or manager_profile.employee_id,
            reason=command.get("reason"),
        )
        if decision_result.get("success") is False:
            return decision_result

        updated_status = self._resolve_claim_status(claim_id)
        if updated_status.get("success") is False:
            return updated_status

        notification_result = self.receipt_agent.send_employee_decision_email(
            claim_id=claim_id,
            approval_result=decision_result.get("approval_result", {}),
            claim_status=updated_status,
        )
        if notification_result.get("success") is False:
            notification_result["assistant_message"] = (
                f"{decision_result.get('assistant_message', '')}\n\n"
                f"{notification_result.get('assistant_message', '')}"
            ).strip()
            notification_result["approval_result"] = decision_result.get("approval_result")
            return notification_result

        return {
            "success": True,
            "status": decision_result.get("status"),
            "approval_result": decision_result.get("approval_result"),
            "assistant_message": (
                f"{decision_result.get('assistant_message', '')}\n\n"
                f"{notification_result.get('assistant_message', '')}"
            ).strip(),
            "next_state": "completed",
        }

    def _continue_pending_rejection(self, message: str) -> dict[str, Any]:
        claim_id = self.approval_agent._pending_rejection["claim_id"]
        claim_status = self._resolve_claim_status(claim_id)
        if claim_status.get("success") is False:
            return claim_status

        employee_id = claim_status.get("employee_id")
        if not isinstance(employee_id, str) or not employee_id.strip():
            return self._structured_error(
                error_code="EMPLOYEE_NOT_FOUND",
                assistant_message="I couldn't resolve the employee for that claim.",
                recoverable=False,
            )

        employee_profile = self._resolve_employee_profile(employee_id)
        if isinstance(employee_profile, Mapping) and employee_profile.get("success") is False:
            return employee_profile

        manager_id = employee_profile.manager_id
        if not manager_id:
            return self._structured_error(
                error_code="MANAGER_NOT_FOUND",
                assistant_message="Unable to locate the employee's manager.",
                recoverable=True,
            )

        manager_profile = self._resolve_employee_profile(manager_id)
        if isinstance(manager_profile, Mapping) and manager_profile.get("success") is False:
            return manager_profile

        decision_result = self.approval_agent.process_pending_rejection_reason(
            message,
            approver_id=manager_profile.employee_id,
            approver_name=manager_profile.employee_name or manager_profile.employee_id,
        )
        if decision_result.get("success") is False:
            return decision_result

        updated_status = self._resolve_claim_status(claim_id)
        if updated_status.get("success") is False:
            return updated_status

        notification_result = self.receipt_agent.send_employee_decision_email(
            claim_id=claim_id,
            approval_result=decision_result.get("approval_result", {}),
            claim_status=updated_status,
        )
        if notification_result.get("success") is False:
            notification_result["assistant_message"] = (
                f"{decision_result.get('assistant_message', '')}\n\n"
                f"{notification_result.get('assistant_message', '')}"
            ).strip()
            notification_result["approval_result"] = decision_result.get("approval_result")
            return notification_result

        return {
            "success": True,
            "status": decision_result.get("status"),
            "approval_result": decision_result.get("approval_result"),
            "assistant_message": (
                f"{decision_result.get('assistant_message', '')}\n\n"
                f"{notification_result.get('assistant_message', '')}"
            ).strip(),
            "next_state": "completed",
        }

    def _resolve_claim_status(self, claim_id: str) -> dict[str, Any]:
        try:
            result = self.expense_agent.get_claim_status(claim_id)
        except Exception as exc:
            return self._structured_error(
                error_code=getattr(exc, "error_code", exc.__class__.__name__.upper()),
                assistant_message=getattr(exc, "message", str(exc)),
                recoverable=False,
            )
        if isinstance(result, Mapping):
            return dict(result)
        return self._structured_error(
            error_code="CLAIM_NOT_FOUND",
            assistant_message=f"Claim {claim_id} could not be found.",
            recoverable=False,
        )

    def _resolve_employee_profile(self, employee_id: str) -> Any:
        try:
            return self.employee_agent.get_employee_profile(employee_id)
        except Exception as exc:
            return self._structured_error(
                error_code=getattr(exc, "error_code", exc.__class__.__name__.upper()),
                assistant_message=getattr(exc, "message", str(exc)),
                recoverable=False,
            )

    def _has_pending_notification(self) -> bool:
        return self.receipt_agent.has_pending_notification()

    def _is_notification_retry(self, message: str) -> bool:
        return message.strip().lower() in self._NOTIFICATION_RETRY_COMMANDS

    def _structured_error(
        self,
        *,
        error_code: str,
        assistant_message: str,
        recoverable: bool,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": error_code,
            "assistant_message": assistant_message,
            "recoverable": recoverable,
            "next_state": "waiting_user",
        }

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
