"""Unit tests for :mod:`pds4indextools.schema_types` (Phase 6).

Covers the schema download cache (:class:`~pds4indextools.schema_types.SchemaCache`)
and the per-run XSD type resolver
(:class:`~pds4indextools.schema_types.SchemaTypeResolver`), exercising
spec section 11 (R-SCH-010..R-SCH-070), R-FS-005, R-AUTO-001, and the
22-query resolution chain of Appendix G.

Real network is OFF in every test here: HTTP GETs are mocked with the
``responses`` library and non-network resolution reads from a per-test
cache seeded with the hand-curated XSD snippets in
``tests/data/xsd_cache_seed/`` (Appendix A.11). A handful of rows inspect
``SchemaCache._session`` directly; that is the sanctioned exception to
the public-names boundary noted in plan section 6.2 (the internally
constructed session has no public accessor).
"""

import hashlib
import os
from pathlib import Path
from unittest import mock

import pytest
import requests
import responses
from lxml import etree

from pds4indextools.errors import (
    SchemaCacheError,
    SchemaNetworkError,
    SchemaResolutionError,
    SchemaVersionError,
)
from pds4indextools.schema_types import (
    AUTO_COLUMN_TYPES,
    SchemaCache,
    SchemaTypeResolver,
)

NS_PDS = 'http://pds.nasa.gov/pds4/pds/v1'
NS_GEOM = 'http://pds.nasa.gov/pds4/geom/v1'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'

PDS_URL = 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd'
PDS_URL_ALT = 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1K00.xsd'
GEOM_URL = 'https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1L00_2000.xsd'

SEED_DIR = Path(__file__).resolve().parents[1] / 'data' / 'xsd_cache_seed'


def _seed_bytes(name: str) -> bytes:
    """Return the raw bytes of a seed XSD under ``tests/data/xsd_cache_seed/``."""
    return (SEED_DIR / name).read_bytes()


def _seed_cache(cache_dir: Path, url: str, seed_name: str) -> Path:
    """Write ``seed_name`` into ``cache_dir`` at the sha256 cache-hit key for ``url``."""
    digest = hashlib.sha256(url.encode('utf-8')).hexdigest()
    path = cache_dir / f'{digest}.xsd'
    path.write_bytes(_seed_bytes(seed_name))
    return path


def _label_root(schema_location: str | None) -> etree._Element:
    """Build a minimal label root element carrying ``xsi:schemaLocation``.

    Parameters:
        schema_location: The value for the ``xsi:schemaLocation`` attribute,
            or ``None`` to omit the attribute entirely.

    Returns:
        The parsed root :class:`lxml.etree._Element`.
    """
    attr = '' if schema_location is None else f' xsi:schemaLocation="{schema_location}"'
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Product_Observational xmlns="{NS_PDS}" xmlns:xsi="{NS_XSI}"{attr}>'
        '<Identification_Area/>'
        '</Product_Observational>'
    )
    return etree.fromstring(xml.encode('utf-8'))


class _StubAdapter(requests.adapters.BaseAdapter):
    """Minimal requests adapter returning a fixed body for any URL scheme.

    Used to prove R-FS-005: a scheme with no builtin adapter (e.g.
    ``ftp://``) works iff the caller registered an adapter on the session.
    """

    def __init__(self, body: bytes) -> None:
        super().__init__()
        self._body = body

    def send(
        self, request: requests.PreparedRequest, *args: object, **kwargs: object
    ) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response._content = self._body
        response.url = request.url or ''
        return response

    def close(self) -> None:
        return None


# --------------------------------------------------------------------------
# SchemaCache — download, cache, and session defaults
# --------------------------------------------------------------------------


@responses.activate
def test_schemacache_cache_miss_downloads_and_caches(isolated_xsd_cache: Path) -> None:
    """T-SCH-001, T-SCH-002, R-SCH-010, R-SCH-020: miss downloads; hit is offline."""
    responses.add(responses.GET, PDS_URL, body=_seed_bytes('pds_v1_basic.xsd'), status=200)
    cache = SchemaCache(isolated_xsd_cache)

    first = cache.fetch(PDS_URL)
    assert first == _seed_bytes('pds_v1_basic.xsd')

    digest = hashlib.sha256(PDS_URL.encode('utf-8')).hexdigest()
    assert (isolated_xsd_cache / f'{digest}.xsd').is_file()

    second = cache.fetch(PDS_URL)
    assert second == first
    assert len(responses.calls) == 1


