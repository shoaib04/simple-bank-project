# Implementation Plan: Fund Transfer

**Branch**: `001-fund-transfer` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-fund-transfer/spec.md`; user-selected stack: Python 3.12, UV, FastAPI, PostgreSQL, and an independently unit-testable transfer rules service.

## Summary

Deliver fund transfers through `POST /api/v1/transfers`, with transfer eligibility isolated in a pure `TransferRulesService`. A FastAPI application coordinates trusted customer identity, PostgreSQL persistence, idempotency, and atomic balance updates; a React/Vite customer client calls only the versioned API.

## Technical Context

**Language/Version**: Python 3.12 for the API; React/Vite client as required by the constitution.

**Primary Dependencies**: UV with committed `uv.lock`; FastAPI and Pydantic; SQLAlchemy 2.x async ORM, Psycopg 3, and Alembic; pytest and HTTPX; React and Vite for the customer client.

**Storage**: PostgreSQL; exact currency values use `NUMERIC`, timestamps use `TIMESTAMPTZ`.

**Testing**: pytest unit tests for pure transfer rules; HTTPX/FastAPI API tests; PostgreSQL integration tests for persistence, idempotency, rollback, and concurrency; frontend tests for the `/api/v1` boundary.

**Target Platform**: Linux-compatible server; local development uses Python 3.12, UV, and PostgreSQL.

**Project Type**: Web application with a FastAPI backend and React/Vite customer client.

**Performance Goals**: Support 100 concurrent transfer requests and return each outcome within one second, as specified in FR-007 and FR-012; verify by PostgreSQL-backed load tests rather than assume from the async stack.

**Constraints**: Use `Decimal` and half-up rounding to two places; atomically persist the outcome and (on success) both balance changes; serialize customer and source-account daily-limit checks; enforce the Rs 50,000 source-account limit before 30 elapsed days and Rs 1,00,000 thereafter alongside the customer-wide Rs 1,00,000 limit; enforce idempotency; mask account numbers in responses and logs; expose routes only under `/api/v1`. Customer identity is supplied by the bank application's trusted auth context; authentication protocol is outside this feature's scope.

**Scale/Scope**: Account and transaction records; one transfer-creation endpoint; a customer transfer flow; up to 100 concurrent requests. Jurisdiction-specific compliance, retention, production posture, and monthly availability remain release decisions called out in the spec.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **PASS**: All API routes use the `/api/v1` prefix; the React/Vite client calls only that API boundary.
- **PASS**: Transfer eligibility is isolated from HTTP and database concerns and receives automated unit coverage.
- **PASS**: The persistence coordinator uses exact decimal values and one PostgreSQL transaction for balance integrity and saved outcomes.
- **PASS**: Customer-visible references and operational logs mask account numbers to the final four digits.
- **PASS WITH VERIFICATION**: The feature spec supplies the one-second target and 100-request concurrency target; PostgreSQL-backed tests must measure them under same-customer and mixed-customer contention. Passing the target is not assumed from the framework choice.
- **RELEASE GATE**: Confirm production status, jurisdictional obligations, record retention, and availability before production, as required by the spec.

## Project Structure

### Documentation (this feature)

```text
specs/001-fund-transfer/
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
├── pyproject.toml
├── uv.lock
├── alembic/
├── src/simple_bank/
│   ├── main.py
│   ├── api/v1/transfers.py
│   ├── schemas/transfers.py
│   ├── services/
│   │   ├── transfer_rules.py
│   │   └── transfer_service.py
│   └── db/
│       ├── models.py
│       └── session.py
└── tests/
    ├── unit/
    ├── api/
    └── integration/

frontend/
├── src/features/transfers/
│   ├── TransferForm.jsx
│   └── api.js
└── tests/
```

**Structure Decision**: Keep the Python backend and React/Vite client as separate projects. `TransferRulesService` is a pure domain service under `backend/src/simple_bank/services/`; `TransferService` coordinates persistence, idempotency, and database transactions. The API route handles HTTP mapping only. Alembic owns PostgreSQL schema changes. The client communicates with the backend only through `/api/v1`.

## Complexity Tracking

No constitution violations are introduced; complexity tracking is not required.
