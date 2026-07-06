from __future__ import annotations

import logging
import mimetypes
import tempfile
from collections.abc import Sequence
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import boto3
import requests
from botocore.config import Config
from strands import tool

from config.settings import settings
from models.receipt import Receipt
from services.receipt_service import ReceiptService

receipt_service = ReceiptService()
LOGGER = logging.getLogger(__name__)


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


def _normalize_source_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _is_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _allowed_content_types() -> set[str]:
    return {"image/jpeg", "image/png", "application/pdf"}


def _extension_from_content_type(content_type: str) -> str | None:
    normalized = content_type.split(";", 1)[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "application/pdf": ".pdf",
    }
    if normalized in mapping:
        return mapping[normalized]
    guessed = mimetypes.guess_extension(normalized)
    if guessed == ".jpe":
        return ".jpg"
    return guessed


def _resolve_content_type(content_type: str | None, source_url: str) -> str:
    if content_type:
        normalized = content_type.split(";", 1)[0].strip().lower()
        if normalized in _allowed_content_types():
            return normalized

    candidates = [source_url]
    parsed = urlparse(source_url)
    query_url = parse_qs(parsed.query).get("url")
    if query_url:
        nested_url = unquote(query_url[0])
        if nested_url:
            candidates.insert(0, nested_url)

    for candidate in candidates:
        guessed, _ = mimetypes.guess_type(urlparse(candidate).path or candidate)
        if guessed:
            normalized_guess = guessed.split(";", 1)[0].strip().lower()
            if normalized_guess in _allowed_content_types():
                return normalized_guess

    return (content_type or "").split(";", 1)[0].strip().lower()


def _infer_remote_filename(url: str, response: Any, extension: str) -> str:
    candidates: list[str] = []
    parsed = urlparse(url)
    query_url = parse_qs(parsed.query).get("url")
    if query_url:
        nested_url = unquote(query_url[0])
        if nested_url:
            candidates.append(nested_url)
    response_url = getattr(response, "url", None)
    if isinstance(response_url, str) and response_url:
        candidates.append(response_url)
    candidates.append(url)

    for candidate in candidates:
        candidate_name = Path(urlparse(candidate).path).name
        if candidate_name:
            if Path(candidate_name).suffix:
                return candidate_name
            return f"{candidate_name}{extension}"

    return f"receipt{extension}"


@tool
def upload_receipt(
    *,
    file_path: str,
    bucket: str,
    key: str,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Upload a receipt file or URL to S3 and return object metadata."""

    normalized_path = _normalize_source_value(file_path)
    temp_path: Path | None = None
    source_url: str | None = None
    resolved_content_type = content_type
    file_name = Path(normalized_path).name
    path = Path(normalized_path)

    try:
        if "://" in normalized_path and not _is_url(normalized_path):
            raise ValueError("The provided receipt URL is invalid.")
        if _is_url(normalized_path):
            source_url = normalized_path
            timeout_seconds = settings.receipt_upload.download_timeout_seconds
            try:
                response = requests.get(normalized_path, stream=True, timeout=timeout_seconds)
                if response.status_code == 404:
                    raise ValueError(
                        "The receipt could not be downloaded dute the remote file does not exist."
                    )
                response.raise_for_status()
                resolved_content_type = _resolve_content_type(
                    resolved_content_type,
                    normalized_path,
                )
                if resolved_content_type not in _allowed_content_types():
                    raise ValueError("The downloaded receipt must be JPG, JPEG, PNG, or PDF.")
                extension = _extension_from_content_type(resolved_content_type)
                if extension is None:
                    raise ValueError("The downloaded receipt must be JPG, JPEG, PNG, or PDF.")

                with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                    temp_path = Path(temp_file.name)
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        temp_file.write(chunk)

                path = temp_path
                file_name = _infer_remote_filename(normalized_path, response, extension)
            except requests.Timeout as exc:
                raise ValueError("The receipt download timed out. Please try again.") from exc
            except requests.RequestException as exc:
                if getattr(getattr(exc, "response", None), "status_code", None) == 404:
                    raise ValueError(
                        "The receipt could not be downloaded because the remote file does not exist"
                    ) from exc
                raise ValueError("Unable to download the receipt from the provided URL.") from exc
        else:
            if resolved_content_type is None:
                resolved_content_type = mimetypes.guess_type(path.name)[0]
            if resolved_content_type is None:
                raise ValueError("Unable to determine the receipt content type.")

        file_size = path.stat().st_size
        if file_size <= 0:
            raise ValueError("The receipt file is empty. Please upload a non-empty receipt file.")
        max_size_bytes = settings.receipt_upload.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValueError(
                f"The receipt file exceeds the {settings.receipt_upload.max_file_size_mb} MB limit."
                "Please upload a smaller receipt file."
            )

        with path.open("rb") as receipt_file:
            try:
                receipt_file.read(1)
                receipt_file.seek(0)
                _s3_client().put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=receipt_file,
                    ContentType=resolved_content_type,
                )
            except OSError as exc:
                raise ValueError("Unable to read the receipt file.") from exc

        result = {
            "bucket": bucket,
            "key": key,
            "content_type": resolved_content_type,
            "file_name": file_name,
            "source_path": normalized_path,
            "size_bytes": file_size,
            "uploaded": True,
        }
        if source_url:
            result["source_url"] = source_url
        return result
    except OSError as exc:
        raise ValueError("Unable to read the receipt file.") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                LOGGER.debug(
                    "Unable to remove temporary receipt file: %s", temp_path, exc_info=True
                )


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