def test_schemacache_uses_platformdirs_when_dir_none(
    guard_user_platform_cache: Path,
) -> None:
    """R-SCH-020: a ``None`` cache dir resolves through ``platformdirs``."""
    cache = SchemaCache()
    assert cache.cache_dir == guard_user_platform_cache / 'pds4indextools'


@responses.activate
def test_schemacache_network_failure_raises_schemanetworkerror(
    isolated_xsd_cache: Path,
) -> None:
    """T-SCH-040, R-SCH-060: HTTP 500 raises a non-fail-slow network error."""
    responses.add(responses.GET, PDS_URL, status=500)
    cache = SchemaCache(isolated_xsd_cache)

    with pytest.raises(SchemaNetworkError) as exc_info:
        cache.fetch(PDS_URL)
    assert 'PDS4_PDS_1L00.xsd' in str(exc_info.value)
    assert type(exc_info.value).FAIL_SLOW_ELIGIBLE is False


@responses.activate
def test_schemacache_connection_refused_raises_schemanetworkerror(
    isolated_xsd_cache: Path,
) -> None:
    """R-SCH-060: a transport-level connection error surfaces as a network error."""
    responses.add(responses.GET, PDS_URL, body=requests.exceptions.ConnectionError('refused'))
    cache = SchemaCache(isolated_xsd_cache)

    with pytest.raises(SchemaNetworkError) as exc_info:
        cache.fetch(PDS_URL)
    assert 'PDS4_PDS_1L00.xsd' in str(exc_info.value)


def test_schemacache_fetch_uses_30s_timeout(isolated_xsd_cache: Path) -> None:
    """R-SCH-010: the download passes the 30-second timeout to the session."""
    response = mock.Mock()
    response.content = _seed_bytes('pds_v1_basic.xsd')
    response.raise_for_status = mock.Mock()
    mock_session = mock.Mock()
    mock_session.get.return_value = response

    cache = SchemaCache(isolated_xsd_cache, session=mock_session)
    cache.fetch(PDS_URL)

    mock_session.get.assert_called_once_with(PDS_URL, timeout=30.0)


def test_schemacache_corrupt_cache_raises_schemacacheerror(
    isolated_xsd_cache: Path,
) -> None:
    """T-SCH-050, R-SCH-070: an unparseable cache file raises a cache error."""
    digest = hashlib.sha256(PDS_URL.encode('utf-8')).hexdigest()
    (isolated_xsd_cache / f'{digest}.xsd').write_bytes(b'<not-well-formed')
    cache = SchemaCache(isolated_xsd_cache)

    with pytest.raises(SchemaCacheError) as exc_info:
        cache.parse_xsd(PDS_URL)
    assert 'PDS4_PDS_1L00.xsd' in str(exc_info.value)


def test_schemacache_file_url_uses_filemount(isolated_xsd_cache: Path, tmp_path: Path) -> None:
    """R-FS-005: ``file://`` URLs are read via the requests-file adapter, no HTTP."""
    xsd_file = tmp_path / 'local.xsd'
    xsd_file.write_bytes(_seed_bytes('pds_v1_basic.xsd'))
    cache = SchemaCache(isolated_xsd_cache)

    body = cache.fetch(xsd_file.as_uri())
    assert body == _seed_bytes('pds_v1_basic.xsd')


@responses.activate
def test_schemacache_url_to_path_uses_sha256(isolated_xsd_cache: Path) -> None:
    """R-SCH-020: the cache filename is ``sha256(url).hexdigest() + '.xsd'``."""
    responses.add(responses.GET, PDS_URL, body=_seed_bytes('pds_v1_basic.xsd'))
    cache = SchemaCache(isolated_xsd_cache)
    cache.fetch(PDS_URL)

    expected = hashlib.sha256(PDS_URL.encode('utf-8')).hexdigest() + '.xsd'
    assert (isolated_xsd_cache / expected).is_file()


def test_schemacache_url_with_userinfo_refuses_to_cache(
    isolated_xsd_cache: Path,
) -> None:
    """codebase-analysis section 7: a URL carrying userinfo is refused."""
    cache = SchemaCache(isolated_xsd_cache)

    with pytest.raises(SchemaCacheError) as exc_info:
        cache.fetch('https://user:pw@example.com/schema.xsd')
    assert 'userinfo' in str(exc_info.value)


