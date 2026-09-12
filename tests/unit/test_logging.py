import json
import logging

from mpi.core.logging import JsonFormatter


def test_json_formatter_emits_expected_fields() -> None:
    record = logging.LogRecord(
        name="mpi.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="ready",
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "mpi.test"
    assert payload["message"] == "ready"
    assert payload["timestamp"].endswith("+00:00")
