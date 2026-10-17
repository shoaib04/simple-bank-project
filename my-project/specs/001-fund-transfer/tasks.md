# Tasks: Fund Transfer

**Input**: Design documents from `/specs/001-fund-transfer/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/transfers.openapi.yaml`, and `quickstart.md`

**Tests**: Included because FR-010 and the constitution explicitly require automated tests for functional, security, API-boundary, and performance requirements.

**Organization**: Tasks are grouped by user story to support incremental implementation and verification.

## Path Conventions

- Backend: `backend/src/`, `backend/tests/`
- Customer web client: `frontend/src/`, `frontend/tests/`
- Feature design and validation docs: `specs/001-fund-transfer/`

## Phase 1: Setup

**Purpose**: Create project scaffolding and dependency manifests.

- [X] T001 Create the planned backend, migration, test, and frontend feature directories under `backend/src/simple_bank/`, `backend/alembic/`, `backend/tests/`, and `frontend/src/features/transfers/`.
- [X] T002 [P] Configure Python 3.12 project metadata and FastAPI, Pydantic, SQLAlchemy, Psycopg 3, Alembic, pytest, pytest-asyncio, and HTTPX dependencies in `backend/pyproject.toml`; generate and commit the UV lockfile at `backend/uv.lock`.
- [X] T003 [P] Scaffold the React/Vite client and Vitest test script in `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.js`, `frontend/vitest.config.js`, and `frontend/src/main.jsx`.

---

## Phase 2: Foundational

**Purpose**: Build shared persistence, API routing, and rule-evaluation foundations required by all user stories.

- [X] T004 Configure the async PostgreSQL engine/session using `postgresql+psycopg` and `DATABASE_URL` in `backend/src/simple_bank/config.py`, `backend/src/simple_bank/db/session.py`, `backend/alembic/env.py`, and `backend/alembic.ini`; keep credentials out of source control and logs.
- [X] T005 Create the `Customer` and `Account` SQLAlchemy models in `backend/src/simple_bank/db/models.py`. Preserve these constraints verbatim: Customer `customer_id` is string/UUID and a "Primary key; identity supplied by the bank application"; Account `account_number` is string and a "Primary key", `customer_id` is string/UUID and "Required; references the account owner", `opened_at` is `TIMESTAMPTZ` and required, `balance` is `NUMERIC(18,2)` and "Required; stored and updated using exact decimal currency values", and `status` is enum/string and "Required; transfer eligibility requires `active`". Use `opened_at` to evaluate the 30-elapsed-day boundary in UTC.
- [X] T006 Add the `Transaction` SQLAlchemy model in `backend/src/simple_bank/db/models.py`. Preserve these constraints verbatim: `transaction_id` is UUID/string and a "Primary key; unique for each evaluated request"; `from_account` is string and "Required; references the source account"; `to_account` is string and "Required; references the recipient account"; `amount` is `NUMERIC(18,2)` and "Required; normalized with half-up rounding before rule evaluation"; `status` is enum/string and "Required; terminal value is `completed` or `rejected`"; `created_at` is `TIMESTAMPTZ` and "Required; generated in UTC by the persistence layer"; `customer_id` is string/UUID and "Required; initiating customer and daily-limit/idempotency scope"; `idempotency_key` is string and "Required; unique together with `customer_id`"; and `error_code` is string/null and "Required for rejected transactions; null for completed transactions".
- [X] T007 Create the initial Alembic migration in `backend/alembic/versions/0001_transfer_schema.py` for the Customer, Account, and Transaction models, including required UTC `opened_at`, the `(customer_id, idempotency_key)` uniqueness constraint, and required account/customer references.
- [X] T008 [P] Create the FastAPI app, trusted customer-identity dependency, and `/api/v1` router registration in `backend/src/simple_bank/main.py`, `backend/src/simple_bank/api/dependencies.py`, and `backend/src/simple_bank/api/v1/router.py`; derive `customer_id` from the bank application's trusted auth context, never from a caller-controlled field.
- [X] T009 [P] Write rule-unit tests in `backend/tests/unit/test_transfer_rules.py` for FR-001 through FR-005, FR-008, and FR-013, including zero/negative/rounded-zero amounts, half-up rounding, exact available balance, exact customer/account daily caps and Rs 0.01 overages, accounts just under 30 elapsed days old and exactly 30 days old, same-account requests, and inactive accounts.
- [X] T010 Implement the database-independent `TransferRulesService` in `backend/src/simple_bank/services/transfer_rules.py`; use exact `Decimal` values and return the first rejection in FR-001 through FR-005 order without importing FastAPI or SQLAlchemy.

