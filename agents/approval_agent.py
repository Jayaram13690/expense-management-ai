"""
ApprovalAgent for handling claim approval workflows.

This module implements the ApprovalAgent that inherits from BaseAgent and
is responsible for expense claim approval operations including approving,
rejecting, and managing approval queues.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from agents.base_agent import BaseAgent
from contracts import EmployeeProfile
from exceptions.base import ApplicationException
from prompts.approval_prompt import APPROVAL_AGENT_SYSTEM_PROMPT
from tools.approval_tools import (
    approve_claim,
    get_approval_history,
    get_approval_status,
    list_manager_queue,
    list_pending_claims,
    reject_claim,
)


class ApprovalAgent(BaseAgent):
    """Approval agent with deterministic orchestration helpers."""

    _APPROVE_PATTERN = re.compile(
        r"^(?:approve(?:\s+the)?(?:\s+claim)?\s+(CLM\d+)|approve\s+(CLM\d+)|claim\s+(CLM\d+)\s+approved)\s*$",
        re.IGNORECASE,
    )
    _REJECT_PATTERN = re.compile(
        r"^(?:"
        r"reject(?:\s+the)?(?:\s+claim)?\s+(CLM\d+)"
        r"|claim\s+(CLM\d+)\s+rejected"
        r")"
        r"(?:\s+(?:because|due\s+to|comment:|reason:)\s+(.+))?\s*$",
        re.IGNORECASE,
    )

    def __init__(self, model: str | None = None) -> None:
        super().__init__(
            model=model,
            system_prompt=APPROVAL_AGENT_SYSTEM_PROMPT,
            tools=[
                approve_claim,
                reject_claim,
                list_pending_claims,
                list_manager_queue,
                get_approval_status,
                get_approval_history,
            ],
            name="ApprovalAgent",
            description="Handles approval workflows.",
        )
        self._pending_rejection: dict[str, str] | None = None

    def get_approval_result(self, claim_id: str) -> dict[str, Any]:
        """Retrieve approval status for orchestration."""

        result = get_approval_status(claim_id)
        if hasattr(result, "model_dump") and callable(result.model_dump):
            return result.model_dump()
        if isinstance(result, Mapping):
            return dict(result)
        return {"value": result}

    def create_approval_request(
        self,
        *,
        claim_id: str,
        employee_profile: EmployeeProfile,
        manager_profile: EmployeeProfile,
    ) -> dict[str, Any]:
        """Create a structured pending approval result after claim submission."""

        if not claim_id.strip():
            return self._error_result(
                error_code="CLAIM_ID_MISSING",
                assistant_message=(
                    "I couldn't create the approval request because the claim ID is missing."
                ),
                recoverable=False,
            )
        if not manager_profile.employee_id:
            return self._error_result(
                error_code="MANAGER_NOT_FOUND",
                assistant_message="Unable to locate the employee's manager.",
                recoverable=True,
            )

        status = self.get_approval_result(claim_id)
        claim_status = str(status.get("status", "")).lower()
        if claim_status and claim_status not in {
            "submitted",
            "pending",
            "under_review",
            "under review",
        }:
            return self._error_result(
                error_code="APPROVAL_ALREADY_COMPLETED",
                assistant_message=(
                    f"Claim {claim_id} is already in "
                    f"'{status.get('approval_status', status.get('status'))}' status."
                ),
                recoverable=False,
            )

        timestamp = self._utc_now()
        approval_result = {
            "approval_id": self._approval_id(claim_id),
            "claim_id": claim_id,
            "employee_id": employee_profile.employee_id,
            "approver_id": manager_profile.employee_id,
            "approver_name": manager_profile.employee_name,
            "status": "PENDING",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        return {
            "success": True,
            "status": "PENDING",
            "assistant_message": "Approval request created successfully.",
            "next_state": "receipt",
            "approval_result": approval_result,
        }

    def parse_decision_command(self, message: str) -> dict[str, Any] | None:
        """Parse deterministic manager approval commands."""

        text = message.strip()
        approve_match = self._APPROVE_PATTERN.match(text)
        if approve_match:
            claim_id = approve_match.group(1) or approve_match.group(2) or approve_match.group(3)
            return {
                "decision": "approve",
                "claim_id": claim_id.upper() if claim_id else "",
                "reason": None,
            }

        reject_match = self._REJECT_PATTERN.match(text)
        if reject_match:
            claim_id = reject_match.group(1) or reject_match.group(2)
            reason = reject_match.group(3).strip() if reject_match.group(3) else None
            return {
                "decision": "reject",
                "claim_id": claim_id.upper() if claim_id else "",
                "reason": reason,
            }
        return None

    def has_pending_rejection(self) -> bool:
        return self._pending_rejection is not None

    def process_pending_rejection_reason(
        self,
        reason: str,
        *,
        approver_id: str,
        approver_name: str,
    ) -> dict[str, Any]:
        """Resume a pending rejection after the manager provides comments."""

        if self._pending_rejection is None:
            return self._error_result(
                error_code="NO_PENDING_REJECTION",
                assistant_message="There is no pending rejection waiting for a reason.",
                recoverable=False,
            )

        claim_id = self._pending_rejection["claim_id"]
        self._pending_rejection = None
        return self.process_decision(
            claim_id=claim_id,
            decision="reject",
            approver_id=approver_id,
            approver_name=approver_name,
            reason=reason,
        )

    def process_decision(
        self,
        *,
        claim_id: str,
        decision: str,
        approver_id: str,
        approver_name: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Approve or reject a claim with structured error handling."""

        normalized_decision = decision.strip().lower()
        if normalized_decision not in {"approve", "reject"}:
            return self._error_result(
                error_code="INVALID_APPROVAL_COMMAND",
                assistant_message="I couldn't understand that approval command.",
                recoverable=True,
            )

        if normalized_decision == "reject" and (reason is None or len(reason.strip()) < 5):
            self._pending_rejection = {"claim_id": claim_id}
            return self._error_result(
                error_code="REJECTION_REASON_REQUIRED",
                assistant_message="Please provide a reason for rejection.",
                recoverable=True,
                next_state="waiting_rejection_reason",
            )

        try:
            if normalized_decision == "approve":
                result = approve_claim(
                    claim_id=claim_id,
                    approver_id=approver_id,
                    approver_name=approver_name,
                )
                status = "APPROVED"
                assistant_message = f"Claim {claim_id} has been approved."
            else:
                result = reject_claim(
                    claim_id=claim_id,
                    approver_id=approver_id,
                    approver_name=approver_name,
                    reason=reason.strip(),
                )
                status = "REJECTED"
                assistant_message = f"Claim {claim_id} has been rejected."
        except ApplicationException as exc:
            return self._error_result(
                error_code=exc.error_code,
                assistant_message=exc.message,
                recoverable=exc.recoverable,
            )
        except ValueError as exc:
            return self._error_result(
                error_code="APPROVAL_ALREADY_COMPLETED",
                assistant_message=str(exc),
                recoverable=False,
            )
        except Exception as exc:
            return self._error_result(
                error_code=exc.__class__.__name__.upper(),
                assistant_message="I couldn't process the approval decision right now.",
                recoverable=True,
            )

        plain = self._plain_value(result)
        approval_result = {
            "approval_id": self._approval_id(claim_id),
            "claim_id": claim_id,
            "status": status,
            "approver_id": approver_id,
            "approver_name": approver_name,
            "approved_at": self._stringify_datetime(
                self._nested_value(plain, "approval", "approved_at") or plain.get("processed_at")
            ),
            "reason": reason.strip() if reason else None,
        }
        return {
            "success": True,
            "status": status,
            "assistant_message": assistant_message,
            "next_state": "completed",
            "approval_result": approval_result,
            "claim": plain,
        }

    def _error_result(
        self,
        *,
        error_code: str,
        assistant_message: str,
        recoverable: bool,
        next_state: str = "waiting_user",
    ) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": error_code,
            "assistant_message": assistant_message,
            "recoverable": recoverable,
            "next_state": next_state,
        }

    def _approval_id(self, claim_id: str) -> str:
        suffix = claim_id.removeprefix("CLM") or claim_id
        return f"APR{suffix}"

    def _plain_value(self, value: Any) -> Any:
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return self._plain_value(value.model_dump())
        if isinstance(value, Mapping):
            return {str(key): self._plain_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._plain_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._plain_value(item) for item in value]
        return value

    def _nested_value(self, payload: Any, section: str, key: str) -> Any:
        if isinstance(payload, Mapping):
            section_value = payload.get(section)
            if isinstance(section_value, Mapping):
                return section_value.get(key)
        return None

    def _stringify_datetime(self, value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat()
        if value is None:
            return None
        return str(value)

    def _utc_now(self) -> str:
        return datetime.now(UTC).isoformat()
