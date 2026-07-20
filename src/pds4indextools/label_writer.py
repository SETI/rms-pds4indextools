"""Substitution-dict assembly and PdsTemplate label rendering.

This module implements spec section 14 (R-LBL-001..R-LBL-091): it builds the
PdsTemplate substitution dictionary from a validated
:class:`~pds4indextools.config.LabelContents` and the
:class:`~pds4indextools.csv_writer.CsvWritePlan` produced by CSV writing, then
renders the generated ``.lblx`` label through
`rms-pdstemplate <https://rms-pdstemplate.readthedocs.io/>`_ (version 2.4.x).

The public API is four symbols.
:func:`build_substitution_dict` assembles the full substitution mapping,
including the eleven reserved BASE variables (R-LBL-012), the per-column
``Field_Content`` list (R-LBL-020), and the ``RECORD_DELIMITER`` name that
keeps the emitted ``<record_delimiter>`` consistent with the CSV terminator
(R-LBL-060). :func:`normalize_modification_detail` turns the optional
modification history into the list PdsTemplate iterates, generating a default
single entry when the user supplied none (R-LBL-090/091).
:func:`write_label` invokes PdsTemplate with the correct line-ending mode and
wraps any rendering failure as :exc:`~pds4indextools.errors.OutputError`
(R-LBL-040). :func:`load_packaged_template` yields the packaged default
template path (R-LBL-001).

The default PdsTemplate logger prints to stdout when it has no handlers, which
would violate the library/CLI output boundary; this module routes PdsTemplate
logging into the ``pds4indextools.pdstemplate`` logger tree once at import.
"""

import datetime
import importlib.resources
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pdstemplate import PdsTemplate, TemplateError, set_logger

from pds4indextools._logging import module_logger
from pds4indextools.config import ColumnSpec, LabelContents, ModificationDetail
from pds4indextools.csv_writer import CsvWritePlan
from pds4indextools.errors import OutputError, Pds4IndexError

__all__ = [
    'build_substitution_dict',
    'load_packaged_template',
    'normalize_modification_detail',
    'write_label',
]

# Route PdsTemplate's own logging into our namespaced tree once at import. Its
# default PdsLogger has no handlers and therefore PRINTS to stdout; leaving it
# unrouted would break the library/CLI output boundary and any capsys-based
# CLI test (R-LBL-040, codebase-analysis section 2).
set_logger(module_logger('pdstemplate'))

# The default single modification-history description generated when the user
# supplies no ``Modification_Detail`` (owner decision #3, R-LBL-090/091).
_DEFAULT_MODIFICATION_DESCRIPTION = 'Initial version.'
_DEFAULT_MODIFICATION_VERSION_ID = '1.0'

# The <record_delimiter> element text keyed by the CSV line terminator, so the
# emitted label always matches the actual CSV terminator (R-LBL-060, R-CSV-003).
_RECORD_DELIMITER_NAMES: dict[bytes, str] = {
    b'\n': 'Line-Feed',
    b'\r\n': 'Carriage-Return Line-Feed',
}

# Exceptions PdsTemplate 2.4.0 may raise from construction or ``write`` with
# ``raise_exceptions=True``: its own ``TemplateError`` plus the evaluation
# errors a failed ``$...$`` expression can surface. Bugs outside this set must
# stay uncaught so they reach the exit-code-3 handler (R-LBL-040).
_PDSTEMPLATE_RAISES: tuple[type[BaseException], ...] = (
    TemplateError,
    KeyError,
    NameError,
    ValueError,
    TypeError,
    SyntaxError,
)


def _strip_namespace_prefix(data_type: str) -> str:
    """Return a PDS4 data-type name without its namespace prefix.

    Parameters:
        data_type: The resolved data-type name, possibly prefixed (for
            example ``pds:ASCII_LID``).

    Returns:
        The text after the final ``:``; an unprefixed name is returned
        unchanged (spec section 11.3).
    """
    return data_type.rpartition(':')[2]


