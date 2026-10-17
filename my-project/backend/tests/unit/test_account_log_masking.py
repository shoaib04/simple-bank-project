import logging

import pytest
from simple_bank.logging import log_transfer_accounts


@pytest.mark.parametrize("account_number", ["1234567890121001", "9876543210982002"])
def test_transfer_logs_never_include_full_account_numbers(
    caplog: pytest.LogCaptureFixture, account_number: str
) -> None:
    caplog.set_level(logging.INFO, logger="simple_bank.transfer")

    log_transfer_accounts("1234567890121001", "9876543210982002")

    assert account_number not in caplog.text
    assert "XXXX1001" in caplog.text
    assert "XXXX2002" in caplog.text
