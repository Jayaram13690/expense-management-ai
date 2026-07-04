from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent, ReceiptUploadError
from contracts import EmployeeProfile
from conversation.conversation_state import ConversationState
from conversation.orchestrator import ConversationOrchestrator


def _build_orchestrator(receipt_upload_side_effect=None) -> ConversationOrchestrator:
    employee_agent = EmployeeAgent()
    employee_agent.get_employee_profile = Mock(side_effect=_employee_profile_side_effect)

    policy_agent = PolicyAgent()
    policy_agent.check_employee_eligibility = Mock(side_effect=_policy_eligibility_side_effect)
    policy_agent.get_category_limits = Mock(side_effect=_policy_limits_side_effect)

    expense_agent = ExpenseAgent()
    expense_agent.preview_claim_request = Mock(side_effect=_preview_side_effect)
    expense_agent.submit_claim_request = Mock(side_effect=_submit_side_effect)

    approval_agent = ApprovalAgent()
    approval_agent.get_approval_result = Mock(
        return_value={"approval_id": "APR-2001", "status": "pending"}
    )

    receipt_agent = ReceiptAgent()
    receipt_agent.upload_receipt_file = Mock(
        side_effect=receipt_upload_side_effect or _receipt_upload_side_effect
    )
    receipt_agent.generate_receipt_result = Mock(
        return_value={"receipt_id": "RCT-3001", "status": "generated"}
    )

    return ConversationOrchestrator(
        employee_agent=employee_agent,
        expense_agent=expense_agent,
        policy_agent=policy_agent,
        approval_agent=approval_agent,
        receipt_agent=receipt_agent,
    )


def _employee_profile_side_effect(employee_id: str) -> EmployeeProfile:
    return EmployeeProfile(
        employee_id=employee_id,
        employee_name="Asha Rao",
        employee_grade="G5",
        department="Engineering",
        manager_id="MGR001",
    )


def _policy_eligibility_side_effect(category_identifier: str, employee_grade: str) -> bool:
    assert employee_grade == "G5"
    assert category_identifier.upper() in {"HOTEL", "TAXI"}
    return True


def _policy_limits_side_effect(category_identifier: str, employee_grade: str) -> dict[str, object]:
    assert employee_grade == "G5"
    return {
        "daily_limit": "5000" if category_identifier.upper() == "HOTEL" else "1500",
        "monthly_limit": "20000" if category_identifier.upper() == "HOTEL" else "10000",
        "receipt_required": True,
        "approval_required": False,
    }


def _preview_side_effect(*_, **__) -> dict[str, object]:
    return {
        "total_requested": "6700",
        "total_approved": "6500",
        "variance": "200",
        "warnings": ["Policy limits applied"],
    }


def _submit_side_effect(*_, **__) -> dict[str, object]:
    return {
        "claim_id": "CLM-1001",
        "status": "submitted",
    }


def _receipt_upload_side_effect(
    *, file_path: str, claim_id: str, category: str, receipt_index: int, **__
) -> dict[str, object]:
    normalized = file_path.replace("/", "\\")
    if normalized.endswith("missing.jpg"):
        raise ReceiptUploadError(
            "I couldn't find the file. Please provide a valid local file path."
        )
    if normalized.endswith("notes.txt"):
        raise ReceiptUploadError(
            "Unsupported receipt file type. Please upload a JPG, JPEG, PNG, or PDF file."
        )
    if normalized.endswith("duplicate.jpg"):
        raise ReceiptUploadError(
            f"That file has already been uploaded for the {category.upper()} receipt. "
            "Please provide a different file."
        )
    return {
        "uploaded": True,
        "bucket": "expense-ai-receipts",
        "key": f"claims/{claim_id}/{category}/receipt_{receipt_index}.jpg",
        "content_type": "image/jpeg",
        "file_name": Path(file_path).name,
        "source_path": file_path,
    }


def _claim_data() -> dict[str, object]:
    return {
        "employee_id": "EMP0006",
        "trip_name": "AWS Summit Bangalore 2026",
        "business_purpose": "Evaluate AWS Agentic AI for enterprise expense workflows.",
        "destination": "Bangalore",
        "trip_start_date": "2026-07-01",
        "trip_end_date": "2026-07-03",
        "expense_items": [
            {
                "category_code": "HOTEL",
                "description": "Hotel stay",
                "expense_date": "2026-07-01",
                "requested_amount": "5800",
                "currency": "INR",
                "receipt_available": False,
            },
            {
                "category_code": "TAXI",
                "description": "Airport transfer",
                "expense_date": "2026-07-03",
                "requested_amount": "900",
                "currency": "INR",
                "receipt_available": False,
            },
        ],
    }


