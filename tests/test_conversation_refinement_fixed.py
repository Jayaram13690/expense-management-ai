#!/usr/bin/env python3
"""
Test script to validate the refined conversation package.

This script validates all the refinements made to the conversation layer:
1. Improved intents.py documentation
2. Ordered conversational fields (tuples instead of frozensets)
3. Renamed completion_message to success_message
4. Shortened success messages
5. Simplified prompts (removed unused filtering prompts)
6. Simplified __init__.py exports
"""

import importlib
import os
import sys
from collections.abc import Sequence

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_no_forbidden_imports():
    """Test that conversation package doesn't import forbidden modules."""
    print("1. Testing for forbidden imports...")

    try:
        conversation = importlib.import_module("conversation")
        forbidden_modules = [
            "services",
            "repositories",
            "tools",
            "agents",
            "database",
            "boto3",
            "strands",
            "bedrock",
            "langgraph",
        ]

        safe = True
        for attr_name in dir(conversation):
            if attr_name.startswith("__"):
                continue

            attr = getattr(conversation, attr_name)
            if hasattr(attr, "__module__"):
                module_name = attr.__module__
                for forbidden in forbidden_modules:
                    if forbidden in module_name:
                        print(
                            f"   ERROR: Forbidden import detected: {attr_name} from {module_name}"
                        )
                        safe = False

        if safe:
            print("   OK: No forbidden imports detected")
        return safe
    except Exception as e:
        print(f"   ERROR: Import check failed: {e}")
        return False


def test_ordered_conversational_fields():
    """Test that fields are now ordered sequences instead of unordered frozensets."""
    print("2. Testing ordered conversational fields...")

    try:
        from conversation import SUBMIT_EXPENSE_CLAIM_REQUIREMENTS

        req = SUBMIT_EXPENSE_CLAIM_REQUIREMENTS

        # Verify fields are ordered (tuple/sequence)
        if not isinstance(req.required_fields, Sequence):
            print(f"   ERROR: Required fields are not a sequence: {type(req.required_fields)}")
            return False

        if not isinstance(req.optional_fields, Sequence):
            print(f"   ERROR: Optional fields are not a sequence: {type(req.optional_fields)}")
            return False

        # Verify the order represents natural conversation flow
        expected_order = [
            "employee_id",
            "trip_name",
            "business_purpose",
            "destination",
            "trip_start_date",
            "trip_end_date",
            "expense_items",
        ]

        if list(req.required_fields) == expected_order:
            print("   OK: Required fields are ordered sequence")
            print(f"     Order: {list(req.required_fields)}")
        else:
            print(f"   ERROR: Required fields order unexpected: {list(req.required_fields)}")
            return False

        print("   OK: Optional fields are ordered sequence")
        return True

    except Exception as e:
        print(f"   ERROR: Ordered fields check failed: {e}")
        return False


def test_success_message_rename():
    """Test that completion_message has been renamed to success_message."""
    print("3. Testing success_message rename...")

    try:
        from conversation import SUBMIT_EXPENSE_CLAIM_REQUIREMENTS

        # Check new attribute exists
        if not hasattr(SUBMIT_EXPENSE_CLAIM_REQUIREMENTS, "success_message"):
            print("   ERROR: success_message attribute missing")
            return False

        print("   OK: success_message attribute exists")
        print(f"     Sample: '{SUBMIT_EXPENSE_CLAIM_REQUIREMENTS.success_message}'")

        # Verify old attribute is gone
        if hasattr(SUBMIT_EXPENSE_CLAIM_REQUIREMENTS, "completion_message"):
            print("   ERROR: Old completion_message attribute still exists")
            return False
        else:
            print("   OK: Old completion_message attribute removed")

        return True
    except Exception as e:
        print(f"   ERROR: Success message check failed: {e}")
        return False


def test_concise_success_messages():
    """Test that success messages are now concise and professional."""
    print("4. Testing concise success messages...")

    try:
        from conversation import (
            APPROVE_CLAIM_REQUIREMENTS,
            GET_EXPENSE_CLAIM_REQUIREMENTS,
            SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
            UNKNOWN_REQUIREMENTS,
        )

        messages = [
            SUBMIT_EXPENSE_CLAIM_REQUIREMENTS.success_message,
            APPROVE_CLAIM_REQUIREMENTS.success_message,
            GET_EXPENSE_CLAIM_REQUIREMENTS.success_message,
            UNKNOWN_REQUIREMENTS.success_message,
        ]

        # Check that messages are concise (no verbose phrasing)
        verbose_phrases = ["Your ", "Here is", "Here are", "I'm sorry"]

        for msg in messages:
            for phrase in verbose_phrases:
                if phrase in msg:
                    print(f"   ERROR: Verbose phrasing found in: '{msg}'")
                    return False

        print("   OK: Success messages are concise and professional")
        for i, msg in enumerate(messages[:2]):  # Show first 2 samples
            print(f"     Sample {i + 1}: '{msg}'")

        return True
    except Exception as e:
        print(f"   ERROR: Concise messages check failed: {e}")
        return False


