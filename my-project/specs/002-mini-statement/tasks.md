# Tasks: Mini Statement

**Input**: Design documents from `/specs/002-mini-statement/`

**Prerequisites**: `spec.md`; existing application structure is defined in `backend/pyproject.toml`, `frontend/package.json`, and the current transfer/account modules.

**Tests**: Required by FR-012 and the project constitution. The PostgreSQL tests use the existing `TEST_DATABASE_URL`-guarded fixture in `backend/tests/conftest.py`.

**Organization**: Tasks are grouped by user story. Existing Python, FastAPI, SQLAlchemy, PostgreSQL, React, and Vite projects are reused; no new dependency is planned.

## Path Conventions

- Backend: `backend/src/simple_bank/`, `backend/tests/`
- Customer web client: `frontend/src/`, `frontend/tests/`
- Feature design and validation docs: `specs/002-mini-statement/`

## Phase 1: Setup

**Purpose**: Add the Mini Statement feature module and prepare regression coverage.

- [X] T001 [P] Create the frontend Mini Statement feature directory and initial test files at `frontend/src/features/mini-statement/`, `frontend/tests/mini-statement/`, and `backend/tests/` without changing existing project manifests or dependencies.
- [X] T002 [P] Add PostgreSQL integration tests in `backend/tests/integration/test_transaction_balance_snapshots.py` proving completed transfers persist source and destination post-transfer balances atomically, rejected transfers keep both snapshots null, and a failed transaction insert rolls back balances and snapshots. Add backfill tests that verify legacy snapshots against authoritative historical balances and reject unreconciled accounts.

---

## Phase 2: Foundational

**Purpose**: Preserve historical account balances on each completed transfer so statements remain correct after later transfers.

- [X] T003 Add `from_balance_after` and `to_balance_after` fields to the `Transaction` model in `backend/src/simple_bank/db/models.py` as nullable `NUMERIC(18,2)` values; add a check constraint requiring both values for `completed` transactions and both null for `rejected` transactions.
- [X] T004 Create `backend/alembic/versions/0002_transfer_balance_snapshots.py` to add the snapshot columns, backfill existing completed rows in stable `(created_at, transaction_id)` order using each account's current balance and later completed transaction effects, leave rejected rows null, and support downgrade. Because legacy rows have no posting sequence, reconcile derived values against authoritative history and abort or block release for any unreconciled account. Offline PostgreSQL DDL and Ruff pass; live backfill execution awaits a PostgreSQL test service.
- [X] T005 Update `backend/src/simple_bank/services/transfer_service.py` to set `from_balance_after` and `to_balance_after` after the atomic debit/credit and before flush; leave both null for rejected transactions and preserve rollback behavior.

**Checkpoint**: Completed transactions contain stable post-transfer balances for both account sides; rejected attempts remain excluded from account activity.

---

## Phase 3: User Story 1 - View Recent Account Activity (Priority: P1)

**Goal**: An authenticated customer can retrieve up to 10 newest completed transactions for an account they own.

**Independent Test**: Request a statement for an owned account with more than 10 completed transfers; verify exactly the newest 10 appear in descending order, rejected attempts are absent, and an account not owned by the customer returns no statement data.

### Tests for User Story 1

- [X] T013 [P] [US3] Add API-client tests in `frontend/tests/mini-statement/api.test.js` asserting the account path is URL-encoded, the request uses only `/api/v1/accounts/{account_number}/mini-statement`, credentials are included, and API errors are surfaced.
- [X] T014 [P] [US3] Add component tests in `frontend/tests/mini-statement/MiniStatement.test.jsx` for account submission, loading feedback, empty state, populated newest-first entries, debit/credit/balance rendering, masked account references, and retryable errors.

### Implementation for User Story 1

