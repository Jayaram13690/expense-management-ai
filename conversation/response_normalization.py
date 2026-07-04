from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, TypedDict


class CanonicalEmployeeProfile(TypedDict, total=False):
    employee_id: str
    employee_name: str
    employee_grade: str
    department: str
    manager_id: str
    history: list[Any]
    raw: dict[str, Any]


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
    raw: dict[str, Any]


class CanonicalClaimSubmission(TypedDict, total=False):
    claim_id: str
    status: str
    employee_id: str
    employee_name: str
    employee_grade: str
    total_claimed: str
    total_approved: str
    currency: str
    raw: dict[str, Any]


class CanonicalApprovalResult(TypedDict, total=False):
    approval_id: str
    status: str
    approver_id: str
    approver_name: str
    approved_at: str
    reason: str
    raw: dict[str, Any]


class CanonicalReceiptResult(TypedDict, total=False):
    receipt_id: str
    status: str
    document_type: str
    summary: Any
    raw: dict[str, Any]


def normalize_response(value: Any) -> Any:
    if hasattr(value, "model_dump") and callable(value.model_dump):
        value = value.model_dump()
    if isinstance(value, Mapping):
        return {key: normalize_response(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_response(item) for item in value]
    return value


def normalize_employee_profile(value: Any) -> CanonicalEmployeeProfile:
    data = _as_dict(value)
    profile: CanonicalEmployeeProfile = {
        "employee_id": _first_str(data, "employee_id", "id"),
        "employee_name": _first_str(data, "employee_name", "full_name", "name"),
        "employee_grade": _first_str(data, "employee_grade", "grade"),
        "department": _first_str(data, "department"),
        "manager_id": _first_str(data, "manager_id"),
        "history": _as_list(data.get("history")),
        "raw": data,
    }
    return _strip_nones(profile)


def normalize_policy_context(
    value: Any, employee_grade: str | None = None
) -> CanonicalPolicyContext:
    data = _as_dict(value)

    if "categories" in data and isinstance(data["categories"], Mapping):
        categories: dict[str, CanonicalPolicyCategory] = {}
        for category_code, category_value in data["categories"].items():
            categories[str(category_code)] = normalize_policy_category(category_value)
        policy_context: CanonicalPolicyContext = {
            "employee_grade": _first_str(data, "employee_grade") or (employee_grade or ""),
            "categories": categories,
        }
        return _strip_nones(policy_context)

    categories = _coerce_flat_policy_categories(data)
    policy_context = {
        "employee_grade": _first_str(data, "employee_grade") or (employee_grade or ""),
        "categories": categories,
    }
    return _strip_nones(policy_context)


def normalize_policy_category(value: Any) -> CanonicalPolicyCategory:
    data = _as_dict(value)
    eligible_value = data.get("eligible")
    limits_source = data.get("limits") if isinstance(data.get("limits"), Mapping) else data
    category: CanonicalPolicyCategory = {
        "eligible": bool(eligible_value) if eligible_value is not None else False,
        "limits": _strip_nones(
            {
                key: normalize_response(val)
                for key, val in _as_dict(limits_source).items()
                if key != "eligible"
            }
        ),
    }
    return _strip_nones(category)


def normalize_expense_preview(value: Any) -> CanonicalExpensePreview:
    data = _as_dict(value)
    claimed_amount = _first_value(data, "claimed_amount", "total_requested", "requested_amount")
    approved_amount = _first_value(data, "approved_amount", "total_approved")
    variance = _first_value(data, "variance", "overall_variance_amount")
    policy_limits = _first_value(data, "policy_limits", "warnings")
    preview: CanonicalExpensePreview = {
        "claimed_amount": _stringify_amount(claimed_amount),
        "approved_amount": _stringify_amount(approved_amount),
        "variance": _stringify_amount(variance),
        "policy_limits": normalize_response(policy_limits),
        "reimbursement_summary": normalize_response(_first_value(data, "reimbursement_summary")),
        "warnings": _as_list(data.get("warnings")),
        "items": _as_list(data.get("items")),
        "employee_id": _first_str(data, "employee_id"),
        "employee_name": _first_str(data, "employee_name"),
        "employee_grade": _first_str(data, "employee_grade", "grade"),
        "raw": data,
    }
    return _strip_nones(preview)


def normalize_claim_submission(value: Any) -> CanonicalClaimSubmission:
    data = _as_dict(value)
    submission: CanonicalClaimSubmission = {
        "claim_id": _first_str(data, "claim_id", "id"),
        "status": _first_str(data, "status"),
        "employee_id": _first_str(data, "employee_id"),
        "employee_name": _first_str(data, "employee_name"),
        "employee_grade": _first_str(data, "employee_grade", "grade"),
        "total_claimed": _stringify_amount(_first_value(data, "total_claimed", "claimed_amount")),
        "total_approved": _stringify_amount(
            _first_value(data, "total_approved", "approved_amount")
        ),
        "currency": _first_str(data, "currency"),
        "raw": data,
    }
    return _strip_nones(submission)


def normalize_approval_result(value: Any) -> CanonicalApprovalResult:
    data = _as_dict(value)
    result: CanonicalApprovalResult = {
        "approval_id": _first_str(data, "approval_id", "id"),
        "status": _first_str(data, "status"),
        "approver_id": _first_str(data, "approver_id"),
        "approver_name": _first_str(data, "approver_name"),
        "approved_at": _first_str(data, "approved_at"),
        "reason": _first_str(data, "reason"),
        "raw": data,
    }
    return _strip_nones(result)


def normalize_receipt_result(value: Any) -> CanonicalReceiptResult:
    data = _as_dict(value)
    result: CanonicalReceiptResult = {
        "receipt_id": _first_str(data, "receipt_id", "id"),
        "status": _first_str(data, "status"),
        "document_type": _first_str(data, "document_type"),
        "summary": normalize_response(_first_value(data, "summary", "reimbursement_summary")),
        "raw": data,
    }
    return _strip_nones(result)


def _as_dict(value: Any) -> dict[str, Any]:
    normalized = normalize_response(value)
    if isinstance(normalized, Mapping):
        return dict(normalized)
    return {"value": normalized}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    normalized = normalize_response(value)
    if isinstance(normalized, list):
        return normalized
    return [normalized]


def _first_str(data: Mapping[str, Any], *keys: str) -> str | None:
    value = _first_value(data, *keys)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if value is not None:
        return str(value)
    return None


def _first_value(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


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


def _coerce_flat_policy_categories(data: Mapping[str, Any]) -> dict[str, CanonicalPolicyCategory]:
    categories: dict[str, CanonicalPolicyCategory] = {}
    for key, value in data.items():
        if key in {"employee_grade", "raw"}:
            continue
        if not isinstance(key, str):
            continue
        if not isinstance(value, Mapping):
            continue
        categories[key] = normalize_policy_category(value)
    return categories


def _strip_nones(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _strip_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_nones(v) for v in value if v is not None]
    return value
