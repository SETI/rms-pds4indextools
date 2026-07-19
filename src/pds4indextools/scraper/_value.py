"""Scraped-value normalization and content validation.

This module implements the whitespace and value rules of spec section 9.3.
:func:`normalize_value` performs the R-VAL-010 whitespace collapse and
:func:`checked_value` applies the R-VAL-020 (control character), R-VAL-030
(non-ASCII), and R-VAL-040 (embedded double quote, mode-dependent) checks
against an already-normalized value. All three content checks run after
normalization, so a tab or newline is collapsed before it can trip the
control-character rule.
"""

import re
from pathlib import Path

from pds4indextools.errors import ScrapedValueError

__all__ = [
    'checked_value',
    'normalize_value',
]

# ASCII control characters forbidden in a normalized value (R-VAL-020): the
# C0 range 0x00-0x1F plus DEL 0x7F. The single ASCII space (0x20) that
# R-VAL-010 emits is deliberately outside this class.
_CONTROL_CHARS = re.compile(r'[\x00-\x1f\x7f]')


def normalize_value(text: str) -> str:
    """Collapse whitespace in a scraped text value.

    Parameters:
        text: The raw element text to normalize.

    Returns:
        The value with leading and trailing whitespace stripped and every
        internal run of whitespace (including tabs and newlines) collapsed to a
        single ASCII space, i.e. ``' '.join(text.split())`` (R-VAL-010).

    Implements R-VAL-010.
    """
    return ' '.join(text.split())


def checked_value(
    value: str,
    canonical_xpath: str,
    *,
    fixed_width_mode: bool,
    label_path: Path,
) -> str:
    """Validate an already-normalized value and return it unchanged.

    Parameters:
        value: The normalized value to validate (output of
            :func:`normalize_value`).
        canonical_xpath: The canonical XPath of the element the value came
            from, cited in any raised error.
        fixed_width_mode: ``True`` selects fixed-width output, where an embedded
            double quote is passed through; ``False`` selects variable-width
            output, where an embedded double quote is a hard error (R-VAL-040).
        label_path: The label file :class:`~pathlib.Path`, attached to any
            raised error for diagnostics.

    Returns:
        The ``value`` unchanged when every content check passes.

    Raises:
        ScrapedValueError: If the value contains an ASCII control character
            (R-VAL-020), any non-ASCII character (R-VAL-030), or, in
            variable-width mode only, a literal double quote (R-VAL-040).

    Implements R-VAL-020, R-VAL-030, and R-VAL-040.
    """
    if _CONTROL_CHARS.search(value) is not None:
        raise ScrapedValueError(
            f'value at {canonical_xpath} contains an ASCII control character',
            file_path=label_path,
        )
    if not value.isascii():
        raise ScrapedValueError(
            f'value at {canonical_xpath} contains a non-ASCII character',
            file_path=label_path,
        )
    if not fixed_width_mode and '"' in value:
        raise ScrapedValueError(
            f'value at {canonical_xpath} contains a double quote in variable-width mode',
            file_path=label_path,
        )
    return value
