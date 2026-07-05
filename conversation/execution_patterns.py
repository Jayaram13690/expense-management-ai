from __future__ import annotations

import concurrent.futures
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from contracts import EmployeeProfile, PolicyCategory, PolicyContext
from conversation.conversation_context import ConversationContext
from conversation.execution_plan import ExecutionPattern
from models.dto.submit_claim import SubmitExpenseClaimRequest


class SequentialExecution:
    """Execute one business stage at a time."""

    def __init__(
        self,
        employee_agent: EmployeeAgent,
        expense_agent: ExpenseAgent,
        approval_agent: ApprovalAgent,
        receipt_agent: ReceiptAgent,
        **_: Any,
    ) -> None:
        self.employee_agent = employee_agent
        self.expense_agent = expense_agent
        self.approval_agent = approval_agent
        self.receipt_agent = receipt_agent

    def execute_employee(self, context: ConversationContext) -> dict[str, Any]:
        """Retrieve the employee profile."""
        if not context.employee_id:
            raise ValueError("Employee ID is required before employee retrieval")

        employee_profile = self.employee_agent.get_employee_profile(context.employee_id)
        context.employee_profile = employee_profile
        context.store_execution_result("employee_profile", employee_profile)

        return {
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "EMPLOYEE",
            "employee_profile": employee_profile,
        }

    def execute_expense_preview(self, context: ConversationContext) -> dict[str, Any]:
        """Generate a claim preview after policy data is available."""
        claim_request = self._build_claim_request(context)
        claim_preview = self._plain_value(
            self.expense_agent.preview_claim_request(
                claim_request,
                employee_profile=context.employee_profile,
                policy_context=context.policy_context,
            )
        )
        context.claim_preview = claim_preview
        context.store_execution_result("claim_preview", claim_preview)

        return {
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "PREVIEW",
            "claim_preview": claim_preview,
        }

    def execute_expense_submission(self, context: ConversationContext) -> dict[str, Any]:
        """Submit the confirmed expense claim."""
        claim_request = self._build_claim_request(context)
        submitted_claim = self._plain_value(
            self.expense_agent.submit_claim_request(
                claim_request,
                employee_profile=context.employee_profile,
                policy_context=context.policy_context,
            )
        )
        context.store_execution_result("submitted_claim", submitted_claim)

        claim_id = self._extract_claim_id(submitted_claim)
        if claim_id:
            context.claim_id = claim_id

        return {
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "SUBMISSION",
            "submitted_claim": submitted_claim,
        }

    def execute_approval(self, context: ConversationContext) -> dict[str, Any]:
        """Create the approval request."""
        if not context.claim_id:
            raise ValueError("Claim ID is required before approval execution")

        approval_result = self._plain_value(
            self.approval_agent.get_approval_result(context.claim_id)
        )
        context.store_execution_result("approval_result", approval_result)

        return {
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "APPROVAL",
            "approval_result": approval_result,
        }

    def execute_receipt(self, context: ConversationContext) -> dict[str, Any]:
        """Generate the acknowledgement payload."""
        if not context.claim_id:
            raise ValueError("Claim ID is required before receipt execution")

        receipt_result = self._plain_value(
            self.receipt_agent.generate_receipt_result(context.claim_id)
        )
        context.store_execution_result("receipt_result", receipt_result)

        return {
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "RECEIPT",
            "receipt_result": receipt_result,
        }

    def _employee_prompt(self, context: ConversationContext) -> str:
        return (
            "Retrieve the employee profile for employee_id "
            f"{context.employee_id} using the available tools."
        )

    def _expense_prompt(self, context: ConversationContext, *, action: str) -> str:
        claim = self._build_claim_request(context).model_dump(exclude_none=True)
        employee_profile = self._plain_value(
            context.employee_profile or context.get_execution_result("employee_profile") or {}
        )
        policy_context = self._plain_value(
            context.policy_context or context.get_execution_result("policy_context") or {}
        )
        return self._json_prompt(
            self._orchestration_payload(
                {
                    "task": action,
                    "employee_profile": employee_profile,
                    "policy_context": policy_context,
                    "claim": claim,
                },
                {
                    "preview": {"claim_preview": "canonical JSON only"},
                    "submit": {"submitted_claim": "canonical JSON only"},
                },
            )
        )

    def _build_claim_request(self, context: ConversationContext) -> SubmitExpenseClaimRequest:
        expense_items = []
        for item in context.expense_items:
            if not isinstance(item, Mapping):
                continue
            expense_items.append(
                {
                    "category_code": item.get("category_code"),
                    "description": item.get("description"),
                    "expense_date": item.get("expense_date"),
                    "requested_amount": item.get("requested_amount"),
                    "currency": item.get("currency"),
                    "receipt_available": item.get("receipt_available", False),
                }
            )

        return SubmitExpenseClaimRequest.model_validate(
            {
                "employee_id": context.employee_id,
                "trip_name": context.trip_name,
                "business_purpose": context.business_purpose,
                "destination": context.destination,
                "trip_start_date": context.trip_start_date,
                "trip_end_date": context.trip_end_date,
                "expense_items": expense_items,
            }
        )

    def _plain_value(self, value: Any) -> Any:
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return self._plain_value(value.model_dump())
        if isinstance(value, Mapping):
            return {key: self._plain_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._plain_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._plain_value(item) for item in value]
        return value

    def _has_only_keys(self, value: Any, allowed: set[str], *, required: set[str]) -> bool:
        if not isinstance(value, Mapping):
            return False
        keys = {str(key) for key in value}
        return required.issubset(keys) and keys.issubset(allowed)

    def _extract_claim_id(self, result: Any) -> str | None:
        if hasattr(result, "model_dump") and callable(result.model_dump):
            result = result.model_dump()
        if isinstance(result, Mapping):
            value = result.get("claim_id")
            if isinstance(value, str):
                return value
        return getattr(result, "claim_id", None)


