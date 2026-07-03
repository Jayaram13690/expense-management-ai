#!/usr/bin/env python3
"""
Simple test script to verify the policy domain fix.
"""

from services.expense_category_service import ExpenseCategoryService
from services.expense_policy_service import ExpensePolicyService


def test_category_resolution():
    """Test the category resolution functionality."""

    # Initialize services
    policy_service = ExpensePolicyService()
    category_service = ExpenseCategoryService()

    print("Testing Category Resolution...")
    print("=" * 50)

    # Test the category resolution method directly
    test_cases = [
        {
            "identifier": "CAT0001",  # Direct category_id
            "description": "Direct category_id lookup",
        },
        {
            "identifier": "HOTEL",  # Category code
            "description": "Category code lookup",
        },
        {
            "identifier": "hotel",  # Lowercase category code
            "description": "Lowercase category code lookup",
        },
        {
            "identifier": "Hotel Accommodation",  # Category name
            "description": "Category name lookup",
        },
        {
            "identifier": "hotel accommodation",  # Lowercase category name
            "description": "Lowercase category name lookup",
        },
        {
            "identifier": "NONEXISTENT",  # Non-existent category
            "description": "Non-existent category (should return None)",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Identifier: '{test_case['identifier']}'")

        try:
            # Test the category resolution method directly
            category = policy_service._resolve_category_identifier(test_case["identifier"])

            if category is not None:
                print(
                    f"SUCCESS: Found category '{category.category_name}' with ID '{category.category_id}'"
                )
            else:
                print("SUCCESS: Correctly returned None for non-existent category")

        except Exception as e:
            print(f"FAIL: Unexpected exception: {type(e).__name__}: {str(e)}")

    print("\n" + "=" * 50)
    print("Testing User-Friendly Identifier Formatting...")

    # Test the user-friendly identifier formatting
    test_identifiers = [
        "CAT0001",
        "HOTEL",
        "hotel",
        "Hotel Accommodation",
        "hotel accommodation",
        "taxi",
        "TAXI",
    ]

    for identifier in test_identifiers:
        user_friendly = policy_service._get_user_friendly_identifier(identifier)
        print(f"'{identifier}' -> '{user_friendly}'")

    print("\nTest completed!")


if __name__ == "__main__":
    test_category_resolution()