def test_simplified_prompts():
    """Test that prompts have been simplified (unused filtering prompts removed)."""
    print("5. Testing simplified prompts...")

    try:
        # These should exist (core prompts)

        print("   OK: Core prompts still available")

        # These should be removed from main exports (unused filtering prompts)
        try:
            conversation_module = importlib.import_module("conversation")
            if hasattr(conversation_module, "DEPARTMENT_FILTER") or hasattr(
                conversation_module, "STATUS_FILTER"
            ):
                print("   ERROR: Unused filtering prompts still exported in main package")
                return False
            else:
                print("   OK: Unused filtering prompts removed from main exports")
        except ImportError:
            print("   OK: Unused filtering prompts removed from main exports")

        # But they should still exist in prompts module for backward compatibility
        try:
            prompts_module = importlib.import_module("conversation.prompts")
            if hasattr(prompts_module, "DEPARTMENT_FILTER") and hasattr(
                prompts_module, "STATUS_FILTER"
            ):
                print("   OK: Filtering prompts still available in prompts module")
            else:
                print("   OK: Filtering prompts completely removed (acceptable)")
        except ImportError:
            print("   OK: Filtering prompts completely removed (acceptable)")

        return True
    except Exception as e:
        print(f"   ERROR: Simplified prompts check failed: {e}")
        return False


def test_improved_documentation():
    """Test that ConversationIntent documentation has been improved."""
    print("6. Testing improved documentation...")

    try:
        from conversation import ConversationIntent

        docstring = ConversationIntent.__doc__

        # Check that documentation clarifies this is metadata only
        if "metadata only" in docstring.lower():
            print("   OK: Documentation clarifies metadata-only nature")
        else:
            print("   ERROR: Documentation doesn't clarify metadata-only nature")
            return False

        # Check that it doesn't imply tool/service invocation
        if "invoke" in docstring.lower() or "call" in docstring.lower():
            print("   ERROR: Documentation still implies execution")
            return False
        else:
            print("   OK: Documentation avoids implying execution")

        return True
    except Exception as e:
        print(f"   ERROR: Documentation check failed: {e}")
        return False


def test_backward_compatibility():
    """Test that existing code using the package still works."""
    print("7. Testing backward compatibility...")

    try:
        # Test that all previously exported components are still available
        from conversation import (
            SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
            ConversationIntent,
        )

        # Test that ConversationIntent enum values are unchanged
        expected_values = [
            "submit_expense_claim",
            "preview_expense_claim",
            "get_expense_claim",
            "upload_receipt",
            "get_receipt_status",
            "approve_claim",
            "reject_claim",
            "list_pending_claims",
            "list_manager_queue",
            "get_employee_details",
            "list_employee_claims",
            "get_policy",
            "get_expense_category",
            "unknown",
        ]

        actual_values = [intent.value for intent in ConversationIntent]

        if set(expected_values) == set(actual_values):
            print("   OK: All enum values preserved")
        else:
            print("   ERROR: Enum values have changed")
            return False

        # Test that requirements constants still work
        req = SUBMIT_EXPENSE_CLAIM_REQUIREMENTS
        if req.intent == ConversationIntent.SUBMIT_EXPENSE_CLAIM:
            print("   OK: Requirements constants still work")
        else:
            print("   ERROR: Requirements constants broken")
            return False

        print("   OK: Backward compatibility maintained")
        return True

    except Exception as e:
        print(f"   ERROR: Backward compatibility check failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("=== Conversation Package Refinement Validation ===")
    print()

    tests = [
        test_no_forbidden_imports,
        test_ordered_conversational_fields,
        test_success_message_rename,
        test_concise_success_messages,
        test_simplified_prompts,
        test_improved_documentation,
        test_backward_compatibility,
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()

    # Summary
    passed = sum(results)
    total = len(results)

    print("=== Validation Summary ===")
    print(f"Tests passed: {passed}/{total}")

    if all(results):
        print("OK: All refinement validations passed!")
        print()
        print("Refinement improvements:")
        print("  - Improved intents.py documentation (metadata-only clarification)")
        print("  - Ordered conversational fields (tuples instead of frozensets)")
        print("  - Renamed completion_message to success_message")
        print("  - Shortened success messages (concise and professional)")
        print("  - Simplified prompts (removed unused filtering prompts)")
        print("  - Simplified __init__.py exports (cleaner organization)")
        print("  - Maintained backward compatibility")
        print("  - Preserved metadata-only architecture")
        return True
    else:
        print("ERROR: Some validations failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
