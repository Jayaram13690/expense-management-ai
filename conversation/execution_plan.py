from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ExecutionPattern(StrEnum):
    """Supported orchestration execution patterns."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"


@dataclass(frozen=True)
class ExecutionPlan:
    """Structured execution plan returned by the planner."""

    pattern: ExecutionPattern
    parallel_tasks: tuple[str, ...] = ()
    next_action: str = "execute"
    prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "pattern": self.pattern.value,
            "parallel_tasks": list(self.parallel_tasks),
            "next_action": self.next_action,
            "prompt": self.prompt,
            "metadata": self.metadata,
        }
        stage = self.metadata.get("stage")
        if isinstance(stage, str):
            payload["stage"] = stage
        tasks = self.metadata.get("tasks")
        if isinstance(tasks, list):
            payload["tasks"] = tasks
        return payload


__all__ = ["ExecutionPattern", "ExecutionPlan"]
