from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel

from contracts import (
    ApprovalResult,
    ClaimPreview,
    EmployeeProfile,
    PolicyContext,
    ReceiptResult,
    SubmittedClaim,
)
from conversation.conversation_state import ConversationState


def _normalize_value(value: Any) -> Any:
    """Convert model-like objects into plain Python data."""

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return value.model_dump()
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return value.model_dump()
    if isinstance(value, Mapping):
        return {key: _normalize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_value(item) for item in value)
    if isinstance(value, set):
        return {_normalize_value(item) for item in value}
    return value


@dataclass
class ConversationContext:
    """In-memory conversation memory for the orchestration layer."""

    TRIP_DATE_FORMATS: ClassVar[tuple[str, ...]] = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
    RECEIPT_DONE_COMMANDS: ClassVar[set[str]] = {"done", "finished", "no more", "submit"}
    RECEIPT_RESUME_COMMANDS: ClassVar[set[str]] = {"resume", "continue", "proceed"}
    RECEIPT_CANCEL_COMMANDS: ClassVar[set[str]] = {"cancel"}
    CATEGORY_OPTIONS: ClassVar[tuple[tuple[str, str], ...]] = (
        ("HOTEL", "Hotel"),
        ("TAXI", "Taxi"),
        ("AIR", "Air Travel"),
        ("MEALS", "Meals & Entertainment"),
        ("PARK", "Parking"),
        ("FUEL", "Fuel"),
        ("INTERNET", "Internet"),
        ("TRAIN", "Rail Travel"),
        ("OFFICE", "Office Supplies"),
        ("MOBILE", "Mobile Charges"),
    )
    CATEGORY_ALIASES: ClassVar[dict[str, tuple[str, ...]]] = {
        "HOTEL": ("hotel", "hotel accommodation", "lodging", "room", "stay"),
        "TAXI": ("taxi", "cab", "ride share", "rideshare", "uber", "ola", "transfer", "ride"),
        "AIR": ("air", "air travel", "flight", "airfare", "air ticket", "airline"),
        "MEALS": ("meal", "meals", "meals & entertainment", "food", "lunch", "dinner", "breakfast"),
        "PARK": ("park", "parking"),
        "FUEL": ("fuel", "petrol", "diesel", "gas"),
        "INTERNET": ("internet", "wifi", "wi-fi", "broadband", "data card"),
        "TRAIN": ("train", "rail", "rail travel"),
        "OFFICE": ("office", "office supplies", "stationery", "supplies"),
        "MOBILE": ("mobile", "phone", "cell", "communication", "sim"),
    }

    employee_id: str | None = None
    trip_name: str | None = None
    business_purpose: str | None = None
    destination: str | None = None
    trip_start_date: str | None = None
    trip_end_date: str | None = None
    expense_items: list[dict[str, Any]] = field(default_factory=list)
    expense_collection_complete: bool = False
    employee_profile: EmployeeProfile | None = None
    policy_context: PolicyContext | None = None
    claim_preview: dict[str, Any] | None = None
    confirmation: bool | None = None
    claim_id: str | None = None
    draft_claim_id: str | None = None
    receipt_uploads: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    receipts_complete: bool = False
    receipt_upload_paused: bool = False
    category_clarifications: list[dict[str, Any]] = field(default_factory=list)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    execution_results: dict[str, Any] = field(default_factory=dict)
    execution_stage: ConversationState = ConversationState.ACTIVE

    def record_message(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any] | None) -> ConversationContext:
        context = cls()
        if not snapshot:
            return context

        context.employee_id = snapshot.get("employee_id")
        context.trip_name = snapshot.get("trip_name")
        context.business_purpose = snapshot.get("business_purpose")
        context.destination = snapshot.get("destination")
        context.trip_start_date = snapshot.get("trip_start_date")
        context.trip_end_date = snapshot.get("trip_end_date")
        context.expense_items = []
        expense_items = snapshot.get("expense_items")
        if isinstance(expense_items, list):
            for item in expense_items:
                if isinstance(item, Mapping):
                    context.expense_items.append(context._normalize_expense_item(item))
        context.expense_collection_complete = bool(snapshot.get("expense_collection_complete"))
        context.employee_profile = cls._restore_model(
            snapshot.get("employee_profile"), EmployeeProfile
        )
        context.policy_context = cls._restore_model(snapshot.get("policy_context"), PolicyContext)
        context.claim_preview = cls._restore_model(snapshot.get("claim_preview"), ClaimPreview)
        context.confirmation = snapshot.get("confirmation")
        context.claim_id = snapshot.get("claim_id")
        context.draft_claim_id = snapshot.get("draft_claim_id")
        context.receipt_uploads = cls._restore_receipt_uploads(snapshot.get("receipt_uploads"))
        context.receipts_complete = bool(snapshot.get("receipts_complete"))
        context.receipt_upload_paused = bool(snapshot.get("receipt_upload_paused"))
        context.category_clarifications = cls._restore_mapping_list(
            snapshot.get("category_clarifications")
        )
        context.conversation_history = cls._restore_history(snapshot.get("conversation_history"))
        context.execution_results = cls._restore_execution_results(
            snapshot.get("execution_results")
        )

        execution_stage = snapshot.get("execution_stage")
        if isinstance(execution_stage, str):
            try:
                context.execution_stage = ConversationState(execution_stage)
            except ValueError:
                context.execution_stage = ConversationState.ACTIVE

        return context

    def apply_updates(self, updates: Mapping[str, Any] | None) -> None:
        if not updates:
            return

        for key, value in updates.items():
            if not hasattr(self, key):
                continue
            normalized = _normalize_value(value)
            if key == "expense_items" and normalized is not None:
                self.expense_items = []
                if isinstance(normalized, list):
                    for entry in normalized:
                        if isinstance(entry, Mapping):
                            self.expense_items.append(self._normalize_expense_item(entry))
                self.expense_collection_complete = bool(self.expense_items)
                self.category_clarifications = self.derive_category_clarifications()
            elif key == "receipt_uploads" and isinstance(normalized, Mapping):
                self.receipt_uploads = {
                    str(category): [dict(item) for item in uploads if isinstance(item, Mapping)]
                    for category, uploads in normalized.items()
                    if isinstance(uploads, list)
                }
            else:
                setattr(self, key, normalized)

    @staticmethod
    def _restore_model(value: Any, model_cls: type[BaseModel]) -> Any:
        if isinstance(value, model_cls):
            return value
        if isinstance(value, Mapping):
            return model_cls.model_validate(value)
        return value

    @staticmethod
    def _restore_mapping_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, Mapping)]

    @classmethod
    def _restore_history(cls, value: Any) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        if not isinstance(value, list):
            return history
        for item in value:
            if not isinstance(item, Mapping):
                continue
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str):
                history.append({"role": role, "content": content})
        return history

    @classmethod
    def _restore_receipt_uploads(cls, value: Any) -> dict[str, list[dict[str, Any]]]:
        if not isinstance(value, Mapping):
            return {}

        uploads: dict[str, list[dict[str, Any]]] = {}
        for category, items in value.items():
            if not isinstance(items, list):
                continue
            uploads[str(category)] = [dict(item) for item in items if isinstance(item, Mapping)]
        return uploads

    @classmethod
    def _restore_execution_results(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return {}

        restored: dict[str, Any] = {}
        for key, item in value.items():
            restored[key] = cls._restore_execution_result(key, item)
        return restored

    @classmethod
    def _restore_execution_result(cls, key: str, value: Any) -> Any:
        if key == "employee_profile":
            return cls._restore_model(value, EmployeeProfile)
        if key in {"policy_context", "partial_policy_context"}:
            return cls._restore_model(value, PolicyContext)
        if key == "claim_preview":
            return cls._restore_model(value, ClaimPreview)
        if key == "submitted_claim":
            return cls._restore_model(value, SubmittedClaim)
        if key == "approval_result":
            return cls._restore_model(value, ApprovalResult)
        if key == "receipt_result":
            return cls._restore_model(value, ReceiptResult)
        if key == "last_execution" and isinstance(value, Mapping):
            return {
                nested_key: cls._restore_execution_result(nested_key, nested_value)
                for nested_key, nested_value in value.items()
            }
        return _normalize_value(value)

    def infer_updates_from_message(
        self,
        message: str,
        required_fields: Sequence[str],
    ) -> dict[str, Any]:
        """Infer slot values from the current user reply."""

        missing_fields = self.missing_fields(required_fields)
        if not missing_fields:
            return {}

        text = message.strip()
        if not text:
            return {}

        structured = self._parse_structured_payload(text)
        if structured is not None:
            filtered = self._filter_known_fields(structured, missing_fields)
            if filtered:
                return filtered

        keyed_updates = self._extract_key_value_updates(text, missing_fields)
        if keyed_updates:
            return keyed_updates

        current_field = missing_fields[0]
        scalar_value = self._coerce_scalar_value(current_field, text)
        if scalar_value is None:
            return {}
        return {current_field: scalar_value}

    def is_expense_collection_done_message(self, message: str) -> bool:
        normalized = self._normalize_command(message)
        return normalized in self.RECEIPT_DONE_COMMANDS

    def is_receipt_collection_done_message(self, message: str) -> bool:
        normalized = self._normalize_command(message)
        return normalized in self.RECEIPT_DONE_COMMANDS

    def is_receipt_resume_message(self, message: str) -> bool:
        normalized = self._normalize_command(message)
        return normalized in self.RECEIPT_RESUME_COMMANDS

    def is_receipt_cancel_message(self, message: str) -> bool:
        normalized = self._normalize_command(message)
        return normalized in self.RECEIPT_CANCEL_COMMANDS

    def infer_expense_item_from_message(self, message: str) -> dict[str, Any] | None:
        text = message.strip()
        if not text:
            return None

        structured = self._parse_structured_payload(text)
        if isinstance(structured, Mapping):
            item = dict(structured)
            if item:
                return self._normalize_expense_item(item)

        lower = text.lower()
        category_code = self.normalize_category_identifier(text)

        amount_match = re.search(r"(\d+(?:\.\d{1,2})?)", text)
        requested_amount = amount_match.group(1) if amount_match else "1"

        currency_match = re.search(r"\b([A-Z]{3})\b", text)
        currency = currency_match.group(1) if currency_match else "INR"

        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        expense_date = (
            date_match.group(1)
            if date_match
            else (self.trip_start_date or self.trip_end_date or date.today().isoformat())
        )

        receipt_available = not any(
            phrase in lower for phrase in ("no receipt", "without receipt", "receipt unavailable")
        )

        item = {
            "category_code": category_code,
            "entered_category": text,
            "description": text,
            "expense_date": expense_date,
            "requested_amount": requested_amount,
            "currency": currency,
            "receipt_available": receipt_available,
        }
        return self._normalize_expense_item(item)

    def append_expense_item(self, item: Mapping[str, Any] | None) -> None:
        if not item:
            return
        normalized = _normalize_value(item)
        if isinstance(normalized, Mapping):
            self.expense_items.append(self._normalize_expense_item(normalized))
        elif isinstance(normalized, list):
            for entry in normalized:
                if isinstance(entry, Mapping):
                    self.expense_items.append(self._normalize_expense_item(entry))
        self.expense_collection_complete = False
        self.receipts_complete = False
        self.receipt_uploads.clear()
        self.draft_claim_id = None
        self.policy_context = None
        self.category_clarifications = self.derive_category_clarifications()
        self.execution_results.pop("partial_policy_context", None)
        self.execution_results.pop("policy_context", None)

    def mark_expense_collection_complete(self) -> None:
        if self.expense_items:
            self.expense_collection_complete = True
            self.category_clarifications = self.derive_category_clarifications()

    def set_stage(self, stage: ConversationState) -> None:
        self.execution_stage = stage

    def store_execution_result(self, key: str, value: Any) -> None:
        self.execution_results[key] = value

    def get_execution_result(self, key: str, default: Any | None = None) -> Any | None:
        return self.execution_results.get(key, default)

    def missing_fields(self, required_fields: Sequence[str]) -> list[str]:
        missing: list[str] = []
        for field_name in required_fields:
            value = getattr(self, field_name, None)
            if field_name == "expense_items":
                if not self.expense_items and not self.expense_collection_complete:
                    missing.append(field_name)
                continue
            if value in (None, ""):
                missing.append(field_name)
        return missing

    def has_all_fields(self, required_fields: Sequence[str]) -> bool:
        return not self.missing_fields(required_fields)

    def latest_history(self, limit: int = 10) -> list[dict[str, str]]:
        return self.conversation_history[-limit:]

    def ensure_draft_claim_id(self) -> str:
        if not self.draft_claim_id:
            self.draft_claim_id = f"DRAFT-{uuid4().hex[:12].upper()}"
        return self.draft_claim_id

    def uploaded_receipt_count(self, category: str) -> int:
        uploads = self.receipt_uploads.get(category.upper(), [])
        return len(uploads)

    def total_uploaded_receipts(self) -> int:
        return sum(len(uploads) for uploads in self.receipt_uploads.values())

    def set_category_clarifications(self, clarifications: Sequence[Mapping[str, Any]]) -> None:
        self.category_clarifications = [dict(_normalize_value(item)) for item in clarifications]

    def clear_category_clarifications(self) -> None:
        self.category_clarifications.clear()

    def has_pending_category_clarifications(self) -> bool:
        return bool(self.category_clarifications)

    def next_category_clarification(self) -> dict[str, Any] | None:
        return self.category_clarifications[0] if self.category_clarifications else None

    def apply_category_clarification(self, category_code: str) -> None:
        clarification = self.next_category_clarification()
        if clarification is None:
            return

        expense_index = clarification.get("expense_index")
        if not isinstance(expense_index, int) or not (0 <= expense_index < len(self.expense_items)):
            self.category_clarifications = self.category_clarifications[1:]
            return

        item = dict(self.expense_items[expense_index])
        item["category_code"] = category_code
        item["entered_category"] = item.get("entered_category") or clarification.get(
            "entered_category"
        )
        item["needs_category_clarification"] = False
        item.pop("category_identifier", None)
        self.expense_items[expense_index] = item
        self.category_clarifications = self.derive_category_clarifications()
        self.policy_context = None
        self.execution_results.pop("partial_policy_context", None)
        self.execution_results.pop("policy_context", None)

    def derive_category_clarifications(self) -> list[dict[str, Any]]:
        clarifications: list[dict[str, Any]] = []
        for expense_index, item in enumerate(self.expense_items):
            if not isinstance(item, Mapping):
                continue
            if not item.get("needs_category_clarification"):
                continue
            clarifications.append(
                {
                    "expense_index": expense_index,
                    "entered_category": item.get("entered_category")
                    or item.get("category_code")
                    or item.get("description")
                    or "Unknown category",
                    "requested_amount": item.get("requested_amount"),
                    "currency": item.get("currency") or "INR",
                    "description": item.get("description") or "",
                    "reason": "I couldn't identify the expense category from that entry.",
                    "options": self.category_clarification_options(),
                }
            )
        return clarifications

    def category_clarification_options(self) -> list[dict[str, str]]:
        return [{"code": code, "label": label} for code, label in self.CATEGORY_OPTIONS]

    def resolve_category_choice(self, message: str) -> str | None:
        normalized = self._normalize_command(message)
        if not normalized:
            return None

        if normalized.isdigit():
            choice_index = int(normalized) - 1
            if 0 <= choice_index < len(self.CATEGORY_OPTIONS):
                return self.CATEGORY_OPTIONS[choice_index][0]

        return self.normalize_category_identifier(message)

    def append_receipt_upload(self, category: str, metadata: Mapping[str, Any]) -> None:
        normalized_category = category.upper()
        uploads = self.receipt_uploads.setdefault(normalized_category, [])
        uploads.append(dict(_normalize_value(metadata)))
        self.receipt_upload_paused = False
        self.receipts_complete = self.next_pending_receipt_slot() is None

    def required_receipt_slots(self) -> list[dict[str, Any]]:
        policy_context = self._policy_payload()
        categories = (
            policy_context.get("categories", {}) if isinstance(policy_context, Mapping) else {}
        )
        if not isinstance(categories, Mapping):
            return []

        category_counts: dict[str, int] = {}
        slots: list[dict[str, Any]] = []
        for expense_item_index, item in enumerate(self.expense_items, start=1):
            if not isinstance(item, Mapping):
                continue
            category = self._expense_item_category(item)
            if category is None:
                continue

            category_details = categories.get(category, {})
            if hasattr(category_details, "model_dump") and callable(category_details.model_dump):
                category_details = category_details.model_dump()
            if not isinstance(category_details, Mapping):
                continue

            limits = category_details.get("limits", {})
            if hasattr(limits, "model_dump") and callable(limits.model_dump):
                limits = limits.model_dump()
            receipt_required = False
            if isinstance(limits, Mapping):
                receipt_required = bool(limits.get("receipt_required"))
            if not receipt_required:
                receipt_required = bool(category_details.get("receipt_required"))
            if not receipt_required:
                continue

            category_counts[category] = category_counts.get(category, 0) + 1
            slots.append(
                {
                    "category": category,
                    "receipt_index": category_counts[category],
                    "expense_item_index": expense_item_index,
                }
            )
        return slots

    def next_pending_receipt_slot(self) -> dict[str, Any] | None:
        for slot in self.required_receipt_slots():
            if self.uploaded_receipt_count(slot["category"]) < int(slot["receipt_index"]):
                return slot
        return None

    def required_receipt_categories(self) -> list[str]:
        ordered_categories: list[str] = []
        for slot in self.required_receipt_slots():
            category = str(slot["category"])
            if category not in ordered_categories:
                ordered_categories.append(category)
        return ordered_categories

    def remaining_receipt_categories(self) -> list[str]:
        ordered_categories: list[str] = []
        for slot in self.required_receipt_slots():
            category = str(slot["category"])
            if self.uploaded_receipt_count(category) >= int(slot["receipt_index"]):
                continue
            if category not in ordered_categories:
                ordered_categories.append(category)
        return ordered_categories

    def has_uploaded_source_path(self, file_path: str, category: str | None = None) -> bool:
        normalized_path = file_path.strip().casefold()
        categories = [category.upper()] if category else list(self.receipt_uploads.keys())
        for receipt_category in categories:
            for upload in self.receipt_uploads.get(receipt_category, []):
                for source_field in ("source_path", "source_url"):
                    source_value = upload.get(source_field)
                    if (
                        isinstance(source_value, str)
                        and source_value.strip().casefold() == normalized_path
                    ):
                        return True
        return False

    def snapshot(self) -> dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "trip_name": self.trip_name,
            "business_purpose": self.business_purpose,
            "destination": self.destination,
            "trip_start_date": self.trip_start_date,
            "trip_end_date": self.trip_end_date,
            "expense_items": _normalize_value(self.expense_items),
            "expense_collection_complete": self.expense_collection_complete,
            "employee_profile": _normalize_value(self.employee_profile),
            "policy_context": _normalize_value(self.policy_context),
            "claim_preview": _normalize_value(self.claim_preview),
            "confirmation": self.confirmation,
            "claim_id": self.claim_id,
            "draft_claim_id": self.draft_claim_id,
            "receipt_uploads": _normalize_value(self.receipt_uploads),
            "receipts_complete": self.receipts_complete,
            "receipt_upload_paused": self.receipt_upload_paused,
            "category_clarifications": _normalize_value(self.category_clarifications),
            "conversation_history": _normalize_value(self.conversation_history),
            "execution_results": _normalize_value(self.execution_results),
            "execution_stage": self.execution_stage.value,
        }

    def reset(self) -> None:
        self.employee_id = None
        self.trip_name = None
        self.business_purpose = None
        self.destination = None
        self.trip_start_date = None
        self.trip_end_date = None
        self.expense_items.clear()
        self.expense_collection_complete = False
        self.employee_profile = None
        self.policy_context = None
        self.claim_preview = None
        self.confirmation = None
        self.claim_id = None
        self.draft_claim_id = None
        self.receipt_uploads.clear()
        self.receipts_complete = False
        self.receipt_upload_paused = False
        self.category_clarifications.clear()
        self.conversation_history.clear()
        self.execution_results.clear()
        self.execution_stage = ConversationState.ACTIVE

    def reset_submission_flow(self) -> None:
        """Clear the active claim workflow while preserving conversation history."""

        self.employee_id = None
        self.trip_name = None
        self.business_purpose = None
        self.destination = None
        self.trip_start_date = None
        self.trip_end_date = None
        self.expense_items.clear()
        self.expense_collection_complete = False
        self.employee_profile = None
        self.policy_context = None
        self.claim_preview = None
        self.confirmation = None
        self.claim_id = None
        self.draft_claim_id = None
        self.receipt_uploads.clear()
        self.receipts_complete = False
        self.receipt_upload_paused = False
        self.category_clarifications.clear()
        self.execution_results.clear()
        self.execution_stage = ConversationState.ACTIVE

    def _parse_structured_payload(self, text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        if isinstance(payload, Mapping):
            return dict(payload)
        if isinstance(payload, list):
            return payload
        return None

    def _filter_known_fields(self, payload: Any, missing_fields: Sequence[str]) -> dict[str, Any]:
        if isinstance(payload, list):
            if "expense_items" in missing_fields:
                return {"expense_items": payload}
            return {}

        if not isinstance(payload, Mapping):
            return {}

        allowed = {
            "employee_id",
            "trip_name",
            "business_purpose",
            "destination",
            "trip_start_date",
            "trip_end_date",
            "expense_items",
            "confirmation",
            "claim_id",
        }

        updates: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in allowed or key not in missing_fields:
                continue
            updates[key] = value
        return updates

    def _extract_key_value_updates(
        self, text: str, missing_fields: Sequence[str]
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}

        for field_name in missing_fields:
            if field_name == "expense_items":
                continue

            pattern = rf"{re.escape(field_name)}\s*[:=]\s*(.+)"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                updates[field_name] = match.group(1).strip(" ,;")

        return updates

    def _coerce_scalar_value(self, field_name: str, text: str) -> Any:
        if field_name == "expense_items":
            structured = self._parse_structured_payload(text)
            if isinstance(structured, list):
                return structured
            if isinstance(structured, Mapping):
                items = structured.get("expense_items")
                if isinstance(items, list):
                    return items
            return None

        if field_name == "employee_id":
            if re.fullmatch(r"[A-Za-z]{2,}\d+", text.strip()):
                return text.strip()
            return None

        if field_name in {"trip_start_date", "trip_end_date"}:
            parsed = self.parse_trip_date_value(text)
            return parsed.isoformat() if parsed is not None else None

        if field_name in {
            "trip_name",
            "business_purpose",
            "destination",
        }:
            return text.strip()

        return text

    def parse_trip_date_value(self, value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            return None

        text = value.strip()
        if not text:
            return None

        for fmt in self.TRIP_DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def validate_trip_date_value(
        self,
        field_name: str,
        value: Any,
        *,
        current_trip_start_date: Any | None = None,
        today: date | None = None,
    ) -> tuple[str | None, str | None]:
        """Validate and normalize a trip date input."""

        parsed_value = self.parse_trip_date_value(value)
        if parsed_value is None:
            if field_name == "trip_start_date":
                return None, (
                    "I couldn't understand that date. Please enter the trip "
                    "start date in YYYY-MM-DD format."
                )
            return None, (
                "I couldn't understand that date. Please enter the trip "
                "end date in YYYY-MM-DD format."
            )

        if field_name == "trip_start_date":
            current_day = today or date.today()
            if parsed_value > current_day:
                return None, (
                    "The trip start date cannot be later than today.\n\n"
                    f"Today's date is:\n{current_day.isoformat()}\n\n"
                    "Please enter the trip start date in YYYY-MM-DD format."
                )
            return parsed_value.isoformat(), None

        if field_name == "trip_end_date":
            start_value = self.parse_trip_date_value(current_trip_start_date)
            if start_value is not None and parsed_value < start_value:
                return None, (
                    "The trip end date cannot be earlier than the trip start date.\n\n"
                    f"Your current trip start date is:\n{start_value.isoformat()}\n\n"
                    "Please enter a valid trip end date."
                )
            return parsed_value.isoformat(), None

        return parsed_value.isoformat(), None

    def normalize_category_identifier(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        normalized = self._normalize_command(value)
        if not normalized:
            return None

        compact = normalized.replace(" ", "_").upper()
        direct_codes = {code for code, _ in self.CATEGORY_OPTIONS}
        if compact in direct_codes:
            return compact

        if normalized in {"other", "misc", "miscellaneous"}:
            return None

        for code, label in self.CATEGORY_OPTIONS:
            label_normalized = self._normalize_command(label)
            if normalized == label_normalized or normalized in label_normalized:
                return code

        for code, aliases in self.CATEGORY_ALIASES.items():
            if compact == code:
                return code
            if any(alias in normalized for alias in aliases):
                return code

        return None

    def _normalize_expense_item(self, item: Mapping[str, Any]) -> dict[str, Any]:
        normalized_item = dict(_normalize_value(item))
        entered_category = (
            normalized_item.get("entered_category")
            or normalized_item.get("category")
            or normalized_item.get("category_identifier")
            or normalized_item.get("category_code")
            or normalized_item.get("description")
        )
        category_code = self.normalize_category_identifier(str(entered_category))
        if category_code is None:
            normalized_item["category_code"] = None
            normalized_item["needs_category_clarification"] = True
        else:
            normalized_item["category_code"] = category_code
            normalized_item["needs_category_clarification"] = False
        normalized_item["entered_category"] = entered_category
        return normalized_item

    def format_expense_for_clarification(self, clarification: Mapping[str, Any]) -> str:
        label = (
            clarification.get("entered_category")
            or clarification.get("description")
            or "Unknown category"
        )
        amount = clarification.get("requested_amount")
        currency = clarification.get("currency") or "INR"
        if amount not in (None, ""):
            return f"{label} ({currency} {amount})"
        return str(label)

    def _policy_payload(self) -> Mapping[str, Any]:
        payload = (
            self.policy_context
            or self.get_execution_result("policy_context")
            or self.get_execution_result("partial_policy_context")
            or {}
        )
        if hasattr(payload, "model_dump") and callable(payload.model_dump):
            payload = payload.model_dump()
        if isinstance(payload, Mapping):
            return payload
        return {}

    def _expense_item_category(self, item: Mapping[str, Any]) -> str | None:
        category = (
            item.get("category_code") or item.get("category_identifier") or item.get("category")
        )
        if isinstance(category, str) and category.strip():
            return category.strip().upper()
        return None

    def _normalize_command(self, message: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", message.strip().lower()).strip()


__all__ = ["ConversationContext"]
