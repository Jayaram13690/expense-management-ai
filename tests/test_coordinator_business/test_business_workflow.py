from coordinator.workflow import (
    APPROVE_CLAIM_WORKFLOW,
    PREVIEW_EXPENSE_CLAIM_WORKFLOW,
    SUBMIT_EXPENSE_CLAIM_WORKFLOW,
)


def test_submit_claim_business_stage_order():
    stages = [s.stage_name for s in SUBMIT_EXPENSE_CLAIM_WORKFLOW.steps]

    assert stages == [
        "employee_retrieval",
        "policy_retrieval",
        "expense_preview",
        "wait_confirmation",
        "expense_submission",
    ]


def test_submit_claim_agent_mapping():
    agents = [s.agent_name for s in SUBMIT_EXPENSE_CLAIM_WORKFLOW.steps]

    assert agents == [
        "EmployeeAgent",
        "PolicyAgent",
        "ExpenseAgent",
        None,
        "ExpenseAgent",
    ]


def test_expense_agent_used_twice():
    expense_steps = [
        s for s in SUBMIT_EXPENSE_CLAIM_WORKFLOW.steps if s.agent_name == "ExpenseAgent"
    ]

    assert len(expense_steps) == 2


def test_wait_confirmation_has_no_agent():
    wait_stage = next(
        s for s in SUBMIT_EXPENSE_CLAIM_WORKFLOW.steps if s.stage_name == "wait_confirmation"
    )

    assert wait_stage.agent_name is None
    assert wait_stage.requires_confirmation is True


def test_preview_contains_no_confirmation():
    stages = [s.stage_name for s in PREVIEW_EXPENSE_CLAIM_WORKFLOW.steps]

    assert "wait_confirmation" not in stages


def test_approval_workflow_contains_manager_stage():
    stages = [s.stage_name for s in APPROVE_CLAIM_WORKFLOW.steps]

    assert "manager_approval" in stages
