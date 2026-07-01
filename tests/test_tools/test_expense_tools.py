from unittest.mock import MagicMock

import tools.expense_tools as expense_tools


def test_preview_claim_delegates_to_service(monkeypatch):
    """preview_claim() should delegate to ExpenseClaimService.preview_claim()."""

    mock_service = MagicMock()
    expected = MagicMock()

    mock_service.preview_claim.return_value = expected

    monkeypatch.setattr(
        expense_tools,
        "expense_claim_service",
        mock_service,
    )

    request = MagicMock()

    result = expense_tools.preview_claim(request)

    mock_service.preview_claim.assert_called_once_with(request)
    assert result is expected


def test_submit_claim_delegates_to_service(monkeypatch):
    """submit_claim() should delegate to ExpenseClaimService.submit_claim()."""

    mock_service = MagicMock()
    expected = MagicMock()

    mock_service.submit_claim.return_value = expected

    monkeypatch.setattr(
        expense_tools,
        "expense_claim_service",
        mock_service,
    )

    request = MagicMock()

    result = expense_tools.submit_claim(request)

    mock_service.submit_claim.assert_called_once_with(request)
    assert result is expected


def test_get_claim_delegates_to_service(monkeypatch):
    """get_claim() should delegate to ExpenseClaimService.get_claim()."""

    mock_service = MagicMock()
    expected = MagicMock()

    mock_service.get_claim.return_value = expected

    monkeypatch.setattr(
        expense_tools,
        "expense_claim_service",
        mock_service,
    )

    claim_id = "CLM000001"

    result = expense_tools.get_claim(claim_id)

    mock_service.get_claim.assert_called_once_with(claim_id)
    assert result is expected
