from __future__ import annotations

import json
import re
from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from typing import Any, TypedDict


class CanonicalEmployeeProfile(TypedDict, total=False):
    employee_id: str
    employee_name: str
    employee_grade: str
    department: str
    manager_id: str
    history: list[Any]


class CanonicalPolicyCategory(TypedDict, total=False):
    eligible: bool
    limits: dict[str, Any]


class CanonicalPolicyContext(TypedDict, total=False):
    employee_grade: str
    categories: dict[str, CanonicalPolicyCategory]


class CanonicalExpensePreview(TypedDict, total=False):
    claimed_amount: str
    approved_amount: str
    variance: str
    policy_limits: Any
    reimbursement_summary: Any
    warnings: list[Any]
    items: list[Any]
    employee_id: str
    employee_name: str
    employee_grade: str


class CanonicalClaimSubmission(TypedDict, total=False):
    claim_id: str
    status: str
    employee_id: str
    employee_name: str
    employee_grade: str
    total_claimed: str
    total_approved: str
    currency: str


class CanonicalClaimStatus(TypedDict, total=False):
    claim_id: str
    status: str
    submitted_at: str
    employee_id: str
    employee_name: str
    total_amount: str
    approved_amount: str
    reimbursable_amount: str
    currency: str
    approval_status: str
    approval_at: str
    approver_id: str
    approver_name: str


class CanonicalApprovalResult(TypedDict, total=False):
    claim_id: str
    approval_id: str
    status: str
    approver_id: str
    approver_name: str
    approved_at: str
    reason: str
    pending_claims: list[Any]


class CanonicalReceiptResult(TypedDict, total=False):
    receipt_id: str
    status: str
    document_type: str
    summary: Any


def parse_agent_response(value: Any) -> Any:
    """Parse agent responses into plain Python values.

    Accepts dicts directly, parses JSON strings, and strips Markdown code fences
    before JSON parsing. Returns the original value when parsing is not possible.
    """

    if hasattr(value, "model_dump") and callable(value.model_dump):
        value = value.model_dump()

    if isinstance(value, Mapping):
        return {key: parse_agent_response(item) for key, item in value.items()}

    if isinstance(value, list):
        return [parse_agent_response(item) for item in value]

    if isinstance(value, tuple):
        return tuple(parse_agent_response(item) for item in value)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return stripped
        fenced = _strip_code_fences(stripped)
        candidate = fenced.strip()
        if candidate:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                return stripped
            return parse_agent_response(parsed)
        return stripped

    return value


def canonical_employee_response(value: Any) -> dict[str, Any]:
    return {"employee_profile": build_employee_profile(value)}


def canonical_policy_response(
    value: Any,
    *,
    employee_grade: str | None = None,
    category_hint: str | None = None,
) -> dict[str, Any]:
    return {
        "policy_context": build_policy_context(
            value,
            employee_grade=employee_grade,
            category_hint=category_hint,
        )
    }


def canonical_expense_response(value: Any, *, payload: Any | None = None) -> dict[str, Any]:
    if _looks_like_claim_status_request(payload, value):
        return {"claim_status": build_claim_status(value)}
    if _looks_like_claim_submission(value):
        return {"submitted_claim": build_claim_submission(value)}
    return {"claim_preview": build_expense_preview(value, payload=payload)}


def canonical_approval_response(value: Any) -> dict[str, Any]:
    return {"approval_result": build_approval_result(value)}


def canonical_receipt_response(value: Any) -> dict[str, Any]:
    return {"receipt_result": build_receipt_result(value)}


def build_employee_profile(value: Any) -> CanonicalEmployeeProfile:
    data = _as_dict(value)
    profile: CanonicalEmployeeProfile = {
        "employee_id": _first_str(data, "employee_id", "id"),
        "employee_name": _first_str(data, "employee_name", "full_name", "name"),
        "employee_grade": _first_str(data, "employee_grade", "grade"),
        "department": _first_str(data, "department"),
        "manager_id": _first_str(data, "manager_id"),
        "history": _as_list(data.get("history") or data.get("claims")),
    }
    return _strip_nones(profile)


