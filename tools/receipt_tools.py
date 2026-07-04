from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from strands import tool

from config.settings import settings
from models.receipt import Receipt
from services.receipt_service import ReceiptService

receipt_service = ReceiptService()


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws.aws_region,
        config=Config(
            connect_timeout=settings.receipt_upload.upload_timeout_seconds,
            read_timeout=settings.receipt_upload.upload_timeout_seconds,
        ),
    )


@tool
def upload_receipt(
    *,
    file_path: str,
    bucket: str,
    key: str,
    content_type: str,
) -> dict[str, Any]:
    """Upload a local receipt file to S3 and return object metadata."""

    path = Path(file_path)
    with path.open("rb") as receipt_file:
        _s3_client().put_object(
            Bucket=bucket,
            Key=key,
            Body=receipt_file,
            ContentType=content_type,
        )

    return {
        "bucket": bucket,
        "key": key,
        "content_type": content_type,
        "file_name": path.name,
    }


@tool
def get_receipt_status(
    receipt_id: str,
) -> Receipt:
    """Retrieve receipt details."""

    return receipt_service.get_receipt(receipt_id)


@tool
def generate_expense_claim_summary(
    claim_id: str,
) -> dict:
    """Generate expense claim summary document."""

    from services.expense_claim_service import ExpenseClaimService

    claim_service = ExpenseClaimService()
    claim = claim_service.get_claim(claim_id)
    return receipt_service.generate_expense_claim_summary(claim)


@tool
def generate_reimbursement_summary(
    claim_id: str,
) -> dict:
    """Generate reimbursement summary document."""

    from services.expense_claim_service import ExpenseClaimService

    claim_service = ExpenseClaimService()
    claim = claim_service.get_claim(claim_id)
    return receipt_service.generate_reimbursement_summary(claim)


@tool
def generate_policy_application_summary(
    claim_id: str,
) -> dict:
    """Generate policy application summary document."""

    from services.expense_claim_service import ExpenseClaimService

    claim_service = ExpenseClaimService()
    claim = claim_service.get_claim(claim_id)
    return receipt_service.generate_policy_application_summary(claim)


@tool
def generate_expense_breakdown(
    claim_id: str,
) -> dict:
    """Generate detailed expense breakdown document."""

    from services.expense_claim_service import ExpenseClaimService

    claim_service = ExpenseClaimService()
    claim = claim_service.get_claim(claim_id)
    return receipt_service.generate_expense_breakdown(claim)


@tool
def generate_variance_report(
    claim_id: str,
) -> dict:
    """Generate variance report document."""

    from services.expense_claim_service import ExpenseClaimService

    claim_service = ExpenseClaimService()
    claim = claim_service.get_claim(claim_id)
    return receipt_service.generate_variance_report(claim)
