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
from services.expense_allowance_service import ExpenseAllowanceService

# Travel validation error codes that are terminal for the current submission
# flow.  When one of these fires the collected trip data is fundamentally
# wrong (wrong dates, expired window, overlap) — there is nothing the user
# can "correct" in the next message without starting from scratch.  Setting
# recoverable=False on these codes causes the orchestrator to call
# reset_submission_flow() and return to ACTIVE state immediately.
#
# EXISTING_DRAFT is the single exception: it is recoverable=True because the
# user should be redirected to the existing draft, not blocked entirely.
_TRAVEL_VALIDATION_ERROR_CODES: frozenset[str] = frozenset(
    {
        "FUTURE_TRIP",
        "ONGOING_TRIP",
        "SUBMISSION_WINDOW_EXPIRED",
        "OVERLAPPING_TRIP",
        "EXPENSE_DATE_OUT_OF_RANGE",
    }
)


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
        self._allowance_service = ExpenseAllowanceService()

    def execute_employee(self, context: ConversationContext) -> dict[str, Any]:
        if not context.employee_id:
            return self._error_result(
                stage_name="EMPLOYEE",
                error_code="EMPLOYEE_ID_MISSING",
                assistant_message="Employee ID is required before employee retrieval.",
                recoverable=True,
            )

        try:
            employee_profile = self.employee_agent.get_employee_profile(context.employee_id)
        except Exception as exc:
            return self._error_result(
                stage_name="EMPLOYEE",
                error_code=getattr(exc, "error_code", exc.__class__.__name__.upper()),
                assistant_message=str(exc),
                recoverable=True,
            )

        context.employee_profile = employee_profile
        context.store_execution_result("employee_profile", employee_profile)
        return {
            "success": True,
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "EMPLOYEE",
            "employee_profile": employee_profile,
            "assistant_message": "Employee profile retrieved successfully.",
            "next_state": "policy",
        }

    def execute_expense_preview(self, context: ConversationContext) -> dict[str, Any]:
        try:
            claim_request = self._build_claim_request(context)
            claim_preview = self._plain_value(
                self.expense_agent.preview_claim_request(
                    claim_request,
                    employee_profile=context.employee_profile,
                    policy_context=context.policy_context,
                )
            )
        except Exception as exc:
            error_code = getattr(exc, "error_code", exc.__class__.__name__.upper())
            # Travel validation failures are terminal for this submission:
            # the collected trip data itself is invalid.  Mark not recoverable
            # so the orchestrator resets the flow and returns to ACTIVE state.
            recoverable = error_code not in _TRAVEL_VALIDATION_ERROR_CODES
            return self._error_result(
                stage_name="PREVIEW",
                error_code=error_code,
                assistant_message=str(exc),
                recoverable=recoverable,
            )

        context.claim_preview = claim_preview
        context.store_execution_result("claim_preview", claim_preview)
        return {
            "success": True,
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "PREVIEW",
            "claim_preview": claim_preview,
            "assistant_message": "Claim preview generated successfully.",
            "next_state": "allowance_validation",
        }

    def execute_allowance_validation(self, context: ConversationContext) -> dict[str, Any]:
        """
        Validate monthly expense allowance limits for the current claim.

        This stage runs AFTER Variance Calculation (expense_preview) and
        BEFORE the Human-in-the-Loop confirmation prompt.  It validates
        every expense category against the employee's remaining monthly
        allowance and blocks submission when any category is exceeded.

        Existing daily validation via ExpensePolicyService is unaffected.
        Both daily (existing) and monthly (new) validations must pass.
        """
        employee_profile = context.employee_profile or context.get_execution_result(
            "employee_profile"
        )
        if not isinstance(employee_profile, EmployeeProfile):
            return self._error_result(
                stage_name="ALLOWANCE_VALIDATION",
                error_code="EMPLOYEE_PROFILE_MISSING",
                assistant_message="Employee profile is required before allowance validation.",
                recoverable=False,
            )

        employee_id = str(employee_profile.employee_id or context.employee_id or "")
        employee_grade = str(employee_profile.employee_grade or "")

        if not employee_id or not employee_grade:
            return self._error_result(
                stage_name="ALLOWANCE_VALIDATION",
                error_code="EMPLOYEE_DATA_INCOMPLETE",
                assistant_message="Employee ID and grade are required for allowance validation.",
                recoverable=False,
            )

        expense_items = [
            {
                "category_code": item.get("category_code"),
                "requested_amount": item.get("requested_amount", Decimal("0.00")),
            }
            for item in context.expense_items
            if isinstance(item, Mapping) and item.get("category_code")
        ]

        if not expense_items:
            # No expense items to validate — skip gracefully
            return {
                "success": True,
                "pattern": ExecutionPattern.SEQUENTIAL.value,
                "stage_name": "ALLOWANCE_VALIDATION",
                "assistant_message": "Allowance Validation Passed — no expense items to validate.",
                "next_state": "confirmation",
            }

        try:
            results = self._allowance_service.validate_claim_allowance(
                employee_id=employee_id,
                employee_grade=employee_grade,
                expense_items=expense_items,
            )
        except Exception as exc:
            return self._error_result(
                stage_name="ALLOWANCE_VALIDATION",
                error_code=getattr(exc, "error_code", "ALLOWANCE_VALIDATION_ERROR"),
                assistant_message=(
                    f"Allowance validation could not be completed: {exc}. "
                    "Please contact support if this problem persists."
                ),
                recoverable=False,
            )

        exceeded = [r for r in results if r.exceeded]
        if exceeded:
            details = "\n".join(r.validation_message for r in exceeded)
            return self._error_result(
                stage_name="ALLOWANCE_VALIDATION",
                error_code="MONTHLY_ALLOWANCE_EXCEEDED",
                assistant_message=(
                    "Expense Allowance Validation Failed.\n\n"
                    f"{details}\n\n"
                    "Please modify your expenses and try again."
                ),
                recoverable=True,
            )

        context.store_execution_result(
            "allowance_validation_results",
            [r.summary_dict() for r in results],
        )

        return {
            "success": True,
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "ALLOWANCE_VALIDATION",
            "allowance_validation_results": [r.summary_dict() for r in results],
            "assistant_message": "Allowance Validation Passed — all categories within monthly limits.",
            "next_state": "confirmation",
        }

    def execute_expense_submission(self, context: ConversationContext) -> dict[str, Any]:
        try:
            claim_request = self._build_claim_request(context)
            submitted_claim = self._plain_value(
                self.expense_agent.submit_claim_request(
                    claim_request,
                    employee_profile=context.employee_profile,
                    policy_context=context.policy_context,
                )
            )
        except Exception as exc:
            error_code = getattr(exc, "error_code", exc.__class__.__name__.upper())
            # Same logic as execute_expense_preview: travel validation errors
            # are not recoverable within the current submission flow.
            recoverable = error_code not in _TRAVEL_VALIDATION_ERROR_CODES
            return self._error_result(
                stage_name="SUBMISSION",
                error_code=error_code,
                assistant_message=str(exc),
                recoverable=recoverable,
            )

        context.store_execution_result("submitted_claim", submitted_claim)
        claim_id = self._extract_claim_id(submitted_claim)
        if claim_id:
            context.claim_id = claim_id

        return {
            "success": True,
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": "SUBMISSION",
            "submitted_claim": submitted_claim,
            "assistant_message": f"Claim submitted successfully. Claim ID: {claim_id or 'N/A'}",
            "next_state": "approval",
        }

    def execute_approval(self, context: ConversationContext) -> dict[str, Any]:
        if not context.claim_id:
            return self._error_result(
                stage_name="APPROVAL",
                error_code="CLAIM_ID_MISSING",
                assistant_message="Claim ID is required before approval execution.",
                recoverable=False,
            )

        employee_profile = context.employee_profile or context.get_execution_result(
            "employee_profile"
        )
        if not isinstance(employee_profile, EmployeeProfile):
            return self._error_result(
                stage_name="APPROVAL",
                error_code="EMPLOYEE_PROFILE_MISSING",
                assistant_message=(
                    "Employee profile is required before creating the approval request."
                ),
                recoverable=False,
            )
        if not employee_profile.manager_id:
            return self._error_result(
                stage_name="APPROVAL",
                error_code="MANAGER_NOT_FOUND",
                assistant_message="Unable to locate the employee's manager.",
                recoverable=True,
            )

        try:
            manager_profile = self.employee_agent.get_employee_profile(employee_profile.manager_id)
        except Exception as exc:
            return self._error_result(
                stage_name="APPROVAL",
                error_code=getattr(exc, "error_code", exc.__class__.__name__.upper()),
                assistant_message="Unable to locate the employee's manager.",
                recoverable=True,
            )

        context.store_execution_result("manager_profile", manager_profile)
        result = self.approval_agent.create_approval_request(
            claim_id=context.claim_id,
            employee_profile=employee_profile,
            manager_profile=manager_profile,
        )
        result.setdefault("pattern", ExecutionPattern.SEQUENTIAL.value)
        result.setdefault("stage_name", "APPROVAL")
        return result

    def execute_receipt(self, context: ConversationContext) -> dict[str, Any]:
        if not context.claim_id:
            return self._error_result(
                stage_name="RECEIPT",
                error_code="CLAIM_ID_MISSING",
                assistant_message="Claim ID is required before receipt execution.",
                recoverable=False,
            )

        approval_result = context.get_execution_result("approval_result")
        if not isinstance(approval_result, Mapping):
            return self._error_result(
                stage_name="RECEIPT",
                error_code="APPROVAL_RESULT_MISSING",
                assistant_message=(
                    "Approval request details are missing, so the manager notification "
                    "cannot be sent."
                ),
                recoverable=True,
            )

        claim_snapshot = self._plain_value(
            context.get_execution_result("submitted_claim") or {"claim_id": context.claim_id}
        )
        claim_snapshot.setdefault("employee_id", context.employee_id)
        claim_snapshot.setdefault("trip_name", context.trip_name)
        claim_snapshot.setdefault("business_purpose", context.business_purpose)
        claim_snapshot.setdefault("destination", context.destination)
        claim_snapshot.setdefault("trip_start_date", context.trip_start_date)
        claim_snapshot.setdefault("trip_end_date", context.trip_end_date)
        claim_snapshot.setdefault("expense_items", list(context.expense_items))

        policy_context = self._plain_value(
            context.policy_context or context.get_execution_result("policy_context") or {}
        )
        claim_preview = self._plain_value(context.claim_preview or {})
        result = self.receipt_agent.send_manager_approval_email(
            claim_id=context.claim_id,
            approval_result=dict(approval_result),
            claim_snapshot=claim_snapshot,
            claim_preview=claim_preview,
            policy_context=policy_context,
            receipt_uploads=context.receipt_uploads,
        )
        result.setdefault("pattern", ExecutionPattern.SEQUENTIAL.value)
        result.setdefault("stage_name", "RECEIPT")
        return result

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

    def _extract_claim_id(self, result: Any) -> str | None:
        if hasattr(result, "model_dump") and callable(result.model_dump):
            result = result.model_dump()
        if isinstance(result, Mapping):
            value = result.get("claim_id")
            if isinstance(value, str):
                return value
        return getattr(result, "claim_id", None)

    def _error_result(
        self,
        *,
        stage_name: str,
        error_code: str,
        assistant_message: str,
        recoverable: bool,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "pattern": ExecutionPattern.SEQUENTIAL.value,
            "stage_name": stage_name,
            "error_code": error_code,
            "assistant_message": assistant_message,
            "recoverable": recoverable,
            "next_state": "waiting_user",
        }