def _build_field_content(
    *,
    column_specs: Sequence[ColumnSpec],
    plan: CsvWritePlan,
    column_types: Mapping[str, str],
    column_xpaths: Mapping[str, str],
) -> list[dict[str, object]]:
    """Build the ``Field_Content`` list, one seven-key dict per output column.

    Parameters:
        column_specs: The per-column selectors, parallel to ``plan.columns``
            and ``plan.stats`` in config-declared order.
        plan: The CSV write plan supplying per-column byte widths and the
            fixed-width flag.
        column_types: Maps each emitted column header to its resolved PDS4
            data type (possibly namespace-prefixed).
        column_xpaths: Maps each emitted column header to its raw canonical
            XPath or its auto-column token.

    Returns:
        A list of dicts each carrying exactly the seven ``Field_Content`` keys
        of R-LBL-020. ``field_location`` is the 1-based byte offset in
        fixed-width mode (``1 + sum(widths[:index]) + index``, one comma byte
        between columns) or the 1-based column position when delimited.
    """
    widths = [stat.max_byte_length for stat in plan.stats]
    field_content: list[dict[str, object]] = []
    for index, spec in enumerate(column_specs):
        header = spec.header
        stat = plan.stats[index]
        if plan.fixed_width:
            field_location = 1 + sum(widths[:index]) + index
        else:
            field_location = index + 1
        field_content.append(
            {
                'name': header,
                'field_number': index + 1,
                'field_location': field_location,
                'data_type': _strip_namespace_prefix(column_types[header]),
                'field_length': stat.max_byte_length,
                'maximum_field_length': stat.max_byte_length,
                'xpath': column_xpaths[header],
            }
        )
    return field_content


def normalize_modification_detail(
    raw: ModificationDetail | list[ModificationDetail] | None,
    *,
    fallback_version_id: str | None = None,
) -> list[dict[str, object]]:
    """Normalize the modification history into the list PdsTemplate iterates.

    A single :class:`~pds4indextools.config.ModificationDetail` is wrapped into
    a one-element list; a list passes through in declared order; ``None``
    generates a default single entry dated with the current UTC date so the
    emitted ``<Modification_History>`` is always valid PDS4 (an empty history
    would not be). Each entry is rendered with ``model_dump`` so any
    user-supplied extra keys pass through (R-LBL-090).

    Parameters:
        raw: The modification history as a single entry, a list of entries, or
            ``None`` when the user configured none.
        fallback_version_id: The ``version_id`` for the generated default
            entry; ``None`` falls back to ``'1.0'``.

    Returns:
        The normalized list of modification-detail dicts. For ``raw is None``
        this is exactly one entry whose ``modification_date`` is the current
        UTC date (``YYYY-MM-DD``), ``version_id`` is ``fallback_version_id`` or
        ``'1.0'``, and ``description`` is ``'Initial version.'`` (owner
        decision #3, superseding the R-LBL-091 empty-list wording).

    Implements R-LBL-090 and R-LBL-091.
    """
    if raw is None:
        current_date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
        return [
            {
                'modification_date': current_date,
                'version_id': fallback_version_id or _DEFAULT_MODIFICATION_VERSION_ID,
                'description': _DEFAULT_MODIFICATION_DESCRIPTION,
            }
        ]
    if isinstance(raw, list):
        return [entry.model_dump() for entry in raw]
    return [raw.model_dump()]


