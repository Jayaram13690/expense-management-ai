"""
Receipt domain model.

Represents a receipt uploaded as supporting evidence for an expense claim.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from common.identifiers import ClaimId, EmployeeId, ReceiptId
from models.base import BaseEntity


class ReceiptStatus(StrEnum):
    """
    Receipt processing status.
    """

    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    OCR_COMPLETED = "OCR_COMPLETED"
    REJECTED = "REJECTED"


class Receipt(BaseEntity):
    """
    Receipt entity.
    """

    # receipt_id: str = Field(
    #     ...,
    #     pattern=r"^RCT\d{4,12}$",
    # )

    receipt_id: ReceiptId

    # claim_id: str = Field(
    #     ...,
    #     description="Associated expense claim."
    # )

    # employee_id: str = Field(
    #     ...,
    #     description="Employee that uploaded the receipt."
    # )

    claim_id: ClaimId

    employee_id: EmployeeId

    original_filename: str

    content_type: str

    file_size: int = Field(
        ...,
        gt=0,
    )

    file_extension: str

    s3_key: str

    checksum: str

    status: ReceiptStatus = ReceiptStatus.UPLOADED

    is_verified: bool = False

    ocr_completed: bool = False