def build_policy_context(
    value: Any,
    *,
    employee_grade: str | None = None,
    category_hint: str | None = None,
) -> CanonicalPolicyContext:
    data = _as_dict(value)

    if "policy_context" in data and isinstance(data["policy_context"], Mapping):
        return build_policy_context(
            data["policy_context"],
            employee_grade=employee_grade,
            category_hint=category_hint,
        )

    if "categories" in data and isinstance(data["categories"], Mapping):
        categories: dict[str, CanonicalPolicyCategory] = {}
        for category_code, category_value in data["categories"].items():
            categories[str(category_code).upper()] = build_policy_category(category_value)
        context: CanonicalPolicyContext = {
            "employee_grade": _first_str(data, "employee_grade") or employee_grade,
            "categories": categories,
        }
        return _strip_nones(context)

    category_name = _infer_category_name(data, category_hint)
    category_payload = build_policy_category(data)
    categories = {category_name: category_payload} if category_name else {}

    context = {
        "employee_grade": _first_str(data, "employee_grade") or employee_grade,
        "categories": categories,
    }
    return _strip_nones(context)


def build_policy_category(value: Any) -> CanonicalPolicyCategory:
    data = _as_dict(value)
    eligible_value = data.get("eligible")
    limits_source = data.get("limits") if isinstance(data.get("limits"), Mapping) else data
    limits = {
        key: _to_plain(val)
        for key, val in _as_dict(limits_source).items()
        if key
        not in {
            "eligible",
            "policy_context",
            "category",
            "category_code",
            "category_id",
            "category_identifier",
        }
    }
    category: CanonicalPolicyCategory = {}
    if eligible_value is not None:
        category["eligible"] = bool(eligible_value)
    if limits:
        category["limits"] = _strip_nones(limits)
    return _strip_nones(category)


def build_expense_preview(value: Any, *, payload: Any | None = None) -> CanonicalExpensePreview:
    data = _as_dict(value)
    requested = _first_value(data, "claimed_amount", "total_requested", "requested_amount")
    approved = _first_value(data, "approved_amount", "total_approved")
    variance = _first_value(data, "variance", "overall_variance_amount")
    policy_limits = _first_value(data, "policy_limits")

    if policy_limits is None and isinstance(payload, Mapping):
        policy_limits = payload.get("policy_context")

    preview: CanonicalExpensePreview = {
        "claimed_amount": _stringify_amount(requested),
        "approved_amount": _stringify_amount(approved),
        "variance": (
            _stringify_amount(variance)
            if variance is not None
            else _stringify_amount(_subtract_amounts(requested, approved))
        ),
        "policy_limits": _to_plain(policy_limits),
        "reimbursement_summary": _to_plain(_first_value(data, "reimbursement_summary")),
        "warnings": _as_list(data.get("warnings")),
        "items": _as_list(data.get("items")),
        "employee_id": _first_str(data, "employee_id"),
        "employee_name": _first_str(data, "employee_name"),
        "employee_grade": _first_str(data, "employee_grade", "grade"),
    }
    return _strip_nones(preview)


def build_claim_submission(value: Any) -> CanonicalClaimSubmission:
    data = _as_dict(value)
    amount = _nested_mapping(data, "amount")
    submission: CanonicalClaimSubmission = {
        "claim_id": _first_str(data, "claim_id", "id"),
        "status": _first_str(data, "status"),
        "employee_id": _first_str(data, "employee_id"),
        "employee_name": _first_str(data, "employee_name"),
        "employee_grade": _first_str(data, "employee_grade", "grade"),
        "total_claimed": _stringify_amount(
            _first_value(data, "total_claimed", "claimed_amount")
            or _first_value(amount, "claimed_amount")
        ),
        "total_approved": _stringify_amount(
            _first_value(data, "total_approved", "approved_amount")
            or _first_value(amount, "approved_amount", "reimbursable_amount")
        ),
        "currency": _first_str(data, "currency") or _first_str(amount, "currency"),
    }
    return _strip_nones(submission)