class ParallelExecution:
    """Execute independent policy checks concurrently."""

    def __init__(self, policy_agent: PolicyAgent, **_: Any) -> None:
        self.policy_agent = policy_agent

    def execute(self, context: ConversationContext) -> dict[str, Any]:
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
                "success": True,
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
            "success": True,
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
        allowance_summary = self._allowance_summary(context)

        prompt = (
            "Claim Summary\n"
            f"Claimed Amount: {claimed_amount}\n"
            f"Approved Amount: {approved_amount}\n"
            f"Variance: {variance}\n"
            f"Warnings: {self._format_warnings(warnings)}\n"
            f"Applied Policy Limits: {policy_limits}\n"
        )
        if allowance_summary:
            prompt += f"Monthly Allowance Status: {allowance_summary}\n"
        prompt += "\nDo you want to submit?"
        return prompt


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
            claimed_text = claimed_amount
            if not isinstance(claimed_amount, (int, float)):
                claimed_text = str(claimed_amount)
            approved_text = approved_amount
            if not isinstance(approved_amount, (int, float)):
                approved_text = str(approved_amount)
            claimed = float(claimed_text)
            approved = float(approved_text)
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

    def _allowance_summary(self, context: ConversationContext) -> str:
        """Format allowance validation results for the confirmation prompt."""
        allowance_results = context.get_execution_result("allowance_validation_results")
        if not isinstance(allowance_results, list) or not allowance_results:
            return ""

        parts: list[str] = []
        for item in allowance_results:
            if not isinstance(item, Mapping):
                continue
            code = item.get("category_code", "")
            remaining = item.get("remaining", "N/A")
            currency = item.get("currency", "INR")
            parts.append(f"{code}: {currency} {remaining} remaining")

        return "; ".join(parts) if parts else ""


__all__ = ["SequentialExecution", "ParallelExecution", "HumanInTheLoopExecution"]
