import time
from dataclasses import dataclass


@dataclass
class RuntimeScenario:
    name: str
    query: str
    expected_tool: str


def run_scenario(agent, scenario):

    print("=" * 80)
    print(f"Scenario : {scenario.name}")
    print("=" * 80)

    print(f"\nQuery:\n{scenario.query}\n")
    print(f"Expected Tool : {scenario.expected_tool}\n")

    start = time.perf_counter()

    try:
        response = agent.invoke(scenario.query)

        elapsed = time.perf_counter() - start

        print("\nPASS")
        print(f"Execution Time : {elapsed:.2f}s")
        print("\nResponse\n")
        print(response)

    except Exception as ex:
        elapsed = time.perf_counter() - start

        print("\nFAIL")
        print(f"Execution Time : {elapsed:.2f}s")
        print(ex)

    print()