**Checkpoint**: The schema, migrations, trusted customer context, `/api/v1` routing, and independently testable rule service are ready before story work begins.

---

## Phase 3: User Story 1 - Transfer Money (Priority: P1)

**Goal**: A customer can submit an eligible transfer and receive a saved transaction result without moving funds twice on retry.

**Independent Test**: Submit one eligible transfer between two active, different accounts; verify both balance changes, the saved unique transaction ID, and idempotent retry behavior.

### Tests for User Story 1

- [X] T011 [P] [US1] Add POST request/response contract tests for successful transfers in `backend/tests/api/test_transfer_success.py`, using `specs/001-fund-transfer/contracts/transfers.openapi.yaml` as the source of required fields and response status.
- [X] T012 [P] [US1] Add PostgreSQL atomicity tests in `backend/tests/integration/test_transfer_atomicity.py` proving an amount exactly equal to the available balance succeeds, debit/credit/transaction commit together, half-up normalized amounts are used consistently in resulting balances, and a transaction-persistence failure rolls back both balance updates.
- [X] T013 [P] [US1] Add idempotency integration tests in `backend/tests/integration/test_transfer_idempotency.py` proving identical retries return the original transaction ID without a second balance change, a separately initiated request with a new key creates a distinct transaction, and reuse of a key with a different payload returns `409 Conflict`.
- [X] T014 [P] [US1] Add source-ownership API tests in `backend/tests/api/test_transfer_ownership.py` proving a customer cannot debit another customer's source account, the API returns `403 Forbidden`, and the denied request does not change balances.
- [X] T015 [P] [US1] Add Vitest coverage in `frontend/src/features/transfers/api.test.js` proving transfer requests use only `/api/v1` and send `from_account`, `to_account`, decimal-string `amount`, and `idempotency_key`.

### Implementation for User Story 1

- [X] T016 [US1] Define Pydantic request and response schemas in `backend/src/simple_bank/schemas/transfers.py` to match the OpenAPI contract, including required request fields, decimal-string amount parsing, masked response account fields, terminal status values, and nullable `error_code`.
- [X] T017 [US1] Implement the transaction-processing path in `backend/src/simple_bank/services/transfer_service.py`: lock the customer row and both account rows in stable order, verify source ownership, calculate completed customer-wide and source-account UTC-day totals, select the Rs 50,000 cap before 30 elapsed days or Rs 1,00,000 at/after the boundary, call `TransferRulesService`, and atomically save the terminal transaction with balance updates only on approval.
- [X] T018 [US1] Implement customer-scoped idempotency in `backend/src/simple_bank/services/transfer_service.py`: return the original result for an identical key/payload, process a new key as a new transaction, and return `409 Conflict` when an existing key is reused with a different normalized payload.
- [X] T019 [US1] Implement `POST /api/v1/transfers` in `backend/src/simple_bank/api/v1/transfers.py`, returning `201 Created` for a newly saved outcome and `200 OK` with the original result for an identical retry; document source-account ownership rejection as `403 Forbidden` with `FORBIDDEN` in `specs/001-fund-transfer/contracts/transfers.openapi.yaml`.
- [X] T020 [US1] Implement the transfer API client and submission form in `frontend/src/features/transfers/api.js` and `frontend/src/features/transfers/TransferForm.jsx`; submit amounts as decimal strings, provide a stable idempotency key per logical request, and call only `/api/v1` endpoints.

**Checkpoint**: A valid transfer is posted atomically, persisted once, safely scoped to its owner, and independently verifiable through the API and customer client.

---

## Phase 4: User Story 2 - Understand Transfer Rejections (Priority: P1)

**Goal**: A rejected request is saved and tells the customer why it failed, while leaving both account balances unchanged.

