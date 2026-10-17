# Feature Specification: Fund Transfer

**Feature Branch**: `Not created; no before_specify hook is configured`

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Build the Fund Transfer feature described in `docs/requirement-fund-transfer.md`; write user stories, numbered requirements, and Given/When/Then acceptance criteria for every rule."

## Clarifications

### Session 2026-10-16

- Q: Should rejected transfer requests also receive a unique transaction ID and a saved outcome record? → A: All submitted transfer requests, including rejected requests, are saved with a unique transaction ID and outcome.
- Q: When the same transfer request is retried after a timeout, should it create a second transfer or return the original result? → A: Return the original result without processing a second transfer.
- Q: How many transfer requests should the system support simultaneously at peak? → A: Up to 100 concurrent requests.
- Q: Is this a prototype or a production banking feature, and which country’s financial rules apply? → A: Not decided; production status and jurisdiction remain unresolved, and applicable obligations must be confirmed before production.
- Q: What minimum monthly availability should customers expect for transfers? → A: Defer the target until production status and deployment context are decided.

## User Scenarios & Testing

### User Story 1 - Transfer Money (Priority: P1)

As a Simple Bank customer, I want to transfer money from my savings account to another Simple Bank account so that I can move funds when needed.

**Why this priority**: Initiating a valid transfer is the feature's primary customer value.

**Independent Test**: Submit one eligible transfer between two active, different accounts and verify the resulting balance changes and saved transaction record.

**Acceptance Scenarios**:

1. **Given** the customer has an active savings account, the recipient account is active and different, and the requested amount satisfies the balance and daily-limit rules, **When** the customer submits the transfer, **Then** the transfer completes and both account balances reflect it.
2. **Given** a transfer completes, **When** the customer receives the result, **Then** it includes a unique transaction ID and the transfer is saved.
3. **Given** the customer retries the same request after a timeout, **When** the system recognizes it as the same logical request, **Then** it returns the original transaction ID and outcome without moving funds a second time.

---

### User Story 2 - Understand Transfer Rejections (Priority: P1)

As a customer, I want an understandable response when a transfer cannot be completed so that I know whether my funds moved and what condition prevented the transfer.

**Why this priority**: Customers need a clear and timely outcome for financial actions, including rejected requests.

**Independent Test**: Submit requests that violate each eligibility rule and verify each is rejected without changing balances, with a clear reason.

**Acceptance Scenarios**:

1. **Given** a transfer request violates one or more transfer rules, **When** it is processed, **Then** it is rejected, the customer receives the applicable reason and unique transaction ID, the rejected outcome is saved, and account balances remain unchanged.
2. **Given** any transfer request is submitted, **When** the system processes it, **Then** the customer receives an outcome within one second of submission.

---

### User Story 3 - See Protected Transfer Details (Priority: P2)

As a customer, I want transfer details to identify accounts without exposing full account numbers so that my account information remains protected.

**Why this priority**: Account information must remain protected in customer-visible transfer details and operational records.

**Independent Test**: Review a transfer result and its associated operational log output for a test account, confirming only its final four digits are exposed.

**Acceptance Scenarios**:

1. **Given** a transfer has source and recipient account numbers, **When** account references are shown or logged, **Then** each reference uses `XXXX` followed by only the final four digits.

### Edge Cases

- An entered amount is zero, negative, or rounds to zero at two decimal places.
- The sender's balance exactly equals the transfer amount.
- The customer's cumulative transfers reach exactly Rs 1,00,000 or exceed it by Rs 0.01.
- A source account is just under 30 days old or reaches exactly 30 days old at evaluation time.
- The source-account age limit and customer-wide daily limit are reached independently or concurrently.
- The source or recipient account becomes inactive before the transfer is processed.
- Multiple requests arrive close together and could jointly exceed the daily cap or available balance.
- A customer retries the same request after a timeout.
- A transfer cannot be saved or assigned a transaction ID.
- A customer-visible account reference or log entry could reveal more than the last four digits.
- Applicable financial compliance and record-retention requirements are unknown until deployment status and jurisdiction are confirmed.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST reject a transfer amount that is not greater than Rs 0.
  - **Acceptance**: **Given** the customer submits an amount of Rs 0 or less, **When** the transfer is evaluated, **Then** it is rejected and no account balance changes.
