#!/usr/bin/env python3
"""
Simple agent validation script.
"""

import os
import sys
import time

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from agents.employee_agent import EmployeeAgent

    print("[PASS] EmployeeAgent imported successfully")

    agent = EmployeeAgent()
    print("[PASS] EmployeeAgent initialized successfully")

    # Test a simple query
    start_time = time.time()
    try:
        result = agent.invoke("Retrieve employee EMP0001 details.")
        execution_time = time.time() - start_time
        print(f"[PASS] EmployeeAgent invoke successful in {execution_time:.3f}s")
        print(f"Result type: {type(result)}")
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"[FAIL] EmployeeAgent invoke failed after {execution_time:.3f}s")
        print(f"Error: {e}")

except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}")
