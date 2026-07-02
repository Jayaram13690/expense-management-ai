"""
Coordinator Layer Package.

This package provides the Coordinator infrastructure for the Enterprise AI Travel
Expense Management System. The Coordinator serves as the single entry point
into the application, responsible for orchestrating specialized agents and
managing workflow execution.

Design Principles:
------------------
- Single entry point for all user interactions
- No business logic - pure orchestration
- No direct service/repository/tool access
- Uses only specialized agents and conversation layer
- Infrastructure only - workflow execution comes in later phases
- Clean separation of concerns
"""

from coordinator.builders import CoordinatorRequestBuilder
from coordinator.conversation import ConversationManager
from coordinator.coordinator import Coordinator
from coordinator.decision import Decision, DecisionEngine, DecisionType, ExecutionMode
from coordinator.executor import WorkflowExecutor
from coordinator.state import WorkflowState
from coordinator.workflow import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowType,
    get_workflow_definition,
)

__all__ = [
    "Coordinator",
    "WorkflowState",
    "CoordinatorRequestBuilder",
    "ConversationManager",
    "Decision",
    "DecisionEngine",
    "DecisionType",
    "ExecutionMode",
    "WorkflowExecutor",
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowType",
    "get_workflow_definition",
]
