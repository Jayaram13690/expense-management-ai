"""
ReceiptAgent for handling business document generation.

This module implements the ReceiptAgent that inherits from BaseAgent and
is responsible for generating business documents from expense claims.
"""

from __future__ import annotations

import mimetypes
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from agents.base_agent import BaseAgent
from config.settings import settings
from prompts.receipt_prompt import RECEIPT_AGENT_SYSTEM_PROMPT
from tools.receipt_tools import (
    download_receipt_attachment,
    generate_expense_breakdown,
    generate_expense_claim_summary,
    generate_policy_application_summary,
    generate_reimbursement_summary,
    generate_variance_report,
    get_receipt_status,
    send_notification_email,
    upload_receipt,
)


class ReceiptUploadError(Exception):
    """User-facing receipt upload error."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class ReceiptAgent(BaseAgent):
    """ReceiptAgent for document generation, upload, and notifications."""

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
    CONTENT_TYPE_OVERRIDES = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
    }

    def __init__(self, model: str | None = None) -> None:
        super().__init__(
            model=model,
            system_prompt=RECEIPT_AGENT_SYSTEM_PROMPT,
            tools=[
                generate_expense_claim_summary,
                generate_reimbursement_summary,
                generate_policy_application_summary,
                generate_expense_breakdown,
                generate_variance_report,
                upload_receipt,
                get_receipt_status,
            ],
            name="ReceiptAgent",
            description="Handles business document generation.",
        )
        self._pending_notification: dict[str, Any] | None = None

    def upload_receipt_file(
        self,
        *,
        file_path: str,
        claim_id: str,
        category: str,
        receipt_index: int,
        existing_uploads: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Validate and upload a receipt file for orchestration."""

        if not claim_id or not claim_id.strip():
            raise ReceiptUploadError(
                "Receipt upload is unavailable because the claim ID is missing."
            )
        if not category or not category.strip():
            raise ReceiptUploadError(
                "Receipt upload is unavailable because the expense category is missing."
            )
        if receipt_index <= 0:
            raise ReceiptUploadError(
                "Receipt upload is unavailable because the receipt index is invalid."
            )

        normalized_path = self._normalize_path(file_path)
        self._validate_file(normalized_path, category, existing_uploads or [])

        extension = normalized_path.suffix.lower()
        content_type = (
            self.CONTENT_TYPE_OVERRIDES.get(extension)
            or mimetypes.guess_type(normalized_path.name)[0]
        )
        if not content_type:
            raise ReceiptUploadError(
                f"I couldn't determine the file type for the {category.upper()} receipt. "
                "Please upload a JPG, JPEG, PNG, or PDF file."
            )

        bucket = settings.receipt_upload.s3_bucket
        object_key = f"claims/{claim_id}/{category.upper()}/receipt_{receipt_index}{extension}"

        attempts = settings.receipt_upload.upload_retry_count + 1
        for attempt in range(attempts):
            try:
                result = upload_receipt(
                    file_path=str(normalized_path),
                    bucket=bucket,
                    key=object_key,
                    content_type=content_type,
                )
                metadata = self._plain_mapping(result)
                metadata.update(
                    {
                        "uploaded": True,
                        "bucket": bucket,
                        "key": object_key,
                        "content_type": content_type,
                        "file_name": normalized_path.name,
                        "source_path": str(normalized_path),
                        "size_bytes": normalized_path.stat().st_size,
                    }
                )
                return metadata
            except KeyboardInterrupt as exc:
                raise ReceiptUploadError(
                    "Receipt upload was interrupted. Please try uploading the same receipt again."
                ) from exc
            except (NoCredentialsError, ClientError, BotoCoreError, OSError, TimeoutError):
                if attempt < attempts - 1:
                    continue

        raise ReceiptUploadError(
            "I couldn't upload the receipt due to an AWS error. Please try again."
        )

    def send_manager_approval_email(
        self,
        *,
        claim_id: str,
        approval_result: Mapping[str, Any],
        claim_snapshot: Mapping[str, Any],
        claim_preview: Mapping[str, Any] | None,
        policy_context: Mapping[str, Any] | None,
        receipt_uploads: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> dict[str, Any]:
        """Send the approval-required email with receipt attachments."""

        recipient = self._notification_recipient()
        if not recipient:
            return self._error_result(
                error_code="NOTIFICATION_EMAIL_NOT_CONFIGURED",
                assistant_message=(
                    "Manager notification could not be sent because NOTIFICATION_EMAIL "
                    "is not configured."
                ),
                recoverable=False,
            )

        attachments_result = self._load_receipt_attachments(receipt_uploads)
        if attachments_result["success"] is False:
            return attachments_result

        employee_name = str(
            claim_snapshot.get("employee_name") or claim_snapshot.get("employee_id") or "Unknown"
        )
        policy_summary = self._policy_summary(policy_context)
        claim_amount = self._resolve_amount(
            claim_snapshot,
            claim_preview,
            top_level_keys=("total_claimed", "claimed_amount", "total_amount"),
            nested_keys=("claimed_amount", "total_claimed", "total_amount"),
        )
        approved_amount = self._resolve_amount(
            claim_preview,
            claim_snapshot,
            top_level_keys=("total_approved", "approved_amount", "reimbursable_amount"),
            nested_keys=("approved_amount", "reimbursable_amount", "total_approved"),
        )
        body = (
            "Expense Claim Approval Required\n\n"
            f"Claim ID: {claim_id}\n"
            f"Employee ID: {claim_snapshot.get('employee_id', 'N/A')}\n"
            f"Employee Name: {employee_name}\n"
            f"Department: {claim_snapshot.get('department', 'N/A')}\n"
            f"Destination: {claim_snapshot.get('destination', 'N/A')}\n"
            f"Business Purpose: {claim_snapshot.get('business_purpose', 'N/A')}\n"
            f"Trip Dates: {claim_snapshot.get('trip_start_date', 'N/A')} to "
            f"{claim_snapshot.get('trip_end_date', 'N/A')}\n"
            f"Expense Summary: {self._expense_summary(claim_snapshot)}\n"
            f"Claim Amount: {claim_amount}\n"
            f"Approved Amount: {approved_amount}\n"
            f"Variance: {self._variance(claim_amount, approved_amount)}\n"
            f"Policy Summary: {policy_summary}\n"
            f"Approval Status: {approval_result.get('status', 'PENDING')}\n"
        )
        return self._send_email(
            subject="Expense Claim Approval Required",
            body_text=body,
            attachments=attachments_result["attachments"],
            success_message=(
                f"Claim {claim_id} was submitted and the approval request was emailed successfully."
            ),
            pending_payload={
                "kind": "manager_approval",
                "claim_id": claim_id,
                "approval_result": dict(approval_result),
                "claim_snapshot": dict(claim_snapshot),
                "claim_preview": dict(claim_preview or {}),
                "policy_context": dict(policy_context or {}),
                "receipt_uploads": {
                    str(category): [dict(item) for item in uploads]
                    for category, uploads in receipt_uploads.items()
                },
            },
        )

    def send_employee_decision_email(
        self,
        *,
        claim_id: str,
        approval_result: Mapping[str, Any],
        claim_status: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Notify the employee that the manager made a decision."""

        recipient = self._notification_recipient()
        if not recipient:
            return self._error_result(
                error_code="NOTIFICATION_EMAIL_NOT_CONFIGURED",
                assistant_message=(
                    "Employee notification could not be sent because NOTIFICATION_EMAIL "
                    "is not configured."
                ),
                recoverable=False,
            )

        status = str(approval_result.get("status") or claim_status.get("status") or "UNKNOWN")
        body_lines = [
            "Expense Claim Decision",
            "",
            f"Claim ID: {claim_id}",
            f"Employee ID: {claim_status.get('employee_id', 'N/A')}",
            f"Employee Name: {claim_status.get('employee_name', 'N/A')}",
            f"Status: {status}",
            f"Approved Amount: {claim_status.get('approved_amount', 'N/A')}",
            f"Reimbursable Amount: {claim_status.get('reimbursable_amount', 'N/A')}",
        ]
        reason = approval_result.get("reason")
        if reason:
            body_lines.append(f"Reason: {reason}")

        return self._send_email(
            subject=f"Expense Claim {status}",
            body_text="\n".join(body_lines),
            attachments=[],
            success_message=f"Employee notification for claim {claim_id} was sent successfully.",
            pending_payload={
                "kind": "employee_decision",
                "claim_id": claim_id,
                "approval_result": dict(approval_result),
                "claim_status": dict(claim_status),
            },
        )

    def has_pending_notification(self) -> bool:
        return self._pending_notification is not None

    def retry_pending_notification(self) -> dict[str, Any]:
        """Retry the last failed notification delivery."""

        if self._pending_notification is None:
            return self._error_result(
                error_code="NO_PENDING_NOTIFICATION",
                assistant_message="There is no pending notification to retry.",
                recoverable=False,
            )

        payload = dict(self._pending_notification)
        self._pending_notification = None
        kind = payload.pop("kind", None)
        if kind == "manager_approval":
            return self.send_manager_approval_email(**payload)
        if kind == "employee_decision":
            return self.send_employee_decision_email(**payload)
        return self._error_result(
            error_code="INVALID_NOTIFICATION_STATE",
            assistant_message="I couldn't resume the pending notification.",
            recoverable=False,
        )

    def generate_receipt_result(self, claim_id: str) -> dict[str, Any]:
        """Generate the final acknowledgement payload for orchestration."""

        result = generate_reimbursement_summary(claim_id)
        if hasattr(result, "model_dump") and callable(result.model_dump):
            return result.model_dump()
        if isinstance(result, Mapping):
            return dict(result)
        return {"value": result}

    def _send_email(
        self,
        *,
        subject: str,
        body_text: str,
        attachments: Sequence[Mapping[str, Any]],
        success_message: str,
        pending_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        sender = settings.notifications.sender_email.strip() or self._notification_recipient()
        recipient = self._notification_recipient()
        if not sender or not recipient:
            return self._error_result(
                error_code="NOTIFICATION_EMAIL_NOT_CONFIGURED",
                assistant_message=(
                    "Notification delivery is unavailable because the email configuration "
                    "is missing."
                ),
                recoverable=False,
            )

        attempts = settings.notifications.email_retry_count + 1
        for attempt in range(attempts):
            try:
                result = send_notification_email(
                    subject=subject,
                    body_text=body_text,
                    recipient_email=recipient,
                    sender_email=sender,
                    attachments=attachments,
                )
                self._pending_notification = None
                return {
                    "success": True,
                    "status": "sent",
                    "assistant_message": success_message,
                    "next_state": "completed",
                    "receipt_result": self._plain_mapping(result),
                }
            except (NoCredentialsError, ClientError, BotoCoreError, OSError, TimeoutError):
                if attempt < attempts - 1:
                    continue

        self._pending_notification = dict(pending_payload)
        return self._error_result(
            error_code="EMAIL_DELIVERY_FAILED",
            assistant_message=(
                "I couldn't send the notification email due to an AWS error. Please try again."
            ),
            recoverable=True,
        )

    def _load_receipt_attachments(
        self,
        receipt_uploads: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> dict[str, Any]:
        attachments: list[dict[str, Any]] = []
        for uploads in receipt_uploads.values():
            for upload in uploads:
                bucket = upload.get("bucket")
                key = upload.get("key")
                if not isinstance(bucket, str) or not isinstance(key, str):
                    return self._error_result(
                        error_code="RECEIPT_METADATA_MISSING",
                        assistant_message=(
                            "Receipt metadata is incomplete, so I couldn't prepare the "
                            "approval email."
                        ),
                        recoverable=True,
                    )
                try:
                    attachment = download_receipt_attachment(bucket=bucket, key=key)
                except (NoCredentialsError, ClientError, BotoCoreError, OSError, TimeoutError):
                    return self._error_result(
                        error_code="RECEIPT_DOWNLOAD_FAILED",
                        assistant_message=(
                            "I couldn't download one of the uploaded receipts for the "
                            "approval email. Please try again."
                        ),
                        recoverable=True,
                    )
                attachments.append(attachment)

        return {"success": True, "attachments": attachments}

    def _notification_recipient(self) -> str:
        return settings.notifications.notification_email.strip()

    def _policy_summary(self, policy_context: Mapping[str, Any] | None) -> str:
        if not isinstance(policy_context, Mapping):
            return "No policy summary available"
        categories = policy_context.get("categories", {})
        if not isinstance(categories, Mapping) or not categories:
            return "No policy summary available"

        parts: list[str] = []
        for category, details in categories.items():
            if hasattr(details, "model_dump") and callable(details.model_dump):
                details = details.model_dump()
            if not isinstance(details, Mapping):
                continue
            limits = details.get("limits", {})
            if hasattr(limits, "model_dump") and callable(limits.model_dump):
                limits = limits.model_dump()
            limit_text = (
                ", ".join(f"{key}={value}" for key, value in limits.items())
                if isinstance(limits, Mapping) and limits
                else "No limits"
            )
            parts.append(f"{category}: {limit_text}")
        return "; ".join(parts) if parts else "No policy summary available"

    def _expense_summary(self, claim_snapshot: Mapping[str, Any]) -> str:
        items = (
            claim_snapshot.get("expense_line_items") or claim_snapshot.get("expense_items") or []
        )
        if not isinstance(items, Sequence):
            return "No expense items available"
        parts: list[str] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            category = (
                item.get("category_name") or item.get("category_code") or item.get("description")
            )
            amount = item.get("claimed_amount") or item.get("requested_amount")
            currency = item.get("currency") or "INR"
            parts.append(f"{category}: {currency} {amount}")
        return "; ".join(parts) if parts else "No expense items available"

    def _variance(self, claim_amount: Any, approved_amount: Any) -> str:
        try:
            return f"{float(str(claim_amount)) - float(str(approved_amount)):.2f}"
        except (TypeError, ValueError):
            return "N/A"

    def _lookup(self, payload: Mapping[str, Any] | None, key: str, default: Any = None) -> Any:
        if not isinstance(payload, Mapping):
            return default
        return payload.get(key, default)

    def _resolve_amount(
        self,
        *payloads: Mapping[str, Any] | None,
        top_level_keys: Sequence[str],
        nested_keys: Sequence[str],
    ) -> str:
        for payload in payloads:
            if not isinstance(payload, Mapping):
                continue

            for key in top_level_keys:
                value = payload.get(key)
                if value not in (None, "", [], {}):
                    return str(value)

            nested_amount = payload.get("amount")
            if not isinstance(nested_amount, Mapping):
                continue

            for key in nested_keys:
                value = nested_amount.get(key)
                if value not in (None, "", [], {}):
                    return str(value)

        return "N/A"

    def _normalize_path(self, file_path: str) -> Path:
        normalized = file_path.strip().strip('"').strip("'")
        if not normalized:
            raise ReceiptUploadError("Please provide a local file path for the receipt.")
        return Path(normalized).expanduser()

    def _validate_file(
        self,
        file_path: Path,
        category: str,
        existing_uploads: list[Mapping[str, Any]],
    ) -> None:
        if file_path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            raise ReceiptUploadError(
                "Unsupported receipt file type. Please upload a JPG, JPEG, PNG, or PDF file."
            )
        if not file_path.exists():
            raise ReceiptUploadError(
                f"I couldn't find the file '{file_path}'. "
                f"Please provide a valid local file path for the {category.upper()} receipt."
            )
        if not file_path.is_file():
            raise ReceiptUploadError(
                f"'{file_path}' is not a file. "
                f"Please provide a valid local file path for the {category.upper()} receipt."
            )
        if any(
            str(upload.get("source_path", "")).casefold() == str(file_path).casefold()
            for upload in existing_uploads
        ):
            raise ReceiptUploadError(
                f"That file has already been uploaded for the {category.upper()} receipt. "
                "Please provide a different file."
            )
        file_size = file_path.stat().st_size
        if file_size <= 0:
            raise ReceiptUploadError(
                f"The file '{file_path.name}' is empty. Please upload a non-empty receipt file."
            )
        max_size_bytes = settings.receipt_upload.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ReceiptUploadError(
                f"The file '{file_path.name}' exceeds the "
                f"{settings.receipt_upload.max_file_size_mb} MB limit. "
                "Please upload a smaller receipt file."
            )
        try:
            with file_path.open("rb") as receipt_file:
                receipt_file.read(1)
        except OSError as exc:
            raise ReceiptUploadError(
                f"I couldn't read '{file_path}'. Please check the file permissions and try again."
            ) from exc

    def _plain_mapping(self, value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump") and callable(value.model_dump):
            value = value.model_dump()
        if isinstance(value, Mapping):
            return {str(key): item for key, item in value.items()}
        return {"value": value}

    def _error_result(
        self,
        *,
        error_code: str,
        assistant_message: str,
        recoverable: bool,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": error_code,
            "assistant_message": assistant_message,
            "recoverable": recoverable,
            "next_state": "waiting_user",
        }