- [X] T008 [US1] Define `MiniStatementEntry` and `MiniStatementResponse` Pydantic models in `backend/src/simple_bank/schemas/mini_statement.py`; require a masked top-level account reference, an array of zero to 10 entries, UTC date, description, decimal-string debit/credit/amount/balance fields, positive `amount`, and exactly one positive debit or credit.
- [X] T009 [US1] Implement the read-only account statement query in `backend/src/simple_bank/services/mini_statement_service.py`; verify account ownership from the authenticated `customer_id`, query only `completed` transactions where the account is `from_account` or `to_account`, order by `created_at DESC, transaction_id DESC`, and limit to 10. PostgreSQL query execution remains unverified until `TEST_DATABASE_URL` is available.
- [X] T010 [US1] Add `GET /accounts/{account_number}/mini-statement` in `backend/src/simple_bank/api/v1/accounts.py` and register its router in `backend/src/simple_bank/api/v1/router.py`; return the same `404` for missing and non-owned accounts, use the existing trusted customer dependency, and never log or echo the raw path account number.

**Checkpoint**: The endpoint returns only the authenticated customer's latest completed account activity and does not mutate financial data.

---

## Phase 4: User Story 2 - Understand Each Balance Change (Priority: P1)

**Goal**: Every statement row accurately shows the account's debit or credit and the balance immediately after that transaction.

**Independent Test**: Create a completed outgoing and incoming transfer, then later transfers; verify each earlier row still shows the original side-specific post-transaction balance and exact two-decimal direction values.

### Tests for User Story 2

- [X] T011 [P] [US2] Add PostgreSQL integration tests in `backend/tests/integration/test_mini_statement_balances.py` proving outgoing rows use `from_balance_after`, incoming rows use `to_balance_after`, the non-applicable debit/credit is `0.00`, and later transfers do not alter earlier `balance_after` values. Authored and lint-clean; execution awaits TEST_DATABASE_URL.

### Implementation for User Story 2

- [X] T012 [US2] Map statement transactions to `MiniStatementEntry` values in `backend/src/simple_bank/services/mini_statement_service.py`: set positive `amount`, populate only the account's applicable debit or credit, read its side-specific stored balance snapshot, format exact two-place decimal strings, convert the timestamp to UTC, and describe the direction using a masked counterparty.

**Checkpoint**: Both sides of completed transfers reconcile with their account history, including after subsequent activity.

---

## Phase 5: User Story 3 - Open a Statement From the Web App (Priority: P1)

**Goal**: A customer can enter or select an owned account in the web app and see its latest statement with loading, empty, and recoverable-error states.

**Independent Test**: Open the Mini Statement view, request an owned account, and verify the masked account reference and newest-first rows; separately verify empty and retryable error states.

### Tests for User Story 3

- [ ] T013 [P] [US3] Add API-client tests in `frontend/src/features/mini-statement/api.test.js` asserting the account path is URL-encoded, the request uses only `/api/v1/accounts/{account_number}/mini-statement`, credentials are included, and API errors are surfaced.
- [ ] T014 [P] [US3] Add component tests in `frontend/tests/mini-statement/MiniStatement.test.jsx` for account submission, loading feedback, empty state, populated newest-first entries, debit/credit/balance rendering, masked account references, and retryable errors.

### Implementation for User Story 3

- [X] T015 [US3] Implement the statement API client in `frontend/src/features/mini-statement/api.js` using the existing fetch/error pattern and `GET /api/v1/accounts/${encodeURIComponent(accountNumber)}/mini-statement`.
- [X] T016 [US3] Implement the Mini Statement view in `frontend/src/features/mini-statement/MiniStatement.jsx` with account-number entry, request submission, pending state, recoverable error/retry, empty state, and a semantic table for date, description, debit, credit, amount, and balance after.
- [X] T017 [US3] Add navigation between transfers and Mini Statement in `frontend/src/App.jsx` so both customer flows remain reachable without changing the existing transfer form behavior.
- [X] T018 [US3] Add responsive statement-table and view styles in `frontend/src/styles.css`, keeping masked account references and monetary values readable on narrow screens.

