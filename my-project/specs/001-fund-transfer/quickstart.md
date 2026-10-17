# Quickstart: Fund Transfer

## Prerequisites

- Python 3.12 and UV installed.
- A running PostgreSQL instance and an empty development database. Integration tests also require a dedicated test database.
- The bank application's development authentication context, or the test auth dependency override used by the API tests.

Set `DATABASE_URL` to the development PostgreSQL DSN using the Psycopg SQLAlchemy URL form (`postgresql+psycopg://...`). Set `TEST_DATABASE_URL` to a separate disposable PostgreSQL database whose name includes `test`; integration fixtures refuse other database names before running destructive schema setup. Do not put credentials in source control.

## Install and Migrate

From the repository root:

```sh
cd backend
uv sync --locked
uv run alembic upgrade head
```

## Run Automated Checks

```sh
uv run pytest
```

Without `TEST_DATABASE_URL`, PostgreSQL integration and performance tests are skipped. With it configured, the fixtures recreate the test schema before each test; never point it at a development or production database.

The suite should include:

- Unit tests for `TransferRulesService`: zero/negative/rounded-zero amounts, half-up rounding boundaries, exact-balance transfers, insufficient funds, exact and exceeded customer/account daily caps, account ages just under and exactly at 30 elapsed days, same-account transfers, and inactive accounts.
- API tests for request/response schemas, masked account references, every rejection error code, and `/api/v1` routing.
- PostgreSQL integration tests for persisted completed and rejected outcomes, atomic balance updates, rollback, identical idempotent retries, and conflicting reuse of an idempotency key.
- PostgreSQL-backed tests that submit 100 concurrent requests from recently opened and mature accounts, checking both daily caps and correct outcomes under same-customer and mixed-customer contention; verify every measured outcome is returned within one second.
- Customer-client tests confirming transfer calls use only `/api/v1` endpoints.

Expected result: all rule, API, persistence, masking, idempotency, and concurrency checks pass without partial balance updates or duplicate transfers.

## Run the API Locally

```sh
uv run uvicorn simple_bank.main:app --reload
```

Submit a request through the bank application's development authentication context. For a completed transfer, the API returns `201 Created` with `status: "completed"`, a unique `transaction_id`, a two-place decimal-string `amount`, and masked account references. For a rejected but evaluated transfer, it returns `201 Created` with `status: "rejected"`, the saved transaction ID, and the applicable `error_code`; balances remain unchanged. Repeating the same customer-scoped idempotency key and request returns the original result with `200 OK`.

See [the OpenAPI contract](contracts/transfers.openapi.yaml) for request, response, and error schemas, and [the data model](data-model.md) for persistence invariants.

## Run Customer-Client Checks

From the repository root:

```sh
cd frontend
npm ci
npm test
npm run build
```
