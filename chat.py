from __future__ import annotations

import json
from decimal import Decimal

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
        break

    request = {
        "message": user_input,
    }

    try:
        kwargs = {
            "agentRuntimeArn": RUNTIME_ARN,
            "contentType": "application/json",
            "accept": "application/json",
            "payload": json.dumps(request).encode(),
        }

        if runtime_session_id:
            kwargs["runtimeSessionId"] = runtime_session_id

        response = client.invoke_agent_runtime(**kwargs)

    except ClientError as e:
        print("\nERROR")
        print(e)
        continue

    runtime_session_id = response["runtimeSessionId"]

    body = response["response"].read().decode()

    try:
        result = json.loads(body)
    except Exception:
        print("\nAssistant:")
        print(body)
        continue

    print(f"\nSession: {runtime_session_id}")

    #
    # Your runtime currently returns:
    #
    # {
    #   "response": "{...json...}"
    # }
    #

    if isinstance(result, dict) and "response" in result:
        try:
            nested = json.loads(result["response"])

            print("\nAssistant:")

            # Check if this is a claim preview response
            if "claim_preview" in nested:
                print("\n" + "=" * 70)
                print("CLAIM PREVIEW SUMMARY")
                print("=" * 70)

                preview = nested["claim_preview"]

                # Display employee info
                print(f"\nEmployee: {preview['employee_name']} ({preview['employee_id']})")
                print(f"Grade: {preview['employee_grade']}")

                # Display totals
                print("\nFinancial Summary:")
                print(f"  Total Requested: INR {preview['total_requested']}")
                print(f"  Total Approved: INR {preview['total_approved']}")
                variance = Decimal(preview["total_requested"]) - Decimal(preview["total_approved"])
                print(f"  Variance: INR {variance}")

                # Display items
                print(f"\nExpense Items ({len(preview['items'])}):")
                for i, item in enumerate(preview["items"], 1):
                    print(f"\n  {i}. {item['category']}:")
                    print(f"     Requested: INR {item['requested_amount']}")
                    print(f"     Approved: INR {item['approved_amount']}")
                    print(f"     Status: {item['status']}")
                    if item["reason"]:
                        print(f"     Reason: {item['reason']}")
                    print(f"     Receipt Required: {'Yes' if item['receipt_required'] else 'No'}")
                    print(f"     Approval Required: {'Yes' if item['approval_required'] else 'No'}")

                # Display warnings
                if preview["warnings"]:
                    print("\nWarnings:")
                    for warning in preview["warnings"]:
                        print(f"  • {warning}")

                print("\n" + "=" * 70)

            # Also print the assistant message
            if "assistant_message" in nested:
                print(f"\n{nested['assistant_message']}")

        except Exception:
            print("\nAssistant:")
            print(result["response"])

    elif isinstance(result, dict):
        if "assistant_message" in result:
            print("\nAssistant:")
            print(result["assistant_message"])
        else:
            print(json.dumps(result, indent=2))

    else:
        print(result)
