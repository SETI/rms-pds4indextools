"""Shared pytest fixtures for the pds4indextools test suite.

The fixtures here are intentionally minimal. Anything specific to a
single test file should live in that file or in a sibling conftest.
"""

import hashlib
import os
import socket
import sys
from collections.abc import Iterator
from pathlib import Path

import platformdirs
import pytest

HERE = Path(__file__).resolve().parent
DATA_ROOT = HERE / 'data'


@pytest.fixture(scope='session')
def data_root() -> Path:
    """Absolute path to ``tests/data``."""
    return DATA_ROOT


@pytest.fixture(scope='session')
def bundle_root_factory(data_root: Path) -> 'BundleRootFactory':
    """Factory returning the absolute path to ``tests/data/bundles/<name>``."""
    return BundleRootFactory(data_root / 'bundles')


class BundleRootFactory:
    """Helper that resolves a bundle name to an absolute filesystem path."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def __call__(self, name: str) -> Path:
        path = self._root / name
        if not path.is_dir():
            raise FileNotFoundError(f'unknown test bundle: {name} ({path})')
        return path


@pytest.fixture(scope='session')
def xsd_cache_session(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session-scoped XSD cache directory shared across integration tests.

    pytest-xdist gives each worker its own ``tmp_path_factory`` base path
    but the basetemp is a stable per-session directory; we anchor our
    cache one level above so all workers in the same session share the
    download cache (R-TST-021).

    NOTE: ``SchemaCache.fetch`` uses ``write-temp-then-os.replace`` so
    concurrent xdist workers cannot interleave or leave partial files
    (critique skill §6).
    """
    base = tmp_path_factory.getbasetemp().parent / 'xsd_cache_session'
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def isolated_xsd_cache(tmp_path: Path) -> Path:
    """Per-test fresh XSD cache directory (unit tests only)."""
    cache = tmp_path / 'xsd_cache'
    cache.mkdir()
    return cache


# Every xsi:schemaLocation URL that appears in a fixture bundle, mapped
# to the seed XSD (in tests/data/xsd_cache_seed/) that serves it. The
# seeded cache makes schema resolution work with ZERO network in every
# non-live test (R-TST-030 as amended).
_FIXTURE_SCHEMA_URLS: dict[str, str] = {
    'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd': 'pds_v1_basic.xsd',
    'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1K00.xsd': 'pds_v1_basic.xsd',
    'https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1L00_2000.xsd': 'geom_v1.xsd',
    'https://pds.nasa.gov/pds4/rings/v1/PDS4_RINGS_1L00_1G00.xsd': 'rings_v1.xsd',
}


