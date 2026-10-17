# Research: Mini Statement

## Decisions

### Preserve historical balance-after values

- **Decision**: Add nullable `from_balance_after` and `to_balance_after` `NUMERIC(18,2)` fields to `Transaction`. For completed transfers, write the source and destination balances after debit/credit in the same PostgreSQL transaction as the balance updates. Rejected transactions leave both fields null.
- **Rationale**: `Account.balance` is mutable and cannot by itself answer what the balance was immediately after an older transfer. Persisted side-specific snapshots make the statement read bounded and keep an old row stable after later transfers.
- **Existing data**: Backfill completed rows by projecting each account's completed incoming/outgoing ledger effects in stable `(created_at, transaction_id)` order, starting from its current account balance and reversing later effects. The current schema has no separate posting sequence, so this stable order is reproducible but cannot prove the true commit order of every legacy concurrent transfer. Treat historical backfill as a release gate: compare it with authoritative statement/account history and do not present unreconciled historical snapshots as exact. Validate that each account's newest calculated snapshot equals its current balance; abort rather than silently accepting an unreconciled backfill.
- **Alternatives considered**: Reconstruct the balance on every statement request from the account's current balance and all later transactions. This avoids a schema change, but scans more history and makes the response depend on the consistency of the legacy event ordering for every read. Storing only one generic snapshot was rejected because a transfer affects two accounts and each statement needs its own post-transaction value.

### Statement query and ordering

- **Decision**: Select completed transactions where the requested account is the source or destination, sort by `created_at DESC, transaction_id DESC`, and limit the result to 10. Treat the UUID as the deterministic tie-breaker when timestamps are equal.
- **Rationale**: The predicate reflects each account's debit and credit sides; the explicit order guarantees stable output and a bounded result set.
- **Alternatives considered**: Offset pagination was rejected because the feature is explicitly limited to a mini statement of the newest 10. Sorting only by timestamp was rejected because equal timestamps would produce non-deterministic ordering.
- **Indexes**: Add composite indexes on `(from_account, created_at, transaction_id)` and `(to_account, created_at, transaction_id)` to support the account-side history predicates and newest-first order. Confirm the migration's generated indexes against the deployed PostgreSQL version and query plan.

### Ownership and privacy

- **Decision**: Resolve account and owner together using the trusted `customer_id` dependency. Return the same `404` response for a missing account and an account owned by someone else. Mask account and counterparty references with the existing `mask_account_number` helper; never log the raw path parameter.
- **Rationale**: Hiding the distinction avoids confirming another customer's account existence and reuses the transfer feature's established authentication and masking conventions.
- **Alternatives considered**: A distinct forbidden response for non-owned accounts was rejected because it reveals that the account exists. Accepting customer identity from request input was rejected because ownership must be based on trusted application context.

### Entry projection and formatting

- **Decision**: For a source-account row, set debit to the transfer amount, credit to `0.00`, and `balance_after` to `from_balance_after`. For a destination-account row, set credit to the transfer amount, debit to `0.00`, and use `to_balance_after`. Serialize all monetary fields as exact two-decimal strings and dates as ISO 8601 UTC.
- **Rationale**: This gives the two account sides consistent, exactly representable statement entries and conforms to the feature contract.
- **Alternatives considered**: Returning JSON floating-point values was rejected because it can lose exact currency representation. Returning the current account balance was rejected because it is not historical.

### Rejected transfers

- **Decision**: Filter to `TransactionStatus.COMPLETED`; leave rejected attempts out of statement history.
- **Rationale**: The spec and accepted clarification require that statement rows represent actual posted account activity. Rejected requests are persisted operationally but do not move funds.

### Frontend integration

- **Decision**: Add a feature-local API helper and React view under `frontend/src/features/mini-statement/`, then link it from the existing `frontend/src/App.jsx` view navigation. Let customers enter the owned account number because account discovery is explicitly outside scope.
- **Rationale**: This extends the existing React/Vite app and fetch pattern without adding a route framework, state library, or new dependency.
- **Alternatives considered**: Adding account discovery or pagination was rejected as outside the v1 scope.

### Test strategy

- **Decision**: Use pytest API tests for ownership, response contract, and masking; PostgreSQL integration tests for latest-10 selection, backfill, historical balance snapshots, and no mutation; unit tests for debit/credit mapping; Vitest for API path, loading/empty/error/populated states, and rendering. Run PostgreSQL tests with the existing guarded `TEST_DATABASE_URL` fixture.
- **Rationale**: PostgreSQL is necessary to validate migration, numeric schema, and query ordering; unit and frontend tests remain fast and local.
- **Alternatives considered**: SQLite-only verification was rejected for migration/query behavior because it differs from PostgreSQL.

## Constraints and Deferred Decisions

- No new dependency is required; reuse the installed FastAPI/SQLAlchemy/Psycopg and React/Vite stacks.
- Only completed outgoing and incoming transfers are statement entries. Owned inactive accounts remain readable, as specified by the feature assumptions.
- Production data volume, performance SLA, financial jurisdiction, and statement retention are not defined by this feature. Validate migration reconciliation before any production use.
- A research-agent dispatch was unavailable in this session; decisions above are grounded in the existing schema and transfer transaction path, with official product documentation listed below.

## References

- [PostgreSQL window functions](https://www.postgresql.org/docs/current/tutorial-window.html)
- [PostgreSQL indexes](https://www.postgresql.org/docs/current/indexes.html)
- [SQLAlchemy ORM select statements](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html)
- [Alembic operations](https://alembic.sqlalchemy.org/en/latest/ops.html)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI async tests](https://fastapi.tiangolo.com/advanced/async-tests/)
