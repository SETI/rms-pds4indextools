"""Top-level label-scrape orchestrator composing the scraper submodules.

This module ties the parsing, value, nil, and LID submodules together into
the single public :func:`scrape_label` entry point and the immutable
:class:`ScrapeResult` it returns. It composes :mod:`pds4indextools.xpath_norm`
(canonicalization and renumbering) and :mod:`pds4indextools.schema_types` (the
per-run type resolver) to implement the label-scrape pipeline of spec section 9
(R-SCRAPE-*, R-VAL-*), section 10 (R-XP-013, R-XP-020), section 8 (R-LID-*,
R-AUTO-*, R-FS-010), and section 12 (R-NIL-*).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pds4indextools._logging import module_logger
from pds4indextools.config import NillableEntry
from pds4indextools.schema_types import SchemaTypeResolver
from pds4indextools.scraper import _lid, _nil, _parse, _value
from pds4indextools.xpath_norm import canonicalize_xpath, renumber_xpaths

__all__ = [
    'ScrapeResult',
    'scrape_label',
]

_logger = module_logger('scraper')

# The XML Schema instance namespace; its ``schemaLocation`` attribute lists the
# declared schema URLs recorded on the result.
_XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'

# The prefix the XML default namespace is aliased to on the result namespaces
# map (R-XP-010), matching the canonical-XPath aliasing.
_DEFAULT_NAMESPACE_PREFIX = 'pds'


@dataclass(frozen=True, slots=True, kw_only=True)
class ScrapeResult:
    """The immutable outcome of scraping one PDS4 label.

    Parameters:
        label_path: The scraped label file :class:`~pathlib.Path`.
        canonical_root_tag: The canonical, prefixed tag of the root element
            (e.g. ``pds:Product_Observational``), without an occurrence
            predicate.
        rows: The scraped values keyed by renumbered canonical XPath, in DOM
            pre-order insertion order (section 7.1 contract).
        auto_columns: The five derived auto-column values keyed by token, in
            fixed derivation order (section 7.1 contract).
        lid: The validated logical identifier (R-LID-001).
        version_id: The validated version identifier (R-LID-010).
        namespaces: The root namespace map with the XML default namespace
            aliased to ``pds`` and every other prefix preserved (section 10).
        schema_urls: The schema URLs declared in ``xsi:schemaLocation``, in
            declared order.

    The ``rows`` and ``auto_columns`` mappings are ordinary ``dict`` objects
    whose insertion order is load-bearing and MUST NOT be reordered by
    consumers (section 7.1).

    Implements the public result contract of spec sections 8, 9, 10, and 12.
    """

    label_path: Path
    canonical_root_tag: str
    rows: dict[str, str]
    auto_columns: dict[str, str]
    lid: str
    version_id: str
    namespaces: dict[str, str]
    schema_urls: tuple[str, ...]


def _record_namespaces(nsmap: Mapping[str | None, str]) -> dict[str, str]:
    """Alias the default namespace to ``pds`` and preserve the rest (R-XP-010)."""
    namespaces: dict[str, str] = {}
    for prefix, uri in nsmap.items():
        namespaces[_DEFAULT_NAMESPACE_PREFIX if prefix is None else prefix] = uri
    return namespaces


def _record_schema_urls(schema_location: str | None) -> tuple[str, ...]:
    """Extract the declared schema URLs from an ``xsi:schemaLocation`` value.

    Parameters:
        schema_location: The raw ``xsi:schemaLocation`` attribute value, or
            ``None`` when the attribute is absent.

    Returns:
        The URL tokens (the odd-indexed members of the whitespace-split
        namespace/URL pairs) in declared order, or an empty tuple when the
        attribute is absent.
    """
    if schema_location is None:
        return ()
    tokens = schema_location.split()
    return tuple(tokens[1::2])


def scrape_label(
    label_path: Path,
    *,
    bundle_root: Path,
    resolver: SchemaTypeResolver,
    nillable_config: Mapping[str, NillableEntry],
    fixed_width_mode: bool,
    seen_lids: dict[str, Path] | None = None,
) -> ScrapeResult:
    """Scrape one PDS4 label into a :class:`ScrapeResult`.

    Parameters:
        label_path: The label file :class:`~pathlib.Path` to scrape.
        bundle_root: The bundle root :class:`~pathlib.Path` the ``filespec``
            auto-column is made relative to.
        resolver: The per-run
            :class:`~pds4indextools.schema_types.SchemaTypeResolver` used to
            resolve nilled elements' data types (R-NIL-020).
        nillable_config: The per-data-type nilReason replacement mapping (the
            merged config ``nillable`` section).
        fixed_width_mode: ``True`` selects fixed-width value handling, where an
            embedded double quote is kept; ``False`` rejects it (R-VAL-040).
        seen_lids: A shared mutable dict mapping each already-seen LID to the
            path that declared it, or ``None`` to skip cross-label uniqueness.
            When not ``None`` it is mutated by side effect and is NOT
            thread-safe; the library is documented as single-threaded
            (section 7.1, R-LID-020).

    Returns:
        The :class:`ScrapeResult` describing the label's scraped rows, derived
        auto-columns, identifiers, namespaces, and schema URLs.

    Raises:
        ParseError: On a UTF-8 BOM (R-PARSE-001), malformed XML (R-PARSE-002),
            or a root with no default namespace (R-XP-013).
        ScrapedValueError: On a control character, non-ASCII character, or an
            illegal double quote in a scraped value (R-VAL-020/030/040).
        NilError: On a bad ``nilReason`` or an unmapped nilled data type
            (R-NIL-010/030).
        LidError: On a missing, duplicated, or malformed identifier, or a
            cross-label LID collision (R-LID-001/010/020).
        LabelError: On a ``filespec`` exceeding 255 bytes (R-FS-010).
        XPathError: On a non-monotone occurrence interleave while renumbering
            (R-XP-021).
        SchemaResolutionError: If a nilled element's data type cannot be
            resolved (R-SCH-050).

    Runs the nine-step pipeline of section 7.1: BOM check, parse, default
    namespace validation, pre-order leaf walk with value normalization and nil
    substitution, post-walk renumbering, identifier validation and auto-column
    derivation, and cross-label LID dedup.

    Implements spec sections 8, 9, 10, and 12.
    """
    _parse.reject_bom(label_path)
    tree = _parse.parse_label(label_path)
    root = tree.getroot()
    _parse.require_default_namespace(root, label_path)

    ordered_xpaths: list[str] = []
    pre_rows: dict[str, str] = {}
    for element, canonical_xpath in _parse.iter_leaves(tree):
        if _nil.is_nil(element):
            value = _nil.resolve_nil_value(
                element,
                canonical_xpath,
                resolver=resolver,
                nillable_config=nillable_config,
                label_path=label_path,
            )
        else:
            text = element.text
            if text is None or not text.strip():
                continue
            value = _value.checked_value(
                _value.normalize_value(text),
                canonical_xpath,
                fixed_width_mode=fixed_width_mode,
                label_path=label_path,
            )
        ordered_xpaths.append(canonical_xpath)
        pre_rows[canonical_xpath] = value

    renumbered = renumber_xpaths(ordered_xpaths)
    rows: dict[str, str] = {renumbered[xpath]: pre_rows[xpath] for xpath in ordered_xpaths}

    default_uri = root.nsmap[None]
    lid = _lid.extract_lid(root, default_uri, label_path)
    version_id = _lid.extract_version_id(root, default_uri, label_path)
    auto_columns = _lid.compute_auto_columns(lid, version_id, label_path, bundle_root)
    _lid.check_cross_label_lid(lid, label_path, seen_lids)

    canonical_root_tag = canonicalize_xpath(root.tag, root.nsmap).split('<', 1)[0]
    _logger.debug('scraped %s with %d rows', label_path, len(rows))
    return ScrapeResult(
        label_path=label_path,
        canonical_root_tag=canonical_root_tag,
        rows=rows,
        auto_columns=auto_columns,
        lid=lid,
        version_id=version_id,
        namespaces=_record_namespaces(root.nsmap),
        schema_urls=_record_schema_urls(root.get(f'{{{_XSI_NAMESPACE}}}schemaLocation')),
    )
