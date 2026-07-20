"""XSD download cache and PDS4 base-type resolution for pds4indextools.

This module implements spec section 11 (R-SCH-010..R-SCH-070) plus R-FS-005
(URL-scheme handling). It exposes two classes and one frozen mapping.

:class:`~pds4indextools.schema_types.SchemaCache` owns the on-disk XSD
download cache. It downloads each schema URL at most once (R-SCH-010,
R-SCH-020), storing the body under ``sha256(url).hexdigest() + '.xsd'`` in a
cache directory that defaults to ``platformdirs.user_cache_dir`` when the
caller passes none. Downloads flow through a hardened
:class:`requests.Session` (SSL verification on, capped redirects, a package
User-Agent, and a ``requests-file`` adapter mounted on ``file://`` so
``file://`` URLs resolve without network). Writes are atomic
(``write-temp-then-os.replace``) so concurrent workers cannot observe a
partial cache file. Network failures raise
:exc:`~pds4indextools.errors.SchemaNetworkError` (R-SCH-060) and an
unparseable cache file raises
:exc:`~pds4indextools.errors.SchemaCacheError` (R-SCH-070). The cache is
single-threaded; concurrent in-process callers MUST serialize access
externally.

:class:`~pds4indextools.schema_types.SchemaTypeResolver` holds the XSD trees
registered for a single run and resolves an XPath leaf tag to a PDS4 base
type. It enforces R-SCH-040 (each namespace binds to exactly one schema URL
per run) and raises :exc:`~pds4indextools.errors.SchemaResolutionError` when
no registered tree yields a type (R-SCH-050).

Resolution runs the 22 XPath queries of Appendix G in order against every
registered XSD tree and returns the first non-empty result. The 22 query
strings are reproduced VERBATIM from Appendix G as the module-level
``_XSD_QUERIES`` tuple below (they are physically unbreakable and exceed the
100-column lint gate if inlined here as prose, so they live in the tuple
where implicit string concatenation preserves them byte-for-byte). Query
template variables: ``{tag}`` is the leaf local-name and ``{ns}`` is the
namespace prefix ``pds:``. Their one-sentence rationales, in the same order:

1. A named complexType whose (possibly deep) extension records the base type.
2. A top-level element with an inline restriction anywhere beneath it.
3. A top-level attribute with an inline restriction anywhere beneath it.
4. A named simpleType whose direct child is a restriction.
5. A named simpleType whose restriction is nested under a union or list.
6. A named complexType whose direct child is an extension.
7. A named complexType with an extension one level down (e.g. a content model).
8. A named complexType with an extension two levels down.
9. A named complexType with an extension three levels down.
10. A nillable extension whose child records a nilReason instead of a base.
11. A ``Science_Facets`` member element that names its type directly.
12. A unit-bearing complexType whose extension is the ``_WO_Units`` base.
13. A simpleContent extension that is a direct child of the complexType.
14. A simpleContent extension one level down.
15. A simpleContent extension two levels down.
16. A simpleContent extension three levels down.
17. Any simpleContent extension anywhere beneath the complexType.
18. An element with an inline complexType/simpleContent extension.
19. An element with an inline simpleType restriction.
20. An attribute with an inline simpleType restriction.
21. An attribute that names its type directly.
22. An element that names its type directly.

The base type is returned verbatim with its XSD namespace prefix (e.g.
``pds:ASCII_LID``); the consumer strips the prefix at label-write time per
spec section 11.3.
"""

import hashlib
import os
import urllib.parse
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import platformdirs
import requests
import requests_file
from lxml import etree

from pds4indextools._logging import module_logger
from pds4indextools._version import __version__
from pds4indextools.errors import (
    SchemaCacheError,
    SchemaNetworkError,
    SchemaResolutionError,
    SchemaVersionError,
)

__all__ = [
    'AUTO_COLUMN_TYPES',
    'SchemaCache',
    'SchemaTypeResolver',
]

_logger = module_logger('schema_types')

# XML namespaces used when evaluating the Appendix G queries and when reading
# the ``xsi:schemaLocation`` attribute off a label root.
_XS_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'
_PDS_NAMESPACE = 'http://pds.nasa.gov/pds4/pds/v1'
_XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'

