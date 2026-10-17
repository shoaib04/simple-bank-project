# Implementation Plan: Mini Statement

**Branch**: `002-mini-statement` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-mini-statement/spec.md`.

## Summary

Add a read-only `GET /api/v1/accounts/{account_number}/mini-statement` endpoint and React/Vite view. The endpoint returns up to 10 newest completed transfers for an account owned by the authenticated customer, with masked account references, exact debit/credit values, and stable historical `balance_after` values. Persist source and destination post-transfer balances with completed transactions in the same transaction; backfill existing completed transactions during migration.

## Technical Context

<!--
  Technical choices are inherited from the existing Simple Bank application.
-->

**Language/Version**: Python 3.12 backend; JavaScript/JSX with React 19 frontend.

**Primary Dependencies**: Existing FastAPI, Pydantic 2, SQLAlchemy 2.x async, Psycopg 3, Alembic, pytest, HTTPX, React, Vite, Vitest, and Testing Library; no new runtime package is required.

**Storage**: Existing PostgreSQL `accounts` and `transactions` tables; add per-side balance snapshots to transactions.

**Testing**: pytest unit/API/PostgreSQL integration tests and Vitest component/API-client tests. PostgreSQL integration tests use the dedicated `TEST_DATABASE_URL` fixture.

**Target Platform**: Existing Linux-compatible FastAPI service and browser-based React/Vite application.

**Project Type**: Existing web application with backend and frontend projects.

**Performance Goals**: Return at most 10 rows per request. No latency or throughput target is specified for this feature.

**Constraints**: Restrict statements to the authenticated account owner; return 404 for nonexistent and non-owned accounts; include completed transfers only; use exact two-decimal decimal strings and UTC timestamps; mask account and counterparty numbers in responses and logs; do not mutate state during reads. Preserve historical balances through side-specific transaction snapshots.

**Scale/Scope**: One read-only statement endpoint and one customer view; zero to 10 returned completed transactions; existing transfer, account, authentication, and web-app foundations are reused. Pagination and downloadable statements are out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **PASS**: The statement route is under `/api/v1`, and the React/Vite client calls only that API.
- **PASS**: `customer_id` comes from the trusted application context; the request path cannot choose another customer's account.
- **PASS**: Statement queries are read-only, include completed transfers only, and return exact decimal values.
- **PASS**: Account and counterparty references are masked in customer-visible output and operational logs.
- **RELEASE GATE FOR LEGACY HISTORY**: Backfill uses stable `(created_at, transaction_id)` ordering, but the old schema has no posting sequence for concurrent transactions. Reconcile historical snapshots against authoritative account/statement history before exposing them; abort the migration or block release for any unreconciled account.
- **PASS**: Automated tests cover ownership, latest-10 ordering, debit/credit mapping, balance history, masking, `/api/v1` boundary, and frontend states.

## Project Structure

### Documentation (this feature)

```text
specs/002-mini-statement/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
```text
backend/
├── alembic/versions/0002_transfer_balance_snapshots.py
├── src/simple_bank/
│   ├── api/v1/accounts.py
│   ├── db/models.py
│   ├── schemas/mini_statement.py
│   └── services/mini_statement_service.py
└── tests/
    ├── api/test_mini_statement.py
    ├── integration/test_mini_statement.py
    ├── integration/test_mini_statement_balances.py
    ├── integration/test_transaction_balance_snapshots.py
    └── unit/test_mini_statement.py

frontend/
├── src/features/mini-statement/
│   ├── api.js
│   └── MiniStatement.jsx
└── tests/mini-statement/
```

**Structure Decision**: Extend the existing backend and React/Vite projects. Reuse the `/api/v1` router, trusted customer dependency, masking utility, PostgreSQL session, and existing transfer service. Alembic migration `0002` adds and backfills per-side balance snapshots; a statement service queries completed transactions and maps them to response models. The frontend adds a statement API client and view, wired into the existing `frontend/src/App.jsx`.

No constitution violations are introduced. Side-specific balance snapshots are required data to preserve the specified historical `balance_after` result.
