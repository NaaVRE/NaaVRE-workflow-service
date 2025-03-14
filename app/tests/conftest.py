import pytest
import logging


@pytest.fixture(autouse=True)
def capture_logs(caplog):
    """ Automatically captures logs for all tests """
    caplog.set_level(logging.DEBUG)  # Capture all log levels
    yield
    if caplog.records:
        print("\n===== API LOG MESSAGES =====")
        for record in caplog.records:
            print(f"{record.levelname}: {record.message}")
        print("============================")
