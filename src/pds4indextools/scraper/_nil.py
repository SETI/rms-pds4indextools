"""Nil-element detection and config-driven value substitution.

This module implements the nilled-element half of spec section 12.1
(R-NIL-001, R-NIL-010, R-NIL-020, R-NIL-030). :func:`is_nil` detects a
nilled element by the presence of ``xsi:nil="true"``, and
:func:`resolve_nil_value` validates the ``nilReason`` attribute, resolves the
element's PDS4 data type through the supplied resolver, and returns the
config-supplied substitution value keyed on ``(data_type, nilReason)``.
"""

from collections.abc import Mapping
from pathlib import Path

from lxml import etree

from pds4indextools.config import NillableEntry
from pds4indextools.errors import NilError
from pds4indextools.schema_types import SchemaTypeResolver

__all__ = [
    'is_nil',
    'resolve_nil_value',
]

# The XML Schema instance namespace carrying the ``nil`` attribute.
_XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'
_XSI_NIL_ATTR = f'{{{_XSI_NAMESPACE}}}nil'

# The four nilReason values a nilled element may declare (R-NIL-010); each is
# also the attribute name read off the matching
# :class:`~pds4indextools.config.NillableEntry`.
_VALID_NIL_REASONS: tuple[str, ...] = ('inapplicable', 'missing', 'unknown', 'anticipated')


def is_nil(element: etree._Element) -> bool:
    """Return ``True`` when ``element`` carries ``xsi:nil="true"``.

    Parameters:
        element: The leaf element to test.

    Returns:
        ``True`` only when the element has an ``xsi:nil`` attribute equal to
        the literal string ``"true"``; empty text without the attribute is not
        nil (R-NIL-001).

    Implements R-NIL-001.
    """
    return element.get(_XSI_NIL_ATTR) == 'true'


def resolve_nil_value(
    element: etree._Element,
    canonical_xpath: str,
    *,
    resolver: SchemaTypeResolver,
    nillable_config: Mapping[str, NillableEntry],
    label_path: Path,
) -> str:
    """Return the config substitution value for a nilled element.

    Parameters:
        element: The nilled leaf element (already known to carry
            ``xsi:nil="true"``).
        canonical_xpath: The canonical XPath of the element, cited in any
            raised error.
        resolver: The :class:`~pds4indextools.schema_types.SchemaTypeResolver`
            that maps the element's local tag to its PDS4 base type (R-NIL-020).
        nillable_config: The per-data-type nilReason replacement mapping (the
            merged config ``nillable`` section).
        label_path: The label file :class:`~pathlib.Path`, attached to any
            raised error for diagnostics.

    Returns:
        The substitution string ``nillable_config[data_type][nilReason]``,
        coerced to :class:`str` (R-NIL-020).

    Raises:
        NilError: If the element has no ``nilReason`` or an unrecognized one
            (R-NIL-010), or if the resolved data type is absent from
            ``nillable_config`` (R-NIL-030).
        SchemaResolutionError: If the resolver cannot resolve the element's
            data type (R-SCH-050).

    The ``nilReason`` attribute is validated before the data type is resolved,
    so a bad reason is reported without consulting the schema.

    Implements R-NIL-010, R-NIL-020, and R-NIL-030.
    """
    nil_reason = element.get('nilReason')
    if nil_reason is None:
        raise NilError(
            f'nilled element at {canonical_xpath} has no nilReason attribute',
            file_path=label_path,
        )
    if nil_reason not in _VALID_NIL_REASONS:
        raise NilError(
            f'nilled element at {canonical_xpath} has unrecognized nilReason {nil_reason!r}',
            file_path=label_path,
        )

    local_tag = etree.QName(element).localname
    data_type = resolver.resolve(local_tag)
    entry = nillable_config.get(data_type)
    if entry is None:
        raise NilError(
            f'data type {data_type} for {canonical_xpath} is absent from the nillable config',
            file_path=label_path,
        )
    return str(getattr(entry, nil_reason))
