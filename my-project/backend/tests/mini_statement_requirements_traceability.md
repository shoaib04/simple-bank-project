# Mini Statement Requirement-to-Test Traceability

| Requirement | Automated test coverage |
| --- | --- |
| FR-001: Authenticated customer may read only an owned account | `tests/api/test_mini_statement.py::test_missing_or_non_owned_account_returns_not_found_without_data`; `tests/integration/test_mini_statement.py` |
| FR-002: Versioned mini-statement endpoint | `tests/api/test_mini_statement.py::test_owned_account_returns_masked_statement` |
| FR-003: Latest 10 completed entries, newest first | `tests/integration/test_mini_statement.py::test_returns_ten_newest_completed_entries_and_does_not_mutate_account` |
| FR-004: All six statement entry fields and correct account side | `tests/unit/test_mini_statement.py::test_outgoing_entry_uses_source_snapshot_and_masks_counterparty`; `tests/unit/test_mini_statement.py::test_incoming_entry_uses_destination_snapshot_and_masks_counterparty` |
| FR-005: UTC date, decimal formatting, amount and direction invariants | `tests/unit/test_mini_statement.py`; `tests/api/test_mini_statement.py::test_owned_account_returns_masked_statement` |
| FR-006: Mask account and counterparty references | `tests/unit/test_mini_statement.py`; `tests/api/test_mini_statement.py::test_owned_account_returns_masked_statement` |
| FR-007: Exclude rejected transfer attempts | `tests/integration/test_mini_statement.py::test_returns_ten_newest_completed_entries_and_does_not_mutate_account` |
| FR-008: Read-only statement query | `tests/integration/test_mini_statement.py::test_returns_ten_newest_completed_entries_and_does_not_mutate_account` |
| FR-009: Web view and newest-first rendering | `frontend/tests/mini-statement/MiniStatement.test.jsx` |
| FR-010: Loading, empty, and recoverable error states | `frontend/tests/mini-statement/MiniStatement.test.jsx` |
| FR-011: No full account numbers in content or logs | `tests/api/test_mini_statement.py::test_owned_account_returns_masked_statement`; `tests/unit/test_mini_statement.py` |
| FR-012: Automated mapping of FR-001 through FR-011 | This matrix documents the corresponding automated tests. |
