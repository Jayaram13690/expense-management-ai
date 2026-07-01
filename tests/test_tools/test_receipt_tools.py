"""
Test Receipt Tools.

Test the receipt tools to verify they properly delegate to ReceiptService.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_receipt_service():
    """Create a mock ReceiptService for testing."""
    with patch("tools.receipt_tools.receipt_service") as mock_service:
        yield mock_service


def test_upload_receipt_delegation(mock_receipt_service):
    """Test that upload_receipt properly delegates to ReceiptService."""
    from tools.receipt_tools import upload_receipt

    # Create test data
    mock_receipt = Mock()
    mock_receipt.receipt_id = "RCT000000000001"
    mock_receipt.claim_id = "CLM000000000001"
    mock_receipt.employee_id = "EMP0001"
    mock_receipt.original_filename = "receipt.jpg"
    mock_receipt.content_type = "image/jpeg"
    mock_receipt.file_size = 1024
    mock_receipt.file_extension = ".jpg"
    mock_receipt.s3_key = "receipts/RCT000000000001.jpg"
    mock_receipt.checksum = "abc123"
    mock_receipt.status = "UPLOADED"
    mock_receipt.is_verified = False
    mock_receipt.ocr_completed = False

    # Configure mock
    mock_receipt_service.save_receipt.return_value = mock_receipt

    # Call the tool
    result = upload_receipt(mock_receipt)

    # Verify delegation
    mock_receipt_service.save_receipt.assert_called_once_with(mock_receipt)
    assert result == mock_receipt


def test_get_receipt_status_delegation(mock_receipt_service):
    """Test that get_receipt_status properly delegates to ReceiptService."""
    from tools.receipt_tools import get_receipt_status

    # Test data
    receipt_id = "RCT000000000001"

    # Create mock response
    mock_receipt = Mock()
    mock_receipt.receipt_id = receipt_id
    mock_receipt.claim_id = "CLM000000000001"
    mock_receipt.status = "VALIDATED"
    mock_receipt.is_verified = True
    mock_receipt.ocr_completed = True

    # Configure mock
    mock_receipt_service.get_receipt.return_value = mock_receipt

    # Call the tool
    result = get_receipt_status(receipt_id)

    # Verify delegation
    mock_receipt_service.get_receipt.assert_called_once_with(receipt_id)
    assert result == mock_receipt


def test_receipt_tools_input_validation():
    """Test that receipt tools accept correct input types."""
    from tools.receipt_tools import get_receipt_status, upload_receipt

    # These should not raise type errors
    assert callable(upload_receipt)
    assert callable(get_receipt_status)

    # Verify function signatures
    import inspect

    # upload_receipt signature
    sig = inspect.signature(upload_receipt)
    assert "receipt" in sig.parameters

    # get_receipt_status signature
    sig = inspect.signature(get_receipt_status)
    assert "receipt_id" in sig.parameters


def test_receipt_tools_return_types():
    """Test that receipt tools have correct return type annotations."""
    import inspect

    from tools.receipt_tools import get_receipt_status, upload_receipt

    # Verify the functions exist and are callable
    assert callable(upload_receipt)
    assert callable(get_receipt_status)

    # Check function signatures
    upload_sig = inspect.signature(upload_receipt)
    status_sig = inspect.signature(get_receipt_status)

    # Verify parameter names
    assert "receipt" in upload_sig.parameters
    assert "receipt_id" in status_sig.parameters


def test_receipt_tools_service_isolation(mock_receipt_service):
    """Test that receipt tools only call ReceiptService."""
    from tools.receipt_tools import get_receipt_status, upload_receipt

    # Test upload_receipt
    mock_receipt = Mock()
    mock_receipt_service.save_receipt.return_value = mock_receipt

    result = upload_receipt(mock_receipt)
    mock_receipt_service.save_receipt.assert_called_once()

    # Test get_receipt_status
    mock_receipt = Mock()
    mock_receipt_service.get_receipt.return_value = mock_receipt

    result = get_receipt_status("RCT000000000001")
    mock_receipt_service.get_receipt.assert_called_once()

    # Verify only ReceiptService was called (2 times total)
    assert mock_receipt_service.save_receipt.call_count == 1
    assert mock_receipt_service.get_receipt.call_count == 1


def test_upload_receipt_with_different_statuses(mock_receipt_service):
    """Test that upload_receipt works with receipts in different statuses."""
    from tools.receipt_tools import upload_receipt

    # Test with UPLOADED status
    receipt_uploaded = Mock()
    receipt_uploaded.receipt_id = "RCT000000000001"
    receipt_uploaded.status = "UPLOADED"

    mock_receipt_service.save_receipt.return_value = receipt_uploaded
    result = upload_receipt(receipt_uploaded)
    assert result.status == "UPLOADED"

    # Test with VALIDATED status
    receipt_validated = Mock()
    receipt_validated.receipt_id = "RCT000000000002"
    receipt_validated.status = "VALIDATED"

    mock_receipt_service.save_receipt.return_value = receipt_validated
    result = upload_receipt(receipt_validated)
    assert result.status == "VALIDATED"

    # Test with OCR_COMPLETED status
    receipt_ocr = Mock()
    receipt_ocr.receipt_id = "RCT000000000003"
    receipt_ocr.status = "OCR_COMPLETED"

    mock_receipt_service.save_receipt.return_value = receipt_ocr
    result = upload_receipt(receipt_ocr)
    assert result.status == "OCR_COMPLETED"

    # Verify all three calls were made
    assert mock_receipt_service.save_receipt.call_count == 3


def test_get_receipt_status_with_different_statuses(mock_receipt_service):
    """Test that get_receipt_status works with receipts in different statuses."""
    from tools.receipt_tools import get_receipt_status

    # Test with UPLOADED status
    receipt_uploaded = Mock()
    receipt_uploaded.receipt_id = "RCT000000000001"
    receipt_uploaded.status = "UPLOADED"
    receipt_uploaded.is_verified = False
    receipt_uploaded.ocr_completed = False

    mock_receipt_service.get_receipt.return_value = receipt_uploaded
    result = get_receipt_status("RCT000000000001")
    assert result.status == "UPLOADED"
    assert result.is_verified == False
    assert result.ocr_completed == False

    # Test with REJECTED status
    receipt_rejected = Mock()
    receipt_rejected.receipt_id = "RCT000000000002"
    receipt_rejected.status = "REJECTED"
    receipt_rejected.is_verified = False
    receipt_rejected.ocr_completed = False

    mock_receipt_service.get_receipt.return_value = receipt_rejected
    result = get_receipt_status("RCT000000000002")
    assert result.status == "REJECTED"

    # Verify both calls were made
    assert mock_receipt_service.get_receipt.call_count == 2
