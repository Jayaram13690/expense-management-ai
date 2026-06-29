# 06-workflow-design.md

# Enterprise AI Travel Expense Management System

Version: 1.0

Status: Architecture Review Approved

---

# 1. Purpose

This document defines the end-to-end workflow orchestration of the Enterprise AI Travel Expense Management System.

The workflow coordinates multiple AI agents, business services, and data retrieval operations to process employee travel expense claims.

The workflow is designed to:

- Support AI-driven orchestration
- Demonstrate Parallel Execution
- Demonstrate Sequential Execution
- Support Human-in-the-Loop approval
- Maintain data integrity
- Be extensible for future enhancements

---

# 2. Workflow Overview

The workflow begins when an employee submits a travel expense claim.

The Coordinator Agent orchestrates the complete business process.

Independent retrieval operations execute in parallel.

Business validation and financial computation execute sequentially.

Only approved claims are persisted.

---

# 3. High-Level Workflow

Employee Request

↓

Coordinator Agent

↓

Parallel Context Retrieval

↓

Workflow Context Creation

↓

Validation

↓

Financial Calculation

↓

Human Approval

↓

Persistence

↓

Workflow Complete

---

# 4. Workflow Phases

The workflow consists of six phases.

Phase 1

Request Initialization

↓

Phase 2

Parallel Context Retrieval

↓

Phase 3

Business Validation

↓

Phase 4

Financial Computation

↓

Phase 5

Human Approval

↓

Phase 6

Persistence

---

# 5. Phase 1 — Request Initialization

Purpose

Initialize workflow execution.

Activities

- Receive employee request
- Parse travel expense information
- Generate Workflow ID
- Create initial Workflow Context

Output

Workflow Context created.

---

# 6. Phase 2 — Parallel Context Retrieval

Purpose

Retrieve all independent business data concurrently.

Executed By

Coordinator Agent

Parallel Operations

- Retrieve Employee
- Retrieve Expense Policy
- Retrieve Expense Categories
- Retrieve Previous Claims

Execution Model

Parallel

Reason

These operations do not depend on one another.

Benefits

- Reduced latency
- Faster workflow initialization
- Better resource utilization

Output

Complete business context.

---

# 7. Context Merge

After parallel execution completes,

all retrieved information is merged into the Workflow Context.

Workflow Context now contains:

- Employee
- Policy
- Categories
- Previous Claims
- User Request

No further database retrieval should be required during normal workflow execution.

---

# 8. Phase 3 — Business Validation

Purpose

Validate business correctness.

Executed By

Validation Agent

Validation Activities

- Employee Eligibility
- Policy Availability
- Category Validation
- Receipt Validation
- Duplicate Claim Detection
- Policy Limit Validation

Execution Model

Sequential

Reason

Validation depends on retrieved business context.

Output

Validation Report

If validation fails,

workflow terminates.

---

# 9. Phase 4 — Financial Computation

Purpose

Calculate reimbursement.

Executed By

Finance Agent

Activities

- Calculate Claimed Amount
- Apply Policy Limits
- Calculate Approved Amount
- Calculate Variance
- Calculate Deductions
- Generate Financial Summary

Execution Model

Sequential

Reason

Requires successful validation.

Output

Financial Summary

---

# 10. Phase 5 — Human-in-the-Loop Approval

Purpose

Allow employee confirmation.

Executed By

Approval Agent

Activities

Display:

- Claimed Amount
- Approved Amount
- Deductions
- Policy Violations
- Final Reimbursement

Employee Decision

Approve

or

Cancel

Execution Model

Sequential

Reason

Persistence must never occur without explicit confirmation.

---

# 11. Phase 6 — Persistence

Purpose

Persist approved claims.

Executed By

Approval Agent

Activities

Save:

- Expense Claim
- Receipt Records

Execution Model

Sequential

Reason

Persistence occurs only after approval.

Output

Successful Claim Submission

---

# 12. Parallel Execution Strategy

Parallel execution occurs exactly once.

Coordinator launches:

Retrieve Employee

Retrieve Policy

Retrieve Categories

Retrieve Previous Claims

All tasks execute simultaneously.

The Coordinator waits for all tasks to complete before continuing.

This minimizes workflow latency.

---

# 13. Sequential Execution Strategy

The following stages execute sequentially.

Validation

↓

Finance

↓

Approval

↓

Persistence

Each stage requires the successful completion of the previous stage.

---

# 14. Human-in-the-Loop Strategy

The employee remains responsible for the final submission decision.

Approval options

YES

↓

Persist claim

NO

↓

Cancel workflow

No persistence occurs without approval.

---

# 15. Workflow Context Lifecycle

Workflow Context evolves during execution.

Stage 1

Request

↓

Stage 2

Business Context

↓

Stage 3

Validation Result

↓

Stage 4

Financial Summary

↓

Stage 5

Approval Decision

↓

Stage 6

Persistence Result

The same Workflow Context object is shared across all agents.

---

# 16. Happy Path Workflow

Employee submits claim

↓

Parallel Retrieval

↓

Validation Successful

↓

Financial Calculation

↓

Employee Approves

↓

Claim Saved

↓

Workflow Complete

---

# 17. Failure Workflows

Employee Not Found

↓

Workflow Terminated

---

Policy Missing

↓

Workflow Terminated

---

Duplicate Claim

↓

Workflow Terminated

---

Receipt Missing

↓

Validation Failed

↓

Workflow Terminated

---

Approval Rejected

↓

Workflow Cancelled

---

Persistence Failure

↓

Return Failure Response

---

# 18. Logging Strategy

Every workflow step generates logs.

Examples

Workflow Started

Parallel Retrieval Started

Employee Retrieved

Policy Retrieved

Validation Started

Validation Completed

Finance Started

Finance Completed

Approval Requested

Claim Persisted

Workflow Completed

Each log entry includes

- Workflow ID
- Timestamp
- Agent Name
- Operation
- Duration
- Status

---

# 19. Retry Strategy

Retry is supported for transient infrastructure failures.

Examples

- DynamoDB throttling
- Temporary Bedrock timeout

Business validation failures are never retried.

User rejection is never retried.

Duplicate claims are never retried.

---

# 20. Workflow Benefits

The workflow provides:

- AI-driven orchestration
- Clear separation of responsibilities
- Reduced latency through parallel execution
- Deterministic business processing
- Human oversight
- Strong auditability
- Enterprise scalability
- Production readiness