- **FR-002**: The system MUST reject a transfer when the sender does not have enough available balance.
  - **Acceptance**: **Given** the requested amount exceeds the sender's available balance, **When** the customer submits the transfer, **Then** it is rejected and neither account balance changes.
- **FR-003**: The system MUST limit each customer's total outgoing transfers to at most Rs 1,00,000 per UTC calendar day, from midnight UTC inclusive to the next midnight UTC exclusive.
  - **Acceptance**: **Given** the customer's total for the UTC calendar day is Rs 99,000, **When** the customer transfers Rs 1,000, **Then** the transfer is permitted if all other rules pass; **Given** the total would exceed Rs 1,00,000, **When** the customer submits the transfer, **Then** it is rejected without changing balances. This customer-wide cap applies independently of the source-account age cap in FR-013.
- **FR-004**: The system MUST reject a transfer whose source and recipient are the same account.
  - **Acceptance**: **Given** the selected source and recipient resolve to the same account, **When** the customer submits the transfer, **Then** it is rejected and balances remain unchanged.
- **FR-005**: The system MUST allow a transfer only when both the source and recipient accounts are active.
  - **Acceptance**: **Given** either account is inactive when the transfer is processed, **When** the customer submits the transfer, **Then** it is rejected and balances remain unchanged.
- **FR-006**: Every submitted transfer request MUST be saved with a unique transaction ID and an outcome of completed or rejected.
  - **Acceptance**: **Given** a submitted request completes or is rejected, **When** its result is returned, **Then** it has a saved record with a unique transaction ID and the corresponding outcome; rejected requests do not change balances.
- **FR-007**: The customer MUST receive a clear success or rejection outcome within one second of submitting every transfer request.
  - **Acceptance**: **Given** a transfer request is submitted, **When** processing succeeds or fails, **Then** the customer receives its outcome within one second of submission.
- **FR-008**: Monetary amounts and calculations MUST use exact decimal currency values rounded half up to two decimal places.
  - **Acceptance**: **Given** a transfer amount or resulting balance has more than two fractional digits, **When** it is evaluated or shown, **Then** it is rounded half up to two decimal places and the rounded value is used consistently.
- **FR-009**: Transfer-related logs and customer-visible account references MUST NOT expose full account numbers and MUST show only the last four digits in the form `XXXX1234`.
  - **Acceptance**: **Given** a transfer involves account numbers, **When** account references are shown or logged, **Then** the full numbers are absent and only `XXXX` plus the final four digits is present.
- **FR-010**: Every functional and security rule in this specification MUST have at least one automated test mapped to its acceptance criteria.
  - **Acceptance**: **Given** the specification's requirements are reviewed for test coverage, **When** the coverage mapping is checked, **Then** each functional, security, and performance requirement from FR-001 through FR-009 and FR-011 through FR-013 has at least one automated test for its stated behavior.
- **FR-011**: A retry identified as the same logical transfer request MUST return the original transaction ID and outcome without applying the transfer a second time. A separately initiated transfer MUST be treated as a new request.
  - **Acceptance**: **Given** a transfer request has already been processed but its response timed out, **When** the same logical request is retried, **Then** the original result is returned and sender and recipient balances are changed no more than once.
- **FR-012**: The system MUST support up to 100 concurrent transfer requests while preserving all transfer rules and the one-second response target.
  - **Acceptance**: **Given** 100 transfer requests are processed concurrently, **When** the requests are a mix of eligible and ineligible transfers, **Then** each receives the correct outcome within one second and all account balances and saved records remain consistent with the applicable rules.
- **FR-013**: The system MUST limit outgoing transfers from each source account to Rs 50,000 per UTC calendar day while that account is less than 30 elapsed days old, and to Rs 1,00,000 per UTC calendar day once it is at least 30 elapsed days old. The applicable source-account cap MUST apply alongside the customer-wide cap in FR-003, and exceeding either cap MUST reject the transfer.
  - **Acceptance**: **Given** a source account is 29 days old at transfer evaluation, its completed outgoing total for the UTC calendar day is Rs 49,000, and the customer's total is within the FR-003 limit, **When** the customer transfers Rs 1,000, **Then** the transfer completes and the source-account total reaches Rs 50,000.
  - **Acceptance**: **Given** a source account less than 30 days old has already transferred Rs 50,000 during the UTC calendar day, **When** another transfer is submitted from it, **Then** it is rejected with `DAILY_LIMIT_EXCEEDED`, the rejected outcome is saved, and balances remain unchanged.
  - **Acceptance**: **Given** a source account is exactly 30 elapsed days old, its completed outgoing total is Rs 99,000, and the customer's total remains within the FR-003 limit, **When** the customer transfers Rs 1,000, **Then** the transfer is permitted and the source-account total reaches Rs 1,00,000.
  - **Acceptance**: **Given** a recent source account's transfer would stay within its Rs 50,000 account cap but cause the customer's total to exceed Rs 1,00,000, **When** the transfer is evaluated, **Then** it is rejected under FR-003 without changing balances.