@responses.activate
def test_schemacache_atomic_write_no_partial_file_on_kill(
    isolated_xsd_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """critique skill section 6: an interrupted write leaves no final or temp file."""
    responses.add(responses.GET, PDS_URL, body=_seed_bytes('pds_v1_basic.xsd'))
    cache = SchemaCache(isolated_xsd_cache)
    digest = hashlib.sha256(PDS_URL.encode('utf-8')).hexdigest()
    final = isolated_xsd_cache / f'{digest}.xsd'

    def boom(src: object, dst: object) -> None:
        raise OSError('interrupted before rename completes')

    monkeypatch.setattr(os, 'replace', boom)
    with pytest.raises(OSError, match='interrupted'):
        cache.fetch(PDS_URL)
    assert not final.exists()
    assert list(isolated_xsd_cache.glob('*.tmp.*')) == []

    monkeypatch.undo()
    body = cache.fetch(PDS_URL)
    assert body == _seed_bytes('pds_v1_basic.xsd')
    assert final.is_file()
    assert list(isolated_xsd_cache.glob('*.tmp.*')) == []


def test_schemacache_session_user_agent_set(isolated_xsd_cache: Path) -> None:
    """codebase-analysis section 7: the default session sends a package User-Agent."""
    cache = SchemaCache(isolated_xsd_cache)
    assert 'rms-pds4indextools/' in cache._session.headers['User-Agent']


def test_schemacache_session_ssl_verify_on(isolated_xsd_cache: Path) -> None:
    """codebase-analysis section 7: SSL verification is on by default."""
    cache = SchemaCache(isolated_xsd_cache)
    assert cache._session.verify is True


def test_schemacache_session_max_redirects(isolated_xsd_cache: Path) -> None:
    """codebase-analysis section 7: the default session caps redirects at 5."""
    cache = SchemaCache(isolated_xsd_cache)
    assert cache._session.max_redirects == 5


@responses.activate
def test_url_to_cache_filename_deterministic(isolated_xsd_cache: Path) -> None:
    """R-IDX-001, R-IDX-002: the cache filename is identical across instances."""
    responses.add(responses.GET, PDS_URL, body=_seed_bytes('pds_v1_basic.xsd'))
    first_cache = SchemaCache(isolated_xsd_cache)
    first_cache.fetch(PDS_URL)

    second_cache = SchemaCache(isolated_xsd_cache)
    body = second_cache.fetch(PDS_URL)
    assert body == _seed_bytes('pds_v1_basic.xsd')
    assert len(responses.calls) == 1


# --------------------------------------------------------------------------
# SchemaTypeResolver — registration, resolution, auto-columns
# --------------------------------------------------------------------------


def test_typeresolver_basic_resolution_logical_identifier(
    isolated_xsd_cache: Path,
) -> None:
    """T-SCH-010, R-SCH-030: ``logical_identifier`` resolves to ``pds:ASCII_LID``."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_basic.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    resolver.register_label(Path('label.xml'), _label_root(f'{NS_PDS} {PDS_URL}'))

    assert resolver.resolve('logical_identifier') == 'pds:ASCII_LID'


def test_typeresolver_unit_aware_wo_units_fallback(isolated_xsd_cache: Path) -> None:
    """R-SCH-030: a unit-aware simpleContent/extension type resolves to its ``_WO_Units`` base."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_units.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    resolver.register_label(Path('label.xml'), _label_root(f'{NS_PDS} {PDS_URL}'))

    assert resolver.resolve('pds:Wavelength_Range') == 'pds:Wavelength_Range_WO_Units'


def test_typeresolver_unresolved_xpath_raises_schemaresolutionerror(
    isolated_xsd_cache: Path,
) -> None:
    """T-SCH-030, R-SCH-050: an unknown leaf raises with its name in the message."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_basic.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    resolver.register_label(Path('label.xml'), _label_root(f'{NS_PDS} {PDS_URL}'))

    with pytest.raises(SchemaResolutionError) as exc_info:
        resolver.resolve('pds:no_such_element')
    assert 'no_such_element' in str(exc_info.value)


def test_typeresolver_cross_label_namespace_consistency_first_url_fixed(
    isolated_xsd_cache: Path,
) -> None:
    """R-SCH-040: two labels sharing a namespace URL register without error."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_basic.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    resolver.register_label(Path('one.xml'), _label_root(f'{NS_PDS} {PDS_URL}'))
    resolver.register_label(Path('two.xml'), _label_root(f'{NS_PDS} {PDS_URL}'))

    assert resolver.resolve('logical_identifier') == 'pds:ASCII_LID'


def test_typeresolver_cross_label_namespace_inconsistency_raises(
    isolated_xsd_cache: Path,
) -> None:
    """T-SCH-020, R-SCH-040: a second URL for a bound namespace names both URLs."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_basic.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    resolver.register_label(Path('one.xml'), _label_root(f'{NS_PDS} {PDS_URL}'))

    with pytest.raises(SchemaVersionError) as exc_info:
        resolver.register_label(Path('two.xml'), _label_root(f'{NS_PDS} {PDS_URL_ALT}'))
    message = str(exc_info.value)
    assert PDS_URL in message
    assert PDS_URL_ALT in message


@pytest.mark.parametrize('schema_location', [None, '', '   '])
def test_typeresolver_no_schemalocation_raises_schemaresolutionerror(
    isolated_xsd_cache: Path, schema_location: str | None
) -> None:
    """R-SCH-050: a missing or empty ``xsi:schemaLocation`` raises a resolution error."""
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))

    with pytest.raises(SchemaResolutionError) as exc_info:
        resolver.register_label(Path('label.xml'), _label_root(schema_location))
    assert 'no xsi:schemaLocation' in str(exc_info.value)


@pytest.mark.parametrize(
    ('token', 'expected'),
    [
        ('lid', 'pds:ASCII_LID'),
        ('lidvid', 'pds:ASCII_LIDVID_LID'),
        ('filespec', 'pds:ASCII_File_Specification_Name'),
        ('filename', 'pds:ASCII_File_Name'),
        ('bundle_name', 'pds:ASCII_Text_Preserved'),
    ],
)
def test_auto_column_types_all_five_keys_present(
    isolated_xsd_cache: Path, token: str, expected: str
) -> None:
    """R-AUTO-001, section 8.2: each of the five auto tokens maps to its fixed type."""
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    assert resolver.auto_column_type(token) == expected
    assert AUTO_COLUMN_TYPES[token] == expected
    assert len(AUTO_COLUMN_TYPES) == 5


def test_auto_column_types_unknown_token_keyerror(isolated_xsd_cache: Path) -> None:
    """Internal contract: an unknown auto token raises ``KeyError`` naming the token."""
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))

    with pytest.raises(KeyError) as exc_info:
        resolver.auto_column_type('frobnicate')
    assert 'frobnicate' in str(exc_info.value)


def test_register_label_parses_multiple_xsds_listed_in_schemalocation(
    isolated_xsd_cache: Path,
) -> None:
    """R-SCH-010: every ``.xsd`` URL in ``xsi:schemaLocation`` is fetched and searched."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_basic.xsd')
    _seed_cache(isolated_xsd_cache, GEOM_URL, 'geom_v1.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    resolver.register_label(
        Path('label.xml'),
        _label_root(f'{NS_PDS} {PDS_URL} {NS_GEOM} {GEOM_URL}'),
    )

    assert resolver.resolve('logical_identifier') == 'pds:ASCII_LID'
    assert resolver.resolve('method') == 'geom:ASCII_Short_String_Collapsed'


def test_register_label_ignores_non_xsd_schemalocation_entries(
    isolated_xsd_cache: Path,
) -> None:
    """R-SCH-010: ``xsi:schemaLocation`` entries not ending in ``.xsd`` are skipped."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_basic.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    schema_location = f'{NS_PDS} {PDS_URL} http://example.com/cat some_catalog.xml'
    resolver.register_label(Path('label.xml'), _label_root(schema_location))

    assert resolver.resolve('logical_identifier') == 'pds:ASCII_LID'


def test_resolve_xpath_preserves_namespace_prefix(isolated_xsd_cache: Path) -> None:
    """Spec section 11.3: the resolved type keeps the XSD namespace prefix."""
    _seed_cache(isolated_xsd_cache, PDS_URL, 'pds_v1_basic.xsd')
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache))
    resolver.register_label(Path('label.xml'), _label_root(f'{NS_PDS} {PDS_URL}'))

    result = resolver.resolve('pds:logical_identifier')
    assert result == 'pds:ASCII_LID'
    assert result.startswith('pds:')


def test_register_label_with_non_default_scheme_uses_registered_adapter(
    isolated_xsd_cache: Path,
) -> None:
    """R-FS-005: a non-default scheme resolves through a caller-registered adapter."""
    session = requests.Session()
    session.mount('ftp://', _StubAdapter(_seed_bytes('pds_v1_basic.xsd')))
    resolver = SchemaTypeResolver(SchemaCache(isolated_xsd_cache, session=session))
    ftp_url = 'ftp://example.com/pds.xsd'
    resolver.register_label(Path('label.xml'), _label_root(f'{NS_PDS} {ftp_url}'))

    assert resolver.resolve('logical_identifier') == 'pds:ASCII_LID'
