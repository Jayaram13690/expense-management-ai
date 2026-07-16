from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from contracts import EmployeeProfile, PolicyContext
from conversation.conversation_context import ConversationContext
from conversation.execution_plan import ExecutionPattern, ExecutionPlan


class ExecutionPlanner:
    """Return a structured execution plan from structured conversation context."""

    def __init__(
        self,
        decision_source: (
            Callable[[dict[str, Any]], Mapping[str, Any] | ExecutionPlan] | None
        ) = None,
    ) -> None:
        self._decision_source = decision_source

    def plan(self, context: ConversationContext) -> ExecutionPlan:
        """Plan the next orchestration step from context only."""

        if self._decision_source is not None:
            source_result = self._decision_source(context.snapshot())
            return self._coerce_plan(source_result)

        return self._default_plan(context)

    def _default_plan(self, context: ConversationContext) -> ExecutionPlan:
        non_expense_required_fields = (
            "employee_id",
            "trip_name",
            "business_purpose",
            "destination",
            "trip_start_date",
            "trip_end_date",
        )
        missing_fields = context.missing_fields(non_expense_required_fields)

        if context.confirmation is False:
            return ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="cancel",
                metadata={"stage": "CONFIRMATION", "reason": "user_cancelled"},
            )

        if missing_fields:
            return ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="collect_information",
                prompt=self._prompt_for_missing_field(missing_fields[0]),
                metadata={"stage": "ACTIVE", "missing_fields": missing_fields},
            )

        if not context.expense_collection_complete:
            return ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="collect_expenses",
                prompt=self._prompt_for_expense_collection(),
                metadata={"stage": "COLLECTING_EXPENSES", "tasks": ["collect_expenses"]},
            )

        employee_profile = self._employee_profile(context)
        if employee_profile is None:
            return ExecutionPlan(
                pattern=ExecutionPattern.SEQUENTIAL,
                next_action="employee_profile",
                metadata={"stage": "EMPLOYEE", "tasks": ["employee_profile"]},
            )

        policy_context = self._policy_context(context)
        if policy_context is None:
            return ExecutionPlan(
                pattern=ExecutionPattern.PARALLEL,
                parallel_tasks=("check_employee_eligibility", "get_category_limits"),
                next_action="policy_context",
                metadata={
                    "stage": "POLICY",
                    "tasks": ["check_employee_eligibility", "get_category_limits"],
                },
            )

        if context.claim_preview is None:
            return ExecutionPlan(
                pattern=ExecutionPattern.SEQUENTIAL,
                next_action="expense_preview",
                metadata={"stage": "PREVIEW", "tasks": ["expense_preview"]},
            )

        # Allowance Validation — runs once after preview, before HIL confirmation
        if context.execution_results.get("allowance_validation_results") is None:
            return ExecutionPlan(
                pattern=ExecutionPattern.SEQUENTIAL,
                next_action="allowance_validation",
                metadata={
                    "stage": "ALLOWANCE_VALIDATION",
                    "tasks": ["allowance_validation"],
                },
            )

        if context.confirmation is None:
            return ExecutionPlan(
                pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
                next_action="await_confirmation",
                prompt="Do you want to submit?",
                metadata={"stage": "CONFIRMATION"},
            )

        if context.confirmation is True and not context.claim_id:
            return ExecutionPlan(
                pattern=ExecutionPattern.SEQUENTIAL,
                next_action="expense_submission",
                metadata={"stage": "SUBMISSION", "tasks": ["expense_submission"]},
            )

        if context.claim_id and context.execution_results.get("approval_result") is None:
            return ExecutionPlan(
                pattern=ExecutionPattern.SEQUENTIAL,
                next_action="approval",
                metadata={"stage": "APPROVAL", "tasks": ["approval"]},
            )

        if (
            context.execution_results.get("approval_result")
            and context.execution_results.get("receipt_result") is None
        ):
            return ExecutionPlan(
                pattern=ExecutionPattern.SEQUENTIAL,
                next_action="receipt",
                metadata={"stage": "RECEIPT", "tasks": ["receipt"]},
            )

        return ExecutionPlan(
            pattern=ExecutionPattern.HUMAN_IN_THE_LOOP,
            next_action="complete",
            metadata={"stage": "COMPLETED"},
        )

    def _employee_profile(self, context: ConversationContext) -> EmployeeProfile | None:
        employee_profile = context.employee_profile or context.get_execution_result(
            "employee_profile"
        )
        if isinstance(employee_profile, EmployeeProfile):
            return employee_profile
        return None

    def _policy_context(self, context: ConversationContext) -> PolicyContext | None:
        policy_context = context.policy_context or context.get_execution_result("policy_context")
        if isinstance(policy_context, PolicyContext):
            return policy_context
        return None

    def _prompt_for_missing_field(self, field_name: str) -> str | None:
        from conversation.field_mappings import get_prompt_for_field

        return get_prompt_for_field(field_name)

    def _prompt_for_expense_collection(self) -> str:
        from conversation.field_mappings import get_prompt_for_field

        return get_prompt_for_field("expense_items") or "Please list the expenses you incurred."

    def _coerce_plan(self, source_result: Mapping[str, Any] | ExecutionPlan) -> ExecutionPlan:
        if isinstance(source_result, ExecutionPlan):
            return source_result

        pattern_value = source_result.get("pattern", ExecutionPattern.SEQUENTIAL.value)
        pattern = ExecutionPattern(pattern_value)
        parallel_tasks = tuple(source_result.get("parallel_tasks", ()))
        next_action = str(source_result.get("next_action", "execute"))
        prompt = source_result.get("prompt")
        metadata = dict(source_result.get("metadata", {}))

        stage = source_result.get("stage")
        if isinstance(stage, str) and "stage" not in metadata:
            metadata["stage"] = stage

        tasks = source_result.get("tasks")
        if isinstance(tasks, list) and "tasks" not in metadata:
            metadata["tasks"] = tasks

        return ExecutionPlan(
            pattern=pattern,
            parallel_tasks=parallel_tasks,
            next_action=next_action,
            prompt=prompt if prompt is None or isinstance(prompt, str) else str(prompt),
            metadata=metadata,
        )


__all__ = ["ExecutionPlanner"]
