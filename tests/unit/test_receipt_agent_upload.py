from __future__ import annotations

from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from agents.receipt_agent import ReceiptAgent, ReceiptUploadError


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