def _start_receipt_flow(orchestrator: ConversationOrchestrator) -> None:
    preview_result = orchestrator.process_turn(
        "I want to submit an expense claim.",
        extracted_data=_claim_data(),
    )
    assert preview_result["state"] == ConversationState.WAITING_USER.value
    receipt_prompt = orchestrator.process_turn("YES")
    assert receipt_prompt["state"] == ConversationState.COLLECTING_RECEIPTS.value


def test_receipt_collection_blocks_submission_until_all_receipts_uploaded():
    orchestrator = _build_orchestrator()

    _start_receipt_flow(orchestrator)

    hotel_result = orchestrator.process_turn(r"C:\Receipts\hotel.jpg")
    assert hotel_result["state"] == ConversationState.COLLECTING_RECEIPTS.value
    assert "TAXI receipt" in hotel_result["assistant_message"]
    assert orchestrator.expense_agent.submit_claim_request.call_count == 0

    taxi_result = orchestrator.process_turn(r"C:\Receipts\taxi.jpg")
    assert taxi_result["state"] == ConversationState.COMPLETED.value
    assert orchestrator.context.receipts_complete is True
    assert orchestrator.expense_agent.submit_claim_request.call_count == 1
    assert orchestrator.context.claim_id == "CLM-1001"
    assert set(orchestrator.context.receipt_uploads.keys()) == {"HOTEL", "TAXI"}


def test_invalid_receipt_path_keeps_receipt_collection_active():
    orchestrator = _build_orchestrator()

    _start_receipt_flow(orchestrator)
    result = orchestrator.process_turn(r"C:\Receipts\missing.jpg")

    assert result["state"] == ConversationState.COLLECTING_RECEIPTS.value
    assert "valid local file path" in result["assistant_message"]
    assert orchestrator.expense_agent.submit_claim_request.call_count == 0
    assert orchestrator.context.receipt_uploads == {}


def test_unsupported_receipt_extension_keeps_same_slot_active():
    orchestrator = _build_orchestrator()

    _start_receipt_flow(orchestrator)
    result = orchestrator.process_turn(r"C:\Receipts\notes.txt")

    assert result["state"] == ConversationState.COLLECTING_RECEIPTS.value
    assert "unsupported receipt file type" in result["assistant_message"].lower()
    assert "HOTEL receipt" in result["assistant_message"]
    assert orchestrator.expense_agent.submit_claim_request.call_count == 0


def test_duplicate_receipt_upload_is_rejected_without_losing_existing_uploads():
    orchestrator = _build_orchestrator()

    _start_receipt_flow(orchestrator)
    orchestrator.process_turn(r"C:\Receipts\hotel.jpg")
    result = orchestrator.process_turn(r"C:\Receipts\duplicate.jpg")

    assert result["state"] == ConversationState.COLLECTING_RECEIPTS.value
    assert "already been uploaded" in result["assistant_message"].lower()
    assert len(orchestrator.context.receipt_uploads["HOTEL"]) == 1
    assert "TAXI" not in orchestrator.context.receipt_uploads


def test_receipt_upload_can_be_cancelled_and_resumed():
    orchestrator = _build_orchestrator()

    _start_receipt_flow(orchestrator)
    cancel_result = orchestrator.process_turn("CANCEL")
    assert cancel_result["state"] == ConversationState.WAITING_USER.value
    assert orchestrator.expense_agent.submit_claim_request.call_count == 0

    resume_result = orchestrator.process_turn("RESUME")
    assert resume_result["state"] == ConversationState.COLLECTING_RECEIPTS.value
    assert "HOTEL receipt" in resume_result["assistant_message"]


def test_done_before_all_receipts_uploaded_keeps_receipt_collection_active():
    orchestrator = _build_orchestrator()

    _start_receipt_flow(orchestrator)
    result = orchestrator.process_turn("DONE")

    assert result["state"] == ConversationState.COLLECTING_RECEIPTS.value
    assert "Receipts are still required" in result["assistant_message"]
    assert orchestrator.expense_agent.submit_claim_request.call_count == 0


def test_successful_receipt_collection_submits_claim_and_generates_acknowledgement():
    orchestrator = _build_orchestrator()

    _start_receipt_flow(orchestrator)
    orchestrator.process_turn(r"C:\Receipts\hotel.jpg")
    result = orchestrator.process_turn(r"C:\Receipts\taxi.jpg")

    assert "Submitting your claim" in result["assistant_message"]
    assert "Claim submitted successfully" in result["assistant_message"]
    assert orchestrator.approval_agent.get_approval_result.call_count == 1
    assert orchestrator.receipt_agent.generate_receipt_result.call_count == 1