# The fixed namespace prefix substituted for ``{ns}`` in the query chain
# (Appendix G): every base type is recorded against the ``pds:`` prefix.
_PDS_PREFIX = 'pds:'

# Advisory only (R-FS-005): schemes with a builtin adapter on the default
# session. Other schemes succeed iff the caller registered an adapter.
_URL_SCHEMES_WITH_BUILTIN_ADAPTERS: tuple[str, ...] = ('http', 'https', 'file')

# Default download timeout in seconds (R-SCH-010).
_DEFAULT_TIMEOUT_SECONDS = 30.0

# The 22 XSD-resolution queries (Appendix G) as DATA. ``resolve`` runs them in
# order against every registered tree and returns the first non-empty match.
_XSD_QUERIES: tuple[str, ...] = (
    ".//xs:complexType[@name='{tag}']//xs:extension/@base",
    ".//*[local-name()='element' and @name='{tag}']"
    "/descendant::*[local-name()='restriction']/@base",
    ".//*[local-name()='attribute' and @name='{tag}']"
    "/descendant::*[local-name()='restriction']/@base",
    ".//*[local-name()='simpleType' and @name='{tag}']/*[local-name()='restriction']/@base",
    ".//*[local-name()='simpleType' and @name='{tag}']"
    "/descendant::*[local-name()='restriction']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']/*/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']/*/*/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']/*/*/*/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']//*[local-name()='extension']/*/@nilReason",
    ".//*[local-name()='complexType' and @name='Science_Facets']"
    "//*[local-name()='element' and @name='{tag}']/@type",
    ".//xs:complexType[@name='{tag}']"
    "//xs:extension[@base='{ns}{tag}_WO_Units']"
    "/xs:attribute[@name='unit']/@type",
    ".//*[local-name()='complexType' and @name='{tag}']"
    "/*[local-name()='simpleContent']/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']"
    "/*/*[local-name()='simpleContent']/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']"
    "/*/*/*[local-name()='simpleContent']/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']"
    "/*/*/*/*[local-name()='simpleContent']/*[local-name()='extension']/@base",
    ".//*[local-name()='complexType' and @name='{tag}']"
    "/descendant::*[local-name()='simpleContent']/*[local-name()='extension']/@base",
    ".//*[local-name()='element' and @name='{tag}']"
    "/*[local-name()='complexType']/*[local-name()='simpleContent']"
    "/*[local-name()='extension']/@base",
    ".//*[local-name()='element' and @name='{tag}']"
    "/*[local-name()='simpleType']/*[local-name()='restriction']/@base",
    ".//*[local-name()='attribute' and @name='{tag}']"
    "/*[local-name()='simpleType']/*[local-name()='restriction']/@base",
    ".//*[local-name()='attribute' and @name='{tag}']/@type",
    ".//*[local-name()='element' and @name='{tag}']/@type",
)

# Auto-column type table (R-AUTO-001, spec section 8.2). A frozen view
# prevents accidental mutation by callers (codebase-analysis section 5).
AUTO_COLUMN_TYPES: Mapping[str, str] = MappingProxyType(
    {
        'lid': 'pds:ASCII_LID',
        'lidvid': 'pds:ASCII_LIDVID_LID',
        'filespec': 'pds:ASCII_File_Specification_Name',
        'filename': 'pds:ASCII_File_Name',
        'bundle_name': 'pds:ASCII_Text_Preserved',
    }
)


def _xsd_query(
    xsd_tree: etree._Element,
    target_name: str,
    namespaces: dict[str, str],
) -> str | None:
    """Run the 22-query Appendix G chain and return the first non-empty match.

    Parameters:
        xsd_tree: The parsed root :class:`lxml.etree._Element` of one XSD.
        target_name: The leaf local-name to resolve (no namespace prefix).
        namespaces: The prefix-to-URI map used to evaluate the queries; MUST
            bind at least ``xs`` and ``pds``.

    Returns:
        The base type recorded in the XSD (prefix preserved, e.g.
        ``pds:ASCII_LID``), or ``None`` if all 22 queries are empty.

    Implements the resolution chain of spec section 11.2 (R-SCH-030) and
    Appendix G.
    """
    for template in _XSD_QUERIES:
        query = template.format(tag=target_name, ns=_PDS_PREFIX)
        matches = xsd_tree.xpath(query, namespaces=namespaces)
        if isinstance(matches, list) and matches:
            return str(matches[0])
    return None


