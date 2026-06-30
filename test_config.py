#!/usr/bin/env python3
"""
Test script to verify the configuration foundation implementation.
"""

import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_configuration():
    """Test that all configuration modules can be imported and work correctly."""

    print("Testing Configuration Foundation...")
    print("=" * 50)

    try:
        # Test settings.py
        print("\n1. Testing settings.py...")
        from config.settings import settings

        print(f"   [OK] Application Name: {settings.app.application_name}")
        print(f"   [OK] Application Version: {settings.app.application_version}")
        print(f"   [OK] Environment: {settings.app.environment.value}")
        print(f"   [OK] Debug Mode: {settings.app.debug}")
        print(f"   [OK] AWS Region: {settings.aws.aws_region}")
        print(f"   [OK] Bedrock Model ID: {settings.aws.bedrock_model_id}")
        print(f"   [OK] Employees Table: {settings.dynamodb.employees_table}")
        print(f"   [OK] Log Level: {settings.logging.log_level}")
        print(f"   [OK] Default Timeout: {settings.workflow.default_timeout}")
        print(f"   [OK] Retry Count: {settings.workflow.retry_count}")

        # Test constants.py
        print("\n2. Testing constants.py...")
        from config.constants import DATE_FORMAT, DEFAULT_CURRENCY, MAX_RECEIPT_SIZE_MB
        from config.settings import settings

        print(f"   [OK] DEFAULT_TIMEOUT: {settings.workflow.default_timeout}")
        print(f"   [OK] MAX_RETRY_COUNT: {settings.workflow.max_retry_count}")
        print(f"   [OK] DATE_FORMAT: {DATE_FORMAT}")
        print(f"   [OK] DEFAULT_CURRENCY: {DEFAULT_CURRENCY}")
        print(f"   [OK] MAX_RECEIPT_SIZE_MB: {MAX_RECEIPT_SIZE_MB}")

        # Test enums.py
        print("\n3. Testing enums.py...")
        # isort: off
        from config.enums import (
            ApprovalStatus,
            ClaimStatus,
        )
        from config.enums import Environment as EnvEnum
        from config.enums import (
            ExpenseCategory,
            LogLevel,
            ValidationStatus,
        )

        # isort: on

        # isort: on

        print(f"   [OK] ExpenseCategory.AIRFARE: {ExpenseCategory.AIRFARE.value}")
        print(f"   [OK] ClaimStatus.DRAFT: {ClaimStatus.DRAFT.value}")
        print(f"   [OK] ApprovalStatus.PENDING: {ApprovalStatus.PENDING.value}")
        print(f"   [OK] ValidationStatus.VALID: {ValidationStatus.VALID.value}")
        print(f"   [OK] LogLevel.INFO: {LogLevel.INFO.value}")
        print(f"   [OK] Environment.PRODUCTION: {EnvEnum.PRODUCTION.value}")

        print("\n" + "=" * 50)
        print("[SUCCESS] All configuration tests passed successfully!")
        print("Configuration Foundation is working correctly.")

        return True

    except Exception as e:
        print(f"\n[ERROR] Configuration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_configuration()
    sys.exit(0 if success else 1)
