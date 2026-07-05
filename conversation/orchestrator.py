from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent, ReceiptUploadError
from contracts import EmployeeProfile, PolicyContext
from conversation.conversation_context import ConversationContext
from conversation.conversation_state import ConversationState
from conversation.execution_patterns import (
    HumanInTheLoopExecution,
    ParallelExecution,
    SequentialExecution,
)
from conversation.execution_plan import ExecutionPattern, ExecutionPlan
from conversation.execution_planner import ExecutionPlanner


class ConversationOrchestrator:
    """Thin conversational orchestrator that coordinates existing agents."""

    REQUIRED_FIELDS = (
        "employee_id",
        "trip_name",
        "business_purpose",
        "destination",
        "trip_start_date",
        "trip_end_date",
    )

    def __init__(
        self,
        employee_agent: EmployeeAgent,
        expense_agent: ExpenseAgent,
        policy_agent: PolicyAgent,
        approval_agent: ApprovalAgent,
        receipt_agent: ReceiptAgent,
        planner: ExecutionPlanner | None = None,
        context: ConversationContext | None = None,
        extraction_source: Callable[[str, ConversationContext], Mapping[str, Any]] | None = None,
    ) -> None:
        if None in (employee_agent, expense_agent, policy_agent, approval_agent, receipt_agent):
            raise ValueError("All specialized agents must be provided")

        self.employee_agent = employee_agent
        self.expense_agent = expense_agent
        self.policy_agent = policy_agent
        self.approval_agent = approval_agent
        self.receipt_agent = receipt_agent
        self.context = context or ConversationContext()
        self.planner = planner or ExecutionPlanner()
        self._extraction_source = extraction_source

        self._sequential = SequentialExecution(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
        )
        self._parallel = ParallelExecution(policy_agent=policy_agent)
        self._hil = HumanInTheLoopExecution()

    @property
    def state(self) -> ConversationState:
        return self.context.execution_stage

    def reset(self) -> None:
        self.context.reset()

    def process_turn(
        self,
        message: str,
        extracted_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process one user turn and return the assistant response payload."""

        self.context.record_message("user", message)

        if self.context.execution_stage == ConversationState.COLLECTING_EXPENSES:
            return self._handle_expense_collection_turn(message, extracted_data)

        if self.context.execution_stage == ConversationState.COLLECTING_RECEIPTS:
            return self._handle_receipt_collection_turn(message)

        if (
            self.context.execution_stage == ConversationState.WAITING_USER
            and self.context.has_pending_category_clarifications()
        ):
            return self._handle_category_clarification_turn(message)

        confirmation = self._hil.interpret(message)
        if confirmation is not None and self.context.claim_preview is not None:
            self.context.confirmation = confirmation

        updates, validation_prompt = self._collect_updates_with_validation(message, extracted_data)
        if validation_prompt:
            return self._prompt_for_information(validation_prompt)
        if updates:
            self.context.apply_updates(updates)

        if self.context.confirmation is False:
            return self._cancel_conversation()

        if self.context.missing_fields(self.REQUIRED_FIELDS) and self.context.confirmation is None:
            return self._prompt_for_information()

        if self._needs_category_clarification():
            return self._prompt_for_category_clarification()

        if self._needs_receipt_collection():
            return self._route_to_receipt_collection(message)

        return self._continue_execution()

    def resume(self, message: str) -> dict[str, Any]:
        return self.process_turn(message)

    def _collect_updates(
        self,
        message: str,
        extracted_data: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}

        if extracted_data:
            updates.update(extracted_data)
        elif self._extraction_source is not None:
            source_updates = self._extraction_source(message, self.context)
            if source_updates:
                updates.update(source_updates)
        elif self.context.execution_stage == ConversationState.WAITING_USER:
            inferred_updates = self.context.infer_updates_from_message(
                message, self.REQUIRED_FIELDS
            )
            if inferred_updates:
                updates.update(inferred_updates)

        return updates

    def _collect_updates_with_validation(
        self,
        message: str,
        extracted_data: Mapping[str, Any] | None,
    ) -> tuple[dict[str, Any], str | None]:
        updates = self._collect_updates(message, extracted_data)
        current_field = self._current_expected_field()

        if (
            not updates
            and current_field in {"trip_start_date", "trip_end_date"}
            and message.strip()
        ):
            normalized_value, validation_prompt = self.context.validate_trip_date_value(
                current_field,
                message,
                current_trip_start_date=self.context.trip_start_date,
            )
            if validation_prompt:
                if current_field == "trip_end_date":
                    self.context.trip_end_date = None
                return {}, validation_prompt
            if normalized_value is not None:
                updates[current_field] = normalized_value

        return self._validate_trip_date_updates(updates)

    def _validate_trip_date_updates(
        self,
        updates: Mapping[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        if not updates:
            return {}, None

        normalized_updates = dict(updates)

        if "trip_start_date" in normalized_updates:
            normalized_value, validation_prompt = self.context.validate_trip_date_value(
                "trip_start_date",
                normalized_updates["trip_start_date"],
            )
            if validation_prompt:
                return {}, validation_prompt
            normalized_updates["trip_start_date"] = normalized_value

        start_candidate = normalized_updates.get("trip_start_date", self.context.trip_start_date)

        if "trip_end_date" in normalized_updates:
            normalized_value, validation_prompt = self.context.validate_trip_date_value(
                "trip_end_date",
                normalized_updates["trip_end_date"],
                current_trip_start_date=start_candidate,
            )
            if validation_prompt:
                self.context.trip_end_date = None
                return {}, validation_prompt
            normalized_updates["trip_end_date"] = normalized_value

        start_value = normalized_updates.get("trip_start_date", self.context.trip_start_date)
        end_value = normalized_updates.get("trip_end_date", self.context.trip_end_date)
        start_dt = self.context.parse_trip_date_value(start_value)
        end_dt = self.context.parse_trip_date_value(end_value)
        if start_dt is not None and end_dt is not None and end_dt < start_dt:
            self.context.trip_end_date = None
            return {}, (
                "The trip end date cannot be earlier than the trip start date.\n\n"
                f"Your current trip start date is:\n{start_dt.isoformat()}\n\n"
                "Please enter a valid trip end date."
            )

        return normalized_updates, None

    def _current_expected_field(self) -> str | None:
        missing_fields = self.context.missing_fields(self.REQUIRED_FIELDS)
        return missing_fields[0] if missing_fields else None

    def _handle_expense_collection_turn(
        self,
        message: str,
        extracted_data: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if self.context.is_expense_collection_done_message(message):
            if self.context.expense_items:
                self.context.mark_expense_collection_complete()
                self.context.set_stage(ConversationState.ACTIVE)
                return self._resume_after_expense_collection(extracted_data)

            prompt = self._expense_collection_prompt()
            self.context.set_stage(ConversationState.COLLECTING_EXPENSES)
            self.context.record_message("assistant", prompt)
            return self._build_stage_response(
                assistant_message=prompt,
                stage=ConversationState.COLLECTING_EXPENSES,
                next_action="collect_expenses",
                metadata={"stage": "COLLECTING_EXPENSES", "missing_fields": ["expense_items"]},
            )

        if extracted_data and "expense_items" in extracted_data:
            items = extracted_data.get("expense_items")
            if isinstance(items, list) and items:
                for item in items:
                    if isinstance(item, Mapping):
                        self.context.append_expense_item(item)
        else:
            item = self.context.infer_expense_item_from_message(message)
            if item is not None:
                self.context.append_expense_item(item)

        self.context.set_stage(ConversationState.COLLECTING_EXPENSES)
        self.context.category_clarifications = self.context.derive_category_clarifications()
        prompt = self._expense_follow_up_prompt()
        self.context.record_message("assistant", prompt)
        return self._build_stage_response(
            assistant_message=prompt,
            stage=ConversationState.COLLECTING_EXPENSES,
            next_action="collect_expenses",
            metadata={"stage": "COLLECTING_EXPENSES"},
        )

    def _resume_after_expense_collection(
        self,
        extracted_data: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        updates, validation_prompt = self._collect_updates_with_validation("", extracted_data)
        if validation_prompt:
            return self._prompt_for_information(validation_prompt)
        if updates:
            self.context.apply_updates(updates)
        return self._continue_execution()

    def _needs_category_clarification(self) -> bool:
        if self.context.has_pending_category_clarifications():
            return True
        clarifications = self.context.derive_category_clarifications()
        if clarifications:
            self.context.set_category_clarifications(clarifications)
            return True
        return False

    def _handle_category_clarification_turn(self, message: str) -> dict[str, Any]:
        category_code = self.context.resolve_category_choice(message)
        if category_code is None:
            prompt = (
                "Please choose one of the listed categories so I can continue."
                f"{self._category_clarification_prompt()}"
            )
            self.context.set_stage(ConversationState.WAITING_USER)
            self.context.record_message("assistant", prompt)
            return self._build_stage_response(
                assistant_message=prompt,
                stage=ConversationState.WAITING_USER,
                next_action="category_clarification",
                metadata={"stage": "WAITING_CATEGORY_CLARIFICATION"},
            )

        self.context.apply_category_clarification(category_code)
        if self._needs_category_clarification():
            return self._prompt_for_category_clarification()

        return self._continue_execution()

    def _prompt_for_category_clarification(self) -> dict[str, Any]:
        prompt = self._category_clarification_prompt()
        self.context.set_stage(ConversationState.WAITING_USER)
        self.context.record_message("assistant", prompt)
        return self._build_stage_response(
            assistant_message=prompt,
            stage=ConversationState.WAITING_USER,
            next_action="category_clarification",
            metadata={"stage": "WAITING_CATEGORY_CLARIFICATION"},
        )

    def _category_clarification_prompt(self) -> str:
        clarification = self.context.next_category_clarification()
        if clarification is None:
            return "I need a bit more detail about one of your expense categories."

        expense_summary = self.context.format_expense_for_clarification(clarification)
        reason = clarification.get("reason")
        lines = ["I couldn't identify the category for:", "", expense_summary]
        if isinstance(reason, str) and reason.strip():
            lines.extend(["", reason.strip()])
        lines.extend(["", "Please choose one of the following categories:", ""])
        lines.extend(
            f"{index}. {option['label']}"
            for index, option in enumerate(self.context.category_clarification_options(), start=1)
        )
        return "\n".join(lines)

    def _route_to_receipt_collection(self, message: str) -> dict[str, Any]:
        if self.context.is_receipt_cancel_message(message):
            return self._pause_receipt_collection()
        if self.context.is_receipt_resume_message(message):
            self.context.receipt_upload_paused = False
            return self._start_receipt_collection()
        if (
            self.context.execution_stage == ConversationState.WAITING_USER
            and not self.context.receipt_upload_paused
        ):
            return self._start_receipt_collection()
        if self._hil.interpret(message) is True:
            return self._start_receipt_collection()

        self.context.set_stage(ConversationState.COLLECTING_RECEIPTS)
        return self._handle_receipt_collection_turn(message)

    def _start_receipt_collection(self) -> dict[str, Any]:
        required_slots = self._required_receipt_slots()
        if not required_slots:
            self.context.receipts_complete = True
            return self._continue_execution()

        self.context.ensure_draft_claim_id()
        self.context.receipt_upload_paused = False
        self.context.set_stage(ConversationState.COLLECTING_RECEIPTS)
        prompt = self._receipt_collection_intro_prompt()
        self.context.record_message("assistant", prompt)
        return self._build_stage_response(
            assistant_message=prompt,
            stage=ConversationState.COLLECTING_RECEIPTS,
            next_action="collect_receipts",
            metadata={
                "stage": "WAITING_RECEIPTS",
                "required_categories": self.context.required_receipt_categories(),
            },
        )

    def _handle_receipt_collection_turn(self, message: str) -> dict[str, Any]:
        if self.context.is_receipt_cancel_message(message):
            return self._pause_receipt_collection()

        current_slot = self.context.next_pending_receipt_slot()
        if current_slot is None:
            self.context.receipts_complete = True
            return self._continue_execution()

        if self.context.is_receipt_resume_message(message):
            prompt = self._receipt_prompt_for_slot(current_slot)
            self.context.set_stage(ConversationState.COLLECTING_RECEIPTS)
            self.context.receipt_upload_paused = False
            self.context.record_message("assistant", prompt)
            return self._build_stage_response(
                assistant_message=prompt,
                stage=ConversationState.COLLECTING_RECEIPTS,
                next_action="collect_receipts",
                metadata={"stage": "COLLECTING_RECEIPTS", "current_slot": current_slot},
            )

        if self.context.is_receipt_collection_done_message(message):
            remaining_categories = self.context.remaining_receipt_categories()
            prompt_lines = ["Receipts are still required for the following categories:", ""]
            prompt_lines.extend(
                f"{index}. {category}"
                for index, category in enumerate(remaining_categories, start=1)
            )
            prompt_lines.extend(["", self._receipt_prompt_for_slot(current_slot)])
            prompt = "\n".join(prompt_lines)
            self.context.set_stage(ConversationState.COLLECTING_RECEIPTS)
            self.context.record_message("assistant", prompt)
            return self._build_stage_response(
                assistant_message=prompt,
                stage=ConversationState.COLLECTING_RECEIPTS,
                next_action="collect_receipts",
                metadata={"stage": "COLLECTING_RECEIPTS", "current_slot": current_slot},
            )

        try:
            metadata = self.receipt_agent.upload_receipt_file(
                file_path=message,
                claim_id=self.context.ensure_draft_claim_id(),
                category=str(current_slot["category"]),
                receipt_index=int(current_slot["receipt_index"]),
                existing_uploads=self.context.receipt_uploads.get(
                    str(current_slot["category"]), []
                ),
            )
        except ReceiptUploadError as exc:
            prompt = f"{exc.user_message}\n\n{self._receipt_prompt_for_slot(current_slot)}"
            self.context.set_stage(ConversationState.COLLECTING_RECEIPTS)
            self.context.record_message("assistant", prompt)
            return self._build_stage_response(
                assistant_message=prompt,
                stage=ConversationState.COLLECTING_RECEIPTS,
                next_action="collect_receipts",
                metadata={"stage": "COLLECTING_RECEIPTS", "current_slot": current_slot},
            )

        category = str(current_slot["category"])
        self.context.append_receipt_upload(category, metadata)
        next_slot = self.context.next_pending_receipt_slot()
        if next_slot is None:
            self.context.receipts_complete = True
            return self._continue_execution(
                prefix_message=(
                    f"{category} receipt uploaded successfully.\n"
                    "All required receipts have been uploaded.\n"
                    "Submitting your claim..."
                )
            )

        prompt = (
            f"{category} receipt uploaded successfully.\n\n"
            f"{self._receipt_prompt_for_slot(next_slot)}"
        )
        self.context.set_stage(ConversationState.COLLECTING_RECEIPTS)
        self.context.record_message("assistant", prompt)
        return self._build_stage_response(
            assistant_message=prompt,
            stage=ConversationState.COLLECTING_RECEIPTS,
            next_action="collect_receipts",
            metadata={"stage": "COLLECTING_RECEIPTS", "current_slot": next_slot},
        )

    def _pause_receipt_collection(self) -> dict[str, Any]:
        self.context.receipt_upload_paused = True
        self.context.set_stage(ConversationState.WAITING_USER)
        prompt = (
            "Receipt upload has been cancelled for now. Your draft claim is still available.\n\n"
            "Send RESUME or provide the next receipt file path when you want to continue."
        )
        self.context.record_message("assistant", prompt)
        return self._build_stage_response(
            assistant_message=prompt,
            stage=ConversationState.WAITING_USER,
            next_action="collect_receipts",
            metadata={"stage": "WAITING_RECEIPTS", "paused": True},
        )

    def _continue_execution(self, prefix_message: str | None = None) -> dict[str, Any]:
        execution_result: dict[str, Any] | None = None
        assistant_message: str | None = None
        plan = ExecutionPlan(pattern=ExecutionPattern.HUMAN_IN_THE_LOOP, next_action="execute")

        while True:
            plan = self.planner.plan(self.context)
            self.context.set_stage(ConversationState.EXECUTING)

            if plan.pattern == ExecutionPattern.HUMAN_IN_THE_LOOP:
                if plan.next_action == "collect_information":
                    return self._prompt_for_information(plan.prompt)
                if plan.next_action == "collect_expenses":
                    return self._start_expense_collection(plan.prompt)
                if self._needs_category_clarification():
                    return self._prompt_for_category_clarification()
                if plan.next_action == "await_confirmation":
                    assistant_message = self._hil.build_prompt(self.context)
                    self.context.set_stage(ConversationState.WAITING_USER)
                    plan = ExecutionPlan(
                        pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                        next_action="await_confirmation",
                        prompt=assistant_message,
                        metadata={"stage": "WAITING_CONFIRMATION"},
                    )
                    break
                if plan.next_action == "complete":
                    assistant_message = self._completion_message()
                    self.context.set_stage(ConversationState.COMPLETED)
                    break
                if plan.next_action == "cancel":
                    return self._cancel_conversation()
                assistant_message = plan.prompt or "I need a bit more information to continue."
                self.context.set_stage(ConversationState.WAITING_USER)
                break

            if plan.pattern == ExecutionPattern.SEQUENTIAL:
                try:
                    if plan.next_action == "employee_profile":
                        execution_result = self._sequential.execute_employee(self.context)
                    elif plan.next_action == "expense_preview":
                        execution_result = self._sequential.execute_expense_preview(self.context)
                        assistant_message = self._preview_message(execution_result)
                        self.context.set_stage(ConversationState.WAITING_USER)
                        plan = ExecutionPlan(
                            pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                            next_action="await_confirmation",
                            prompt=assistant_message,
                            metadata={"stage": "WAITING_CONFIRMATION"},
                        )
                        break
                    elif plan.next_action == "expense_submission":
                        execution_result = self._sequential.execute_expense_submission(self.context)
                    elif plan.next_action == "approval":
                        execution_result = self._sequential.execute_approval(self.context)
                    elif plan.next_action == "receipt":
                        execution_result = self._sequential.execute_receipt(self.context)
                        assistant_message = self._completion_message()
                        self.context.set_stage(ConversationState.COMPLETED)
                        break
                    else:
                        assistant_message = (
                            plan.prompt or "I need a bit more information to continue."
                        )
                        self.context.set_stage(ConversationState.WAITING_USER)
                        break
                except Exception as exc:
                    return self._handle_execution_exception(exc)

                self._record_execution(execution_result)
                continue

            if plan.pattern == ExecutionPattern.PARALLEL:
                try:
                    execution_result = self._parallel.execute(self.context)
                except Exception as exc:
                    return self._handle_execution_exception(exc)
                self._record_execution(execution_result)
                if self._needs_category_clarification():
                    return self._prompt_for_category_clarification()
                continue

            assistant_message = plan.prompt or "I need a bit more information to continue."
            self.context.set_stage(ConversationState.WAITING_USER)
            break

        assistant_message = assistant_message or self._completion_message()
        if prefix_message:
            assistant_message = f"{prefix_message}\n\n{assistant_message}"
        self.context.record_message("assistant", assistant_message)
        return self._build_response(
            assistant_message=assistant_message,
            plan=plan,
            execution_result=execution_result,
        )

    def _start_expense_collection(self, prompt: str | None = None) -> dict[str, Any]:
        if prompt is None:
            prompt = self._expense_collection_prompt()
        self.context.set_stage(ConversationState.COLLECTING_EXPENSES)
        self.context.record_message("assistant", prompt)
        return self._build_stage_response(
            assistant_message=prompt,
            stage=ConversationState.COLLECTING_EXPENSES,
            next_action="collect_expenses",
            metadata={"stage": "COLLECTING_EXPENSES"},
        )

    def _expense_collection_prompt(self) -> str:
        return (
            "Please list the expenses you incurred. "
            "After each expense, I'll ask if you want to add another expense. "
            "Type DONE if you have finished entering expenses."
        )

    def _expense_follow_up_prompt(self) -> str:
        return (
            "Do you want to add another expense? Type DONE if you have finished entering expenses."
        )

    def _prompt_for_information(self, prompt: str | None = None) -> dict[str, Any]:
        if prompt is None:
            prompt = self._missing_field_prompt()
        self.context.set_stage(ConversationState.WAITING_USER)
        self.context.record_message("assistant", prompt)
        return self._build_stage_response(
            assistant_message=prompt,
            stage=ConversationState.WAITING_USER,
            next_action="collect_information",
            metadata={
                "stage": "COLLECTING_INFORMATION",
                "missing_fields": self.context.missing_fields(self.REQUIRED_FIELDS),
            },
        )

    def _missing_field_prompt(self) -> str:
        missing_fields = self.context.missing_fields(self.REQUIRED_FIELDS)
        if not missing_fields:
            return "I need a bit more information to continue."

        from conversation.field_mappings import get_prompt_for_field

        prompt = get_prompt_for_field(missing_fields[0])
        return prompt or f"Please provide {missing_fields[0]}."

    def _cancel_conversation(self) -> dict[str, Any]:
        self.context.confirmation = False
        self.context.set_stage(ConversationState.CANCELLED)
        assistant_message = "Conversation cancelled. No claim was persisted."
        self.context.record_message("assistant", assistant_message)
        return self._build_stage_response(
            assistant_message=assistant_message,
            stage=ConversationState.CANCELLED,
            next_action="cancel",
            metadata={"reason": "user_cancelled"},
        )

    def _record_execution(self, execution_result: Mapping[str, Any] | None) -> None:
        if execution_result is None:
            return
        self.context.store_execution_result("last_execution", execution_result)

        employee_profile = execution_result.get("employee_profile")
        if isinstance(employee_profile, EmployeeProfile):
            self.context.employee_profile = employee_profile
            self.context.store_execution_result("employee_profile", employee_profile)

        policy_context = execution_result.get("policy_context")
        if isinstance(policy_context, PolicyContext):
            self.context.policy_context = policy_context
            self.context.store_execution_result("policy_context", policy_context)
            self.context.execution_results.pop("partial_policy_context", None)
            self.context.clear_category_clarifications()

        partial_policy_context = execution_result.get("partial_policy_context")
        if isinstance(partial_policy_context, PolicyContext):
            self.context.policy_context = None
            self.context.store_execution_result("partial_policy_context", partial_policy_context)

        category_clarifications = execution_result.get("category_clarifications")
        if isinstance(category_clarifications, list):
            self.context.set_category_clarifications(category_clarifications)

        claim_preview = execution_result.get("claim_preview")
        if claim_preview is not None:
            self.context.claim_preview = claim_preview

        submitted = execution_result.get("submitted_claim")
        if submitted is not None:
            self.context.store_execution_result("submitted_claim", submitted)
            if isinstance(submitted, Mapping):
                claim_id = submitted.get("claim_id")
                if isinstance(claim_id, str):
                    self.context.claim_id = claim_id

        approval_result = execution_result.get("approval_result")
        if approval_result is not None:
            self.context.store_execution_result("approval_result", approval_result)

        receipt_result = execution_result.get("receipt_result")
        if receipt_result is not None:
            self.context.store_execution_result("receipt_result", receipt_result)

    def _preview_message(self, result: Mapping[str, Any]) -> str:
        preview = self.context.claim_preview or result.get("claim_preview", {})
        claimed_amount = self._lookup(preview, "total_requested", "claimed_amount", default="N/A")
        approved_amount = self._lookup(preview, "total_approved", "approved_amount", default="N/A")
        variance = self._format_variance(claimed_amount, approved_amount)
        warnings = self._lookup(preview, "warnings", default=[])
        policy_limits = self._policy_limits_summary()
        warnings_text = self._format_warnings(warnings)
        return (
            "Claim Summary\n"
            f"Claimed Amount: {claimed_amount}\n"
            f"Approved Amount: {approved_amount}\n"
            f"Variance: {variance}\n"
            f"Warnings: {warnings_text}\n"
            f"Applied Policy Limits: {policy_limits}\n\n"
            "Do you want to submit?"
        )

    def _completion_message(self) -> str:
        return f"Claim submitted successfully. Claim ID: {self.context.claim_id or 'N/A'}"

    def _format_variance(self, claimed_amount: Any, approved_amount: Any) -> str:
        try:
            claimed = (
                claimed_amount
                if isinstance(claimed_amount, (int, float))
                else float(str(claimed_amount))
            )
            approved = (
                approved_amount
                if isinstance(approved_amount, (int, float))
                else float(str(approved_amount))
            )
            return f"{claimed - approved:.2f}"
        except (TypeError, ValueError):
            return "N/A"

    def _format_warnings(self, warnings: Any) -> str:
        if isinstance(warnings, list) and warnings:
            return "; ".join(str(item) for item in warnings)
        if warnings:
            return str(warnings)
        return "No warnings"

    def _policy_limits_summary(self) -> str:
        policy_context = self.context.policy_context
        if policy_context is None:
            return "No policy limits available"

        payload = (
            policy_context.model_dump()
            if hasattr(policy_context, "model_dump") and callable(policy_context.model_dump)
            else policy_context
        )
        categories = payload.get("categories", {}) if isinstance(payload, Mapping) else {}
        if not isinstance(categories, Mapping) or not categories:
            return "No policy limits available"

        parts: list[str] = []
        for category, details in categories.items():
            if hasattr(details, "model_dump") and callable(details.model_dump):
                details = details.model_dump()
            if not isinstance(details, Mapping):
                continue
            limits = details.get("limits", {})
            if hasattr(limits, "model_dump") and callable(limits.model_dump):
                limits = limits.model_dump()
            if isinstance(limits, Mapping) and limits:
                limit_bits = ", ".join(f"{key}={value}" for key, value in limits.items())
            else:
                limit_bits = "No limits available"
            parts.append(f"{category}: {limit_bits}")

        return "; ".join(parts) if parts else "No policy limits available"

    def _lookup(self, payload: Any, *keys: str, default: Any = None) -> Any:
        if hasattr(payload, "model_dump") and callable(payload.model_dump):
            payload = payload.model_dump()
        if isinstance(payload, Mapping):
            for key in keys:
                if key in payload:
                    return payload[key]
        return default

    def _needs_receipt_collection(self) -> bool:
        if self.context.confirmation is not True or self.context.claim_id is not None:
            return False
        required_slots = self._required_receipt_slots()
        if not required_slots:
            self.context.receipts_complete = True
            return False
        return not self.context.receipts_complete

    def _has_pending_receipt_collection(self) -> bool:
        if self.context.claim_id is not None or self.context.receipts_complete:
            return False
        return bool(self._required_receipt_slots())

    def _required_receipt_slots(self) -> list[dict[str, Any]]:
        return self.context.required_receipt_slots()

    def _receipt_collection_intro_prompt(self) -> str:
        categories = self.context.required_receipt_categories()
        current_slot = self.context.next_pending_receipt_slot()
        lines = [
            (
                "Before submitting your expense claim, receipts are required for the "
                "following expense categories:"
            ),
            "",
        ]
        lines.extend(f"{index}. {category}" for index, category in enumerate(categories, start=1))
        lines.extend(["", "Let's upload them one at a time."])
        if current_slot is not None:
            lines.extend(["", self._receipt_prompt_for_slot(current_slot)])
        return "\n".join(lines)

    def _receipt_prompt_for_slot(self, slot: Mapping[str, Any]) -> str:
        category = str(slot.get("category", "receipt")).upper()
        return f"Please provide the local file path for the {category} receipt."

    def _build_stage_response(
        self,
        *,
        assistant_message: str,
        stage: ConversationState,
        next_action: str,
        metadata: Mapping[str, Any] | None = None,
        execution_result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.context.set_stage(stage)
        plan = ExecutionPlan(
            pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
            next_action=next_action,
            prompt=assistant_message,
            metadata=dict(metadata or {}),
        )
        return self._build_response(
            assistant_message=assistant_message,
            plan=plan,
            execution_result=execution_result,
        )

    def _build_response(
        self,
        assistant_message: str,
        plan: ExecutionPlan,
        execution_result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "assistant_message": assistant_message,
            "state": self.context.execution_stage.value,
            "conversation_stage": self._response_state(plan),
            "plan": plan.to_dict(),
            "context": self.context.snapshot(),
            "execution_result": execution_result,
        }

    def _handle_execution_exception(self, exc: Exception) -> dict[str, Any]:
        if self._needs_category_clarification():
            return self._prompt_for_category_clarification()

        assistant_message = (
            "I couldn't continue with that expense entry yet. "
            "Please review the claim details and try again."
        )
        self.context.set_stage(ConversationState.WAITING_USER)
        self.context.record_message("assistant", assistant_message)
        return self._build_stage_response(
            assistant_message=assistant_message,
            stage=ConversationState.WAITING_USER,
            next_action="collect_information",
            metadata={
                "stage": "COLLECTING_INFORMATION",
                "error": str(exc),
            },
        )

    def _response_state(self, plan: ExecutionPlan) -> str:
        if self.context.execution_stage == ConversationState.COMPLETED:
            return ConversationState.COMPLETED.value
        if self.context.execution_stage == ConversationState.CANCELLED:
            return ConversationState.CANCELLED.value
        if self.context.execution_stage == ConversationState.EXECUTING:
            return ConversationState.EXECUTING.value
        if self.context.execution_stage == ConversationState.COLLECTING_EXPENSES:
            return ConversationState.COLLECTING_EXPENSES.value
        if self.context.execution_stage == ConversationState.COLLECTING_RECEIPTS:
            return "waiting_receipts"
        if self.context.has_pending_category_clarifications():
            return "waiting_category_clarification"
        if self.context.receipt_upload_paused and self._has_pending_receipt_collection():
            return "waiting_receipts"
        if self.context.claim_preview is not None and self.context.confirmation is None:
            return "waiting_confirmation"
        if self.context.missing_fields(self.REQUIRED_FIELDS):
            return "collecting_information"
        stage = plan.metadata.get("stage") if isinstance(plan.metadata, Mapping) else None
        if isinstance(stage, str):
            return stage.lower()
        return self.context.execution_stage.value


__all__ = ["ConversationOrchestrator"]
