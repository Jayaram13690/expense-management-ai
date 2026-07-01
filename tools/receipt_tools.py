# """
# Receipt Tools for AI Agents.

# This module provides native Strands tools that delegate receipt operations to the
# ReceiptService. These tools are designed for use by AI agents and follow the
# Strands Agents SDK pattern.

# Tools are thin delegation layers that:
# - Call exactly one service method
# - Do not contain business logic
# - Do not duplicate receipt validation
# - Do not access repositories directly
# - Use existing domain models and exception handling
# - Follow project logging and typing conventions
# """

# from __future__ import annotations

# from strands import tool

# from services.receipt_service import ReceiptService
# from models.receipt import Receipt
# from common.identifiers import ReceiptId

# # Shared service instance for all tools in this module
# receipt_service = ReceiptService()


# @tool
# def upload_receipt(
#     receipt: Receipt,
# ) -> Receipt:
#     """
#     Upload or update a receipt.

#     This tool delegates to ReceiptService.save_receipt() to persist
#     a receipt document. The service handles both new uploads and
#     updates to existing receipts.

#     Args:
#         receipt: Receipt domain model containing complete receipt details
#                  including file metadata and claim association

#     Returns:
#         Saved Receipt with updated audit information

#     Note:
#         This is a thin delegation layer. All receipt validation, persistence,
#         and metadata processing is managed by the ReceiptService. No receipt
#         validation or business rules are implemented in this tool.
#     """
#     return receipt_service.save_receipt(receipt)


# @tool
# def get_receipt_status(
#     receipt_id: ReceiptId,
# ) -> Receipt:
#     """
#     Retrieve the current status and details of a receipt.

#     This tool delegates to ReceiptService.get_receipt() to fetch
#     complete information about a receipt including its processing status,
#     verification state, and OCR completion status.

#     Args:
#         receipt_id: ReceiptId of the receipt to retrieve

#     Returns:
#         Receipt domain model with complete receipt details including
#         current status (UPLOADED, VALIDATED, OCR_COMPLETED, REJECTED)

#     Note:
#         This is a thin delegation layer. All receipt retrieval logic and
#         error handling is managed by the ReceiptService. No receipt status
#         calculations or business rules are implemented in this tool.
#     """
#     return receipt_service.get_receipt(receipt_id)

from __future__ import annotations

from strands import tool

from models.receipt import Receipt
from services.receipt_service import ReceiptService

receipt_service = ReceiptService()


@tool
def upload_receipt(
    receipt: Receipt,
) -> Receipt:
    """
    Upload or update a receipt.
    """
    return receipt_service.save_receipt(receipt)


@tool
def get_receipt_status(
    receipt_id: str,
) -> Receipt:
    """
    Retrieve receipt details.
    """
    return receipt_service.get_receipt(receipt_id)
