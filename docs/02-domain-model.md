# 02-domain-model.md

# Enterprise AI Travel Expense Management System

Version: 1.0

Status: Architecture Review Draft

---

# 1. Purpose

This document defines the core business entities of the Enterprise AI Travel Expense Management System.

The Domain Model represents the business concepts used throughout the application and serves as the foundation for the database design, business services, AI agents, repositories, and workflow orchestration.

This document intentionally excludes implementation details.

---

# 2. Domain Overview

The system is centered around the processing of employee travel expense claims.

The primary business entities are:

* Employee
* Expense Policy
* Expense Category
* Expense Claim
* Receipt
* Workflow Context

These entities represent the business language used throughout the application.

---

# 3. Business Entity Relationships

```text
Employee
    │
    │ belongs to
    ▼
Expense Policy

Employee
    │
    │ submits
    ▼
Expense Claim

Expense Claim
    │
    │ contains
    ▼
Receipts

Receipt
    │
    │ belongs to
    ▼
Expense Category
```

---

# 4. Entity Definitions

## 4.1 Employee

Represents an employee who submits travel expense claims.

### Attributes

* Employee ID
* Employee Name
* Email
* Department
* Grade
* Policy ID
* Employment Status

### Responsibilities

* Submit expense claims
* View reimbursement summary
* Approve or cancel submission

---

## 4.2 Expense Policy

Represents the reimbursement policy assigned to an employee.

### Attributes

* Policy ID
* Employee Grade
* Meal Limit (per day)
* Transport Limit (per day)
* Accommodation Limit (per night)
* Maximum Claim Amount
* Currency
* Effective Status

### Responsibilities

* Define reimbursement limits
* Define employee eligibility
* Provide financial rules

---

## 4.3 Expense Category

Represents a valid category of travel expense.

### Supported Categories

* Meals
* Transport
* Accommodation
* Parking
* Fuel
* Internet

### Attributes

* Category ID
* Category Name
* Receipt Required
* Daily Limit
* Status

### Responsibilities

* Categorize expenses
* Define receipt requirements
* Apply category-level validations

---

## 4.4 Expense Claim

Represents a single reimbursement request submitted by an employee.

### Attributes

* Claim ID
* Employee ID
* Trip ID
* Claim Date
* Total Claimed Amount
* Total Approved Amount
* Status
* Submission Timestamp

### Responsibilities

* Represent the overall reimbursement request
* Track workflow status
* Store financial summary

---

## 4.5 Receipt

Represents an individual expense item within a claim.

### Attributes

* Receipt ID
* Claim ID
* Expense Category
* Expense Date
* Claimed Amount
* Approved Amount
* Receipt Reference
* Validation Status

### Responsibilities

* Represent a single expense line
* Support validation
* Store reimbursement decisions

---

## 4.6 Workflow Context

Represents the shared business context exchanged between agents during execution.

### Attributes

* User Request
* Employee
* Expense Policy
* Categories
* Submitted Expenses
* Validation Result
* Financial Summary
* Approval Decision

### Responsibilities

* Maintain workflow state during execution
* Share information between agents
* Prevent repeated database retrievals

---

# 5. Entity Ownership

| Entity           | Business Owner  |
| ---------------- | --------------- |
| Employee         | Human Resources |
| Expense Policy   | Finance         |
| Expense Category | Finance         |
| Expense Claim    | Employee        |
| Receipt          | Employee        |
| Workflow Context | System          |

---

# 6. Entity Lifecycle

## Expense Claim Lifecycle

Draft

↓

Validated

↓

Calculated

↓

Awaiting Approval

↓

Submitted

or

Cancelled

---

# 7. Domain Constraints

* Every employee must have one policy.
* Every claim belongs to exactly one employee.
* Every receipt belongs to exactly one claim.
* Every receipt must reference a valid expense category.
* One claim may contain multiple receipts.
* Claims cannot be submitted without employee approval.
* Duplicate claims for the same employee and trip are not permitted.

---

# 8. Aggregate Boundaries

## Employee Aggregate

Employee

↓

Expense Policy

---

## Claim Aggregate

Expense Claim

↓

Receipts

These aggregates define transactional boundaries for the business workflow.

---

# 9. Value Objects

The following concepts are treated as value objects rather than standalone entities:

* Money
* Currency
* Employee Grade
* Expense Status
* Approval Decision

These values are immutable within the scope of a workflow execution.

---

# 10. Domain Events

The following business events occur during the workflow:

* Expense Claim Submitted
* Employee Retrieved
* Policy Retrieved
* Expenses Validated
* Reimbursement Calculated
* Approval Requested
* Claim Approved
* Claim Rejected
* Claim Persisted

These events support future enhancements such as notifications, auditing, and analytics.

---

# 11. Future Domain Extensions

The domain model has been designed to support future additions without breaking existing entities.

Potential future entities include:

* Manager
* Approval Workflow
* Fraud Case
* OCR Result
* Currency Exchange Rate
* Notification
* Audit Log
* Travel Itinerary

These entities are intentionally excluded from the initial implementation but can be incorporated without major architectural changes.
