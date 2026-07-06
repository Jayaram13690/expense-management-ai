from __future__ import annotations

import json

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"

RUNTIME_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:042989515908:runtime/expensemanagementai-ftUjYU5lAr"
)

client = boto3.client(
    "bedrock-agentcore",
    region_name=REGION,
)

runtime_session_id = None

print("=" * 70)
print("Expense Management AI")
print("Type 'exit' to quit.")
print("=" * 70)

while True:
    user_input = input("\nYou: ").strip()

    if not user_input:
        continue

    if user_input.lower() in ("exit", "quit"):
        print("\nGoodbye!")
        break

    request = {"message": user_input}

    kwargs = {
        "agentRuntimeArn": RUNTIME_ARN,
        "contentType": "application/json",
        "accept": "application/json",
        "payload": json.dumps(request).encode(),
    }

    #
    # Continue the existing conversation
    #
    if runtime_session_id:
        kwargs["runtimeSessionId"] = runtime_session_id

    try:
        response = client.invoke_agent_runtime(**kwargs)

    except ClientError as e:
        print("\nERROR")
        print(e)
        continue

    #
    # Save runtime session
    #
    runtime_session_id = response["runtimeSessionId"]

    body = response["response"].read().decode()

    assistant_message = None

    try:
        result = json.loads(body)

        #
        # Runtime now returns
        #
        # {
        #     "assistant_message": "...",
        #     "conversation_stage": "...",
        #     "session_id": "..."
        # }
        #
        if isinstance(result, dict):
            assistant_message = result.get("assistant_message")

            #
            # Optional values if you later expose them
            #
            conversation_stage = result.get("conversation_stage")

            if conversation_stage:
                print(f"\nStage: {conversation_stage}")

        elif isinstance(result, str):
            assistant_message = result

    except Exception:
        assistant_message = body

    if not assistant_message:
        assistant_message = "No response received."

    print(f"\nSession: {runtime_session_id}")

    print("\nAssistant")
    print("-" * 70)
    print(assistant_message)
    print("-" * 70)
