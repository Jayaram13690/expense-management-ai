# Enterprise AI Travel Expense Management System

> An enterprise-grade **Multi-Agent AI Travel Expense Management System** built using **Amazon Bedrock AgentCore**, **Strands Agents SDK**, and AWS services. The application automates the complete travel expense reimbursement lifecycle through intelligent agent orchestration, conversational workflows, policy validation, Human-in-the-Loop (HITL) interactions, and automated approval processing.

---

## Overview

The Enterprise AI Travel Expense Management System simplifies and automates the travel reimbursement process using a collaborative multi-agent architecture. Instead of relying on static forms, users interact with an AI assistant through natural language to submit claims, retrieve employee information, understand reimbursement policies, upload receipts, track claim status, and manage approvals.

The system combines deterministic business logic with Large Language Models (LLMs) to deliver conversational, policy-aware, and enterprise-ready expense management.

---

## Key Features

- Multi-Agent Architecture using Strands Agents SDK
- Amazon Bedrock AgentCore Runtime deployment
- Conversational expense claim submission
- Employee information retrieval
- Expense policy validation
- Parallel reimbursement calculation
- Human-in-the-Loop (HITL) confirmation
- Receipt upload (Local Path / URL)
- Amazon S3 receipt storage
- Duplicate claim detection
- Claim approval & rejection workflow
- Email notifications using Amazon SES
- Conversation context persistence
- Session-based conversations
- DynamoDB-backed data storage

---

# System Architecture

```
                           User
                             │
                             ▼
                   Amazon Bedrock AgentCore
                             │
                             ▼
                    Coordinator Agent
                             │
        ┌──────────────┬──────────────┬─────────────┐
        ▼              ▼              ▼             ▼
 Employee Agent   Expense Agent  Policy Agent  Approval Agent
        │              │              │             │
        └──────────────┼──────────────┘             │
                       ▼                            │
                 Receipt Agent                      │
                       │                            │
                       ▼                            ▼
                 AWS Services (DynamoDB, S3, SES)
```

---

# Multi-Agent Architecture

## Coordinator Agent

The Coordinator Agent serves as the central orchestrator responsible for:

- Intent classification
- Conversation routing
- Context management
- Agent selection
- Conversation continuation
- Greeting handling
- Out-of-scope response handling

---

## Expense Agent

Responsibilities

- Expense claim submission
- Claim status retrieval
- Expense validation
- Duplicate detection
- Reimbursement calculation
- Claim persistence

---

## Employee Agent

Responsibilities

- Employee validation
- Employee profile retrieval
- Manager lookup
- Employee hierarchy
- Employee claim history

---

## Policy Agent

Responsibilities

- Expense policy retrieval
- Category limits
- Daily limits
- Monthly limits
- Approval requirements
- Receipt requirements

---

## Receipt Agent

Responsibilities

- Receipt upload
- URL download
- Local file upload
- Amazon S3 storage
- Receipt validation

---

## Approval Agent

Responsibilities

- List pending approvals
- Approve claims
- Reject claims
- Update claim status
- Email notifications

---

# Execution Patterns

## 1. Sequential Execution (Happy Path)

```
User

↓

Employee Validation

↓

Trip Details

↓

Expense Collection

↓

Expense Validation

↓

Claim Summary

↓

Human Confirmation

↓

Receipt Upload

↓

Claim Submission

↓

Approval Workflow
```

---

## 2. Parallel Execution

The application performs multiple independent operations simultaneously before merging the results.

```
                 Expense Agent
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼

Employee Grade              Policy Retrieval

        ▼                            ▼

Expense Category      Approval Requirements

        └─────────────┬──────────────┘
                      ▼

      Reimbursement Calculation

                      ▼

            Claim Summary
```

Parallel execution significantly reduces response latency while ensuring accurate reimbursement calculations.

---

## 3. Human-in-the-Loop (HITL)

```
Expense Validation

↓

Policy Validation

↓

Claim Summary

↓

Do you want to submit?

      │
 ┌────┴─────┐

YES         NO

│            │

Receipt      Cancel

Upload       Claim

↓

Submit
```