**Independent Test**: Submit requests that independently trigger each specified rejection code; verify the response contains the reason and transaction ID, a rejected record is saved, and neither balance changes.

### Tests for User Story 2

- [X] T021 [P] [US2] Add API tests in `backend/tests/api/test_transfer_rejections.py` asserting `INVALID_AMOUNT`, `INSUFFICIENT_BALANCE`, `DAILY_LIMIT_EXCEEDED`, `SAME_AMOUNT`, and `ACCOUNT_INACTIVE` responses each include `status: rejected`, a transaction ID, and a customer-readable message.
- [X] T022 [P] [US2] Add PostgreSQL integration tests in `backend/tests/integration/test_transfer_rejections.py` proving each rule violation, including either daily cap, persists one rejected transaction, leaves both balances unchanged, and does not consume either completed-transfer daily limit.
- [X] T023 [P] [US2] Add Vitest cases in `frontend/src/features/transfers/TransferForm.test.jsx` verifying rejection code, message, and transaction ID are shown without presenting the transfer as successful.

### Implementation for User Story 2

- [X] T024 [US2] Map each `TransferRulesService` rejection to its specified API `error_code` and a clear customer-readable message in `backend/src/simple_bank/api/v1/transfers.py`; preserve the saved rejected transaction result for idempotent retries.
- [X] T025 [US2] Render rejected status, reason, and transaction ID in `frontend/src/features/transfers/TransferForm.jsx` without changing account balances or treating the response as success.

**Checkpoint**: Every specified business rejection has a saved, understandable outcome and no partial balance change.

---

## Phase 5: User Story 3 - See Protected Transfer Details (Priority: P2)

**Goal**: Customer-visible transfer results and operational logs reveal no full account numbers.

**Independent Test**: Inspect successful and rejected responses and captured transfer logs; verify each account reference is `XXXX` plus only its final four digits.

### Tests for User Story 3

- [X] T026 [P] [US3] Add API response masking tests in `backend/tests/api/test_transfer_masking.py` asserting both account references match `XXXX` plus the final four digits and never contain the full account number.
- [X] T027 [P] [US3] Add captured-log tests in `backend/tests/unit/test_account_log_masking.py` asserting transfer logs contain only masked account references and no full account numbers.

### Implementation for User Story 3

- [X] T028 [US3] Implement a shared account-number masking helper in `backend/src/simple_bank/security/account_masking.py` and apply it when serializing transfer responses in `backend/src/simple_bank/api/v1/transfers.py` using the `XXXX` plus final-four-digits format.
- [X] T029 [US3] Apply the shared masking helper to transfer operational logs in `backend/src/simple_bank/logging.py` and `backend/src/simple_bank/services/transfer_service.py`; ensure raw account numbers are never passed to log records.

**Checkpoint**: Successful and rejected responses and captured operational logs expose no full account numbers.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify end-to-end concurrency, requirement coverage, and the documented quickstart.

