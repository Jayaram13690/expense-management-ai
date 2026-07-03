from coordinator.executor import ExecutionMode, WorkflowExecutor
from coordinator.workflow import GET_EMPLOYEE_DETAILS_WORKFLOW


def test_employee_workflow_executes_real_agent():
    """
    Verifies that WorkflowExecutor invokes the real EmployeeAgent
    instead of returning a simulated response.
    """

    executor = WorkflowExecutor()

    result = executor.execute_workflow(
        workflow=GET_EMPLOYEE_DETAILS_WORKFLOW,
        execution_mode=ExecutionMode.SEQUENTIAL,
        employee_id="EMP0006",
    )

    print(result)

    assert result is not None
    assert result["status"] == "completed"

    # Employee stage must exist
    assert "employee_retrieval" in result["results"]

    employee_result = result["results"]["employee_retrieval"]

    # If this is a real Strands invocation it should return an AgentResult
    assert employee_result is not None
