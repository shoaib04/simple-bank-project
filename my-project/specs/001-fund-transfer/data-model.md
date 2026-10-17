# Data Model: Fund Transfer

## Entities

### Customer

The existing bank customer identity used to scope account ownership, daily limits, and idempotency. The transfer API obtains `customer_id` from trusted application authentication context; callers do not submit it as a request field.

| Field | Type | Constraints |
| --- | --- | --- |
| `customer_id` | string/UUID | Primary key; identity supplied by the bank application. |

### Account

| Field | Type | Constraints |
| --- | --- | --- |
| `account_number` | string | Primary key; customer-facing responses must mask all but the final four characters. |
| `customer_id` | string/UUID | Required; references the account owner. |
| `opened_at` | `TIMESTAMPTZ` | Required; account opening timestamp used to determine the account-age transfer cap at evaluation time. |
| `balance` | `NUMERIC(18,2)` | Required; stored and updated using exact decimal currency values. |
| `status` | enum/string | Required; transfer eligibility requires `active`. |

A customer owns one or more accounts. A transfer's source account must belong to the authenticated customer; the recipient may belong to another Simple Bank customer. Source and recipient must be different active accounts. Account references in a transfer request must resolve to persisted accounts.

### Transaction

| Field | Type | Constraints |
| --- | --- | --- |
| `transaction_id` | UUID/string | Primary key; unique for each evaluated request. |
| `from_account` | string | Required; references the source account. |
| `to_account` | string | Required; references the recipient account. |
| `amount` | `NUMERIC(18,2)` | Required; normalized with half-up rounding before rule evaluation. Rejected rows may retain a rounded non-positive amount. |
| `status` | enum/string | Required; terminal value is `completed` or `rejected`. |
| `created_at` | `TIMESTAMPTZ` | Required; generated in UTC by the persistence layer. |
| `customer_id` | string/UUID | Required; initiating customer and daily-limit/idempotency scope. |
| `idempotency_key` | string | Required; unique together with `customer_id`. |
| `error_code` | string/null | Required for rejected transactions; null for completed transactions. |

The `customer_id`, `idempotency_key`, and `error_code` fields are persistence support needed to enforce and replay the specified idempotency and rejected outcomes. A unique constraint on `(customer_id, idempotency_key)` prevents duplicate processing. Persist the normalized request fields so reuse of a key with a different payload can be rejected with `409 Conflict`.

## Relationships and Invariants

- One customer owns many accounts and initiates many transactions.
- Each transaction references one source account and one recipient account.
- For `completed` transactions, `amount` is greater than zero, the accounts differ, both accounts are active, and `error_code` is null.
- For `rejected` transactions, `error_code` identifies the first failed rule; no account balance is changed.
- Every saved transaction has a unique ID. Retrying the same customer/key and normalized request returns the original terminal transaction.
- Both account balance changes and the completed transaction are committed in one database transaction. Rejected transaction persistence does not alter balances.
- Customer-wide and source-account outgoing totals are calculated from completed transactions in the UTC calendar-day interval `[00:00, next 00:00)`. The customer and source-account rows are locked while checking both totals and deciding the outcome so concurrent transfers cannot jointly exceed either limit. The source-account cap is Rs 50,000 before 30 elapsed days of age and Rs 1,00,000 from the 30-day boundary onward; the customer-wide cap remains Rs 1,00,000. Rejections do not count toward either daily total.
- Use a stable account-number lock order when locking both accounts to reduce deadlock risk.
- Store monetary values as exact decimals; do not pass through binary floating-point values.
- Store full account numbers only where required for account resolution and transaction processing. Mask account references in every customer-visible response and operational log.

## State

A transfer request is evaluated and persisted directly as a terminal `completed` or `rejected` transaction within one database transaction. No durable `processing` state is exposed. For a completed outcome, the source debit, recipient credit, and transaction row commit together; for a rejected outcome, only the transaction row commits.
