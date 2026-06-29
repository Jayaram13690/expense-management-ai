# 03-database-design.md

# Enterprise AI Travel Expense Management System

Version: 1.0

Status: Architecture Review Draft

---

# 1. Purpose

This document defines the database architecture for the Enterprise AI Travel Expense Management System.

The objective is to design a scalable, maintainable, and production-ready persistence layer using Amazon DynamoDB.

The design follows AWS DynamoDB best practices by identifying business access patterns before defining tables, keys, and relationships.

---

# 2. Database Technology

Database Engine

Amazon DynamoDB

Reasons

* Fully managed
* Serverless
* Highly scalable
* Low latency
* Native AWS integration
* Suitable for AI workflow systems

---

# 3. Database Design Principles

The database design follows these principles:

* Business-driven schema
* Access-pattern-first design
* Single responsibility per table
* Avoid duplicated business data
* Externalize business rules
* Idempotent writes
* Future extensibility

---

# 4. Business Access Patterns

The following access patterns are required by the application.

## Employee

AP-001

Retrieve employee by Employee ID.

AP-002

Retrieve employee travel policy.

---

## Expense Policy

AP-003

Retrieve policy by Policy ID.

AP-004

Retrieve policy by Employee Grade.

---

## Expense Categories

AP-005

Retrieve all active categories.

AP-006

Retrieve category by Category ID.

---

## Expense Claims

AP-007

Create new claim.

AP-008

Retrieve claim by Claim ID.

AP-009

Retrieve claims for Employee.

AP-010

Check duplicate Trip ID.

---

## Receipts

AP-011

Store receipt.

AP-012

Retrieve receipts by Claim ID.

---

# 5. Database Tables

The system contains five business tables.

1. Employees

2. ExpensePolicies

3. ExpenseCategories

4. ExpenseClaims

5. Receipts

---

# 6. Employees Table

Purpose

Stores employee master information.

Primary Key

Partition Key

EmployeeId

Attributes

* EmployeeId
* EmployeeName
* Email
* Department
* Grade
* PolicyId
* Status
* CreatedAt
* UpdatedAt

Business Owner

Human Resources

---

# 7. ExpensePolicies Table

Purpose

Stores reimbursement policies.

Primary Key

Partition Key

PolicyId

Attributes

* PolicyId
* Grade
* MealLimit
* TransportLimit
* AccommodationLimit
* MaximumClaimAmount
* Currency
* Status

Business Owner

Finance

---

# 8. ExpenseCategories Table

Purpose

Stores supported expense categories.

Primary Key

Partition Key

CategoryId

Attributes

* CategoryId
* CategoryName
* ReceiptRequired
* DailyLimit
* Status

Reference Data

Meals

Transport

Accommodation

Parking

Fuel

Internet

---

# 9. ExpenseClaims Table

Purpose

Stores travel expense claim summary.

Primary Key

Partition Key

ClaimId

Recommended Global Secondary Indexes

GSI-1

EmployeeId

GSI-2

TripId

Attributes

* ClaimId
* EmployeeId
* TripId
* TotalClaimedAmount
* TotalApprovedAmount
* ClaimStatus
* SubmittedAt
* ApprovedAt

Business Owner

Employee

---

# 10. Receipts Table

Purpose

Stores expense line items.

Primary Key

Partition Key

ReceiptId

Recommended GSI

ClaimId

Attributes

* ReceiptId
* ClaimId
* CategoryId
* ExpenseDate
* ClaimedAmount
* ApprovedAmount
* ReceiptReference
* ValidationStatus

---

# 11. Table Relationships

Employee

↓

Expense Policy

Employee

↓

Expense Claim

Expense Claim

↓

Receipts

Receipt

↓

Expense Category

---

# 12. Seed Data

The initialization script shall populate:

Employees

* EMP001
* EMP002
* EMP003

Expense Policies

* G3 Policy
* G4 Policy
* G5 Policy

Expense Categories

* Meals
* Transport
* Accommodation
* Parking
* Fuel
* Internet

Expense Claims

Sample historical claims.

Receipts

Sample expense line items.

---

# 13. Repository Layer

Each table shall have a dedicated repository.

EmployeeRepository

PolicyRepository

CategoryRepository

ClaimRepository

ReceiptRepository

Responsibilities

* CRUD Operations
* Query Operations
* Error Handling
* DynamoDB Mapping

Repositories shall NOT contain business logic.

---

# 14. Data Integrity Rules

* Employee must exist before claim creation.
* Policy must exist.
* Category must exist.
* Claim must exist before receipt insertion.
* Duplicate Trip IDs shall be rejected.
* Claim totals shall equal the sum of approved receipt amounts.

---

# 15. Security Considerations

* Least-privilege IAM access.
* No direct table access from agents.
* Repositories are the only persistence layer.
* No hardcoded table names.
* Configuration managed through environment variables.

---

# 16. Performance Considerations

* Frequently queried attributes indexed using GSIs.
* Independent reads executed in parallel.
* Optimized partition key usage.
* Minimize unnecessary scans.
* Prefer Query over Scan operations.

---

# 17. Error Handling Strategy

Repository layer shall handle:

* Conditional write failures
* Missing records
* Duplicate records
* DynamoDB throttling
* AWS SDK exceptions

Business exceptions are propagated to the Service Layer.

---

# 18. Future Database Extensions

The design supports future tables including:

* AuditLogs
* Notifications
* WorkflowHistory
* FraudCases
* OCRResults
* CurrencyExchangeRates

These tables are intentionally excluded from Version 1.
