import json

from evaluations.runners.agentcore_runner import AgentCoreRuntimeRunner
from evaluations.runners.conversation_runner import ConversationRunner


class DummyCase:
    def __init__(self, input, metadata):
        self.input = input
        self.metadata = metadata


def main():
    runner = AgentCoreRuntimeRunner()
    conv_runner = ConversationRunner(runner)

    with open("evaluations/datasets/duplicate_detection.json") as f:
        data = json.load(f)[0]

    case = DummyCase(
        data["initial_user_message"],
        {"simulation": data["simulation"], "expected_outcome": data["expected_outcome"]},
    )

    res = conv_runner.run_workflow(case)
    for m in res["transcript"]:
        print(f"{m['role']}: {m['message']}")


if __name__ == "__main__":
    main()
