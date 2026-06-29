# 07-system-architecture.md

# Enterprise AI Travel Expense Management System

Version: 1.0

Status: Final Architecture

---

# 1. Purpose

This document defines the complete system architecture of the Enterprise AI Travel Expense Management System.

The architecture has been designed following enterprise software engineering principles, AWS Well-Architected best practices, and AI Multi-Agent design patterns.

The system separates AI reasoning from deterministic business logic while ensuring scalability, maintainability, security, and extensibility.

---

# 2. Architecture Goals

The architecture aims to achieve:

- Modular Design
- Separation of Concerns
- Enterprise Maintainability
- AI-driven Workflow Orchestration
- Deterministic Business Logic
- Production Readiness
- Cloud Native Deployment
- Future Extensibility

---

# 3. High-Level Architecture

```
                        Employee
                            │
                            ▼
               Strands CLI / AgentCore Runtime
                            │
                            ▼
             Expense Workflow Coordinator Agent
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  Policy Agent      Validation Agent     Finance Agent
                            │
                            ▼
                    Approval Agent
                            │
                            ▼
                        Tool Layer
                            │
                            ▼
                     Business Services
                            │
                            ▼
                      Repository Layer
                            │
                            ▼
                     Amazon DynamoDB
```

---

# 4. Layered Architecture

The application follows a layered architecture.

```
Presentation Layer

↓

AI Agent Layer

↓

Tool Layer

↓

Business Service Layer

↓

Repository Layer

↓

Database Layer
```

Each layer communicates only with the layer immediately below it.

This reduces coupling and improves maintainability.

---

# 5. Presentation Layer

Responsible for receiving user requests.

Components

- Strands CLI
- Amazon Bedrock AgentCore Runtime

Responsibilities

- Accept employee requests
- Display workflow responses
- Support Human-in-the-Loop interaction

No business logic exists in this layer.

---

# 6. AI Agent Layer

Contains all AI agents responsible for workflow orchestration.

Agents

- Expense Workflow Coordinator Agent
- Policy Agent
- Validation Agent
- Finance Agent
- Approval Agent

Responsibilities

- Understand user intent
- Coordinate workflow
- Invoke tools
- Produce business decisions

Agents never access DynamoDB directly.

---

# 7. Tool Layer

Acts as the interface between AI agents and deterministic business logic.

Tools

- Employee Tool
- Policy Tool
- Validation Tool
- Finance Tool
- Claim Tool

Responsibilities

- Expose business capabilities
- Delegate processing to Services

---

# 8. Business Service Layer

Contains deterministic business logic.

Services

- EmployeeService
- PolicyService
- ValidationService
- FinanceService
- ClaimService

Responsibilities

- Business rules
- Financial calculations
- Policy evaluation
- Claim processing

---

# 9. Repository Layer

Responsible for persistence.

Repositories

- EmployeeRepository
- PolicyRepository
- CategoryRepository
- ClaimRepository
- ReceiptRepository

Responsibilities

- CRUD
- Query
- Data mapping

Repositories never contain business logic.

---

# 10. Database Layer

Technology

Amazon DynamoDB

Tables

- Employees
- ExpensePolicies
- ExpenseCategories
- ExpenseClaims
- Receipts

The database layer is isolated behind repositories.

---

# 11. Multi-Agent Architecture

The system follows a Coordinator-Orchestrator pattern.

```
Coordinator

↓

Policy Agent

↓

Validation Agent

↓

Finance Agent

↓

Approval Agent
```

Only the Coordinator controls workflow execution.

Business agents never invoke each other.

---

# 12. Parallel Execution

The Coordinator executes independent retrieval tasks concurrently.

Parallel Operations

- Retrieve Employee
- Retrieve Policy
- Retrieve Categories
- Retrieve Previous Claims

Benefits

- Reduced latency
- Faster workflow initialization
- Better scalability

---

# 13. Sequential Execution

After context retrieval, the workflow executes sequentially.

```
Validation

↓

Finance

↓

Approval

↓

Persistence
```

Each stage depends on the previous stage.

---

# 14. Workflow Context

Workflow Context acts as the shared execution state.

Contains

- Request
- Employee
- Policy
- Categories
- Claims
- Validation
- Finance Summary
- Approval

The same object is passed throughout workflow execution.

---

# 15. Data Flow

```
Employee Request

↓

Coordinator

↓

Agents

↓

Tools

↓

Services

↓

Repositories

↓

DynamoDB

↓

Repositories

↓

Services

↓

Agents

↓

Employee
```

---

# 16. Security Architecture

Security principles

- Least Privilege IAM
- Externalized Configuration
- No Hardcoded Secrets
- Repository-only Database Access
- Validation Before Persistence

Future Enhancements

- AWS Secrets Manager
- IAM Identity Center
- Role-based Authorization

---

# 17. Error Handling

Each architectural layer owns its exceptions.

Presentation

↓

WorkflowException

↓

AgentException

↓

ToolException

↓

ServiceException

↓

RepositoryException

↓

DatabaseException

Errors are propagated upward using structured responses.

---

# 18. Logging Architecture

Every workflow receives a unique Workflow ID.

Each log entry contains

- Workflow ID
- Timestamp
- Agent
- Tool
- Operation
- Duration
- Status

CloudWatch integration is supported.

---

# 19. Deployment Architecture

```
Developer

↓

Git

↓

Local Testing

↓

Strands CLI

↓

AgentCore Runtime

↓

Amazon Bedrock

↓

DynamoDB

↓

CloudWatch
```

Deployment Target

Amazon Bedrock AgentCore Runtime

---

# 20. Scalability

The architecture supports future expansion through additional agents.

Possible future agents

- OCR Agent
- Fraud Detection Agent
- Notification Agent
- Currency Conversion Agent
- Manager Approval Agent
- Analytics Agent

Existing architecture does not require modification.

---

# 21. Enterprise Design Principles

The system follows

- SOLID Principles
- Separation of Concerns
- Repository Pattern
- Service Layer Pattern
- Coordinator Pattern
- Tool Abstraction
- AI-Orchestrated Workflow
- Human-in-the-Loop
- Cloud Native Design

---

# 22. Architecture Benefits

The chosen architecture provides

- Modular Components
- Independent Business Capabilities
- Easy Testing
- Maintainability
- Scalability
- Enterprise Readiness
- AI Workflow Orchestration
- Production Deployability