from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmployeeProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    employee_id: str
    employee_name: str | None = None
    employee_grade: str
    department: str | None = None
    manager_id: str | None = None
    history: list[Any] = Field(default_factory=list)


class PolicyCategory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eligible: bool | None = None
    limits: dict[str, Any] = Field(default_factory=dict)


class PolicyContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    employee_grade: str | None = None
    categories: dict[str, PolicyCategory] = Field(default_factory=dict)


class ClaimPreview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claimed_amount: str | None = None
    approved_amount: str | None = None
    variance: str | None = None
    policy_limits: Any = None
    reimbursement_summary: Any = None
    warnings: list[Any] = Field(default_factory=list)
    items: list[Any] = Field(default_factory=list)
    employee_id: str | None = None
    employee_name: str | None = None
    employee_grade: str | None = None


class SubmittedClaim(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim_id: str
    status: str
    employee_id: str | None = None
    employee_name: str | None = None
    employee_grade: str | None = None
    total_claimed: str | None = None
    total_approved: str | None = None
    currency: str | None = None


class ApprovalResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim_id: str | None = None
    approval_id: str | None = None
    status: str
    approver_id: str | None = None
    approver_name: str | None = None
    approved_at: str | None = None
    reason: str | None = None
    pending_claims: list[Any] = Field(default_factory=list)


class ReceiptResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    receipt_id: str | None = None
    status: str
    document_type: str | None = None
    summary: Any = None
