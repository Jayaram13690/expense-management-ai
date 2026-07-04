from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
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
        if None in (
            employee_agent,
            expense_agent,
            policy_agent,
            approval_agent,
            receipt_agent,
        ):
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

        confirmation = self._hil.interpret(message)
        if confirmation is not None and self.context.claim_preview is not None:
            self.context.confirmation = confirmation

        if self.context.execution_stage == ConversationState.COLLECTING_EXPENSES:
            return self._handle_expense_collection_turn(message, extracted_data)

        updates = self._collect_updates(message, extracted_data)
        if updates:
            self.context.apply_updates(updates)

        if self.context.confirmation is False:
            return self._cancel_conversation()

        if self.context.missing_fields(self.REQUIRED_FIELDS) and self.context.confirmation is None:
            return self._prompt_for_information()

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
                if plan.next_action == "await_confirmation":
                    assistant_message = self._hil.build_prompt(self.context)
                    self.context.set_stage(ConversationState.WAITING_USER)
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
                if plan.next_action == "employee_profile":
                    execution_result = self._sequential.execute_employee(self.context)
                elif plan.next_action == "expense_preview":
                    execution_result = self._sequential.execute_expense_preview(self.context)
                    assistant_message = self._preview_message(execution_result)
                    self.context.set_stage(ConversationState.WAITING_USER)
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
                    assistant_message = plan.prompt or "I need a bit more information to continue."
                    self.context.set_stage(ConversationState.WAITING_USER)
                    break
                self._record_execution(execution_result)
                continue

            if plan.pattern == ExecutionPattern.PARALLEL:
                execution_result = self._parallel.execute(self.context)
                self._record_execution(execution_result)
                continue

            assistant_message = plan.prompt or "I need a bit more information to continue."
            self.context.set_stage(ConversationState.WAITING_USER)
            break

        assistant_message = assistant_message or self._completion_message()
        self.context.record_message("assistant", assistant_message)
        return self._build_response(
            assistant_message=assistant_message,
            plan=plan,
            execution_result=execution_result,
        )

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
            return self._build_response(
                assistant_message=prompt,
                plan=ExecutionPlan(
                    pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                    next_action="collect_expenses",
                    prompt=prompt,
                    metadata={"stage": "COLLECTING_EXPENSES", "missing_fields": ["expense_items"]},
                ),
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
        prompt = self._expense_follow_up_prompt()
        self.context.record_message("assistant", prompt)
        return self._build_response(
            assistant_message=prompt,
            plan=ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="collect_expenses",
                prompt=prompt,
                metadata={"stage": "COLLECTING_EXPENSES"},
            ),
        )

    def _resume_after_expense_collection(
        self, extracted_data: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        updates = self._collect_updates("", extracted_data)
        if updates:
            self.context.apply_updates(updates)

        execution_result: dict[str, Any] | None = None
        assistant_message: str | None = None
        plan = ExecutionPlan(pattern=ExecutionPattern.HUMAN_IN_THE_LOOP, next_action="execute")

        while True:
            plan = self.planner.plan(self.context)
            self.context.set_stage(ConversationState.EXECUTING)

            if plan.pattern == ExecutionPattern.SEQUENTIAL:
                if plan.next_action == "employee_profile":
                    execution_result = self._sequential.execute_employee(self.context)
                elif plan.next_action == "expense_preview":
                    execution_result = self._sequential.execute_expense_preview(self.context)
                    assistant_message = self._preview_message(execution_result)
                    self.context.set_stage(ConversationState.WAITING_USER)
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
                    assistant_message = plan.prompt or "I need a bit more information to continue."
                    self.context.set_stage(ConversationState.WAITING_USER)
                    break
                self._record_execution(execution_result)
                continue

            if plan.pattern == ExecutionPattern.PARALLEL:
                execution_result = self._parallel.execute(self.context)
                self._record_execution(execution_result)
                continue

            if plan.pattern == ExecutionPattern.HUMAN_IN_THE_LOOP:
                if plan.next_action == "await_confirmation":
                    assistant_message = self._hil.build_prompt(self.context)
                    self.context.set_stage(ConversationState.WAITING_USER)
                    break
                if plan.next_action == "complete":
                    assistant_message = self._completion_message()
                    self.context.set_stage(ConversationState.COMPLETED)
                    break
                if plan.next_action == "collect_expenses":
                    assistant_message = self._expense_collection_prompt()
                    self.context.set_stage(ConversationState.COLLECTING_EXPENSES)
                    break
                if plan.next_action == "cancel":
                    return self._cancel_conversation()

            assistant_message = plan.prompt or "I need a bit more information to continue."
            self.context.set_stage(ConversationState.WAITING_USER)
            break

        assistant_message = assistant_message or self._completion_message()
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
        return self._build_response(
            assistant_message=prompt,
            plan=ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="collect_expenses",
                prompt=prompt,
                metadata={"stage": "COLLECTING_EXPENSES"},
            ),
        )

    def _expense_collection_prompt(self) -> str:
        return (
            "Please list the expenses you incurred. "
            "After each expense, I?ll ask if you want to add another expense. "
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
        return self._build_response(
            assistant_message=prompt,
            plan=ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="collect_information",
                prompt=prompt,
                metadata={"missing_fields": self.context.missing_fields(self.REQUIRED_FIELDS)},
            ),
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
        return self._build_response(
            assistant_message=assistant_message,
            plan=ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="cancel",
                metadata={"reason": "user_cancelled"},
            ),
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

    def _build_response(
        self,
        assistant_message: str,
        plan: ExecutionPlan,
        execution_result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "assistant_message": assistant_message,
            "state": self.context.execution_stage.value,
            "plan": plan.to_dict(),
            "context": self.context.snapshot(),
            "execution_result": execution_result,
        }


__all__ = ["ConversationOrchestrator"]
