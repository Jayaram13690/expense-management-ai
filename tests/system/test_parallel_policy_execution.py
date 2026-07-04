from __future__ import annotations

from contracts import PolicyContext
from conversation.conversation_context import ConversationContext


def test_parallel_policy_execution_merges_results(live_system, claim_data):
    context = ConversationContext()
    context.apply_updates(claim_data)

    employee_stage = live_system.orchestrator._sequential.execute_employee(context)
    employee_profile = employee_stage["employee_profile"]

    assert employee_profile.employee_id == "EMP0006"
    assert employee_profile.employee_grade == "G5"
    assert employee_profile.department
    assert employee_profile.manager_id

    result = live_system.orchestrator._parallel.execute(context)

    assert result["stage_name"] == "POLICY"
    assert isinstance(result["policy_context"], PolicyContext)
    assert result["policy_context"].employee_grade == "G5"
    assert set(result["policy_context"].categories.keys()) == {"HOTEL", "TAXI"}
    assert result["policy_context"].categories["HOTEL"].eligible in {True, False}
    assert "limits" in result["policy_context"].categories["HOTEL"].model_dump()
    assert "daily_limit" in result["policy_context"].categories["HOTEL"].limits
    assert "daily_limit" in result["policy_context"].categories["TAXI"].limits
