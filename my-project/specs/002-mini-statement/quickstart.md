# Quickstart: Mini Statement

## Prerequisites

- Python 3.12, UV, Node.js/npm, and a running PostgreSQL instance.
- A development database configured with `DATABASE_URL` using the `postgresql+psycopg://` scheme.
- A separate disposable PostgreSQL database whose name includes `test`, configured as `TEST_DATABASE_URL` for integration tests. The shared test fixture refuses other database names before dropping or creating tables.
- The bank application's trusted customer authentication context, or the API tests' dependency override.

Do not put database credentials in source control or point `TEST_DATABASE_URL` at a development or production database.

## Apply the Schema Migration

From the repository root:

```sh
cd backend
uv sync --locked
uv run alembic upgrade head
```

The Mini Statement migration adds source- and destination-side post-transfer balance snapshots, backfills completed historical transactions, and verifies that each account's latest snapshot reconciles to its current balance. Because legacy rows have no explicit posting sequence, reconcile historical backfill against authoritative account history before relying on legacy snapshots; block release for unreconciled accounts.

## Run Backend Tests

```sh
uv run pytest tests/unit/test_mini_statement.py tests/api/test_mini_statement.py
uv run pytest tests/integration/test_transaction_balance_snapshots.py tests/integration/test_mini_statement.py tests/integration/test_mini_statement_balances.py
```

The API tests should cover 200 responses, 404 for missing/non-owned accounts, masking, and the zero-to-10 response size. PostgreSQL integration tests should verify the migration backfill, completed-only ordering, incoming/outgoing formatting, stable tie order, unchanged historical balances after later transfers, and no writes during a statement read.

Without `TEST_DATABASE_URL`, PostgreSQL integration tests are skipped. A passing local unit/API suite does not replace live migration/backfill reconciliation before release.

## Run Frontend Checks

From the repository root:

```sh
cd frontend
npm ci
npm test
npm run build
```

Expected results: the account input requests only the selected account's `/api/v1` mini statement; the view shows loading, empty, populated, and retryable error states; all displayed account references remain masked.

See [the OpenAPI contract](contracts/mini-statement.openapi.yaml) for response fields, [the data model](data-model.md) for transaction snapshot semantics, and `backend/tests/mini_statement_requirements_traceability.md` for FR-to-test mapping.