def build_claim_status(value: Any) -> CanonicalClaimStatus:
    data = _as_dict(value)
    amount = _nested_mapping(data, "amount")
    approval = _nested_mapping(data, "approval")
    status: CanonicalClaimStatus = {
        "claim_id": _first_str(data, "claim_id", "id"),
        "status": _first_str(data, "status"),
        "submitted_at": _stringify_datetime(_first_value(data, "submitted_at")),
        "employee_id": _first_str(data, "employee_id"),
        "employee_name": _first_str(data, "employee_name"),
        "total_amount": _stringify_amount(
            _first_value(data, "total_amount", "claimed_amount")
            or _first_value(amount, "claimed_amount")
        ),
        "approved_amount": _stringify_amount(
            _first_value(data, "approved_amount") or _first_value(amount, "approved_amount")
        ),
        "reimbursable_amount": _stringify_amount(
            _first_value(data, "reimbursable_amount") or _first_value(amount, "reimbursable_amount")
        ),
        "currency": _first_str(data, "currency") or _first_str(amount, "currency"),
        "approval_status": _first_str(data, "approval_status"),
        "approval_at": _stringify_datetime(
            _first_value(data, "approval_at") or _first_value(approval, "approved_at")
        ),
        "approver_id": _first_str(data, "approver_id") or _first_str(approval, "approver_id"),
        "approver_name": _first_str(data, "approver_name") or _first_str(approval, "approver_name"),
    }
    return _strip_nones(status)


def build_approval_result(value: Any) -> CanonicalApprovalResult:
    data = _as_dict(value)
    if isinstance(value, list):
        return {"pending_claims": _as_list(value)}

    approval = _nested_mapping(data, "approval")
    result: CanonicalApprovalResult = {
        "claim_id": _first_str(data, "claim_id", "id"),
        "approval_id": _first_str(data, "approval_id"),
        "status": _first_str(data, "status") or _first_str(approval, "status"),
        "approver_id": _first_str(data, "approver_id") or _first_str(approval, "approver_id"),
        "approver_name": _first_str(data, "approver_name") or _first_str(approval, "approver_name"),
        "approved_at": _stringify_datetime(
            _first_value(data, "approved_at") or _first_value(approval, "approved_at")
        ),
        "reason": _first_str(data, "reason") or _first_str(approval, "rejection_reason"),
    }
    return _strip_nones(result)


def build_receipt_result(value: Any) -> CanonicalReceiptResult:
    data = _as_dict(value)
    summary = _first_value(data, "summary", "reimbursement_summary")
    if summary is None:
        summary = data
    result: CanonicalReceiptResult = {
        "receipt_id": _first_str(data, "receipt_id", "id"),
        "status": _first_str(data, "status"),
        "document_type": _first_str(data, "document_type"),
        "summary": _to_plain(summary),
    }
    return _strip_nones(result)


def _looks_like_claim_submission(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(key in value for key in ("claim_id", "submitted_at", "total_claimed"))
    return hasattr(value, "claim_id") and hasattr(value, "submitted_at")


def _looks_like_claim_status_request(payload: Any, value: Any) -> bool:
    if isinstance(payload, str):
        text = payload.lower()
        if "status of claim" in text or "approval status" in text:
            return True
    if isinstance(value, Mapping):
        return "approval_status" in value and "reimbursable_amount" in value
    return False


def _infer_category_name(data: Mapping[str, Any], category_hint: str | None) -> str | None:
    for key in (
        "category_identifier",
        "category_id",
        "category_code",
        "category",
        "expense_category",
    ):
        value = _first_str(data, key)
        if value:
            return value.upper()
    if category_hint:
        return category_hint.upper()
    return None


def _subtract_amounts(requested: Any, approved: Any) -> Decimal | None:
    requested_decimal = _to_decimal(requested)
    approved_decimal = _to_decimal(approved)
    if requested_decimal is None or approved_decimal is None:
        return None
    return requested_decimal - approved_decimal


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        try:
            return Decimal(str(value))
        except Exception:  # pragma: no cover - defensive
            return None
    return None


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump") and callable(value.model_dump):
        value = value.model_dump()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_to_plain(item) for item in value)
    return value


def _as_dict(value: Any) -> dict[str, Any]:
    normalized = parse_agent_response(value)
    if isinstance(normalized, Mapping):
        return dict(normalized)
    return {"value": normalized}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    normalized = parse_agent_response(value)
    if isinstance(normalized, list):
        return normalized
    return [normalized]


def _first_value(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _nested_mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


def _first_str(data: Mapping[str, Any], *keys: str) -> str | None:
    value = _first_value(data, *keys)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if value is None:
        return None
    return str(value)


def _stringify_amount(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return str(value)


def _stringify_datetime(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _strip_nones(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _strip_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_nones(v) for v in value if v is not None]
    return value


def _strip_code_fences(value: str) -> str:
    text = value.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        body = "\n".join(lines[1:-1]).strip()
        if lines[0].lower().startswith("```json"):
            return body
        return body

    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text
