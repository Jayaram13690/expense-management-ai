"""
Receipt service.

Contains business operations related to receipts.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from common.identifiers import ClaimId, ReceiptId
from exceptions.repository import RepositoryException
from models.expense_claim import ExpenseClaim
from models.expense_line_item import LineItemStatus
from models.receipt import Receipt
from repositories.receipt_repository import ReceiptRepository
from services.base import BaseService


class ReceiptService(BaseService):
    """
    Receipt business service.
    """

    def __init__(self) -> None:
        super().__init__()

        self.receipt_repository = ReceiptRepository()

    ###########################################################################
    # Receipt Operations
    ###########################################################################

    def get_receipt(
        self,
        receipt_id: ReceiptId,
    ) -> Receipt:
        """
        Retrieve a receipt by identifier.
        """

        self.log_start("Get Receipt")

        receipt = self.receipt_repository.get_receipt(receipt_id)

        if receipt is None:
            self.log_failure(
                "Get Receipt",
                f"Receipt '{receipt_id}' does not exist.",
            )

            raise RepositoryException(message=f"Receipt '{receipt_id}' does not exist.")

        self.log_success("Get Receipt")

        return receipt

    def save_receipt(
        self,
        receipt: Receipt,
    ) -> Receipt:
        """
        Create or update a receipt.
        """

        self.log_start("Save Receipt")

        saved_receipt = self.receipt_repository.save(receipt)

        self.log_success("Save Receipt")

        return saved_receipt

    def delete_receipt(
        self,
        receipt_id: ReceiptId,
    ) -> None:
        """
        Delete a receipt.
        """

        self.log_start("Delete Receipt")

        self.receipt_repository.delete_receipt(receipt_id)

        self.log_success("Delete Receipt")

    ###########################################################################
    # Claim Receipt Operations
    ###########################################################################

    def get_claim_receipts(
        self,
        claim_id: ClaimId,
    ) -> list[Receipt]:
        """
        Return all receipts attached to a claim.
        """

        self.log_start("Get Claim Receipts")

        receipts = self.receipt_repository.list_claim_receipts(claim_id)

        self.log_success("Get Claim Receipts")

        return receipts

    def count_claim_receipts(
        self,
        claim_id: ClaimId,
    ) -> int:
        """
        Return the number of receipts attached to a claim.
        """

        return self.receipt_repository.count_claim_receipts(claim_id)

    def receipt_exists(
        self,
        receipt_id: ReceiptId,
    ) -> bool:
        """
        Check whether a receipt exists.
        """

        return self.receipt_repository.receipt_exists(receipt_id)

    ###########################################################################
    # Business Document Generation
    ###########################################################################

    def generate_expense_claim_summary(
        self,
        claim: ExpenseClaim,
    ) -> dict:
        """
        Generate expense claim summary document.
        """
        self.log_start("Generate Expense Claim Summary")

        summary = {
            "document_type": "ExpenseClaimSummary",
            "claim_id": claim.claim_id,
            "employee_id": claim.employee_id,
            "employee_name": claim.employee_name,
            "employee_grade": claim.employee_grade,
            "department": claim.department,
            "trip_name": claim.trip_name,
            "business_purpose": claim.business_purpose,
            "destination": claim.destination,
            "trip_start_date": str(claim.trip_start_date),
            "trip_end_date": str(claim.trip_end_date),
            "submitted_date": str(claim.submitted_date),
            "status": claim.status,
            "total_claimed": str(claim.amount.claimed_amount),
            "total_approved": str(claim.amount.approved_amount),
            "total_reimbursable": str(claim.amount.reimbursable_amount),
            "currency": claim.amount.currency,
            "expense_items": [
                {
                    "category": item.category_name,
                    "expense_date": str(item.expense_date),
                    "claimed_amount": str(item.claimed_amount),
                    "approved_amount": str(item.approved_amount),
                    "status": item.status,
                    "remarks": item.remarks
                }
                for item in claim.expense_line_items
            ]
        }

        self.log_success("Generate Expense Claim Summary")
        return summary

    def generate_reimbursement_summary(
        self,
        claim: ExpenseClaim,
    ) -> dict:
        """
        Generate reimbursement summary document.
        """
        self.log_start("Generate Reimbursement Summary")

        reimbursement_summary = {
            "document_type": "ReimbursementSummary",
            "claim_id": claim.claim_id,
            "employee_id": claim.employee_id,
            "employee_name": claim.employee_name,
            "reimbursement_amount": str(claim.amount.reimbursable_amount),
            "currency": claim.amount.currency,
            "payment_method": "Bank Transfer",
            "payment_status": "Pending" if claim.status == ClaimStatus.APPROVED else "Not Approved",
            "expected_payment_date": "Within 7 business days of approval",
            "bank_account": "**** **** **** 1234",  # Masked for security
            "reimbursement_breakdown": [
                {
                    "category": item.category_name,
                    "reimbursement_amount": str(item.approved_amount),
                    "reason": item.remarks
                }
                for item in claim.expense_line_items
                if item.approved_amount > 0
            ]
        }

        self.log_success("Generate Reimbursement Summary")
        return reimbursement_summary

    def generate_policy_application_summary(
        self,
        claim: ExpenseClaim,
    ) -> dict:
        """
        Generate policy application summary document.
        """
        self.log_start("Generate Policy Application Summary")

        policy_summary = {
            "document_type": "PolicyApplicationSummary",
            "claim_id": claim.claim_id,
            "employee_id": claim.employee_id,
            "employee_name": claim.employee_name,
            "employee_grade": claim.employee_grade,
            "policy_compliance": {
                "compliant_items": 0,
                "non_compliant_items": 0,
                "compliance_details": []
            }
        }

        for item in claim.expense_line_items:
            compliance_detail = {
                "category": item.category_name,
                "claimed_amount": str(item.claimed_amount),
                "approved_amount": str(item.approved_amount),
                "compliant": item.status == LineItemStatus.APPROVED,
                "reason": item.remarks if item.remarks else "Policy compliant"
            }
            policy_summary["policy_compliance"]["compliance_details"].append(compliance_detail)
            
            if compliance_detail["compliant"]:
                policy_summary["policy_compliance"]["compliant_items"] += 1
            else:
                policy_summary["policy_compliance"]["non_compliant_items"] += 1

        self.log_success("Generate Policy Application Summary")
        return policy_summary

    def generate_expense_breakdown(
        self,
        claim: ExpenseClaim,
    ) -> dict:
        """
        Generate detailed expense breakdown document.
        """
        self.log_start("Generate Expense Breakdown")

        expense_breakdown = {
            "document_type": "ExpenseBreakdown",
            "claim_id": claim.claim_id,
            "employee_id": claim.employee_id,
            "employee_name": claim.employee_name,
            "trip_details": {
                "trip_name": claim.trip_name,
                "business_purpose": claim.business_purpose,
                "destination": claim.destination,
                "trip_duration": f"{(claim.trip_end_date - claim.trip_start_date).days + 1} days",
                "trip_dates": f"{claim.trip_start_date} to {claim.trip_end_date}"
            },
            "expense_categories": {},
            "summary": {
                "total_claimed": str(claim.amount.claimed_amount),
                "total_approved": str(claim.amount.approved_amount),
                "total_reimbursable": str(claim.amount.reimbursable_amount),
                "currency": claim.amount.currency
            }
        }

        # Group expenses by category
        for item in claim.expense_line_items:
            if item.category_name not in expense_breakdown["expense_categories"]:
                expense_breakdown["expense_categories"][item.category_name] = {
                    "claimed_total": Decimal("0.00"),
                    "approved_total": Decimal("0.00"),
                    "items": []
                }
            
            expense_breakdown["expense_categories"][item.category_name]["claimed_total"] += item.claimed_amount
            expense_breakdown["expense_categories"][item.category_name]["approved_total"] += item.approved_amount
            expense_breakdown["expense_categories"][item.category_name]["items"].append({
                "expense_date": str(item.expense_date),
                "claimed_amount": str(item.claimed_amount),
                "approved_amount": str(item.approved_amount),
                "status": item.status,
                "remarks": item.remarks
            })

        # Convert Decimal totals to strings
        for category in expense_breakdown["expense_categories"]:
            expense_breakdown["expense_categories"][category]["claimed_total"] = str(
                expense_breakdown["expense_categories"][category]["claimed_total"]
            )
            expense_breakdown["expense_categories"][category]["approved_total"] = str(
                expense_breakdown["expense_categories"][category]["approved_total"]
            )

        self.log_success("Generate Expense Breakdown")
        return expense_breakdown

    def generate_variance_report(
        self,
        claim: ExpenseClaim,
    ) -> dict:
        """
        Generate variance report document.
        """
        self.log_start("Generate Variance Report")

        from decimal import Decimal
        
        total_claimed = Decimal("0.00")
        total_approved = Decimal("0.00")
        
        variance_report = {
            "document_type": "VarianceReport",
            "claim_id": claim.claim_id,
            "employee_id": claim.employee_id,
            "employee_name": claim.employee_name,
            "overall_variance": {
                "total_claimed": "0.00",
                "total_approved": "0.00",
                "variance_amount": "0.00",
                "variance_percentage": "0.00%"
            },
            "item_variances": []
        }

        for item in claim.expense_line_items:
            total_claimed += item.claimed_amount
            total_approved += item.approved_amount
            
            variance_amount = item.claimed_amount - item.approved_amount
            variance_percentage = ((variance_amount / item.claimed_amount) * 100) if item.claimed_amount > 0 else 0
            
            variance_report["item_variances"].append({
                "category": item.category_name,
                "claimed_amount": str(item.claimed_amount),
                "approved_amount": str(item.approved_amount),
                "variance_amount": str(variance_amount),
                "variance_percentage": f"{round(variance_percentage, 2)}%",
                "reason": item.remarks if item.remarks else "No variance - policy compliant"
            })

        overall_variance = total_claimed - total_approved
        overall_variance_percentage = ((overall_variance / total_claimed) * 100) if total_claimed > 0 else 0
        
        variance_report["overall_variance"] = {
            "total_claimed": str(total_claimed),
            "total_approved": str(total_approved),
            "variance_amount": str(overall_variance),
            "variance_percentage": f"{round(overall_variance_percentage, 2)}%"
        }

        self.log_success("Generate Variance Report")
        return variance_report