@pytest.fixture(scope='session')
def seeded_xsd_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session cache dir pre-seeded with every fixture schema URL.

    Files are stored under ``sha256(url).xsd`` — exactly the cache-hit
    key ``SchemaCache.fetch`` uses — so no test that requests this
    cache ever touches the network.
    """
    cache = tmp_path_factory.mktemp('seeded_xsd_cache')
    for url, seed in _FIXTURE_SCHEMA_URLS.items():
        digest = hashlib.sha256(url.encode('utf-8')).hexdigest()
        (cache / f'{digest}.xsd').write_bytes((DATA_ROOT / 'xsd_cache_seed' / seed).read_bytes())
    return cache


@pytest.fixture
def seeded_cache_overlay(seeded_xsd_cache: Path, tmp_path: Path) -> Path:
    """Config-overlay YAML pointing ``xsd_cache_dir`` at the seeded cache.

    Tests append this path as the LAST ``--config-file`` (or
    ``config_files`` entry) so the run resolves schemas from the seeded
    cache with zero network.
    """
    overlay = tmp_path / 'xsd_cache_overlay.yaml'
    overlay.write_text(f'xsd_cache_dir: {seeded_xsd_cache}\n', encoding='utf-8')
    return overlay


@pytest.fixture
def chdir_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Chdir into ``tmp_path`` for the duration of the test."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _has_network(host: str = 'pds.nasa.gov', port: int = 443, timeout: float = 1.0) -> bool:
    """Return True iff the given host:port accepts a TCP connection.

    Overridable via the ``PDS4INDEX_TEST_HOST`` env var; timeout is
    bounded to 1s to keep the cost of a session-scoped call small
    (critique skill §15).
    """
    host = os.environ.get('PDS4INDEX_TEST_HOST', host)
    try:
        socket.create_connection((host, port), timeout=timeout).close()
    except OSError:
        return False
    return True


@pytest.fixture(scope='session')
def has_network() -> bool:
    """``True`` iff the configured test host is reachable."""
    return _has_network()


class _NonTtyStream:
    """Delegating wrapper whose ``isatty()`` is always ``False``.

    Setting ``isatty`` directly on a real ``TextIOWrapper`` raises
    ``AttributeError`` (C-level slots), so we swap the whole stream for
    a wrapper instead.
    """

    def __init__(self, wrapped: object) -> None:
        self._wrapped = wrapped

    def __getattr__(self, name: str) -> object:
        return getattr(self._wrapped, name)

    def isatty(self) -> bool:
        return False


@pytest.fixture
def deterministic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Erase non-deterministic environment knobs.

    Forces ``TZ=UTC``, ``PYTHONHASHSEED=0``, clears ``COLUMNS``/``LINES``,
    forces stderr to be considered non-TTY so the progress bar is off
    (R-LOG-021).
    """
    monkeypatch.setenv('TZ', 'UTC')
    monkeypatch.setenv('PYTHONHASHSEED', '0')
    monkeypatch.delenv('COLUMNS', raising=False)
    monkeypatch.delenv('LINES', raising=False)
    monkeypatch.setattr(sys, 'stderr', _NonTtyStream(sys.stderr))


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Auto-mark integration tests under ``tests/integration/``."""
    integration_root = (HERE / 'integration').resolve()
    for item in items:
        if integration_root in item.path.resolve().parents:
            item.add_marker(pytest.mark.integration)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the opt-in flag for live-network tests."""
    parser.addoption(
        '--run-live',
        action='store_true',
        default=False,
        help='Run tests marked @pytest.mark.live (network beyond XSD lookup).',
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip @pytest.mark.live tests unless opted in."""
    if 'live' in item.keywords and not item.config.getoption('--run-live'):
        pytest.skip('live test (use --run-live to enable)')


@pytest.fixture
def guard_user_platform_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Force ``platformdirs.user_cache_dir`` to a per-test scratch path.

    ``schema_types`` is REQUIRED to use ``import platformdirs`` and call
    ``platformdirs.user_cache_dir(...)`` through the module attribute
    (Phase 6), so patching that one attribute is sufficient — the name
    is looked up on the ``platformdirs`` module at call time (critique
    skill §7). Tests that touch the schema cache request this fixture
    explicitly. Returns the scratch path so tests may inspect it.
    """
    scratch = tmp_path / 'platform_cache_guard'
    scratch.mkdir()

    def fake_user_cache_dir(app: str) -> str:
        return str(scratch / app)

    monkeypatch.setattr(platformdirs, 'user_cache_dir', fake_user_cache_dir)
    return scratch


@pytest.fixture
def frozen_time() -> Iterator[None]:
    """Freeze wall clock to ``2026-05-14T00:00:00Z`` for byte-identical output.

    Note: freezegun does NOT freeze OS file mtime (``os.stat(...).st_mtime``).
    Phase 9's `$FILE_ZULU(index_file_name)$` macro reads file mtime, so
    tests that compare lblx bytes also need ``frozen_csv_mtime`` (below)
    or apply ``os.utime`` after writing the CSV. See Appendix I for the
    binding generation procedure.
    """
    from freezegun import freeze_time

    with freeze_time('2026-05-14T00:00:00Z'):
        yield


# POSIX seconds for 2026-05-14T00:00:00Z (UTC). MUST equal the
# frozen_time date; Appendix I's FROZEN_MTIME is the same value.
_FROZEN_MTIME_EPOCH = 1778716800


@pytest.fixture
def frozen_csv_mtime() -> int:
    """Provide the canonical frozen CSV mtime (POSIX seconds).

    Tests that produce byte-identical lblx outputs request this fixture
    in addition to ``frozen_time`` and pass
    ``csv_post_write_hook=lambda p: os.utime(p, (frozen_csv_mtime, frozen_csv_mtime))``
    to ``run_generate_index_file`` (or call ``os.utime`` on the CSV
    directly before label generation). This mirrors exactly what the
    golden-bytes generator does (Appendix I).
    """
    return _FROZEN_MTIME_EPOCH