### Key Entities

- **Customer**: The person initiating a transfer and subject to the daily transfer limit.
- **Account**: A Simple Bank account with an owner, opening time, status, and balance; its age determines the source-account daily transfer cap.
- **Transfer**: A request to move a monetary amount between two accounts, with a unique transaction ID and saved outcome record; completed requests move funds, while rejected requests do not.

## API Contract

### `POST /api/v1/transfers`

The endpoint evaluates and saves a transfer request. A new request returns `201 Created` whether its transaction status is `completed` or `rejected`; a retry with the same idempotency key returns `200 OK` with the original result.

**Request fields**:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `from_account` | string | Yes | Sender account number. |
| `to_account` | string | Yes | Recipient account number. |
| `amount` | decimal string | Yes | Transfer amount in Rs, evaluated using the rounding rule in FR-008. |
| `idempotency_key` | string | Yes | Identifies retries of the same logical request. |

**Response fields**:

| Field | Type | Description |
| --- | --- | --- |
| `transaction_id` | string | Unique ID of the saved transaction. |
| `from_account` | string | Masked sender account reference, formatted `XXXX1234`. |
| `to_account` | string | Masked recipient account reference, formatted `XXXX1234`. |
| `amount` | decimal string | Evaluated transfer amount in Rs, to two decimal places. |
| `status` | string | `completed` or `rejected`. |
| `created_at` | string | Transaction creation time in UTC using ISO 8601 format. |
| `error_code` | string or null | Rejection code, or `null` when the transfer completes. |
| `message` | string | Customer-readable outcome. |

**Rejection error codes**:

| Code | Meaning |
| --- | --- |
| `INSUFFICIENT_BALANCE` | The sender does not have enough balance. |
| `DAILY_LIMIT_EXCEEDED` | The transfer would exceed the source account's age-based daily cap in FR-013 or the customer's Rs 1,00,000 daily cap in FR-003. |
| `SAME_AMOUNT` | The source and destination identify the same account, as prohibited by FR-004. |
| `ACCOUNT_INACTIVE` | The source or destination account is inactive. |
| `INVALID_AMOUNT` | The amount is zero or less after applying FR-008 rounding. |

Every evaluated request, including a rejected request, returns its saved transaction outcome and unique transaction ID. A retry with the same `idempotency_key` returns the original transaction result without applying the transfer again.

## Data Model

| Entity | Field | Type | Description |
| --- | --- | --- | --- |
| `Account` | `account_number` | string | Unique account identifier. |
| `Account` | `customer_id` | string | Identifier of the account owner. |
| `Account` | `balance` | decimal | Account balance in Rs, represented and calculated using exact decimal currency values. |
| `Account` | `status` | string | Account state; transfer eligibility requires `active`. |
| `Account` | `opened_at` | string | Account opening timestamp in UTC, used to determine whether the account is less than 30 elapsed days old at transfer evaluation. |
| `Transaction` | `transaction_id` | string | Unique identifier for the saved transfer outcome. |
| `Transaction` | `from_account` | string | Sender account number. |
| `Transaction` | `to_account` | string | Recipient account number. |
| `Transaction` | `amount` | decimal | Evaluated transfer amount in Rs, to two decimal places. |
| `Transaction` | `status` | string | `completed` or `rejected`. |
| `Transaction` | `created_at` | string | Creation time in UTC using ISO 8601 format. |

## Example Transfers

