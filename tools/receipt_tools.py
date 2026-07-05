from __future__ import annotations

from collections.abc import Sequence
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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


def _ses_client():
    return boto3.client(
        "ses",
        region_name=settings.aws.aws_region,
        config=Config(
            connect_timeout=settings.notifications.email_timeout_seconds,
            read_timeout=settings.notifications.email_timeout_seconds,
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


def download_receipt_attachment(*, bucket: str, key: str) -> dict[str, Any]:
    """Download a receipt object from S3 for email attachment use."""

    response = _s3_client().get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    content_type = response.get("ContentType") or "application/octet-stream"
    file_name = Path(key).name
    return {
        "bucket": bucket,
        "key": key,
        "file_name": file_name,
        "content_type": content_type,
        "content_bytes": body,
    }


def send_notification_email(
    *,
    subject: str,
    body_text: str,
    recipient_email: str,
    sender_email: str,
    attachments: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send an email through SES, optionally with binary attachments."""

    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email
    message.attach(MIMEText(body_text, "plain", "utf-8"))

    for attachment in attachments or []:
        payload = attachment.get("content_bytes", b"")
        if not isinstance(payload, (bytes, bytearray)):
            payload = bytes(str(payload), "utf-8")
        content_type = str(attachment.get("content_type") or "application/octet-stream")
        maintype, _, subtype = content_type.partition("/")
        mime_part = MIMEApplication(payload, _subtype=subtype or "octet-stream")
        file_name = str(attachment.get("file_name") or "attachment")
        mime_part.add_header("Content-Disposition", "attachment", filename=file_name)
        if maintype:
            mime_part.replace_header("Content-Type", content_type)
        message.attach(mime_part)

    _ses_client().send_raw_email(
        Source=sender_email,
        Destinations=[recipient_email],
        RawMessage={"Data": message.as_string()},
    )

    return {
        "status": "sent",
        "recipient_email": recipient_email,
        "subject": subject,
        "attachment_count": len(list(attachments or [])),
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
