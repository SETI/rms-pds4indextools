"""LID / version_id validation, auto-column derivation, and LID dedup.

This module implements the identifier and auto-column rules of spec section 8:
R-LID-001 (the ``logical_identifier`` regex and cardinality), R-LID-010
(``version_id`` cardinality), R-LID-020 (cross-label LID uniqueness), the
section 8.2 auto-column derivations, and R-FS-010 (the 255-byte ``filespec``
limit). It is independent of the parsing, value, and nil modules.
"""

import re
from pathlib import Path

from lxml import etree

from pds4indextools.errors import LabelError, LidError

__all__ = [
    'check_cross_label_lid',
    'compute_auto_columns',
    'extract_lid',
    'extract_version_id',
]

# The PDS4 ``urn_pds`` LID pattern (R-LID-001, PDS4 Standards Reference
# section 6D.1): a lowercase ``urn:NID:NSS`` head followed by 1-4 trailing
# tokens that may mix case, so the full LID has 4-7 colon-separated tokens.
_LID_REGEX = re.compile(r'^urn:[a-z0-9-]+:[a-z0-9-]+(?::[a-zA-Z0-9_.-]+){1,4}$')

# The maximum permitted UTF-8 byte length of a filespec (R-FS-010).
_MAX_FILESPEC_BYTES = 255

# The zero-based colon-token index of the bundle name inside a LID (section
# 8.2): ``urn:nasa:pds:bundle_x:...`` -> token 3 is ``bundle_x``.
_BUNDLE_NAME_TOKEN_INDEX = 3


def _find_unique(
    root: etree._Element,
    default_uri: str,
    local_name: str,
    label_path: Path,
) -> str:
    """Return the stripped text of the unique Identification_Area child.

    Parameters:
        root: The parsed label root :class:`lxml.etree._Element`.
        default_uri: The label's XML default-namespace URI.
        local_name: The child local name to locate (``logical_identifier`` or
            ``version_id``).
        label_path: The label file :class:`~pathlib.Path`, attached to any
            raised error for diagnostics.

    Returns:
        The stripped text of the single matching element.

    Raises:
        LidError: If the label has zero or more than one matching element
            (R-LID-001, R-LID-010).
    """
    query = f'.//{{{default_uri}}}Identification_Area/{{{default_uri}}}{local_name}'
    matches = root.findall(query)
    if len(matches) != 1:
        raise LidError(
            f'label must contain exactly one <{local_name}>; found {len(matches)}',
            file_path=label_path,
        )
    return (matches[0].text or '').strip()


def extract_lid(root: etree._Element, default_uri: str, label_path: Path) -> str:
    """Extract and validate the label's logical identifier.

    Parameters:
        root: The parsed label root :class:`lxml.etree._Element`.
        default_uri: The label's XML default-namespace URI.
        label_path: The label file :class:`~pathlib.Path`, attached to any
            raised error for diagnostics.

    Returns:
        The single ``logical_identifier`` text after ``.strip()``, guaranteed
        to match the LID regex (R-LID-001).

    Raises:
        LidError: If the label has zero or more than one ``logical_identifier``
            (R-LID-001), or the value fails the ``urn_pds`` regex; the failing
            value is cited in the message.

    Implements R-LID-001.
    """
    lid = _find_unique(root, default_uri, 'logical_identifier', label_path)
    if _LID_REGEX.match(lid) is None:
        raise LidError(
            f'logical_identifier {lid!r} does not match the LID pattern', file_path=label_path
        )
    return lid


def extract_version_id(root: etree._Element, default_uri: str, label_path: Path) -> str:
    """Extract and validate the label's version identifier.

    Parameters:
        root: The parsed label root :class:`lxml.etree._Element`.
        default_uri: The label's XML default-namespace URI.
        label_path: The label file :class:`~pathlib.Path`, attached to any
            raised error for diagnostics.

    Returns:
        The single ``version_id`` text after ``.strip()`` (R-LID-010).

    Raises:
        LidError: If the label has zero or more than one ``version_id``
            (R-LID-010).

    Implements R-LID-010.
    """
    return _find_unique(root, default_uri, 'version_id', label_path)


def compute_auto_columns(
    lid: str,
    version_id: str,
    label_path: Path,
    bundle_root: Path,
) -> dict[str, str]:
    """Derive the five auto-column values for one label.

    Parameters:
        lid: The validated logical identifier (from :func:`extract_lid`).
        version_id: The validated version identifier (from
            :func:`extract_version_id`).
        label_path: The absolute label file :class:`~pathlib.Path`.
        bundle_root: The bundle root :class:`~pathlib.Path` the ``filespec`` is
            made relative to.

    Returns:
        A dict mapping each auto-column token to its value, inserted in the
        fixed order ``lid``, ``lidvid``, ``filespec``, ``filename``,
        ``bundle_name`` (section 7.1 insertion-order contract). ``filespec``
        always uses forward slashes via :meth:`~pathlib.PurePath.as_posix`.

    Raises:
        LabelError: If the derived ``filespec`` exceeds 255 UTF-8 bytes
            (R-FS-010); the message cites both ``filespec`` and ``255``.

    Implements section 8.2 (R-AUTO-001) and R-FS-010.
    """
    auto: dict[str, str] = {}
    auto['lid'] = lid
    auto['lidvid'] = f'{lid}::{version_id}'
    filespec = label_path.relative_to(bundle_root).as_posix()
    if len(filespec.encode('utf-8')) > _MAX_FILESPEC_BYTES:
        raise LabelError(f'filespec exceeds 255 bytes: {filespec}', file_path=label_path)
    auto['filespec'] = filespec
    auto['filename'] = label_path.name
    auto['bundle_name'] = lid.split(':')[_BUNDLE_NAME_TOKEN_INDEX]
    return auto


def check_cross_label_lid(
    lid: str,
    label_path: Path,
    seen_lids: dict[str, Path] | None,
) -> None:
    """Enforce cross-label LID uniqueness, mutating the shared registry.

    Parameters:
        lid: The validated logical identifier for the current label.
        label_path: The current label's :class:`~pathlib.Path`.
        seen_lids: A shared mutable dict mapping each already-seen LID to the
            path that declared it, or ``None`` to skip the check entirely. When
            not ``None``, the current ``lid`` is inserted by side effect on a
            first sighting; the mapping is NOT thread-safe and the library is
            documented as single-threaded (section 7.1).

    Raises:
        LidError: If ``lid`` is already present in ``seen_lids`` (R-LID-020);
            the message cites both the current path and the prior path.

    Implements R-LID-020.
    """
    if seen_lids is None:
        return
    existing = seen_lids.get(lid)
    if existing is not None:
        raise LidError(
            f'duplicate LID {lid!r} in {label_path} and {existing}',
            file_path=label_path,
        )
    seen_lids[lid] = label_path
