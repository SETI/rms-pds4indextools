"""Integration-suite fixtures shared across the five integration modules.

The only fixture here resets the package logger so ``main``-based tests that
assert on ``caplog`` bind a fresh handler each run; every other fixture the
integration tests use lives in the top-level ``tests/conftest.py``.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def _reset_pkg_logger() -> None:
    """Clear the package logger's handlers before each integration test.

    ``setup_logging`` never re-points its stream handler, so a handler
    attached during an earlier test would keep targeting that test's captured
    stream; clearing first forces ``main`` to attach a handler bound to the
    current capture buffer (mirrors the Phase 10 unit-suite fixture).
    """
    logging.getLogger('pds4indextools').handlers.clear()
