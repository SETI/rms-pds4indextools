"""Integration tests for the ``copy_default_config`` subcommand (§11.2).

These verify that the copied file is byte-identical to the packaged
``default_config.yaml``, that overwrite is refused without ``--force``, and
that a forced copy is warned about and idempotent.
"""

import hashlib
import importlib.resources
import logging
from pathlib import Path

import pytest

from pds4indextools import CopyDefaultConfigArgs
from pds4indextools.cli import _runners as runners_mod
from pds4indextools.cli import main


def _packaged_bytes() -> bytes:
    """Return the bytes of the packaged ``default_config.yaml``."""
    return (
        importlib.resources.files('pds4indextools.templates')
        .joinpath('default_config.yaml')
        .read_bytes()
    )


def test_copy_default_config_bytes_byte_identical_to_packaged(tmp_path: Path) -> None:
    """T-CDC-001, R-CFG-201: the copy is byte-identical to the packaged config."""
    dest = tmp_path / 'config.yaml'
    result = runners_mod.run_copy_default_config(
        CopyDefaultConfigArgs(output_file=dest, force=False)
    )
    assert dest.read_bytes() == _packaged_bytes()
    assert result.output_path == dest.resolve()
    assert result.warnings == ()


def test_copy_default_config_refuses_overwrite_without_force(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-CDC-002, R-CLI-031: an existing destination is refused without --force."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    dest = tmp_path / 'config.yaml'
    dest.write_bytes(b'OLD')
    assert main(['copy_default_config', '--output-file', str(dest)]) == 1
    assert dest.read_bytes() == b'OLD'
    assert 'destination exists' in caplog.text


def test_copy_default_config_force_overwrites_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-CDC-003, R-CLI-031: --force overwrites an existing destination with a warning."""
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    dest = tmp_path / 'config.yaml'
    dest.write_bytes(b'OLD')
    assert main(['copy_default_config', '--output-file', str(dest), '--force']) == 0
    assert dest.read_bytes() == _packaged_bytes()
    assert 'overwriting' in caplog.text


def test_copy_default_config_force_is_idempotent(tmp_path: Path) -> None:
    """R-CLI-031: forcing twice leaves the packaged bytes with a stable digest."""
    dest = tmp_path / 'config.yaml'
    packaged_digest = hashlib.md5(_packaged_bytes()).hexdigest()
    runners_mod.run_copy_default_config(CopyDefaultConfigArgs(output_file=dest, force=True))
    first = hashlib.md5(dest.read_bytes()).hexdigest()
    assert dest.read_bytes() == _packaged_bytes()
    runners_mod.run_copy_default_config(CopyDefaultConfigArgs(output_file=dest, force=True))
    second = hashlib.md5(dest.read_bytes()).hexdigest()
    assert dest.read_bytes() == _packaged_bytes()
    assert first == second == packaged_digest