**Checkpoint**: Customers can request and understand a mini statement in the web app without exposing full account numbers.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify requirement coverage and document runnable validation.

- [X] T019 [P] Create `backend/tests/mini_statement_requirements_traceability.md` mapping FR-001 through FR-011 to API, service, database, and frontend test paths, satisfying FR-012.
- [X] T020 [P] Create `specs/002-mini-statement/quickstart.md` with `uv sync --locked`, migration, backend test, `npm ci`, frontend test/build, account ownership, empty statement, and 10-row ordering scenarios; document the PostgreSQL `TEST_DATABASE_URL` prerequisite.
- [ ] T021 Run the Mini Statement backend and frontend scenarios from `specs/002-mini-statement/quickstart.md`, including PostgreSQL migration/backfill validation, API ownership checks, account-balance reconciliation, `npm test`, and `npm run build`; update the quickstart with verified results.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 and T002 can begin in parallel; no package or dependency changes are expected.
- **Foundational (Phase 2)**: Depends on Setup; T002's snapshot test precedes T003-T005; model changes precede the migration; the migration precedes transfer-service snapshot writes.
- **User Story 1 (Phase 3)**: Depends on Foundational; T006 and T007 test files can be prepared in parallel, then T008-T010 implement schema, query service, and endpoint.
- **User Story 2 (Phase 4)**: Depends on US1's query path and foundational balance snapshots; T011's test precedes T012's entry projection.
- **User Story 3 (Phase 5)**: Depends on the API response contract from US1/US2; T013 and T014 can be developed in parallel, then T015-T018 implement client, view, navigation, and styling.
- **Polish (Phase 6)**: Depends on all user stories; T019 and T020 can be written in parallel; T021 validates the completed system.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational and delivers the read-only latest-transactions endpoint.
- **US2 (P1)**: Depends on the transfer snapshots from Foundational and the transaction query from US1 to render correct historical balances.
- **US3 (P1)**: Depends on the response contract and endpoint from US1/US2; it can begin test development in parallel with backend integration work after the contract is fixed.

### Parallel Opportunities

- Setup: T001 and T002 are separate directory/test tasks.
- Foundational: T002 can be authored in parallel with T001; schema and migration implementation tasks are sequential.
- US1: T006 API tests and T007 database integration tests use separate files and can be prepared in parallel.
- US2: T011 can be prepared in parallel with US3 client test work after response fields are fixed.
- US3: T013 and T014 are separate API-client and component test files and can be prepared in parallel.
- Polish: T019 and T020 are separate documentation files; T021 follows both.

## Parallel Examples

### User Story 1

```text
T006: Add endpoint contract tests in backend/tests/api/test_mini_statement.py
T007: Add latest-10 and ownership integration tests in backend/tests/integration/test_mini_statement.py
```

### User Story 3

```text
T013: Add API client tests in frontend/src/features/mini-statement/api.test.js
T014: Add view tests in frontend/tests/mini-statement/MiniStatement.test.jsx
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational balance-snapshot work.
2. Complete US1 and US2 to deliver a correct read-only endpoint with account ownership, the latest 10 completed transfers, debit/credit direction, and historical post-transaction balances.
3. Add US3 so customers can use the endpoint through the web app; do not expose the view before the masking and ownership tests pass.

### Incremental Delivery

1. Persist side-specific post-transfer balances for existing and new completed transactions.
2. Deliver the secured, read-only latest-transactions endpoint.
3. Verify both account sides, stable ordering, exact decimal formatting, and unchanged historical balance snapshots.
4. Add the React/Vite view with account entry/selection and loading, empty, populated, and recoverable-error states.
5. Run the quickstart and traceability checks.

### Parallel Team Strategy

1. Complete foundational snapshot and migration work first.
2. After the API contract is fixed, parallelize backend API tests and database tests.
3. Parallelize the frontend API client and component test work; integrate the view after the endpoint schema is available.
4. Complete end-to-end validation after all story checkpoints pass.
