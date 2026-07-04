"""
ReceiptAgent for handling business document generation.

This module implements the ReceiptAgent that inherits from BaseAgent and
is responsible for generating business documents from expense claims.

The ReceiptAgent uses ONLY the following Strands tools:
- upload_receipt: Upload receipt documents to S3
- get_receipt_status: Retrieve receipt processing status (legacy)
- generate_expense_claim_summary: Generate expense claim summary
- generate_reimbursement_summary: Generate reimbursement summary
- generate_policy_application_summary: Generate policy application summary
- generate_expense_breakdown: Generate detailed expense breakdown
- generate_variance_report: Generate variance report
"""

from __future__ import annotations

import mimetypes
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from agents.base_agent import BaseAgent
from config.settings import settings
from prompts.receipt_prompt import RECEIPT_AGENT_SYSTEM_PROMPT
from tools.receipt_tools import (
    generate_expense_breakdown,
    generate_expense_claim_summary,
    generate_policy_application_summary,
    generate_reimbursement_summary,
    generate_variance_report,
    get_receipt_status,
    upload_receipt,
)


class ReceiptUploadError(Exception):
    """User-facing receipt upload error."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class ReceiptAgent(BaseAgent):
    """ReceiptAgent for document generation and receipt upload."""

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
        last_error: Exception | None = None
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
            except (NoCredentialsError, ClientError, BotoCoreError, OSError, TimeoutError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    continue

        raise ReceiptUploadError(
            "I couldn't upload the receipt due to an AWS error. Please try again."
        ) from last_error

    def generate_receipt_result(self, claim_id: str) -> dict[str, Any]:
        """Generate the final acknowledgement payload for orchestration."""

        result = generate_reimbursement_summary(claim_id)
        if hasattr(result, "model_dump") and callable(result.model_dump):
            return result.model_dump()
        if isinstance(result, Mapping):
            return dict(result)
        return {"value": result}

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
