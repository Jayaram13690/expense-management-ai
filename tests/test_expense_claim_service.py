"""
Integration tests for ExpenseClaimService.

Run these tests only after:
1. DynamoDB tables are created.
2. Seed data has been inserted.
"""

from datetime import date

from models.dto.expense_item import ExpenseItem
from models.dto.submit_claim import SubmitExpenseClaimRequest
from services.expense_claim_service import ExpenseClaimService

service = ExpenseClaimService()


def build_request() -> SubmitExpenseClaimRequest:
    """Create a valid expense claim request."""

    return SubmitExpenseClaimRequest(
        employee_id="EMP0001",
        trip_name="AWS Summit Bangalore 2026",
        business_purpose=("Attend AWS Summit to evaluate Amazon Bedrock AgentCore capabilities."),
        destination="Bangalore",
        trip_start_date=date(2026, 6, 10),
        trip_end_date=date(2026, 6, 12),
        comments="Integration test",
        expense_items=[
            ExpenseItem(
                category_code="HOTEL",  # Verify this exists in your DB
                description="Hotel accommodation for conference",
                expense_date=date(2026, 6, 10),
                requested_amount=4500,
                currency="INR",
                receipt_available=True,
            ),
            ExpenseItem(
                category_code="MEALS",  # Verify this exists in your DB
                description="Business lunch with client",
                expense_date=date(2026, 6, 11),
                requested_amount=1200,
                currency="INR",
                receipt_available=True,
            ),
        ],
    )


def test_preview_claim():
    """Preview should calculate totals without persisting."""

    request = build_request()

    preview = service.preview_claim(request)

    assert preview.total_requested > 0
    assert preview.total_approved > 0
    assert len(preview.items) == 2

    print("\nPreview Test Passed")
    print(preview)


def test_submit_claim():
    """Submitting should persist a claim."""

    request = build_request()

    claim = service.submit_claim(request)

    assert claim.claim_id is not None
    assert claim.employee_id == "EMP0001"

    print("\nSubmit Test Passed")
    print(claim.claim_id)

    return claim.claim_id


def test_get_claim():
    """Retrieve persisted claim."""

    claim_id = test_submit_claim()

    claim = service.get_claim(claim_id)

    assert claim is not None
    assert claim.claim_id == claim_id

    print("\nGet Claim Test Passed")


def test_employee_claims():
    """List employee claims."""

    claims = service.list_employee_claims("EMP0001")

    assert len(claims) >= 1

    print("\nEmployee Claim List Passed")
    print(len(claims))


def test_pending_claims():
    """List submitted claims."""

    claims = service.list_pending_claims()

    print("\nPending Claims")
    print(len(claims))


if __name__ == "__main__":
    print("=" * 60)

    test_preview_claim()

    claim_id = test_submit_claim()

    test_get_claim()

    test_employee_claims()

    test_pending_claims()

    print("=" * 60)
    print("ALL TESTS PASSED")