The user always has the final decision before claim submission.

---

# Duplicate Detection

The system prevents duplicate travel expense submissions.

Duplicate detection compares:

- Employee
- Trip Name
- Destination
- Travel Dates
- Expense Items

If a duplicate exists:

```
A claim already exists for this employee and trip.

Please change the trip name,
travel dates,
or expense details.
```

---

# Conversation Flow

```
Greeting

↓

Employee Validation

↓

Trip Information

↓

Expense Collection

↓

Parallel Policy Validation

↓

Reimbursement Calculation

↓

Claim Summary

↓

Human Approval

↓

Receipt Upload

↓

Submit Claim

↓

Approval Workflow

↓

Status Tracking
```

---

# Technology Stack

## AI

- Amazon Bedrock
- Amazon Nova Lite
- Strands Agents SDK
- Amazon Bedrock AgentCore Runtime

---

## Backend

- Python 3.13
- UV Package Manager

---

## AWS Services

- Amazon Bedrock
- Amazon Bedrock AgentCore
- DynamoDB
- Amazon S3
- Amazon SES
- IAM
- CloudWatch

---

## Data Storage

- Amazon DynamoDB

Tables

- Employees
- ExpensePolicies
- ExpenseCategories
- ExpenseClaims
- Receipts
- ConversationContext

---

# Project Structure

```
expense-management-ai/

├── agents/
│   ├── approval_agent.py
│   ├── coordinator_agent.py
│   ├── employee_agent.py
│   ├── expense_agent.py
│   ├── policy_agent.py
│   └── receipt_agent.py
│
├── conversation/
│   ├── conversation_context.py
│   ├── conversation_orchestrator.py
│   ├── execution_patterns.py
│   └── session_runtime.py
│
├── repositories/
├── services/
├── tools/
├── prompts/
├── config/
├── scripts/
├── chat.py
├── agentcore_runtime.py
└── README.md
```

---

# Running Locally

## Install dependencies

```bash
uv sync
```

---

## Configure AWS credentials

```bash
aws configure
```

---

## Initialize DynamoDB

```bash
uv run python scripts/init_dynamodb.py
```

---

## Run the CLI

```bash
uv run python chat.py
```

---

## Run AgentCore Development Runtime

```bash
agentcore dev
```

---

# Deploy

Deploy to Amazon Bedrock AgentCore

```bash
agentcore launch
```

Invoke

```bash
agentcore invoke "Hello"
```

---

# Example Conversation

```
User

I want to submit an expense claim.

↓

Assistant

What is your employee ID?

↓

EMP0007

↓

Trip Details

↓

Expense Collection

↓

Parallel Policy Validation

↓

Claim Summary

↓

Do you want to submit?

↓

Yes

↓

Upload Receipts

↓

Claim Submitted

↓

Approve Claim

↓

Check Claim Status
```

---

# Sample Capabilities

- Submit Expense Claim
- Retrieve Employee Details
- View Expense Policies
- Upload Receipts
- Check Claim Status
- Approve Claims
- Reject Claims
- List Employee Claims
- List Pending Approvals
- Duplicate Detection

---

# Error Handling

The system includes validation and recovery mechanisms for:

- Invalid employee IDs
- Invalid claim IDs
- Missing receipts
- Policy violations
- Duplicate claims
- Repository failures
- Runtime exceptions
- AWS service errors

---

# Future Enhancements

- OCR-based receipt extraction
- Vision model integration
- Multi-language support
- Voice interface
- Mobile application
- Analytics dashboard
- RAG-powered policy assistant
- Audit logging
- Role-Based Access Control (RBAC)

---

# License

This project was developed as part of the **Tachyon Technologies AIML Internship Program – AWS Track (2026)**.

---

# Acknowledgements

- Amazon Bedrock
- Amazon Bedrock AgentCore
- Strands Agents SDK
- AWS SDK for Python (Boto3)
- Tachyon Technologies