class SchemaCache:
    """On-disk cache and downloader for PDS4 XSD schema files.

    Downloads each schema URL at most once and caches the body forever under
    ``sha256(url).hexdigest() + '.xsd'``. The default cache directory is
    ``platformdirs.user_cache_dir('pds4indextools')`` (R-SCH-020). The
    default session verifies SSL, caps redirects at five, sends a package
    User-Agent, and mounts a ``requests-file`` adapter on ``file://`` so
    ``file://`` URLs resolve locally (R-FS-005). Cache writes are atomic
    (``write-temp-then-os.replace``) so concurrent workers never see a
    partial file. The cache is single-threaded; concurrent in-process
    callers MUST serialize access externally.

    Parameters:
        cache_dir: The cache directory :class:`~pathlib.Path`, or ``None`` to
            use ``platformdirs.user_cache_dir('pds4indextools')`` (R-SCH-020).
        session: A pre-built :class:`requests.Session` to download through, or
            ``None`` to build the hardened default session.
        timeout: The per-request download timeout in seconds (R-SCH-010).

    Implements spec section 11.2 (R-SCH-010, R-SCH-020, R-SCH-060, R-SCH-070)
    and R-FS-005.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        *,
        session: requests.Session | None = None,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Store the cache directory, download session, and timeout.

        Parameters:
            cache_dir: The cache directory, or ``None`` for the platform cache.
            session: A pre-built session, or ``None`` for the default session.
            timeout: The per-request download timeout in seconds.
        """
        if cache_dir is None:
            cache_dir = Path(platformdirs.user_cache_dir('pds4indextools'))
        self.cache_dir = cache_dir
        self._timeout = timeout
        self._session = session if session is not None else self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        """Build the hardened default download session.

        Returns:
            A :class:`requests.Session` with SSL verification on, redirects
            capped at five, a package User-Agent, and a ``requests-file``
            adapter mounted on ``file://`` (R-FS-005, codebase-analysis
            section 7).
        """
        session = requests.Session()
        session.mount('file://', requests_file.FileAdapter())
        session.verify = True
        session.max_redirects = 5
        session.headers['User-Agent'] = f'rms-pds4indextools/{__version__}'
        return session

    def _cache_path(self, url: str) -> Path:
        """Return the cache-file path for ``url`` (``sha256(url).hexdigest() + '.xsd'``)."""
        digest = hashlib.sha256(url.encode('utf-8')).hexdigest()
        return self.cache_dir / f'{digest}.xsd'

    def fetch(self, url: str) -> bytes:
        """Return the body bytes for ``url``, downloading and caching on a miss.

        Parameters:
            url: The schema URL to fetch.

        Returns:
            The schema body bytes, read from cache on a hit or downloaded and
            cached on a miss.

        Raises:
            SchemaCacheError: If ``url`` contains userinfo (a username or
                password); such URLs are refused rather than cached
                (codebase-analysis section 7).
            SchemaNetworkError: If the download fails with a transport error or
                a non-2xx status (R-SCH-060).

        A cache hit issues no network request; a miss downloads once and
        writes the body atomically before returning (R-SCH-010, R-SCH-020).
        """
        parsed = urllib.parse.urlparse(url)
        if parsed.username or parsed.password:
            raise SchemaCacheError('URL contains userinfo; refuse to cache')

        cache_path = self._cache_path(url)
        if cache_path.is_file():
            return cache_path.read_bytes()

        _logger.debug('schema cache miss; downloading %s', url)
        body = self._download(url)
        self._store(cache_path, body)
        return body

    def _download(self, url: str) -> bytes:
        """Download ``url`` through the session and return the body bytes.

        Parameters:
            url: The schema URL to download.

        Returns:
            The response body bytes.

        Raises:
            SchemaNetworkError: On any transport error or non-2xx status
                (R-SCH-060).
        """
        try:
            response = self._session.get(url, timeout=self._timeout)
        except requests.RequestException as exc:
            raise SchemaNetworkError(f'failed to download XSD from {url}: {exc}') from exc
        try:
            response.raise_for_status()
            body = response.content
        except requests.RequestException as exc:
            raise SchemaNetworkError(f'failed to download XSD from {url}: {exc}') from exc
        finally:
            response.close()
        return body

    def _store(self, cache_path: Path, body: bytes) -> None:
        """Write ``body`` to ``cache_path`` atomically.

        Parameters:
            cache_path: The final cache-file path.
            body: The schema body bytes to store.

        The body is written to ``<cache_path>.tmp.<pid>`` then renamed with
        :func:`os.replace`; on any interruption the temp file is removed so no
        partial or orphaned file remains (critique skill section 6).
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_name(f'{cache_path.name}.tmp.{os.getpid()}')
        try:
            tmp_path.write_bytes(body)
            os.replace(tmp_path, cache_path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

    def parse_xsd(self, url: str) -> etree._Element:
        """Fetch ``url`` and parse it into an XSD element tree.

        Parameters:
            url: The schema URL to fetch and parse.

        Returns:
            The parsed root :class:`lxml.etree._Element`.

        Raises:
            SchemaCacheError: If the cached bytes are not well-formed XML
                (R-SCH-070).
            SchemaNetworkError: If the download fails (R-SCH-060).

        The cache is single-threaded; concurrent in-process callers MUST
        serialize access externally (codebase-analysis section 5).
        """
        body = self.fetch(url)
        try:
            return etree.fromstring(body)
        except etree.XMLSyntaxError as exc:
            raise SchemaCacheError(f'corrupt cached XSD for {url}: {exc}') from exc


class SchemaTypeResolver:
    """Per-run resolver of XPath leaf tags to PDS4 base types.

    Holds the XSD trees registered for a single run and the namespace-to-URL
    bookkeeping that enforces R-SCH-040 (each namespace binds to exactly one
    schema URL per run). :meth:`resolve` runs the 22-query Appendix G chain
    against every registered tree and returns the first non-empty match.

    Parameters:
        cache: The :class:`~pds4indextools.schema_types.SchemaCache` used to
            download and parse the registered XSDs.

    Implements spec section 11.2 (R-SCH-030, R-SCH-040, R-SCH-050) and the
    auto-column table of spec section 8.2 (R-AUTO-001).
    """

    def __init__(self, cache: SchemaCache) -> None:
        """Store the cache and initialise empty tree/namespace bookkeeping.

        Parameters:
            cache: The schema cache used to download and parse XSDs.
        """
        self._cache = cache
        self._trees: dict[str, etree._Element] = {}
        self._namespace_urls: dict[str, str] = {}
        # Canonical XPath prefix -> namespace URI, accumulated from label nsmaps
        # so :meth:`resolve` can prefer the schema of a leaf tag's OWN namespace.
        self._prefix_namespaces: dict[str, str] = {}
        # Prefixes bound to conflicting URIs across labels in this run: dropped
        # to the safe full scan rather than preferring one namespace's schema.
        self._ambiguous_prefixes: set[str] = set()

    def register_label(self, label_path: Path, root: etree._Element) -> None:
        """Register every ``.xsd`` URL declared in a label's ``xsi:schemaLocation``.

        Parameters:
            label_path: The label file :class:`~pathlib.Path`, attached to any
                raised error for diagnostic context.
            root: The parsed label root :class:`lxml.etree._Element`.

        Raises:
            SchemaResolutionError: If the label declares no (or an empty)
                ``xsi:schemaLocation`` attribute (R-SCH-050).
            SchemaVersionError: If a namespace already bound to one URL is
                re-declared with a different URL (R-SCH-040).
            SchemaNetworkError: If a schema download fails (R-SCH-060).
            SchemaCacheError: If a cached schema is unparseable (R-SCH-070).

        Each ``namespace-URI schema-URL`` pair whose URL ends in ``.xsd`` is
        downloaded (once) and parsed. The first label to declare a namespace
        fixes its URL for the whole run (R-SCH-040).
        """
        schema_location = root.get(f'{{{_XSI_NAMESPACE}}}schemaLocation')
        if schema_location is None or not schema_location.strip():
            raise SchemaResolutionError(
                'no xsi:schemaLocation declared in label', file_path=label_path
            )

        tokens = schema_location.split()
        for namespace_uri, url in zip(tokens[::2], tokens[1::2], strict=False):
            if not url.endswith('.xsd'):
                continue
            existing = self._namespace_urls.get(namespace_uri)
            if existing is not None and existing != url:
                raise SchemaVersionError(
                    f'namespace {namespace_uri} already bound to {existing}; label declares {url}',
                    file_path=label_path,
                )
            self._namespace_urls[namespace_uri] = url
            if url not in self._trees:
                self._trees[url] = self._cache.parse_xsd(url)

        # Record the canonical XPath prefix -> namespace URI bindings this label
        # declares, so a prefixed leaf tag resolves against its own namespace's
        # schema first. The default namespace is aliased to ``pds`` (R-XP-010).
        for prefix, uri in root.nsmap.items():
            key = _PDS_PREFIX.rstrip(':') if prefix is None else prefix
            existing = self._prefix_namespaces.get(key)
            if existing is not None and existing != uri:
                # Same canonical prefix bound to different URIs across labels:
                # neither may claim the resolve() fast path, so fall back to the
                # full registration-order scan (R-SCH-030) for this prefix.
                self._ambiguous_prefixes.add(key)
            else:
                self._prefix_namespaces.setdefault(key, uri)

    def resolve(self, xpath_leaf_tag: str) -> str:
        """Resolve an XPath leaf tag to its PDS4 base type.

        Parameters:
            xpath_leaf_tag: The canonical leaf tag (e.g. ``pds:logical_identifier``);
                any namespace prefix is stripped before matching by local-name.

        Returns:
            The base type recorded in the XSD, with its namespace prefix
            preserved (e.g. ``pds:ASCII_LID``); the consumer strips the prefix
            at label-write time per spec section 11.3.

        Raises:
            SchemaResolutionError: If no registered XSD yields a base type for
                the tag (R-SCH-050).

        Runs the 22-query Appendix G chain against the registered trees and
        returns the first non-empty match (R-SCH-030). The tree bound to the
        leaf tag's OWN namespace prefix is queried first, so a local-name defined
        in more than one registered schema resolves to the type in its own
        namespace rather than whichever schema registered first.
        """
        target_name = xpath_leaf_tag.rsplit(':', 1)[-1]
        for tree in self._ordered_trees(xpath_leaf_tag):
            namespaces = {'xs': _XS_NAMESPACE, 'pds': _PDS_NAMESPACE}
            for prefix, uri in tree.nsmap.items():
                if prefix is not None:
                    namespaces[prefix] = uri
            result = _xsd_query(tree, target_name, namespaces)
            if result is not None:
                return result
        raise SchemaResolutionError(f'no PDS4 base type for {xpath_leaf_tag}')

    def _ordered_trees(self, xpath_leaf_tag: str) -> list[etree._Element]:
        """Return the registered trees, the leaf tag's own namespace tree first.

        Parameters:
            xpath_leaf_tag: The canonical leaf tag, e.g. ``geom:method``.

        Returns:
            The registered XSD trees ordered so that the tree bound to the tag's
            namespace prefix (if any) comes first, followed by the remaining
            trees in registration order. Falling back to the other trees keeps
            resolution total, so this never resolves fewer tags than before.
        """
        ordered_urls: list[str] = []
        if ':' in xpath_leaf_tag:
            prefix = xpath_leaf_tag.rsplit(':', 1)[0]
            if prefix not in self._ambiguous_prefixes:
                uri = self._prefix_namespaces.get(prefix)
                url = self._namespace_urls.get(uri) if uri is not None else None
                if url is not None and url in self._trees:
                    ordered_urls.append(url)
        ordered_urls.extend(url for url in self._trees if url not in ordered_urls)
        return [self._trees[url] for url in ordered_urls]

    def auto_column_type(self, token: str) -> str:
        """Return the fixed PDS4 type for one of the five auto-column tokens.

        Parameters:
            token: One of ``lid``, ``lidvid``, ``filespec``, ``filename``, or
                ``bundle_name`` (spec section 8.2).

        Returns:
            The fixed PDS4 type string for ``token`` (e.g. ``pds:ASCII_LID``).

        Raises:
            KeyError: If ``token`` is not one of the five auto-column tokens;
                the caller guarantees it is (R-AUTO-001).

        Implements the auto-column type table of spec section 8.2.
        """
        return AUTO_COLUMN_TYPES[token]
