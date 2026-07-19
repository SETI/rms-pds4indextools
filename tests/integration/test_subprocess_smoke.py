"""Subprocess smoke tests for the ``pds4indextools`` console entry (§11.2).

Every test launches ``python -m pds4indextools`` in a child process with the
list-of-strings argv form (never ``shell=True``) and the active interpreter
(``sys.executable``). The 60-second timeout matches the suite's global
``--timeout=60``. Non-``--version`` scraping runs append a seeded-cache
overlay so schema resolution stays zero-network.
"""

import subprocess
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'
BUNDLES = DATA / 'bundles'
CONFIGS = DATA / 'configs'

_MODULE = ['-m', 'pds4indextools']


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke ``python -m pds4indextools`` with the given arguments."""
    return subprocess.run(
        [sys.executable, *_MODULE, *args],
        timeout=60,
        check=False,
        capture_output=True,
        text=True,
    )


def test_subprocess_generate_index_file_happy_path(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-SUB-001: a valid generate_index_file run exits 0 and writes the CSV."""
    out = tmp_path / 'index.csv'
    proc = _run(
        'generate_index_file',
        '--bundle-root',
        str(BUNDLES / 'simple_pds_only'),
        '--config-file',
        str(CONFIGS / 'simple.yaml'),
        '--config-file',
        str(seeded_cache_overlay),
        '--output-file',
        str(out),
        '**/*.lblx',
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    assert out.with_suffix('.lblx').is_file()


def test_subprocess_generate_index_file_bad_bundle_exit_1(tmp_path: Path) -> None:
    """T-SUB-002: a nonexistent bundle root exits 1."""
    proc = _run(
        'generate_index_file',
        '--bundle-root',
        str(tmp_path / 'missing'),
        '--config-file',
        str(CONFIGS / 'simple.yaml'),
        '**/*.lblx',
    )
    assert proc.returncode == 1


def test_subprocess_generate_xpath_list_happy_path(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-SUB-003: a valid generate_xpath_list run exits 0 and writes the YAML."""
    out = tmp_path / 'columns.yaml'
    proc = _run(
        'generate_xpath_list',
        '--bundle-root',
        str(BUNDLES / 'simple_pds_only'),
        '--config-file',
        str(CONFIGS / 'simple.yaml'),
        '--config-file',
        str(seeded_cache_overlay),
        '--output-file',
        str(out),
        '**/*.lblx',
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()


def test_subprocess_generate_xpath_list_bad_bundle_exit_1(tmp_path: Path) -> None:
    """T-SUB-004: a nonexistent bundle root exits 1."""
    proc = _run(
        'generate_xpath_list',
        '--bundle-root',
        str(tmp_path / 'missing'),
        '--config-file',
        str(CONFIGS / 'simple.yaml'),
        '**/*.lblx',
    )
    assert proc.returncode == 1


def test_subprocess_copy_default_config_happy_path(tmp_path: Path) -> None:
    """T-SUB-005: a copy_default_config run exits 0 and writes the config."""
    dest = tmp_path / 'config.yaml'
    proc = _run('copy_default_config', '--output-file', str(dest))
    assert proc.returncode == 0, proc.stderr
    assert dest.is_file()


def test_subprocess_copy_default_config_overwrite_exit_1(tmp_path: Path) -> None:
    """T-SUB-006: copying over an existing file without --force exits 1."""
    dest = tmp_path / 'config.yaml'
    dest.write_bytes(b'OLD')
    proc = _run('copy_default_config', '--output-file', str(dest))
    assert proc.returncode == 1
    assert dest.read_bytes() == b'OLD'


def test_subprocess_version_flag() -> None:
    """R-CLI-003 end-to-end: ``--version`` exits 0 and prints the program name."""
    proc = _run('--version')
    assert proc.returncode == 0
    assert 'pds4_create_xml_index' in proc.stdout


def test_subprocess_no_subcommand_exits_2() -> None:
    """R-CLI-005 end-to-end: no subcommand prints help and exits 2."""
    proc = _run()
    assert proc.returncode == 2
    assert 'SUBCOMMAND' in proc.stderr