def build_substitution_dict(
    *,
    label_contents: LabelContents,
    plan: CsvWritePlan,
    column_specs: Sequence[ColumnSpec],
    column_types: Mapping[str, str],
    column_xpaths: Mapping[str, str],
    csv_absolute_path: Path,
) -> dict[str, object]:
    """Assemble the full PdsTemplate substitution dictionary.

    The dict starts from ``label_contents.model_dump(by_alias=False)`` WITHOUT
    ``exclude_none``, so every optional declared field (``version_id``,
    ``title``, ``Citation_Information``, and the reference/source/file-area
    fields) is present with value ``None``; the packaged template tests these
    names with ``$IF(name)$`` and PdsTemplate treats an UNDEFINED name as a
    render error, whereas a defined ``None`` is falsy and renders nothing
    (R-LBL-001, R-LBL-040). ``Modification_Detail`` is replaced by
    :func:`normalize_modification_detail`, then the eleven reserved BASE
    variables of R-LBL-012 are overlaid, and finally the ``RECORD_DELIMITER``
    name is added from the plan terminator (R-LBL-060).

    Parameters:
        label_contents: The validated label substitution variables.
        plan: The CSV write plan supplying row/byte counts and per-column
            widths.
        column_specs: The per-column selectors, parallel to ``plan.columns``.
        column_types: Maps each emitted column header to its resolved PDS4
            data type.
        column_xpaths: Maps each emitted column header to its raw canonical
            XPath or auto-column token.
        csv_absolute_path: The absolute path of the just-written CSV, used for
            ``index_file_name`` and the template's ``$FILE_MD5``/``$FILE_ZULU``
            macros.

    Returns:
        The substitution mapping ready for :func:`write_label`.

    Raises:
        :exc:`~pds4indextools.errors.Pds4IndexError`: If a reserved BASE
            variable name is already present in ``label_contents`` after
            validation; this is an internal invariant that
            :func:`~pds4indextools.config.load_config` should already have
            rejected (R-LBL-012).

    Implements R-LBL-010, R-LBL-012, R-LBL-020, R-LBL-060, and R-LBL-090.
    """
    substitution: dict[str, object] = label_contents.model_dump(by_alias=False)
    substitution['Modification_Detail'] = normalize_modification_detail(
        label_contents.Modification_Detail,
        fallback_version_id=label_contents.version_id,
    )
    field_content = _build_field_content(
        column_specs=column_specs,
        plan=plan,
        column_types=column_types,
        column_xpaths=column_xpaths,
    )
    base_variables: dict[str, object] = {
        'index_file_name': str(csv_absolute_path),
        'Field_Content': field_content,
        'fields': len(field_content),
        'records': len(plan.rows),
        'Table_Character': plan.fixed_width,
        'Table_Delimited': not plan.fixed_width,
        'Product_Ancillary': label_contents.product_class == 'Product_Ancillary',
        'Product_Metadata_Supplemental': (
            label_contents.product_class == 'Product_Metadata_Supplemental'
        ),
        'object_length_h': plan.header_row_length,
        'object_length_t': plan.total_byte_length,
        'maximum_record_length': plan.max_record_length,
    }
    for key in base_variables:
        if key in substitution:
            raise Pds4IndexError(
                'internal invariant: reserved key collision; '
                'should have been rejected at config load'
            )
    substitution.update(base_variables)
    substitution['RECORD_DELIMITER'] = _RECORD_DELIMITER_NAMES[plan.line_terminator]
    return substitution


def write_label(
    template_path: Path,
    substitution_dict: Mapping[str, object],
    output_label_path: Path,
    *,
    line_ending: Literal['LF', 'CRLF'],
) -> None:
    """Render ``template_path`` to ``output_label_path`` through PdsTemplate.

    The template is constructed with ``crlf=(line_ending == 'CRLF')`` so the
    emitted label's line termination matches the CSV terminator, and
    ``write`` is called with ``raise_exceptions=True`` so a rendering error
    raises instead of embedding ``[[[...]]]`` error text into the label
    (R-LBL-040). The function performs no temporary-file rename; that is the
    CLI's responsibility (R-ERR-002).

    Parameters:
        template_path: The template file to render (packaged default or a
            user-supplied path).
        substitution_dict: The substitution mapping from
            :func:`build_substitution_dict`.
        output_label_path: The destination ``.lblx`` path (R-LBL-050).
        line_ending: The CSV record terminator selector, ``'LF'`` or
            ``'CRLF'`` (R-LBL-060).

    Raises:
        :exc:`~pds4indextools.errors.OutputError`: If PdsTemplate raises during
            construction or rendering, or if ``write`` reports a nonzero error
            count without raising. The original PdsTemplate exception is
            chained as the cause (R-LBL-040, spec section 17).

    Implements R-LBL-040, R-LBL-050, and R-LBL-060.
    """
    try:
        template = PdsTemplate(template_path, crlf=(line_ending == 'CRLF'))
        errors, _warnings = template.write(
            substitution_dict, output_label_path, raise_exceptions=True
        )
    except _PDSTEMPLATE_RAISES as exc:
        raise OutputError(
            f'PdsTemplate failed: {exc}',
            file_path=output_label_path,
        ) from exc
    if errors:
        raise OutputError(
            f'PdsTemplate reported {errors} error(s)',
            file_path=output_label_path,
        )


@contextmanager
def load_packaged_template() -> Iterator[Path]:
    """Yield the filesystem path of the packaged default label template.

    The template is the packaged
    ``pds4indextools/templates/index_label_template.xml`` resource, resolved
    through :mod:`importlib.resources` so it works whether the package is
    installed as a directory or a zip. Callers use it as
    ``with load_packaged_template() as template_path: ...``.

    Returns:
        A context manager yielding the :class:`~pathlib.Path` of the packaged
        template, valid for the duration of the ``with`` block (R-LBL-001).

    Implements R-LBL-001.
    """
    ref = importlib.resources.files('pds4indextools.templates') / 'index_label_template.xml'
    with importlib.resources.as_file(ref) as path:
        yield path
