<!--
Sync Impact Report
Version change: 1.0.0 -> 1.1.0
Modified principles: I. Enforce Transfer Eligibility and Limits; V. Verify Behavior Against Requirements
Modified sections: Security and Configuration Handling
Added sections: API and Client Architecture
Removed sections: None
Follow-up TODOs:
- Confirm the original ratification date.
- Define the timezone and day-boundary convention for daily transfer limits.
- Define a measurable response-time target for a "quick response".
- Define the rounding mode for two-decimal monetary rounding.
-->

# Simple Bank Fund Transfer Constitution

## Core Principles

### I. Enforce Transfer Eligibility and Limits
All monetary values MUST use decimal arithmetic and MUST be rounded to two decimal
places. Transfer validation and posting MUST use the rounded value. Every transfer MUST
have an amount greater than Rs 0, be within the customer's daily Rs 1,00,000 limit, and
have a sender with sufficient funds. The source and destination MUST be different
accounts, and both MUST be active. Requests that violate any condition MUST be rejected
without being represented as successful.

### II. Preserve Balance Integrity
An accepted transfer MUST debit the sender and credit the recipient as one consistent
operation. A failed transfer MUST NOT leave a partial balance change. Transfer behavior
MUST preserve these guarantees under concurrent requests.

### III. Persist and Identify Transfers
Every successful transfer MUST be saved and assigned a unique transaction ID. The system
MUST NOT report success until the transfer and its transaction ID have been persisted.

### IV. Give Prompt, Clear Outcomes
The customer MUST receive a prompt, unambiguous outcome for each transfer request,
including whether it succeeded or why it was rejected. A quantitative response-time
target is not yet defined and MUST be established before performance guarantees are made.

### V. Verify Behavior Against Requirements
Every project requirement and rule MUST have one or more automated tests. Tests MUST
cover invalid amounts and rounding, insufficient funds, the daily limit, same-account
transfers, inactive accounts, transaction ID uniqueness, persistence, account-number
masking, API path prefixes, and the web application's API boundary. Boundary cases MUST
be tested whenever limits or eligibility rules change.

## Security and Configuration Handling

The only environment file that may be accessed is `.env.example`. Contributors and
automated agents MUST NOT access, open, read, search, inspect, or print the contents of
`.env.dev`, `.env.local`, `.env.stage`, `.env.test`, or `.env.prod`. Configuration work
MUST use `.env.example` alone.

Full account numbers MUST never be logged. Logs and customer-visible account references
MUST show only the last four digits, formatted as `XXXX1234`.

## API and Client Architecture

Every API endpoint MUST have a path beginning with `/api/v1`. The customer web application
MUST use React and Vite, and it MUST call only APIs under `/api/v1`.

## Delivery and Review

Changes to transfer behavior MUST map to the requirements in `docs/requirement-fund-transfer.md`
and include appropriate tests. Reviews MUST check compliance with this constitution,
especially transfer validation, balance integrity, persistence, and environment-file
handling. Any exception MUST be documented and approved before implementation.

## Governance

This constitution governs project decisions related to the fund-transfer feature.
Amendments MUST include a rationale, be reviewed by the project owner, and update the
version and last-amended date. Changes MUST follow semantic versioning: MAJOR for
backward-incompatible governance changes, MINOR for new or materially expanded
principles or sections, and PATCH for clarifications that do not change obligations.
Every feature review MUST verify compliance with the constitution; deviations MUST be
documented with an approved justification.

**Version**: 1.1.0 | **Ratified**: TODO(RATIFICATION_DATE): confirm original adoption date | **Last Amended**: 2026-10-16
