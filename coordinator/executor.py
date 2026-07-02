"""
Workflow Executor.

This module implements the WorkflowExecutor that executes workflow definitions
by delegating to specialized agents. The executor contains only execution logic
without any decision-making or business logic.

Design Principles:
------------------
- Pure execution - no decision making
- Delegates to specialized agents only
- No business logic or domain knowledge
- No direct service/repository/tool access
- Supports SEQUENTIAL and PARALLEL execution modes
- Dependency-aware concurrent execution
- No tight coupling to specific agent implementations
"""

from __future__ import annotations

import concurrent.futures
import uuid
from typing import Any

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from coordinator.agent_request_builder import AgentRequestBuilder
from coordinator.decision import ExecutionMode
from coordinator.workflow import WorkflowDefinition, WorkflowStep, get_workflow_definition


class WorkflowExecutor:
    """
    Workflow Executor for executing workflow definitions.

    The WorkflowExecutor is responsible for executing workflow steps by delegating
    to the appropriate specialized agents. It contains only execution logic and
    does not perform any decision-making or business logic.

    Design Principles:
        - Pure execution - no decision making
        - Delegates to specialized agents only
        - No business logic or domain knowledge
        - No direct service/repository/tool access
        - Supports SEQUENTIAL execution mode

    Responsibilities:
        - Execute workflow steps in the specified order or concurrently
        - Delegate to appropriate specialized agents
        - Handle execution results and errors
        - Support multiple execution modes (sequential and parallel)
        - Manage dependency-aware concurrent execution
        - Pause workflows at confirmation points
        - Resume workflows from paused state

    Attributes:
        expense_agent: Reference to ExpenseAgent for expense operations
        employee_agent: Reference to EmployeeAgent for employee operations
        policy_agent: Reference to PolicyAgent for policy operations
        receipt_agent: Reference to ReceiptAgent for receipt operations
        approval_agent: Reference to ApprovalAgent for approval operations
        _workflow_contexts: In-memory storage for paused workflow execution contexts
    """

    def __init__(
        self,
        expense_agent: ExpenseAgent,
        employee_agent: EmployeeAgent,
        policy_agent: PolicyAgent,
        receipt_agent: ReceiptAgent,
        approval_agent: ApprovalAgent,
    ) -> None:
        """
        Initialize the WorkflowExecutor with all specialized agents.

        Args:
            expense_agent: ExpenseAgent instance for expense operations
            employee_agent: EmployeeAgent instance for employee operations
            policy_agent: PolicyAgent instance for policy operations
            receipt_agent: ReceiptAgent instance for receipt operations
            approval_agent: ApprovalAgent instance for approval operations

        Raises:
            ValueError: If any agent is None
        """
        if None in (expense_agent, employee_agent, policy_agent, receipt_agent, approval_agent):
            raise ValueError("All specialized agents must be provided")

        # Build agent registry dynamically using agent.agent_name
        self._agent_registry = {
            expense_agent.agent_name: expense_agent,
            employee_agent.agent_name: employee_agent,
            policy_agent.agent_name: policy_agent,
            receipt_agent.agent_name: receipt_agent,
            approval_agent.agent_name: approval_agent,
        }

        # Keep individual agent references for compatibility
        self.expense_agent = expense_agent
        self.employee_agent = employee_agent
        self.policy_agent = policy_agent
        self.receipt_agent = receipt_agent
        self.approval_agent = approval_agent

        # Initialize workflow context storage for pause/resume functionality
        self._workflow_contexts: dict[str, dict[str, Any]] = {}

    def execute_workflow(
        self,
        workflow_definition: WorkflowDefinition,
        execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        workflow_id: str = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute a workflow according to its definition.

        Args:
            workflow_definition: The workflow definition to execute
            execution_mode: The execution mode (SEQUENTIAL or PARALLEL)
            workflow_id: Optional workflow ID for resume operations
            **kwargs: Additional arguments to pass to workflow steps

        Returns:
            Dictionary containing execution results and metadata

        Raises:
            ValueError: If execution_mode is not supported
            RuntimeError: If workflow execution fails
        """
        # Validate execution mode
        if execution_mode not in (ExecutionMode.SEQUENTIAL, ExecutionMode.PARALLEL):
            raise ValueError(f"Unsupported execution mode: {execution_mode}")

        # Execute using the appropriate strategy
        if execution_mode == ExecutionMode.SEQUENTIAL:
            return self._execute_sequential(
                workflow_definition, workflow_id, execution_mode, **kwargs
            )
        else:
            # PARALLEL mode uses dependency-aware concurrent execution
            return self._execute_parallel(
                workflow_definition, workflow_id, execution_mode, **kwargs
            )

    def _execute_sequential(
        self,
        workflow_definition: WorkflowDefinition,
        workflow_id: str = None,
        execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute workflow stages sequentially.

        Args:
            workflow_definition: The workflow definition to execute
            workflow_id: Optional workflow ID for resume operations
            **kwargs: Additional arguments to pass to workflow stages

        Returns:
            Dictionary containing execution results

        Raises:
            RuntimeError: If any stage fails during execution
        """
        # Generate workflow ID if not provided (for new workflows)
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())

        results: dict[str, Any] = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_definition.workflow_type,
            "status": "started",
            "completed_stages": 0,
            "results": {},
        }

        # Check if we're resuming a paused workflow
        if workflow_id in self._workflow_contexts:
            # Resume from paused state
            context = self._workflow_contexts[workflow_id]
            results["completed_stages"] = context["completed_stages"]
            results["results"] = context["results"].copy()
            start_index = context["next_stage_index"]
        else:
            # Start from beginning
            start_index = 0

        try:
            # Execute stages starting from the appropriate index
            stages = list(workflow_definition.steps)
            for i in range(start_index, len(stages)):
                stage = stages[i]

                # Check if this is a confirmation stage that requires user input
                if stage.stage_name == "wait_confirmation" and stage.requires_confirmation:
                    # Pause workflow and return WAITING_FOR_CONFIRMATION status
                    results["status"] = "waiting_for_confirmation"
                    results["next_required_action"] = "CONFIRM"

                    # Store execution context for potential resume
                    self._workflow_contexts[workflow_id] = {
                        "workflow_type": workflow_definition.workflow_type,
                        "workflow_definition": workflow_definition,
                        "completed_stages": results["completed_stages"],
                        "results": results["results"].copy(),
                        "next_stage_index": i,  # Next stage to execute when resumed
                        "kwargs": kwargs,
                        "execution_mode": execution_mode,  # Persist execution mode
                    }

                    return results

                # Execute the stage and get the raw agent result (or None for non-agent stages)
                stage_result = self._execute_step(
                    stage,
                    workflow_context=kwargs,
                    previous_results=results.get("results", {}),
                )

                # Store the stage result
                results["results"][stage.stage_name] = stage_result
                results["completed_stages"] += 1

            # Clean up context if workflow completed successfully
            if workflow_id in self._workflow_contexts:
                del self._workflow_contexts[workflow_id]

            results["status"] = "completed"

        except Exception as e:
            results["status"] = "failed"
            # Clean up context on failure
            if workflow_id in self._workflow_contexts:
                del self._workflow_contexts[workflow_id]
            # Propagate the exception with minimal context
            raise RuntimeError(
                f"Workflow execution failed during stage '{stage.stage_name}': {e}"
            ) from e

        return results

    def _execute_step(
        self,
        step: WorkflowStep,
        workflow_context: dict[str, Any],
        previous_results: dict[str, Any],
    ) -> Any | None:
        """
        Execute a single workflow stage by delegating to the appropriate agent.

        Args:
            step:
            The workflow stage to execute
            workflow_context: Current workflow execution context
            previous_results: Results from previous workflow stages
            **kwargs: Additional arguments to pass to the agent

        Returns:
            The raw result from the agent invocation, or None if no agent is assigned

        Raises:
            RuntimeError: If the stage has an agent but it cannot be resolved
            Exception: Any exceptions from agent execution (propagated)
        """
        # Check if this stage has an assigned agent
        if step.agent_name is None:
            # This is a stage without an agent (e.g., wait_confirmation)
            # Skip execution for now - implementation will come in later prompts
            return None

        # Resolve the agent from the registry
        agent = self._agent_registry.get(step.agent_name)

        if agent is None:
            raise RuntimeError(f"No agent found for stage '{step.stage_name}': {step.agent_name}")

        # Build runtime business request using AgentRequestBuilder
        request = AgentRequestBuilder.build(
            workflow_step=step,
            workflow_context=workflow_context,
            previous_results=previous_results,
        )

        # Invoke the agent with the runtime business request
        # Let the agent handle its own execution and return its raw result
        return agent.invoke(request)

    def _get_agent_method(self, agent_name: str) -> Any:
        """
        Get the appropriate agent from the registry for the specified agent name.

        Args:
            agent_name: Name of the agent to retrieve

        Returns:
            The agent instance or None if not found
        """
        return self._agent_registry.get(agent_name)

    def resume_workflow(
        self,
        workflow_id: str,
        employee_decision: bool,
        execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    ) -> dict[str, Any]:
        """
        Resume a paused workflow from a confirmation point.

        Args:
            workflow_id: The ID of the paused workflow to resume
            employee_decision: True to continue, False to cancel
            execution_mode: The execution mode to use for resuming

        Returns:
            Dictionary containing workflow execution results

        Raises:
            ValueError: If workflow_id is not found or workflow is not paused
            RuntimeError: If workflow execution fails
        """
        # Check if workflow context exists
        if workflow_id not in self._workflow_contexts:
            raise ValueError(f"No paused workflow found with ID: {workflow_id}")

        context = self._workflow_contexts[workflow_id]

        if employee_decision:
            # Continue workflow execution
            # Use the stored workflow definition instead of looking it up again
            workflow_definition = context.get("workflow_definition")
            if workflow_definition is None:
                # Fallback to lookup if not stored (shouldn't happen)
                workflow_definition = get_workflow_definition(context["workflow_type"])

            # When resuming, skip confirmation and start from next stage
            next_stage_index = context["next_stage_index"] + 1

            # Update context for resume
            context["next_stage_index"] = next_stage_index

            # Use the persisted execution mode instead of the parameter
            persisted_execution_mode = context.get("execution_mode", ExecutionMode.SEQUENTIAL)

            # Resume execution from where it was paused using the original execution mode
            if persisted_execution_mode == ExecutionMode.SEQUENTIAL:
                return self._execute_sequential(
                    workflow_definition=workflow_definition,
                    workflow_id=workflow_id,
                    **context["kwargs"],
                )
            else:
                return self._execute_parallel(
                    workflow_definition=workflow_definition,
                    workflow_id=workflow_id,
                    **context["kwargs"],
                )
        else:
            # Cancel the workflow
            del self._workflow_contexts[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": "cancelled",
                "message": "Workflow cancelled by employee",
            }

    def _execute_parallel(
        self,
        workflow_definition: WorkflowDefinition,
        workflow_id: str = None,
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute workflow steps concurrently with dependency-aware scheduling.

        This method implements true dependency-aware concurrent execution using
        ThreadPoolExecutor. Independent stages execute concurrently, while dependent
        stages wait until their dependencies complete.

        Args:
            workflow_definition: The workflow definition to execute
            workflow_id: Optional workflow ID for resume operations
            **kwargs: Additional arguments to pass to workflow steps

        Returns:
            Dictionary containing execution results and metadata

        Raises:
            RuntimeError: If any stage fails during execution
        """
        # Generate workflow ID if not provided (for new workflows)
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())

        results: dict[str, Any] = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_definition.workflow_type,
            "status": "started",
            "completed_stages": 0,
            "results": {},
        }

        # Check if we're resuming a paused workflow
        if workflow_id in self._workflow_contexts:
            # Resume from paused state
            context = self._workflow_contexts[workflow_id]
            results["completed_stages"] = context["completed_stages"]
            results["results"] = context["results"].copy()
            completed_stages = set(context["completed_stages_list"])
        else:
            # Start from beginning
            completed_stages = set()

        try:
            # Execute workflow in dependency levels
            while len(completed_stages) < len(workflow_definition.steps):
                # Find all stages whose dependencies are satisfied
                ready_stages = []
                for stage in workflow_definition.steps:
                    if stage.stage_name in completed_stages:
                        continue  # Already completed

                    # Check if all dependencies are satisfied
                    dependencies_satisfied = all(
                        dep in completed_stages for dep in stage.depends_on
                    )

                    if dependencies_satisfied:
                        ready_stages.append(stage)

                if not ready_stages:
                    # No stages ready to execute - circular dependency or invalid workflow
                    raise RuntimeError("Circular dependency detected or invalid workflow structure")

                # Check if any ready stage is a confirmation stage that requires user input
                for stage in ready_stages:
                    if stage.stage_name == "wait_confirmation" and stage.requires_confirmation:
                        # Pause workflow and return WAITING_FOR_CONFIRMATION status
                        results["status"] = "waiting_for_confirmation"
                        results["next_required_action"] = "CONFIRM"

                        # Store execution context for potential resume
                        self._workflow_contexts[workflow_id] = {
                            "workflow_type": workflow_definition.workflow_type,
                            "workflow_definition": workflow_definition,
                            "completed_stages": results["completed_stages"],
                            "completed_stages_list": list(completed_stages),
                            "results": results["results"].copy(),
                            "kwargs": kwargs,
                            "execution_mode": execution_mode,  # Persist execution mode
                        }

                        return results

                # Execute ready stages concurrently using ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Create a future for each ready stage
                    future_to_stage = {
                        executor.submit(
                            self._execute_step,
                            stage,
                            workflow_context=kwargs,
                            previous_results=results.get("results", {}),
                        ): stage
                        for stage in ready_stages
                    }

                    # Process completed futures as they complete
                    for future in concurrent.futures.as_completed(future_to_stage):
                        stage = future_to_stage[future]
                        try:
                            stage_result = future.result()

                            # Store the stage result
                            results["results"][stage.stage_name] = stage_result
                            results["completed_stages"] += 1

                            # Mark stage as completed
                            completed_stages.add(stage.stage_name)

                        except Exception as e:
                            # If any stage fails, stop the workflow immediately
                            results["status"] = "failed"
                            raise RuntimeError(
                                f"Workflow execution failed during stage '{stage.stage_name}': {e}"
                            ) from e

            # Clean up context if workflow completed successfully
            if workflow_id in self._workflow_contexts:
                del self._workflow_contexts[workflow_id]

            results["status"] = "completed"

        except Exception as e:
            results["status"] = "failed"
            # Clean up context on failure
            if workflow_id in self._workflow_contexts:
                del self._workflow_contexts[workflow_id]
            # Propagate the exception with minimal context
            raise RuntimeError(f"Workflow execution failed: {e}") from e

        return results


__all__ = ["WorkflowExecutor"]
