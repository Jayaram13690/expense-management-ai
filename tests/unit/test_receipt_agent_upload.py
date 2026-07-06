from __future__ import annotations

from pathlib import Path

import pytest
import requests
from botocore.exceptions import ClientError

from agents.receipt_agent import ReceiptAgent, ReceiptUploadError
from config.settings import settings


def _local_temp_dir() -> Path:
    base = Path("tests/.tmp/receipt-agent-tests")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _write_file(name: str, data: bytes | str) -> Path:
    path = _local_temp_dir() / name
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")
    return path


def test_upload_receipt_file_success(monkeypatch):
    receipt_agent = ReceiptAgent()
    receipt_file = _write_file("hotel.jpg", b"receipt-bytes")
    calls: list[dict[str, str]] = []

    def fake_upload_receipt(**kwargs):
        calls.append(kwargs)
        return {
            "bucket": kwargs["bucket"],
            "key": kwargs["key"],
            "content_type": kwargs["content_type"],
            "file_name": Path(kwargs["file_path"]).name,
        }

    monkeypatch.setattr("agents.receipt_agent.upload_receipt", fake_upload_receipt)

    result = receipt_agent.upload_receipt_file(
        file_path=str(receipt_file),
        claim_id="CLM-1001",
        category="HOTEL",
        receipt_index=1,
    )

    assert result["uploaded"] is True
    assert result["bucket"]
    assert result["key"] == "claims/CLM-1001/HOTEL/receipt_1.jpg"
    assert result["file_name"] == "hotel.jpg"
    assert calls[0]["content_type"] == "image/jpeg"


def test_upload_receipt_file_rejects_invalid_path(monkeypatch):
    receipt_agent = ReceiptAgent()
    monkeypatch.setattr("agents.receipt_agent.upload_receipt", lambda **_: None)

    with pytest.raises(ReceiptUploadError, match="valid local file path"):
        receipt_agent.upload_receipt_file(
            file_path=r"C:\Receipts\missing.jpg",
            claim_id="CLM-1001",
            category="HOTEL",
            receipt_index=1,
        )


def test_upload_receipt_file_rejects_unsupported_extension(monkeypatch):
    receipt_agent = ReceiptAgent()
    receipt_file = _write_file("notes.txt", "not a receipt")
    monkeypatch.setattr("agents.receipt_agent.upload_receipt", lambda **_: None)

    with pytest.raises(ReceiptUploadError, match="Unsupported receipt file type"):
        receipt_agent.upload_receipt_file(
            file_path=str(receipt_file),
            claim_id="CLM-1001",
            category="HOTEL",
            receipt_index=1,
        )


