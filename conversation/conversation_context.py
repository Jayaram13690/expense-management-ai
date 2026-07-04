from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel

from contracts import EmployeeProfile, PolicyContext
from conversation.conversation_state import ConversationState


def _normalize_value(value: Any) -> Any:
    """Convert model-like objects into plain Python data."""

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
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    execution_results: dict[str, Any] = field(default_factory=dict)
    execution_stage: ConversationState = ConversationState.ACTIVE

    def record_message(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})

    def apply_updates(self, updates: Mapping[str, Any] | None) -> None:
        if not updates:
            return

        for key, value in updates.items():
            if not hasattr(self, key):
                continue
            normalized = _normalize_value(value)
            if key == "expense_items" and normalized is not None:
                self.expense_items = list(normalized)
                self.expense_collection_complete = bool(self.expense_items)
            else:
                setattr(self, key, normalized)

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
        normalized = re.sub(r"[^a-z0-9]+", " ", message.strip().lower()).strip()
        return normalized in {"done", "finished", "no more", "submit"}

    def infer_expense_item_from_message(self, message: str) -> dict[str, Any] | None:
        text = message.strip()
        if not text:
            return None

        structured = self._parse_structured_payload(text)
        if isinstance(structured, Mapping):
            item = dict(structured)
            if item:
                return item

        lower = text.lower()
        category_code = "MISC"
        category_patterns = {
            "HOTEL": ("hotel", "lodging", "room", "stay"),
            "TAXI": ("taxi", "cab", "uber", "ola", "transfer", "ride"),
            "MEALS": ("meal", "meals", "food", "lunch", "dinner", "breakfast"),
            "FLIGHT": ("flight", "airfare", "air ticket", "airline"),
            "TRAIN": ("train", "rail"),
        }
        for code, keywords in category_patterns.items():
            if any(keyword in lower for keyword in keywords):
                category_code = code
                break

        amount_match = re.search(r"(\d+(?:\.\d{1,2})?)", text)
        requested_amount = amount_match.group(1) if amount_match else "1"

        currency_match = re.search(r"([A-Z]{3})", text)
        currency = currency_match.group(1) if currency_match else "INR"

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        expense_date = (
            date_match.group(1)
            if date_match
            else (self.trip_start_date or self.trip_end_date or date.today().isoformat())
        )

        receipt_available = not any(
            phrase in lower for phrase in ("no receipt", "without receipt", "receipt unavailable")
        )

        return {
            "category_code": category_code,
            "description": text,
            "expense_date": expense_date,
            "requested_amount": requested_amount,
            "currency": currency,
            "receipt_available": receipt_available,
        }

    def append_expense_item(self, item: Mapping[str, Any] | None) -> None:
        if not item:
            return
        normalized = _normalize_value(item)
        if isinstance(normalized, Mapping):
            self.expense_items.append(dict(normalized))
        elif isinstance(normalized, list):
            for entry in normalized:
                if isinstance(entry, Mapping):
                    self.expense_items.append(dict(entry))
        self.expense_collection_complete = False

    def mark_expense_collection_complete(self) -> None:
        if self.expense_items:
            self.expense_collection_complete = True

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
        self.conversation_history.clear()
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
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text.strip()):
                return text.strip()
            return None

        if field_name in {
            "trip_name",
            "business_purpose",
            "destination",
        }:
            return text.strip()

        return text


__all__ = ["ConversationContext"]
