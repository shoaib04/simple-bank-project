# Data Model: Mini Statement

## Existing Entities

### Account

| Field | Type | Constraints |
| --- | --- | --- |
| `account_number` | string | Primary key; must be masked in customer-visible statement output and logs. |
| `customer_id` | string/UUID | Required owner identity; statement access is restricted to the authenticated owner. |
| `opened_at` | `TIMESTAMPTZ` | Required; existing account opening timestamp. |
| `balance` | `NUMERIC(18,2)` | Required current balance; never modified by statement reads. |
| `status` | enum/string | `active` or `inactive`; an owner may read an inactive account's history. |

### Transaction

| Field | Type | Constraints |
| --- | --- | --- |
| `transaction_id` | UUID | Primary key; used as the deterministic tie-breaker when `created_at` timestamps match. |
| `from_account` | string | Required source account foreign key. |
| `to_account` | string | Required destination account foreign key. |
| `amount` | `NUMERIC(18,2)` | Required positive transfer amount for completed transactions. |
| `status` | enum/string | Completed entries are included; rejected transactions are excluded. |
| `created_at` | `TIMESTAMPTZ` | Required; returned as ISO 8601 UTC `date`. |
| `from_balance_after` | `NUMERIC(18,2)` or null | Source account balance immediately after a completed debit; null for rejected transactions. |
| `to_balance_after` | `NUMERIC(18,2)` or null | Destination account balance immediately after a completed credit; null for rejected transactions. |

For `status = completed`, both snapshot fields are required. For `status = rejected`, both snapshot fields are null. A completed transfer updates both account balances, writes both snapshots, and persists the transaction in one database transaction.

Existing completed rows are backfilled by expanding each transfer into its source debit and destination credit, ordering account-side events by `(created_at, transaction_id)`, and reversing later completed effects from the account's current balance. The migration verifies that each account's newest calculated snapshot equals its current balance before it completes.

The pre-snapshot schema has no explicit posting sequence. Deterministic timestamp/UUID order therefore cannot prove the true commit order of every legacy concurrent transfer. Reconcile backfilled history against authoritative history before exposing legacy `balance_after` values; block migration or release for accounts that do not reconcile.

## Mini Statement Entry

A response projection for one completed transaction from the requested account's perspective:

| Field | Type | Constraints |
| --- | --- | --- |
| `date` | string | ISO 8601 UTC timestamp sourced from `created_at`. |
| `description` | string | Transfer direction and masked counterparty, e.g. `Transfer to XXXX5678`. |
| `debit` | decimal string | Positive `amount` for the source account, otherwise exactly `0.00`. |
| `credit` | decimal string | Positive `amount` for the destination account, otherwise exactly `0.00`. |
| `amount` | decimal string | Positive transfer amount with exactly two fractional digits. |
| `balance_after` | decimal string | `from_balance_after` for the source account or `to_balance_after` for the destination account, with exactly two fractional digits. |

## Mini Statement Response

- `account_number`: required masked account reference, `XXXX` plus the final four digits.
- `transactions`: required array containing zero to 10 completed entries.
- Items are ordered by `created_at DESC, transaction_id DESC` and the query returns at most 10.
- The response contains no customer identifier, raw counterparty account number, rejected transaction, or mutable current balance.

## Read and Security Invariants

- Resolve the requested account using both `account_number` and the authenticated `customer_id`; return the same not-found result for absent and non-owned accounts.
- The statement query is read-only and filters to completed transfers where the account is either the source or destination.
- The full account number in the path is used only for lookup. Do not echo or log it.
- Mask the statement account and counterparty references with the existing shared account-number masking helper.
- Account history uses account-side transaction indexes on `(from_account, created_at, transaction_id)` and `(to_account, created_at, transaction_id)`.
