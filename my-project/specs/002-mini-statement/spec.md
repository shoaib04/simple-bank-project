# Feature Specification: Mini Statement

**Feature Branch**: `Not created; no before_specify hook is configured`

**Created**: 2026-10-17

**Status**: Draft

**Input**: User description: "Mini Statement: GET `/api/v1/accounts/{account_number}/mini-statement` returns the last 10 transactions (date, description, debit, credit, amount, balance after), newest first. The account number in the response must be masked, e.g. `XXXX1234`. Frontend features also need to be developed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Recent Account Activity (Priority: P1)

As a Simple Bank customer, I want to view the latest transactions for an account I own so that I can quickly review its recent activity.

**Why this priority**: A concise view of recent account activity is the primary value of a mini statement.

**Independent Test**: Request the statement for an owned account with more than 10 completed transactions and verify that exactly the 10 newest are returned in newest-first order with all required fields.

**Acceptance Scenarios**:

1. **Given** the authenticated customer owns the requested account and it has more than 10 completed transactions, **When** the customer opens its mini statement, **Then** the 10 newest transactions are shown in descending date order.
2. **Given** the account has between 1 and 9 completed transactions, **When** the statement is requested, **Then** all of them are returned in newest-first order.
3. **Given** the account has no completed transactions, **When** the customer opens the statement, **Then** the response contains an empty transaction list and the frontend shows an empty state.
4. **Given** two transactions have the same timestamp, **When** they are returned, **Then** their order is stable between repeated requests.

---

### User Story 2 - Understand Each Balance Change (Priority: P1)

As a customer, I want each statement entry to show whether money moved out or in and the resulting balance so that I can understand how the account balance changed.

**Why this priority**: A transaction list is useful only when customers can distinguish debits from credits and reconcile the displayed balance.

**Independent Test**: Verify one outgoing and one incoming completed transfer and compare their date, description, debit, credit, amount, and balance-after values with the account's posted transaction history.

**Acceptance Scenarios**:

1. **Given** a completed outgoing transfer, **When** it appears in the source account's statement, **Then** `debit` equals the transfer amount, `credit` is `0.00`, and `balance_after` is the source balance immediately after the transfer.
2. **Given** a completed incoming transfer, **When** it appears in the destination account's statement, **Then** `credit` equals the transfer amount, `debit` is `0.00`, and `balance_after` is the destination balance immediately after the transfer.
3. **Given** a statement entry is displayed, **When** the customer reviews it, **Then** `amount` is the positive transfer amount and the description indicates the transfer direction and masked counterparty account.

---

### User Story 3 - Open a Statement From the Web App (Priority: P1)

As a customer, I want to request a mini statement for an account I own from the Simple Bank web app so that I can review activity without using a separate tool.

**Why this priority**: The statement must be accessible from the customer workflow, not only through a machine interface.

**Independent Test**: Enter or select an account number in the web app and verify that an owned account's statement loads, renders transaction details, and shows a masked account reference; verify loading, empty, and error states.

**Acceptance Scenarios**:

1. **Given** the customer knows or selects an account number, **When** the customer requests its statement, **Then** the frontend loads it through the versioned bank API and the API enforces account ownership.
2. **Given** the statement request is loading, returns no transactions, or fails, **When** the frontend renders the view, **Then** it shows the corresponding loading, empty, or recoverable error state.
3. **Given** a statement is displayed, **When** the customer views the selected account or a transaction description, **Then** account numbers are masked to `XXXX` plus the final four digits.

### Edge Cases

- An account has no completed transactions or fewer than 10.
- More than 10 transactions exist; only the newest 10 are returned.
- Multiple transactions share the same timestamp.
- The account exists but belongs to another customer.
- The requested account does not exist or is inactive.
- A transaction is rejected and saved but did not move funds.
- A transaction amount is a debit for one account and a credit for another.
- A statement entry's historical balance must remain correct after later transfers occur.
- An account reference could be exposed in a response, description, error, or operational log.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST identify the customer from the bank application's trusted authentication context and MUST return a statement only for an account owned by that customer.
  - **Acceptance**: **Given** the requested account is not owned by the authenticated customer, **When** the statement is requested, **Then** the system returns no account or transaction details and responds as if the account were unavailable.
- **FR-002**: The system MUST provide `GET /api/v1/accounts/{account_number}/mini-statement` for an owned account.
  - **Acceptance**: **Given** a valid request for an owned account, **When** the endpoint is called, **Then** it returns a successful response containing the masked account reference and transaction list.
- **FR-003**: The system MUST return no more than the 10 newest completed transactions for the requested account, ordered newest first.
  - **Acceptance**: **Given** an account has more than 10 completed transactions, **When** its statement is requested, **Then** exactly the 10 newest are returned in descending timestamp order; **Given** it has fewer than 10, **Then** all available completed transactions are returned.
- **FR-004**: Each transaction entry MUST include `date`, `description`, `debit`, `credit`, `amount`, and `balance_after`.
  - **Acceptance**: **Given** a completed outgoing or incoming transfer, **When** its entry is returned, **Then** all six fields describe that account's side of the transfer and `balance_after` equals the account balance immediately after that transaction.
- **FR-005**: `date` MUST be expressed as an ISO 8601 UTC timestamp. `debit`, `credit`, `amount`, and `balance_after` MUST be exact decimal currency strings with two fractional digits. `amount` MUST be positive; exactly one of `debit` or `credit` MUST be positive and the other MUST be `0.00`.
  - **Acceptance**: **Given** a statement contains an entry, **When** the customer reads its monetary fields, **Then** they are exact two-decimal values and the debit/credit direction matches the transfer.
