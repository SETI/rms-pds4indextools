"""Byte-determinism tests for the index pipeline (§11.2, R-IDX-001/002).

Each test runs the pipeline twice and asserts the two outputs are identical
byte-for-byte. Both runs share the ``frozen_time`` clock and the
``frozen_csv_mtime`` timestamp (applied via ``os.utime`` before label
generation) so the ``$FILE_ZULU$`` / ``$FILE_MD5$`` macros match; the lblx
comparison is exact bytes with no portion masked.
"""

import filecmp
import hashlib
import os
from pathlib import Path

import pytest

from pds4indextools import GenerateIndexFileArgs
from pds4indextools.cli import _runners as runners_mod

DATA = Path(__file__).resolve().parents[1] / 'data'
BUNDLES = DATA / 'bundles'
CONFIGS = DATA / 'configs'


def _run(bundle: str, config: str, out_dir: Path, seeded_cache_overlay: Path, mtime: int) -> Path:
    """Run the index pipeline into ``out_dir/index.csv``; return the CSV path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / 'index.csv'

    def hook(path: Path) -> None:
        os.utime(path, (mtime, mtime))

    runners_mod.run_generate_index_file(
        GenerateIndexFileArgs(
            bundle_root=BUNDLES / bundle,
            patterns=('**/*.lblx',),
            config_files=(CONFIGS / config, seeded_cache_overlay),
            output_file=out,
            csv_post_write_hook=hook,
        )
    )
    return out


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_identical(first: Path, second: Path) -> None:
    """Assert two files are byte-identical by digest, bytes, filecmp, and size."""
    assert _sha256(first) == _sha256(second)
    assert first.read_bytes() == second.read_bytes()
    assert filecmp.cmp(first, second, shallow=False)
    assert os.path.getsize(first) == os.path.getsize(second)


def test_two_runs_produce_byte_identical_csv_simple_pds_only(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """R-IDX-001: two ``simple_pds_only`` runs write byte-identical CSVs."""
    first = _run(
        'simple_pds_only', 'simple.yaml', tmp_path / 'a', seeded_cache_overlay, frozen_csv_mtime
    )
    second = _run(
        'simple_pds_only', 'simple.yaml', tmp_path / 'b', seeded_cache_overlay, frozen_csv_mtime
    )
    _assert_identical(first, second)


def test_two_runs_produce_byte_identical_lblx_simple_pds_only(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """R-IDX-001: two ``simple_pds_only`` runs write byte-identical labels."""
    first = _run(
        'simple_pds_only', 'simple.yaml', tmp_path / 'a', seeded_cache_overlay, frozen_csv_mtime
    )
    second = _run(
        'simple_pds_only', 'simple.yaml', tmp_path / 'b', seeded_cache_overlay, frozen_csv_mtime
    )
    _assert_identical(first.with_suffix('.lblx'), second.with_suffix('.lblx'))


def test_two_runs_produce_byte_identical_csv_multi_namespace(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """R-IDX-001: two ``multi_namespace`` runs write byte-identical CSVs."""
    first = _run(
        'multi_namespace',
        'multi_namespace.yaml',
        tmp_path / 'a',
        seeded_cache_overlay,
        frozen_csv_mtime,
    )
    second = _run(
        'multi_namespace',
        'multi_namespace.yaml',
        tmp_path / 'b',
        seeded_cache_overlay,
        frozen_csv_mtime,
    )
    _assert_identical(first, second)


def test_two_runs_produce_byte_identical_lblx_multi_namespace(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """R-IDX-001: two ``multi_namespace`` runs write byte-identical labels."""
    first = _run(
        'multi_namespace',
        'multi_namespace.yaml',
        tmp_path / 'a',
        seeded_cache_overlay,
        frozen_csv_mtime,
    )
    second = _run(
        'multi_namespace',
        'multi_namespace.yaml',
        tmp_path / 'b',
        seeded_cache_overlay,
        frozen_csv_mtime,
    )
    _assert_identical(first.with_suffix('.lblx'), second.with_suffix('.lblx'))


def test_two_runs_byte_identical_with_filesystem_order_randomization(
    seeded_cache_overlay: Path,
    tmp_path: Path,
    frozen_time: None,
    frozen_csv_mtime: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-IDX-002: reversing filesystem iteration order changes nothing byte-wise.

    Discovered files are sorted before any per-label work, so scrape order, row
    order, and output bytes are independent of the order ``Path.glob`` returns;
    reversing that order yields identical output.
    """
    first = _run(
        'multi_namespace',
        'multi_namespace.yaml',
        tmp_path / 'a',
        seeded_cache_overlay,
        frozen_csv_mtime,
    )

    original_glob = Path.glob
    calls: list[str] = []

    def reversed_glob(self: Path, pattern: str) -> list[Path]:
        calls.append(pattern)
        return list(reversed(list(original_glob(self, pattern))))

    monkeypatch.setattr(Path, 'glob', reversed_glob)
    second = _run(
        'multi_namespace',
        'multi_namespace.yaml',
        tmp_path / 'b',
        seeded_cache_overlay,
        frozen_csv_mtime,
    )

    assert calls
    assert _sha256(first) == _sha256(second)
    assert _sha256(first.with_suffix('.lblx')) == _sha256(second.with_suffix('.lblx'))


def test_csv_data_rows_sorted_ascending_by_filespec(
    seeded_cache_overlay: Path,
    tmp_path: Path,
    frozen_time: None,
    frozen_csv_mtime: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-DISC-020: CSV data rows appear in ascending lexical ``filespec`` order.

    Discovery is forced to hand back labels in reverse-sorted order, yet the
    emitted ``FILE_NAME`` column (one entry per label, derived from each label's
    ``filespec``) still lands in ascending lexical order equal to its own sort,
    proving the pipeline sorts by ``filespec`` ascending before any per-label
    work rather than preserving file-system iteration order (R-DISC-020).
    """
    original_glob = Path.glob

    def reversed_glob(self: Path, pattern: str) -> list[Path]:
        return list(reversed(list(original_glob(self, pattern))))

    monkeypatch.setattr(Path, 'glob', reversed_glob)
    out = _run(
        'multi_namespace',
        'multi_namespace.yaml',
        tmp_path / 'a',
        seeded_cache_overlay,
        frozen_csv_mtime,
    )

    lines = out.read_text(encoding='utf-8').splitlines()
    header = lines[0].split(',')
    file_col = header.index('FILE_NAME')
    file_names = [line.split(',')[file_col] for line in lines[1:]]
    assert len(file_names) > 1
    assert file_names == sorted(file_names)
