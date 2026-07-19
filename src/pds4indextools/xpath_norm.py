"""Canonicalization and per-label renumbering of lxml-native XPaths.

This module implements spec section 10 (R-XP-001..R-XP-030). It has two
public functions.
:func:`~pds4indextools.xpath_norm.canonicalize_xpath` rewrites an
lxml-native XPath such as
``/{http://pds.nasa.gov/pds4/pds/v1}Product_Observational[2]/{...}foo[1]``
into the canonical form ``pds:Product_Observational<2>/pds:foo<1>``: every
segment carries a namespace prefix and an angle-bracketed occurrence
predicate, the XML default namespace is always aliased to ``pds:``
(R-XP-010), and every other declared prefix is preserved verbatim
(R-XP-011).
:func:`~pds4indextools.xpath_norm.renumber_xpaths` takes a sequence of
already-canonicalized XPaths in pre-order walk order (spec section 9.2) and
remaps lxml's structural ``<n>`` predicates to dense occurrence indexes that
restart at 1 for each distinct parent-and-tag group (R-XP-020), preserving
first-occurrence order (R-XP-030).

Both failure modes surface as fail-slow-eligible label-content errors: a
label whose root declares no default namespace, or an lxml segment that is
structurally malformed, raises
:exc:`~pds4indextools.errors.ParseError` (R-XP-013); a non-monotone
interleave that pre-order traversal can never legitimately produce raises
:exc:`~pds4indextools.errors.XPathError` (R-XP-021).
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pds4indextools.errors import ParseError, XPathError

__all__ = [
    'canonicalize_xpath',
    'renumber_xpaths',
]

# The default namespace (key ``None`` in an lxml ``nsmap``) is always aliased
# to this prefix in canonical XPaths (R-XP-010).
_DEFAULT_NAMESPACE_PREFIX = 'pds'

# Parses one lxml-native segment ``{namespace-uri}LocalName[n]`` where the
# ``[n]`` predicate is optional. The local-name character class deliberately
# does NOT restrict to ASCII: lxml has already validated every parsed element
# as a legal XML name, and XML names may contain non-ASCII characters. The
# spec's ASCII-only rules cover scraped values (R-VAL-020/030) and column
# names (R-MAP-043) only; they do not extend to element names, so the
# canonicalizer must not reject a label because a tag contains a non-ASCII
# character (owner decision #5). The class rejects only structurally
# malformed segments: a missing ``{ns}`` wrapper, an empty name, or a
# malformed ``[n]`` predicate.
_SEGMENT_RE = re.compile(r'^\{(?P<ns>[^}]+)\}(?P<name>[^{}/\[\]]+)(?:\[(?P<idx>\d+)\])?$')

# Splits an lxml-native path into segments at each ``/`` that begins a new
# ``{namespace-uri}`` segment. A plain ``str.split('/')`` cannot be used
# because a namespace URI (e.g. ``http://pds.nasa.gov/...``) itself contains
# slashes; only a ``/`` immediately followed by ``{`` is a real boundary.
_SEGMENT_SPLIT_RE = re.compile(r'/(?=\{)')


@dataclass(frozen=True, slots=True)
class _XPathPart:
    """One parsed segment of an lxml-native XPath.

    Parameters:
        raw_segment: The original segment text, e.g. ``"{ns}Tag[2]"``.
        namespace_uri: The namespace URI inside the braces, e.g.
            ``"http://pds.nasa.gov/pds4/pds/v1"``.
        local_name: The element local name, e.g. ``"Tag"``.
        raw_index: The lxml ``[n]`` structural index, or ``1`` when the
            predicate is absent.
    """

    raw_segment: str
    namespace_uri: str
    local_name: str
    raw_index: int


def canonicalize_xpath(raw: str, nsmap: Mapping[str | None, str]) -> str:
    """Rewrite an lxml-native XPath into its canonical string form.

    Each ``/``-separated segment ``{uri}LocalName[n]`` is rewritten to
    ``prefix:LocalName<n>``: the namespace URI is mapped back to its prefix,
    the XML default namespace is aliased to ``pds:`` (R-XP-010), every other
    declared prefix is preserved verbatim (R-XP-011), and the occurrence
    predicate ``<n>`` is always emitted, defaulting to ``<1>`` when lxml
    omitted the predicate (R-XP-002). Segments are rejoined with forward
    slashes and no leading slash (R-XP-003). Element names are not restricted
    to ASCII (owner decision #5).

    Parameters:
        raw: The lxml-native XPath, e.g.
            ``"/{http://pds.nasa.gov/pds4/pds/v1}Product_Observational[2]"``.
            A single leading slash, if present, is stripped before splitting.
        nsmap: The root element's namespace map, mapping each prefix (or
            ``None`` for the default namespace) to its namespace URI, exactly
            as produced by lxml's ``root.nsmap``.

    Returns:
        The canonical XPath string, e.g.
        ``"pds:Product_Observational<2>"``.

    Raises:
        ParseError: If ``nsmap`` declares no default namespace, i.e.
            ``nsmap.get(None) is None`` (R-XP-013); or if any segment is
            structurally malformed, e.g. it lacks the ``{uri}`` wrapper.

    Implements R-XP-001, R-XP-002, R-XP-003, R-XP-010, R-XP-011, R-XP-012,
    and R-XP-013.
    """
    if nsmap.get(None) is None:
        raise ParseError('label root element declares no default namespace')

    uri_to_prefix: dict[str, str] = {}
    for prefix, uri in nsmap.items():
        uri_to_prefix[uri] = _DEFAULT_NAMESPACE_PREFIX if prefix is None else prefix

    canonical_segments: list[str] = []
    for segment in _SEGMENT_SPLIT_RE.split(raw.removeprefix('/')):
        match = _SEGMENT_RE.match(segment)
        if match is None:
            raise ParseError(f'malformed lxml xpath segment {segment!r}')
        idx_group = match.group('idx')
        part = _XPathPart(
            raw_segment=segment,
            namespace_uri=match.group('ns'),
            local_name=match.group('name'),
            raw_index=int(idx_group) if idx_group is not None else 1,
        )
        prefix = uri_to_prefix[part.namespace_uri]
        canonical_segments.append(f'{prefix}:{part.local_name}<{part.raw_index}>')

    return '/'.join(canonical_segments)


def renumber_xpaths(xpaths: Sequence[str]) -> dict[str, str]:
    """Remap lxml structural indexes to dense per-parent occurrence indexes.

    The input is a sequence of already-canonicalized XPaths in pre-order walk
    order (spec section 9.2). Each segment is grouped by a ``bucket_key`` of
    ``(renumbered_parent_path, prefix:local_name)``: the parent path is the
    already-renumbered canonical text of every preceding segment, and the
    tag text excludes the ``<n>`` predicate. Within each bucket the distinct
    structural indexes are remapped in first-seen order to a dense sequence
    starting at 1 (R-XP-020). Because pre-order traversal never revisits a
    lower sibling index after advancing past it, an index strictly less than
    the largest already seen in its bucket is a non-monotone interleave and is
    rejected (R-XP-021); indexes equal to an already-seen value repeat an
    ancestor segment and are accepted.

    Parameters:
        xpaths: The already-canonicalized XPaths in pre-order walk order. The
            sequence order is the first-occurrence order that the result
            preserves (R-XP-030).

    Returns:
        A dict mapping each input XPath to its renumbered form, iterating in
        input order (R-XP-030).

    Raises:
        XPathError: If a segment's structural index is strictly less than the
            largest index already seen in its bucket, i.e. a non-monotone
            interleave; the message cites the offending XPath and the prior
            key that set the bucket's maximum (R-XP-021).

    Implements R-XP-020, R-XP-021, and R-XP-030.
    """
    # Per bucket: distinct structural index -> dense 1-based occurrence index,
    # in first-seen order.
    bucket_indexes: dict[tuple[str, str], dict[int, int]] = {}
    # Per bucket: the largest structural index seen so far and the input
    # XPath that set it (used to cite the conflict in R-XP-021).
    bucket_max: dict[tuple[str, str], tuple[int, str]] = {}

    result: dict[str, str] = {}
    for xpath in xpaths:
        renumbered_segments: list[str] = []
        parent_path = ''
        for segment in xpath.split('/'):
            prefix_local, _, index_text = segment.partition('<')
            raw_index = int(index_text[:-1])
            bucket_key = (parent_path, prefix_local)

            if bucket_key in bucket_max and raw_index < bucket_max[bucket_key][0]:
                prior_xpath = bucket_max[bucket_key][1]
                raise XPathError(
                    f'non-monotone interleave at {xpath}; conflicts with {prior_xpath}'
                )
            if bucket_key not in bucket_max or raw_index > bucket_max[bucket_key][0]:
                bucket_max[bucket_key] = (raw_index, xpath)

            indexes = bucket_indexes.setdefault(bucket_key, {})
            if raw_index not in indexes:
                indexes[raw_index] = len(indexes) + 1

            renumbered_segments.append(f'{prefix_local}<{indexes[raw_index]}>')
            parent_path = '/'.join(renumbered_segments)

        result[xpath] = '/'.join(renumbered_segments)

    return result