- **FR-006**: The response's `account_number` MUST be masked as `XXXX` followed by only the account's final four digits. Any account reference in `description` MUST also be masked.
  - **Acceptance**: **Given** an account number is included in a statement response, **When** it is returned, **Then** no more than its final four digits are visible and the reference is formatted `XXXX1234`.
- **FR-007**: The statement MUST include completed transfers only; rejected transfer attempts MUST NOT appear as debits or credits.
  - **Acceptance**: **Given** a rejected attempt has a saved transaction record but did not change the account balance, **When** the statement is requested, **Then** the rejected attempt is absent.
- **FR-008**: The mini statement MUST be read-only and MUST NOT change account balances or transaction records.
  - **Acceptance**: **Given** a customer requests or refreshes a statement, **When** the request completes, **Then** account balances and saved transactions are unchanged.
- **FR-009**: The customer web app MUST provide a mini statement view with account selection and render the returned entries newest first using the required fields.
  - **Acceptance**: **Given** the customer selects an owned account, **When** its statement loads, **Then** the view displays up to 10 rows with date, description, debit, credit, amount, and balance after.
- **FR-010**: The frontend MUST provide loading, empty, and recoverable error states for statement requests.
  - **Acceptance**: **Given** the request is pending, returns no transactions, or fails, **When** the view updates, **Then** the customer sees a distinct loading, empty, or retryable error state.
- **FR-011**: Full account numbers MUST NOT appear in customer-visible statement content or transfer-related operational logs.
  - **Acceptance**: **Given** a statement is returned or logged, **When** its account references are inspected, **Then** only masked references are present.
- **FR-012**: Every functional and security rule in this specification MUST have at least one automated test mapped to its acceptance criteria.
  - **Acceptance**: **Given** statement requirements are reviewed for test coverage, **When** the coverage mapping is checked, **Then** each applicable requirement from FR-001 through FR-011 has at least one automated test for its stated behavior.

### API Contract

`GET /api/v1/accounts/{account_number}/mini-statement`

The authenticated customer identity is supplied by the bank application; it is not a caller-controlled query or response field. The path parameter is the requested account's full number and MUST NOT be logged or echoed back.

**Successful response (`200 OK`)**:

| Field | Type | Description |
| --- | --- | --- |
| `account_number` | string | Masked account reference, formatted `XXXX1234`. |
| `transactions` | array | Zero to 10 completed transactions, newest first. |
| `transactions[].date` | string | Transaction timestamp in ISO 8601 UTC format. |
| `transactions[].description` | string | Direction and masked counterparty, such as `Transfer to XXXX5678` or `Transfer from XXXX1234`. |
| `transactions[].debit` | decimal string | Outgoing amount, or `0.00` for an incoming transfer. |
| `transactions[].credit` | decimal string | Incoming amount, or `0.00` for an outgoing transfer. |
| `transactions[].amount` | decimal string | Positive transfer amount, with two fractional digits. |
| `transactions[].balance_after` | decimal string | Account balance immediately after this transaction, with two fractional digits. |

Example:

```json
{
  "account_number": "XXXX1234",
  "transactions": [
    {
      "date": "2026-10-17T12:00:00Z",
      "description": "Transfer to XXXX5678",
      "debit": "125.50",
      "credit": "0.00",
      "amount": "125.50",
      "balance_after": "874.50"
    }
  ]
}
```

**Error responses**:

| Status | Meaning |
| --- | --- |
| `401 Unauthorized` | No authenticated customer context is available. |
| `404 Not Found` | The account does not exist or is not owned by the authenticated customer. |
| `422 Unprocessable Entity` | The account number path parameter is malformed. |

### Key Entities *(include if feature involves data)*

- **Account**: A bank account owned by a customer, identified by an account number and current balance.
- **Transaction**: A completed movement between two accounts with an amount and creation time; each account sees its own debit or credit side.
- **Mini Statement Entry**: A customer-facing representation of one completed transaction with direction, exact amount, masked counterparty description, date, and resulting account balance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of statement responses contain at most 10 completed transactions in newest-first order.
- **SC-002**: 100% of returned entries contain all six required fields, and their debit/credit direction and `balance_after` reconcile with the account's completed transfer history.
- **SC-003**: 100% of account references in statement responses and operational logs reveal no more than the final four digits.
- **SC-004**: 100% of requests for accounts not owned by the authenticated customer return no account or transaction details.
- **SC-005**: Customers can access a selected account's statement in the web app and distinguish loading, empty, populated, and recoverable-error states.

## Assumptions

- Only completed transfers are financial statement entries; rejected attempts remain available in transaction records but are not shown as account activity.
- The account owner may view historical statements for an inactive account; ownership is required, active status is not.
- Account dates are shown in UTC; timestamps that are exactly equal use a stable system-defined order.
- `debit` and `credit` use `0.00` on the non-applicable side; `amount` is always the positive transfer amount.
- `balance_after` is the account balance immediately after the transaction and remains stable when later transactions occur.
- The existing bank authentication context is reused; registration, account opening, and account discovery are outside this feature. A customer may enter or select an account number they own.
- The statement view is read-only and shows no more than the most recent 10 completed transfers; pagination and downloadable statements are out of scope.