def test_upload_receipt_file_retries_once_before_failing(monkeypatch):
    receipt_agent = ReceiptAgent()
    receipt_file = _write_file("taxi.jpg", b"receipt-bytes")
    attempts = {"count": 0}

    def flaky_upload(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ClientError({"Error": {"Code": "500", "Message": "temporary"}}, "PutObject")
        return {
            "bucket": kwargs["bucket"],
            "key": kwargs["key"],
            "content_type": kwargs["content_type"],
            "file_name": Path(kwargs["file_path"]).name,
        }

    monkeypatch.setattr("agents.receipt_agent.upload_receipt", flaky_upload)

    result = receipt_agent.upload_receipt_file(
        file_path=str(receipt_file),
        claim_id="CLM-1001",
        category="TAXI",
        receipt_index=1,
    )

    assert attempts["count"] == 2
    assert result["uploaded"] is True


def test_upload_receipt_file_rejects_duplicate_source_path(monkeypatch):
    receipt_agent = ReceiptAgent()
    receipt_file = _write_file("hotel-duplicate.jpg", b"receipt-bytes")
    monkeypatch.setattr("agents.receipt_agent.upload_receipt", lambda **_: None)

    with pytest.raises(ReceiptUploadError, match="already been uploaded"):
        receipt_agent.upload_receipt_file(
            file_path=str(receipt_file),
            claim_id="CLM-1001",
            category="HOTEL",
            receipt_index=2,
            existing_uploads=[{"source_path": str(receipt_file)}],
        )


def test_send_manager_approval_email_uses_claim_snapshot_amounts(monkeypatch):
    receipt_agent = ReceiptAgent()
    monkeypatch.setattr(settings.notifications, "sender_email", "sender@example.com")
    monkeypatch.setattr(settings.notifications, "notification_email", "manager@example.com")

    captured = {}

    def fake_send_notification_email(**kwargs):
        captured.update(kwargs)
        return {"message_id": "msg-1"}

    monkeypatch.setattr(
        "agents.receipt_agent.send_notification_email", fake_send_notification_email
    )

    result = receipt_agent.send_manager_approval_email(
        claim_id="CLM123456789012",
        approval_result={"status": "PENDING"},
        claim_snapshot={
            "employee_id": "EMP0003",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "destination": "Bangalore",
            "business_purpose": "Attend customer meetings",
            "trip_start_date": "2026-07-01",
            "trip_end_date": "2026-07-03",
            "amount": {
                "claimed_amount": "2500.00",
                "approved_amount": "2000.00",
                "reimbursable_amount": "2000.00",
            },
            "expense_line_items": [
                {
                    "category_name": "Hotel",
                    "claimed_amount": "1500.00",
                    "currency": "INR",
                }
            ],
        },
        claim_preview=None,
        policy_context={},
        receipt_uploads={},
    )

    assert result["success"] is True
    body = captured["body_text"]
    assert "Claim Amount: 2500.00" in body
    assert "Approved Amount: 2000.00" in body
    assert "N/A" not in body


class _FakeResponse:
    def __init__(self, *, body: bytes, content_type: str, status_code: int = 200, url: str) -> None:
        self._body = body
        self.status_code = status_code
        self.url = url
        self.headers = {"Content-Type": content_type}

    def iter_content(self, chunk_size: int = 8192):
        yield self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def test_upload_receipt_file_accepts_remote_url_and_cleans_up_temp_file(monkeypatch):
    receipt_agent = ReceiptAgent()
    url = (
        "https://receiptsmaker.com/_next/image?url="
        "https:%2F%2Fimages.receiptsmaker.com%2Freceipt-templates%2Fhyatt-hotel-receipt.png"
        "&w=3840&q=75"
    )
    calls: list[dict[str, str]] = []

    def fake_upload_receipt(**kwargs):
        calls.append(kwargs)
        return {
            "bucket": kwargs["bucket"],
            "key": kwargs["key"],
            "content_type": kwargs["content_type"],
            "file_name": Path(kwargs["file_path"]).name,
        }

    monkeypatch.setattr("agents.receipt_agent.upload_receipt", fake_upload_receipt)
    monkeypatch.setattr(
        "agents.receipt_agent.requests.get",
        lambda *_, **__: _FakeResponse(
            body=b"downloaded-receipt",
            content_type="image/png",
            url=url,
        ),
    )

    result = receipt_agent.upload_receipt_file(
        file_path=url,
        claim_id="CLM-1001",
        category="HOTEL",
        receipt_index=1,
    )

    assert result["uploaded"] is True
    assert result["source_url"] == url
    assert result["content_type"] == "image/png"
    assert result["file_name"] == "hyatt-hotel-receipt.png"
    assert result["key"] == "claims/CLM-1001/HOTEL/receipt_1.png"
    assert calls
    assert not Path(calls[0]["file_path"]).exists()


def test_upload_receipt_file_rejects_invalid_remote_url(monkeypatch):
    receipt_agent = ReceiptAgent()
    monkeypatch.setattr("agents.receipt_agent.upload_receipt", lambda **_: None)

    with pytest.raises(ReceiptUploadError, match="provided receipt URL is invalid"):
        receipt_agent.upload_receipt_file(
            file_path="ftp://example.com/receipt.jpg",
            claim_id="CLM-1001",
            category="HOTEL",
            receipt_index=1,
        )


def test_upload_receipt_file_rejects_missing_remote_file(monkeypatch):
    receipt_agent = ReceiptAgent()
    url = "https://example.com/receipt.jpg"

    monkeypatch.setattr("agents.receipt_agent.upload_receipt", lambda **_: None)
    monkeypatch.setattr(
        "agents.receipt_agent.requests.get",
        lambda *_, **__: _FakeResponse(
            body=b"", content_type="image/jpeg", status_code=404, url=url
        ),
    )

    with pytest.raises(ReceiptUploadError, match="remote file does not exist"):
        receipt_agent.upload_receipt_file(
            file_path=url,
            claim_id="CLM-1001",
            category="HOTEL",
            receipt_index=1,
        )