- [X] T030 [P] Add PostgreSQL integration tests in `backend/tests/integration/test_transfer_concurrency.py` submitting 100 concurrent eligible and ineligible requests from recently opened and mature accounts; assert balance integrity, both daily limits, unique saved outcomes, and correct results under same-customer and mixed-customer contention. Authored and lint-clean; execution is skipped until a dedicated PostgreSQL test database is available.
- [X] T031 Add a repeatable 100-request latency test in `backend/tests/performance/test_transfer_latency.py` using a mixed eligible/ineligible workload from recently opened and mature accounts; assert every end-to-end response meets the one-second requirement and do not run it concurrently with other database load tests. Authored and lint-clean; execution is skipped until a dedicated PostgreSQL test database is available.
- [X] T032 [P] Create `backend/tests/requirements_traceability.md` mapping every requirement FR-001 through FR-009 and FR-011 through FR-013 to at least one automated test path, satisfying FR-010.
- [ ] T033 Complete the live PostgreSQL backend quickstart from `specs/001-fund-transfer/quickstart.md`: run `DATABASE_URL=... uv run alembic upgrade head` and rerun `uv run pytest` with a dedicated `TEST_DATABASE_URL`. `uv sync --locked`, backend tests (24 passed, 13 database tests skipped), Ruff, and offline Alembic DDL are verified; this task is blocked until a PostgreSQL server is available.
- [X] T034 Run the customer-client quickstart validation from `specs/001-fund-transfer/quickstart.md` using `npm ci` and `npm test`; document the `/api/v1` boundary check and expected outcomes in that file. Verified with two passing Vitest tests and a successful production build.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No prior phase dependency; T002 and T003 can run in parallel after T001 creates their project roots.
- **Foundational (Phase 2)**: Depends on Setup; T005 and T006 define models before T007 creates their migration. T008 and T009 can proceed in parallel after T004; T010 follows the rule tests in T009.
- **User Story 1 (Phase 3)**: Depends on the Foundational phase; tests T011-T015 precede their implementation tasks T016-T020.
- **User Story 2 (Phase 4)**: Depends on User Story 1's endpoint and saved-outcome path; tests T021-T023 precede rejection-message and UI changes.
- **User Story 3 (Phase 5)**: Depends on User Story 1's transfer response and logging path; tests T026-T027 precede masking implementation. US2 and US3 can proceed in parallel after US1 because their implementation files are distinct.
- **Polish (Phase 6)**: Depends on all three stories; T030 checks concurrency correctness before T031 measures latency. T032 can be prepared alongside those tests; T033 and T034 validate the backend and frontend quickstart steps in sequence.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on another user story.
- **US2 (P1)**: Starts after US1 provides the saved transfer outcome path; rejection tests and customer messaging are otherwise independently verifiable.
- **US3 (P2)**: Starts after US1 provides transfer responses and logs; it can run in parallel with US2 after US1 because it owns separate masking and logging files.

### Parallel Opportunities

- Setup: T002 and T003 after T001.
- Foundational: T008 and T009 can proceed while T005/T006 model work is underway after T004; T010 follows T009 and T007 follows both models.
- US1: T011-T015 are separate API, integration, idempotency, ownership, and frontend test files and can be prepared in parallel.
- US2: T021-T023 are separate API, integration, and frontend test files and can be prepared in parallel.
- US3: T026 and T027 are separate API and logging test files and can be prepared in parallel.
- Polish: T030 and T032 touch separate files and can be prepared in parallel; run T031 after T030 to avoid competing database load. Run T033 before T034 because both update `quickstart.md`.

## Parallel Examples

### User Story 1

```text
T011: Add API success contract tests in backend/tests/api/test_transfer_success.py
T012: Add transfer atomicity and balance-rounding tests in backend/tests/integration/test_transfer_atomicity.py
T013: Add retry and separately initiated request tests in backend/tests/integration/test_transfer_idempotency.py
T014: Add source-account ownership tests in backend/tests/api/test_transfer_ownership.py
T015: Add frontend API-boundary tests in frontend/src/features/transfers/api.test.js
```

### User Story 2

```text
T021: Add rejection API tests in backend/tests/api/test_transfer_rejections.py
T022: Add rejected-outcome persistence tests in backend/tests/integration/test_transfer_rejections.py
T023: Add rejection display tests in frontend/src/features/transfers/TransferForm.test.jsx
```

### User Story 3

```text
T026: Add API masking tests in backend/tests/api/test_transfer_masking.py
T027: Add operational log masking tests in backend/tests/unit/test_account_log_masking.py
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 for a working, atomic transfer API and customer submission flow.
3. Treat US1 as an internal MVP only; do not release to customers until US2 rejection outcomes, US3 masking, and the performance/security gates are complete.

### Incremental Delivery

1. Establish the backend, client, schema, trusted identity boundary, and pure rules service.
2. Deliver US1 and validate one completed transfer plus an idempotent retry.
3. Deliver US2 and independently verify every rejection code and unchanged balances.
4. Deliver US3 and independently verify response/log masking.
5. Complete the 100-request integrity test, separate one-second latency measurement, FR-to-test mapping, and backend/frontend quickstart runs.

### Parallel Team Strategy

1. Complete Setup and shared Foundational tasks first.
2. Implement and validate US1 as the base transfer flow.
3. After US1, assign US2 rejection messaging and US3 privacy controls to separate workstreams.
4. Complete Polish only after all user-story checkpoints pass.
