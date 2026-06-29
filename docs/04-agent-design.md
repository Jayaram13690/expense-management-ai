# 04-agent-design.md

# Enterprise AI Travel Expense Management System

Version: 1.0

Status: Architecture Review Draft

---

# 1. Purpose

This document defines the AI Multi-Agent Architecture for the Enterprise AI Travel Expense Management System.

The application follows a Coordinator-Orchestrator pattern where one primary agent controls the workflow while specialized business agents execute individual business capabilities.

The architecture is designed to be:

- Modular
- Scalable
- Extensible
- Testable
- Production-ready

Each agent owns a single business capability.

---

# 2. Design Principles

The Multi-Agent architecture follows these principles.

## Single Responsibility

Each agent owns one business capability.

---

## Separation of Concerns

Agents do not contain persistence logic.

Agents do not directly access DynamoDB.

Agents communicate only through the Workflow Context.

---

## Tool Driven

Agents execute business operations through Tools.

They never call repositories directly.

---

## Coordinator Pattern

Only one agent orchestrates the workflow.

Business agents never invoke each other.

---

## Stateless Execution

Agents do not maintain long-term memory.

The shared Workflow Context carries all required execution data.

---

# 3. Multi-Agent Architecture

                    Employee
                        │
                        ▼
         Expense Workflow Coordinator Agent
                        │
     ┌──────────────────┼───────────────────┐
     │                  │                   │
     ▼                  ▼                   ▼
Policy Agent     Validation Agent    Finance Agent
                        │
                        ▼
                Approval Agent
                        │
                        ▼
                  Tool Layer

---

# 4. Agent Responsibilities

The system contains five AI agents.

1. Expense Workflow Coordinator Agent
2. Policy Agent
3. Validation Agent
4. Finance Agent
5. Approval Agent

---

# 5. Expense Workflow Coordinator Agent

## Purpose

Acts as the workflow orchestrator.

Owns the end-to-end business process.

Coordinates execution between all business agents.

---

## Responsibilities

- Receive employee request
- Create Workflow Context
- Start workflow
- Execute parallel retrieval
- Merge retrieval results
- Execute sequential workflow
- Handle failures
- Return final response

---

## Allowed Tools

None directly.

Coordinator delegates all work to business agents.

---

## Input

Natural language travel expense request.

---

## Output

Completed workflow response.

---

## Never Responsible For

- Policy validation
- Finance calculations
- Database access
- Receipt validation

---

# 6. Policy Agent

## Purpose

Retrieve business policy information.

---

## Responsibilities

Retrieve employee.

Retrieve reimbursement policy.

Retrieve expense categories.

Retrieve historical claims for duplicate detection.

---

## Allowed Tools

Employee Tool

Policy Tool

Category Tool

Claim Tool

---

## Output

Business Context

Employee

Policy

Categories

Previous Claims

---

## Never Responsible For

Validation.

Calculation.

Persistence.

---

# 7. Validation Agent

## Purpose

Validate business correctness.

---

## Responsibilities

Validate employee.

Validate categories.

Validate policy.

Validate receipts.

Validate duplicate claims.

Validate expense limits.

Generate validation report.

---

## Allowed Tools

Validation Tool

---

## Output

Validation Report

---

## Never Responsible For

Finance calculations.

Persistence.

---

# 8. Finance Agent

## Purpose

Calculate reimbursement.

---

## Responsibilities

Calculate:

- Claimed Amount
- Approved Amount
- Variance
- Deductions
- Total Reimbursement

Generate financial summary.

---

## Allowed Tools

Finance Tool

---

## Output

Financial Summary

---

## Never Responsible For

Validation.

Persistence.

---

# 9. Approval Agent

## Purpose

Support Human-in-the-Loop.

---

## Responsibilities

Present claim summary.

Request employee confirmation.

Capture decision.

Return approval result.

---

## Allowed Tools

Approval Tool

Claim Tool (after approval only)

---

## Output

Approval Decision

---

## Never Responsible For

Policy retrieval.

Financial calculation.

Validation.

---

# 10. Workflow Context

The Workflow Context is the shared execution object passed between all agents.

It contains:

- User Request
- Employee
- Policy
- Categories
- Previous Claims
- Submitted Expenses
- Validation Result
- Financial Summary
- Approval Result

Agents enrich the context but never replace it.

---

# 11. Agent Interaction Rules

Rule 1

Business agents never call each other.

---

Rule 2

Only the Coordinator invokes business agents.

---

Rule 3

Business agents never communicate directly.

---

Rule 4

All shared information passes through Workflow Context.

---

Rule 5

Agents never access DynamoDB directly.

---

Rule 6

Agents never perform repository operations.

---

# 12. Parallel Execution Strategy

The Coordinator launches independent retrieval operations simultaneously.

Parallel tasks include:

- Employee Retrieval
- Policy Retrieval
- Category Retrieval
- Previous Claim Retrieval

These tasks execute concurrently.

The results are merged into the Workflow Context.

---

# 13. Sequential Execution Strategy

After context preparation, the Coordinator executes:

Validation

↓

Finance Calculation

↓

Approval

↓

Persistence

Each stage depends on the successful completion of the previous stage.

---

# 14. Failure Handling

Coordinator owns workflow failure handling.

Possible failures:

- Employee not found
- Policy unavailable
- Validation failure
- Approval rejected
- Persistence failure

Coordinator terminates workflow gracefully and returns an appropriate response.

---

# 15. Agent Boundaries

| Agent | Owns | Never Owns |
|---------|---------------------------|--------------------------|
| Coordinator | Workflow | Business Logic |
| Policy | Policy Retrieval | Calculations |
| Validation | Validation | Persistence |
| Finance | Financial Computation | Validation |
| Approval | Human Decision | Policy Retrieval |

---

# 16. Future Agents

The architecture supports future expansion.

Potential future agents:

- OCR Agent
- Fraud Detection Agent
- Notification Agent
- Currency Conversion Agent
- Manager Approval Agent
- Analytics Agent

These can be introduced without changing existing business agents because the Coordinator owns orchestration.

---

# 17. Architecture Benefits

The chosen architecture provides:

- High cohesion
- Low coupling
- Clear ownership
- Easy testing
- Easy extensibility
- Maintainable workflows
- Enterprise scalability
- Production readiness