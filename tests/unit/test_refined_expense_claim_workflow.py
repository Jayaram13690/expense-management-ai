from datetime import date, timedelta
from decimal import Decimal

import pytest

from exceptions.service import ServiceException
from models.dto.expense_item import ExpenseItem
from models.dto.submit_claim import SubmitExpenseClaimRequest
from models.expense_line_item import LineItemStatus
from services.expense_claim_service import ExpenseClaimService

service = ExpenseClaimService()


def build_unique_request(
    trip_offset_days: int, receipt_available: bool = True
) -> SubmitExpenseClaimRequest:
    # Use dynamically generated dates to avoid duplicates across test runs if needed
    start_date = date(2026, 7, 10) + timedelta(days=trip_offset_days)
    end_date = start_date + timedelta(days=2)
    return SubmitExpenseClaimRequest(
        employee_id="EMP0001",
        trip_name=f"AWS Summit Hyderabad {trip_offset_days}",
        business_purpose="Evaluate Amazon Bedrock AgentCore capabilities for enterprise clients.",
        destination="Hyderabad",
        trip_start_date=start_date,
        trip_end_date=end_date,
        comments="Unit test preview and submit",
        expense_items=[
            ExpenseItem(
                category_code="HOTEL",
                description="Hotel stay",
                expense_date=start_date,
                requested_amount=Decimal("4500.00"),
                currency="INR",
                receipt_available=receipt_available,
            )
        ],
    )


def test_duplicate_claims_raise_exception():
    # 1. Clear database of any test records for this trip
    req = build_unique_request(100)
    claims = service.detect_duplicate_claims(
        req.employee_id, req.trip_name, req.trip_start_date, req.trip_end_date
    )
    for c in claims:
        service.claim_repository.delete(c.claim_id)

    # 2. First preview should succeed
    preview1 = service.preview_claim(req)
    assert preview1 is not None

    # 3. Submit the claim
    claim = service.submit_claim(req)
    assert claim is not None
    assert claim.claim_id is not None

    # 4. Previewing again should raise ServiceException with CLAIM_ALREADY_EXISTS
    with pytest.raises(ServiceException) as exc_info:
        service.preview_claim(req)
    assert exc_info.value.error_code == "CLAIM_ALREADY_EXISTS"
    assert "already exists for this employee and trip" in exc_info.value.message

    # 5. Submitting again should also raise ServiceException with CLAIM_ALREADY_EXISTS
    with pytest.raises(ServiceException) as exc_info2:
        service.submit_claim(req)
    assert exc_info2.value.error_code == "CLAIM_ALREADY_EXISTS"
    assert "already exists for this employee and trip" in exc_info2.value.message

    # Clean up
    service.claim_repository.delete(claim.claim_id)


def test_receipt_warning_logic():
    # Submit request with receipt_available = False
    req = build_unique_request(200, receipt_available=False)

    # Clean up any potential leftover duplicate claim from failed runs
    claims = service.detect_duplicate_claims(
        req.employee_id, req.trip_name, req.trip_start_date, req.trip_end_date
    )
    for c in claims:
        service.claim_repository.delete(c.claim_id)

    # 1. Preview the claim
    preview = service.preview_claim(req)
    assert preview.total_requested == Decimal("4500.00")
    # Hotel has policy daily limit. G11 grade (Rajesh Sharma) has limits. Let's see if G11 has hotel limit.
    # In any case, it should NOT be zeroed out or rejected!
    assert preview.total_approved > Decimal("0.00")

    # The status of the item must not be REJECTED
    assert preview.items[0].status != LineItemStatus.REJECTED

    # Warnings should contain receipt pending warning
    receipt_warning_found = False
    for warning in preview.warnings:
        if "Receipt upload is pending and can be attached later" in warning:
            receipt_warning_found = True
            break
    assert receipt_warning_found, f"Expected receipt warning, got: {preview.warnings}"

    # 2. Submit the claim
    claim = service.submit_claim(req)
    assert claim.expense_line_items[0].status != LineItemStatus.REJECTED
    assert claim.expense_line_items[0].approved_amount > Decimal("0.00")
    assert claim.status == "submitted"

    # Clean up
    service.claim_repository.delete(claim.claim_id)