| # | From | To | Amount (Rs) | Relevant starting conditions | Expected result |
| --- | --- | --- | ---: | --- | --- |
| 1 | `XXXX1001` | `XXXX2002` | 500.00 | Both accounts active; sender balance Rs 2,000.00; daily outgoing total Rs 1,000.00. | `completed`; sender balance becomes Rs 1,500.00, recipient balance increases by Rs 500.00, and a transaction ID is returned. |
| 2 | `XXXX1001` | `XXXX2002` | 0.00 | Both accounts active. | `rejected` with `INVALID_AMOUNT`; balances are unchanged and the rejected transaction is saved. |
| 3 | `XXXX1001` | `XXXX2002` | 150.00 | Both accounts active; sender balance Rs 100.00. | `rejected` with `INSUFFICIENT_BALANCE`; balances are unchanged and the rejected transaction is saved. |
| 4 | `XXXX1001` | `XXXX2002` | 600.00 | Both accounts active; daily outgoing total is Rs 99,500.00. | `rejected` with `DAILY_LIMIT_EXCEEDED`; balances are unchanged and the rejected transaction is saved. |
| 5 | `XXXX1001` | `XXXX2002` | 50.00 | Recipient account is inactive. | `rejected` with `ACCOUNT_INACTIVE`; balances are unchanged and the rejected transaction is saved. |

### Account-Age Daily Limit Examples

All examples assume both accounts are active, the sender has sufficient balance, and all rules other than the stated daily-limit conditions pass. The customer-wide UTC-day total includes completed outgoing transfers from all of the customer's accounts; the account-age cap applies to the stated source account.

| Account age at evaluation | Source-account completed outgoing total today (Rs) | Customer completed outgoing total today (Rs) | Request (Rs) | Expected result |
| --- | ---: | ---: | ---: | --- |
| 29 elapsed days | 49,000.00 | 49,000.00 | 1,000.00 | `completed`; both totals reach Rs 50,000.00 and remain within their caps. |
| 29 elapsed days | 50,000.00 | 50,000.00 | 0.01 | `rejected` with `DAILY_LIMIT_EXCEEDED`; rejected outcome is saved and balances are unchanged. |
| 29 elapsed days | 49,000.00 | 99,500.00 | 1,000.00 | `rejected` with `DAILY_LIMIT_EXCEEDED`; the account cap would be met, but the customer-wide cap would be exceeded. |
| Exactly 30 elapsed days | 99,000.00 | 99,000.00 | 1,000.00 | `completed`; both totals reach Rs 1,00,000.00. |
| Exactly 30 elapsed days | 1,00,000.00 | 1,00,000.00 | 0.01 | `rejected` with `DAILY_LIMIT_EXCEEDED`; rejected outcome is saved and balances are unchanged. |

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of logical transfer requests have one saved outcome record with a unique transaction ID; retries return the original result, and completed transfers change balances only once.
- **SC-002**: 100% of requests that violate a transfer rule are rejected without changing either account balance.
- **SC-003**: 100% of transfer-related account references in customer-visible details and operational logs expose no more than the final four digits.
- **SC-004**: 100% of transfer requests receive a success or rejection outcome within one second of submission.
- **SC-005**: The system processes 100 concurrent transfer requests with 100% correct outcomes within one second and no balance or record inconsistencies.
- **SC-006**: 100% of source accounts are limited to Rs 50,000 in completed outgoing transfers per UTC day before 30 elapsed days of age and Rs 1,00,000 from the 30-day boundary onward; no transfer may exceed either its account cap or the customer's cap.

## Assumptions

- The Rs 1,00,000 daily cap applies to the customer's cumulative outgoing transfer amount, not to each individual request.
- A total exactly equal to Rs 1,00,000 is permitted because the requirement says "at most".
- The new-account cap is per source account and is applied in addition to the existing customer-wide cap; the first cap reached governs.
- Account age is measured in elapsed UTC time from the account's opening timestamp to transfer evaluation; an account exactly 30 elapsed days old receives the Rs 1,00,000 account cap.
- Both account-age and customer-wide daily caps use the same UTC calendar-day window, and only completed outgoing transfers count toward either cap.
- The customer is already identified by the bank web app; registration and authentication are outside this feature's scope.
- Rejected requests are saved with a unique transaction ID and rejected outcome but do not move funds.
- Production status and applicable jurisdiction are not yet decided; this specification does not define jurisdiction-specific compliance or record-retention obligations, which must be confirmed before production.
- No monthly availability target is set; it must be decided before production.
- Implementation must comply with `.specify/memory/constitution.md`; architecture constraints are left to planning and are not specified as user-facing requirements here.