class ParallelExecution:
    """Execute independent policy checks concurrently."""

    def __init__(self, policy_agent: PolicyAgent, **_: Any) -> None:
        self.policy_agent = policy_agent

    def execute(self, context: ConversationContext) -> dict[str, Any]:
        """Run eligibility and limits lookups concurrently for each category."""

        employee_grade = self._employee_grade(context)
        existing_policy_context = self._existing_policy_context(context)
        existing_categories = set(existing_policy_context.categories.keys())
        categories = self._expense_categories(context)
        if not categories:
            raise ValueError("At least one expense category is required for parallel execution")

        categories_to_lookup = [
            category for category in categories if category not in existing_categories
        ]
        category_results = self._category_payload(existing_policy_context)
        category_errors: dict[str, list[dict[str, Any]]] = {}

        if categories_to_lookup:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, len(categories_to_lookup) * 2)
            ) as executor:
                future_map: dict[concurrent.futures.Future[Any], tuple[str, str]] = {}
                for category in categories_to_lookup:
                    future_map[
                        executor.submit(
                            self.policy_agent.check_employee_eligibility,
                            category,
                            employee_grade,
                        )
                    ] = (category, "eligible")
                    future_map[
                        executor.submit(
                            self.policy_agent.get_category_limits,
                            category,
                            employee_grade,
                        )
                    ] = (category, "limits")

                for future in concurrent.futures.as_completed(future_map):
                    category, kind = future_map[future]
                    bucket = category_results.setdefault(category.upper(), {})
                    try:
                        result = future.result()
                    except Exception as exc:
                        category_errors.setdefault(category.upper(), []).append(
                            self._serialize_error(exc, kind)
                        )
                        continue

                    if kind == "eligible":
                        bucket["eligible"] = bool(result)
                    else:
                        bucket["limits"] = self._plain_mapping(result)

        completed_categories = {
            category: values
            for category, values in category_results.items()
            if {"eligible", "limits"}.issubset(values.keys())
        }
        policy_context = PolicyContext(
            employee_grade=employee_grade,
            categories={
                category: PolicyCategory.model_validate(values)
                for category, values in completed_categories.items()
            },
        )

        category_clarifications = self._build_category_clarifications(
            context,
            category_results=category_results,
            category_errors=category_errors,
        )

        if category_clarifications:
            context.store_execution_result("partial_policy_context", policy_context)
            return {
                "pattern": ExecutionPattern.PARALLEL.value,
                "stage_name": "POLICY",
                "tasks": ["check_employee_eligibility", "get_category_limits"],
                "results": category_results,
                "partial_policy_context": policy_context,
                "category_clarifications": category_clarifications,
                "failed_categories": category_errors,
            }

        context.policy_context = policy_context
        context.store_execution_result("policy_context", policy_context)
        context.execution_results.pop("partial_policy_context", None)

        return {
            "pattern": ExecutionPattern.PARALLEL.value,
            "stage_name": "POLICY",
            "tasks": ["check_employee_eligibility", "get_category_limits"],
            "results": category_results,
            "policy_context": policy_context,
            "failed_categories": category_errors,
        }

    def _employee_grade(self, context: ConversationContext) -> str:
        employee_profile = context.employee_profile or context.get_execution_result(
            "employee_profile"
        )
        if isinstance(employee_profile, EmployeeProfile) and employee_profile.employee_grade:
            return employee_profile.employee_grade
        raise ValueError("Employee grade is required before parallel policy execution")

    def _expense_categories(self, context: ConversationContext) -> list[str]:
        categories: list[str] = []
        for item in context.expense_items:
            if not isinstance(item, Mapping):
                continue
            category = (
                item.get("category_code") or item.get("category_identifier") or item.get("category")
            )
            if isinstance(category, str) and category and category.upper() not in categories:
                categories.append(category.upper())
        return categories

    def _existing_policy_context(self, context: ConversationContext) -> PolicyContext:
        existing = context.policy_context or context.get_execution_result("partial_policy_context")
        if isinstance(existing, PolicyContext):
            return existing
        if isinstance(existing, Mapping):
            return PolicyContext.model_validate(existing)
        return PolicyContext(employee_grade=None, categories={})

    def _category_payload(self, policy_context: PolicyContext) -> dict[str, dict[str, Any]]:
        payload: dict[str, dict[str, Any]] = {}
        for category, details in policy_context.categories.items():
            detail_payload = details.model_dump() if hasattr(details, "model_dump") else details
            if isinstance(detail_payload, Mapping):
                payload[category] = self._plain_mapping(detail_payload)
        return payload

    def _build_category_clarifications(
        self,
        context: ConversationContext,
        *,
        category_results: Mapping[str, Mapping[str, Any]],
        category_errors: Mapping[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        clarifications: list[dict[str, Any]] = []
        failing_categories = {category for category, errors in category_errors.items() if errors}
        failing_categories.update(
            category
            for category, values in category_results.items()
            if not {"eligible", "limits"}.issubset(values.keys())
        )

        for expense_index, item in enumerate(context.expense_items):
            if not isinstance(item, Mapping):
                continue
            category = (
                item.get("category_code") or item.get("category_identifier") or item.get("category")
            )
            if not isinstance(category, str) or category.upper() not in failing_categories:
                continue

            errors = category_errors.get(category.upper(), [])
            first_error = errors[0] if errors else {}
            clarifications.append(
                {
                    "expense_index": expense_index,
                    "entered_category": item.get("entered_category")
                    or category
                    or item.get("description")
                    or "Unknown category",
                    "requested_amount": item.get("requested_amount"),
                    "currency": item.get("currency") or "INR",
                    "description": item.get("description") or "",
                    "reason": first_error.get(
                        "message",
                        f"I couldn't retrieve policy details for {category.upper()}.",
                    ),
                    "error_code": first_error.get("error_code"),
                    "options": context.category_clarification_options(),
                }
            )

        return clarifications

    def _serialize_error(self, exc: Exception, stage: str) -> dict[str, Any]:
        return {
            "stage": stage,
            "error_code": getattr(exc, "error_code", exc.__class__.__name__),
            "message": getattr(exc, "message", str(exc)),
        }

    def _plain_mapping(self, value: Any) -> dict[str, Any]:
        plain: dict[str, Any] = {}
        if isinstance(value, Mapping):
            for key, item in value.items():
                plain[key] = self._plain_value(item)
        return plain

    def _plain_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Mapping):
            return {key: self._plain_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._plain_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._plain_value(item) for item in value]
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return self._plain_value(value.model_dump())
        return value


class HumanInTheLoopExecution:
    """Handle the confirmation pause and resume step."""

    def build_prompt(self, context: ConversationContext) -> str:
        preview = context.claim_preview or {}
        claimed_amount = self._lookup(preview, "total_requested", "claimed_amount", default="N/A")
        approved_amount = self._lookup(preview, "total_approved", "approved_amount", default="N/A")
        variance = self._format_variance(claimed_amount, approved_amount)
        warnings = self._lookup(preview, "warnings", default=[])
        policy_limits = self._policy_limits_summary(context)

        return (
            "Claim Summary\n"
            f"Claimed Amount: {claimed_amount}\n"
            f"Approved Amount: {approved_amount}\n"
            f"Variance: {variance}\n"
            f"Warnings: {self._format_warnings(warnings)}\n"
            f"Applied Policy Limits: {policy_limits}\n\n"
            "Do you want to submit?"
        )

    def _format_variance(self, claimed_amount: Any, approved_amount: Any) -> str:
        try:
            claimed = (
                claimed_amount
                if isinstance(claimed_amount, (int, float))
                else float(str(claimed_amount))
            )
            approved = (
                approved_amount
                if isinstance(approved_amount, (int, float))
                else float(str(approved_amount))
            )
            return f"{claimed - approved:.2f}"
        except (TypeError, ValueError):
            return "N/A"

    def _format_warnings(self, warnings: Any) -> str:
        if isinstance(warnings, list) and warnings:
            return "; ".join(str(item) for item in warnings)
        if warnings:
            return str(warnings)
        return "No warnings"

    def _policy_limits_summary(self, context: ConversationContext) -> str:
        policy_context = context.policy_context
        if policy_context is None:
            return "No policy limits available"

        payload = (
            policy_context.model_dump()
            if hasattr(policy_context, "model_dump") and callable(policy_context.model_dump)
            else policy_context
        )
        categories = payload.get("categories", {}) if isinstance(payload, Mapping) else {}
        if not isinstance(categories, Mapping) or not categories:
            return "No policy limits available"

        parts: list[str] = []
        for category, details in categories.items():
            if hasattr(details, "model_dump") and callable(details.model_dump):
                details = details.model_dump()
            if not isinstance(details, Mapping):
                continue
            limits = details.get("limits", {})
            if hasattr(limits, "model_dump") and callable(limits.model_dump):
                limits = limits.model_dump()
            if isinstance(limits, Mapping) and limits:
                limit_bits = ", ".join(f"{key}={value}" for key, value in limits.items())
            else:
                limit_bits = "No limits available"
            parts.append(f"{category}: {limit_bits}")

        return "; ".join(parts) if parts else "No policy limits available"

    def interpret(self, message: str) -> bool | None:
        normalized = message.strip().lower()
        if normalized in {"yes", "y", "confirm", "submit"}:
            return True
        if normalized in {"no", "n", "cancel", "stop"}:
            return False
        return None

    def _lookup(self, payload: Any, *keys: str, default: Any = None) -> Any:
        if hasattr(payload, "model_dump") and callable(payload.model_dump):
            payload = payload.model_dump()
        if isinstance(payload, Mapping):
            for key in keys:
                if key in payload:
                    return payload[key]
        return default

    def _format_variance(self, claimed_amount: Any, approved_amount: Any) -> str:
        try:
            claimed = (
                claimed_amount
                if isinstance(claimed_amount, (int, float))
                else float(str(claimed_amount))
            )
            approved = (
                approved_amount
                if isinstance(approved_amount, (int, float))
                else float(str(approved_amount))
            )
            return f"{claimed - approved:.2f}"
        except (TypeError, ValueError):
            return "N/A"

    def _format_warnings(self, warnings: Any) -> str:
        if isinstance(warnings, list) and warnings:
            return "; ".join(str(item) for item in warnings)
        if warnings:
            return str(warnings)
        return "No warnings"

    def _policy_limits_summary(self, context: ConversationContext) -> str:
        policy_context = context.policy_context
        if policy_context is None:
            return "No policy limits available"

        payload = (
            policy_context.model_dump()
            if hasattr(policy_context, "model_dump") and callable(policy_context.model_dump)
            else policy_context
        )
        categories = payload.get("categories", {}) if isinstance(payload, Mapping) else {}
        if not isinstance(categories, Mapping) or not categories:
            return "No policy limits available"

        parts: list[str] = []
        for category, details in categories.items():
            if hasattr(details, "model_dump") and callable(details.model_dump):
                details = details.model_dump()
            if not isinstance(details, Mapping):
                continue
            limits = details.get("limits", {})
            if hasattr(limits, "model_dump") and callable(limits.model_dump):
                limits = limits.model_dump()
            if isinstance(limits, Mapping) and limits:
                limit_bits = ", ".join(f"{key}={value}" for key, value in limits.items())
            else:
                limit_bits = "No limits available"
            parts.append(f"{category}: {limit_bits}")

        return "; ".join(parts) if parts else "No policy limits available"


__all__ = ["SequentialExecution", "ParallelExecution", "HumanInTheLoopExecution"]
