# Research: Fund Transfer

## Decisions

### Python project and dependency management

- **Decision**: Use Python 3.12 with UV, a backend-local `pyproject.toml`, and a committed `uv.lock`. Keep development dependencies in a development group and use locked synchronization in CI.
- **Rationale**: The user selected Python 3.12 and UV. A single tool-managed lockfile keeps development and CI dependency resolution reproducible.
- **Alternatives considered**: A maintained `requirements.txt` alongside UV was rejected because it duplicates dependency resolution; export one only if a deployment platform requires it.

### HTTP boundary and API schemas

- **Decision**: Use FastAPI with Pydantic request and response models. Accept `amount` as a decimal string, parse it to `Decimal`, apply half-up rounding to two fractional digits, and return the normalized amount as a two-place string.
- **Rationale**: Explicit schemas validate and document the HTTP boundary. Decimal strings avoid binary floating-point ambiguity and match the existing spec's API fields.
- **Alternatives considered**: JSON floating-point amounts were rejected because they cannot guarantee exact decimal currency values. Business rejections remain saved transaction responses; malformed request bodies are HTTP validation errors.

### PostgreSQL access and migrations

- **Decision**: Use SQLAlchemy 2.x async sessions with Psycopg 3, Alembic migrations, and one database session per request/task. Do not share an `AsyncSession` between concurrent tasks.
- **Rationale**: Async PostgreSQL I/O fits the stated concurrency target. Psycopg 3 has SQLAlchemy sync and async support; Alembic provides versioned schema changes. The async choice must still be measured against the one-second target.
- **Alternatives considered**: Synchronous SQLAlchemy/Psycopg was rejected for the initial design because it blocks the event loop during database I/O. `asyncpg` remains a viable driver alternative if measurements or deployment constraints favor it.

### Transfer rule isolation

- **Decision**: Implement a stateless `TransferRulesService` that accepts normalized `Decimal` amounts and already-loaded eligibility facts, returning either an approval or one rejection code. It has no FastAPI, SQLAlchemy, session, or network dependencies. A separate `TransferService` coordinates persistence and calls the rules service.
- **Rationale**: Unit tests can exercise every rule and boundary without a database or HTTP client, while transactional coordination remains in one application-service boundary.
- **Alternatives considered**: Putting rule checks in the route or ORM model was rejected because it couples business behavior to transport or persistence and makes focused tests harder.

### Atomicity, locking, and daily limit

- **Decision**: Each request runs in one PostgreSQL transaction. Lock the customer's row first, then lock both account rows in a stable sorted order. Check idempotency, the customer's completed outgoing total, and the source account's completed outgoing total for the UTC day while holding the customer and account locks. Select a Rs 50,000 source-account cap before 30 elapsed days of account age and Rs 1,00,000 from the 30-day boundary onward; enforce the customer-wide Rs 1,00,000 cap independently. On success, update both balances and insert the completed transaction; on rejection, insert the rejected transaction without changing balances. Commit the outcome atomically.
- **Rationale**: A stable customer-row lock serializes customer-wide limit checks; locking the source account also serializes its age-based limit checks. These locks prevent concurrent requests from jointly exceeding either cap. Ordered account locks reduce deadlock risk. PostgreSQL `READ COMMITTED` plus explicit row locks is adequate for these serialized checks and keeps serialization-retry handling out of the normal path.
- **Alternatives considered**: Summing transfer rows without a customer lock was rejected because concurrent check-then-insert operations can both pass the cap. A maintained daily-total table was considered but adds denormalized state that must be reconciled; aggregate completed transactions under the customer lock is simpler initially.
- **Assumption**: Only completed transfers count toward either daily outgoing cap. Rejected attempts are persisted for outcome/idempotency but do not consume either limit. `DAILY_LIMIT_EXCEEDED` is returned when either the customer-wide or applicable source-account cap would be exceeded.

### Idempotency and transaction persistence

- **Decision**: Scope idempotency to `(customer_id, idempotency_key)` and enforce a database unique constraint. Save the normalized request fields and rejection `error_code` with each terminal transaction. Identical retries return the original saved result; reusing a key with a different normalized payload returns `409 Conflict` without processing another transfer.
- **Rationale**: A unique constraint is the final defense against concurrent duplicate requests. Persisting the rejection code and normalized payload makes a retry return the original outcome even if account state later changes.
- **Alternatives considered**: In-memory idempotency was rejected because it does not survive process restart or coordinate multiple workers. A separate idempotency table is unnecessary while each evaluated request maps to one transaction record.

### Validation order and response mapping

- **Decision**: For requests violating multiple transfer rules, return the first failed rule in FR-001 through FR-005 order: invalid amount, insufficient balance, daily limit, same account (`SAME_AMOUNT`), then inactive account. A newly saved completed or rejected outcome returns `201 Created`; an identical retry returns `200 OK` with the original response.
- **Rationale**: The spec defines one error code per rejection but does not define precedence. Requirement order provides a stable, traceable policy without changing any pass/fail rule. `SAME_AMOUNT` is retained as the user-specified code for the same-account prohibition in FR-004.
- **Alternatives considered**: Returning multiple codes would expand the response contract and complicate clients; an unstable database-dependent order was rejected.

### Testing and performance verification

- **Decision**: Use pytest for rule unit tests, HTTPX/FastAPI tests for the REST boundary, and PostgreSQL-backed integration tests for transaction rollback, persistence, retries, and concurrent balance/daily-limit checks. Include a 100-request load scenario and measure end-to-end response time.
- **Rationale**: Mocks and SQLite cannot verify PostgreSQL row-lock behavior. The one-second/100-concurrent targets must be measured with the actual database path and with both same-customer and different-customer traffic.
- **Alternatives considered**: SQLite-only integration testing was rejected because its concurrency semantics differ from PostgreSQL.

## Deferred Decisions

- Production status, financial jurisdiction, compliance obligations, record retention, and monthly availability are explicitly unresolved in the feature spec and remain release gates.
- The bank application's authentication protocol is outside this feature. The route receives a trusted `customer_id` from the existing application auth dependency; it is not accepted as a caller-controlled request field.

## References

- [UV project layout](https://docs.astral.sh/uv/concepts/projects/layout/)
- [UV lock and sync](https://docs.astral.sh/uv/concepts/projects/sync/)
- [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/)
- [Pydantic standard-library types: Decimal](https://pydantic.dev/docs/validation/latest/api/pydantic/standard_library_types/#decimal)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI async tests](https://fastapi.tiangolo.com/advanced/async-tests/)
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLAlchemy PostgreSQL dialect and Psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#psycopg)
- [PostgreSQL row-level locks](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS)
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
