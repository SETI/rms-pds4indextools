"""Label parsing, BOM rejection, namespace validation, and the leaf walk.

This is the lowest layer of the :mod:`pds4indextools.scraper` package. It
turns a label file on disk into a parsed tree and a pre-order stream of
leaf elements paired with their canonical XPaths, enforcing the parse-time
rules of spec section 9.1 (R-PARSE-001, R-PARSE-002) and section 10.2
(R-XP-013). It performs no value normalization, nil handling, or LID
validation; those live in the sibling ``_value``, ``_nil``, and ``_lid``
modules.
"""

from collections.abc import Iterator
from pathlib import Path

from lxml import etree

from pds4indextools.errors import ParseError
from pds4indextools.xpath_norm import canonicalize_xpath

__all__ = [
    'iter_leaves',
    'parse_label',
    'reject_bom',
    'require_default_namespace',
]

# The three bytes an encoder emits for a UTF-8 byte-order mark (R-PARSE-001).
_UTF8_BOM = b'\xef\xbb\xbf'


def reject_bom(label_path: Path) -> None:
    """Reject a label file that begins with a UTF-8 byte-order mark.

    Parameters:
        label_path: The label file :class:`~pathlib.Path` to inspect. Only the
            first three bytes are read.

    Raises:
        ParseError: If the file starts with the UTF-8 BOM bytes ``EF BB BF``
            (R-PARSE-001).

    Reads at most the first three bytes of the file; an empty or shorter file
    is accepted here and fails later at parse time if malformed.

    Implements R-PARSE-001.
    """
    with label_path.open('rb') as handle:
        prefix = handle.read(3)
    if prefix == _UTF8_BOM:
        raise ParseError('UTF-8 BOM not permitted', file_path=label_path)


def parse_label(label_path: Path) -> etree._ElementTree:
    """Parse a label file into an lxml element tree.

    Parameters:
        label_path: The label file :class:`~pathlib.Path` to parse. Passed to
            :func:`lxml.etree.parse` as a string with no resolver overrides and
            no DTD loading.

    Returns:
        The parsed :class:`lxml.etree._ElementTree`.

    Raises:
        ParseError: If the file is not well-formed XML; the original
            :class:`lxml.etree.XMLSyntaxError` is chained via ``from`` and the
            label path is attached for diagnostics (R-PARSE-002).

    Implements R-PARSE-002.
    """
    try:
        return etree.parse(str(label_path))
    except etree.XMLSyntaxError as exc:
        raise ParseError(f'failed to parse label XML: {exc}', file_path=label_path) from exc


def require_default_namespace(root: etree._Element, label_path: Path) -> None:
    """Require the label root to declare an XML default namespace.

    Parameters:
        root: The parsed label root :class:`lxml.etree._Element`.
        label_path: The label file :class:`~pathlib.Path`, attached to any
            raised error for diagnostics.

    Raises:
        ParseError: If ``root.nsmap.get(None) is None``, i.e. the root declares
            no default namespace (R-XP-013).

    Implements R-XP-013.
    """
    if root.nsmap.get(None) is None:
        raise ParseError('label root element declares no default namespace', file_path=label_path)


def _is_leaf(element: etree._Element) -> bool:
    """Return ``True`` when ``element`` has no child elements.

    Parameters:
        element: The element to test.

    Returns:
        ``True`` if the element has no sub-elements (comments and processing
        instructions are ignored), so its text is a leaf value (R-SCRAPE-030).
    """
    return all(not isinstance(child.tag, str) for child in element)


def iter_leaves(tree: etree._ElementTree) -> Iterator[tuple[etree._Element, str]]:
    """Yield every leaf element with its canonical XPath in pre-order.

    Parameters:
        tree: The parsed label :class:`lxml.etree._ElementTree`. Its root's
            ``nsmap`` supplies the namespace context for canonicalization.

    Yields:
        ``(element, canonical_xpath)`` pairs for each leaf element (an element
        with no child elements) in document pre-order (R-SCRAPE-010). Comments
        and processing instructions are skipped. Parent elements are never
        yielded (R-SCRAPE-030).

    Raises:
        ParseError: If a segment cannot be canonicalized, e.g. a namespace URI
            used by an element is not declared on the root (R-XP-013).

    The canonical XPath is built from the element's qualified path relative to
    the root, prefixed with the root's own tag, so the first segment is always
    the root element (spec section 10.1).

    Implements R-SCRAPE-010, R-SCRAPE-030.
    """
    root = tree.getroot()
    root_tag = root.tag
    nsmap = root.nsmap
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if not _is_leaf(element):
            continue
        relative = tree.getelementpath(element)
        native = root_tag if relative == '.' else f'{root_tag}/{relative}'
        yield element, canonicalize_xpath(native, nsmap)
