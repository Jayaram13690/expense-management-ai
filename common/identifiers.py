"""
Reusable domain identifier types.

This module centralizes all business identifier validation.

Instead of repeating regex patterns across multiple models,
every entity should reuse these types.

Example:
    employee_id: EmployeeId
    claim_id: ClaimId
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

# ---------------------------------------------------------
# Employee
# ---------------------------------------------------------

EmployeeId = Annotated[
    str,
    Field(
        pattern=r"^EMP\d{4,10}$",
        description="Employee Identifier",
    ),
]


# ---------------------------------------------------------
# Category Id
# ---------------------------------------------------------


CategoryId = Annotated[
    str,
    Field(
        ...,
        pattern=r"^CAT\d{4,10}$",
    ),
]


# ---------------------------------------------------------
# Expense Claim
# ---------------------------------------------------------

ClaimId = Annotated[
    str,
    Field(
        pattern=r"^CLM\d{4,12}$",
        description="Expense Claim Identifier",
    ),
]


# ---------------------------------------------------------
# Expense Policy
# ---------------------------------------------------------

PolicyId = Annotated[
    str,
    Field(
        pattern=r"^POL\d{3,10}$",
        description="Expense Policy Identifier",
    ),
]


# ---------------------------------------------------------
# Receipt
# ---------------------------------------------------------

ReceiptId = Annotated[
    str,
    Field(
        pattern=r"^RCT\d{4,12}$",
        description="Receipt Identifier",
    ),
]


# ---------------------------------------------------------
# Workflow
# ---------------------------------------------------------

WorkflowId = Annotated[
    str,
    Field(
        pattern=r"^WF\d{4,12}$",
        description="Workflow Identifier",
    ),
]


RequestId = Annotated[
    str,
    Field(
        min_length=8,
        max_length=100,
        description="Request Identifier",
    ),
]


# ---------------------------------------------------------
# Trip
# ---------------------------------------------------------

TripId = Annotated[
    str,
    Field(
        pattern=r"^TRP\d{4,12}$",
        description="Trip Identifier",
    ),
]
