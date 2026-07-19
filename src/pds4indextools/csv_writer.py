"""Deterministic CSV writing, per-column quoting, and row sorting.

This module implements spec section 13 (R-CSV-001..R-CSV-080) and the sort
contract (R-SORT-010..R-SORT-030). It turns the in-memory row list produced
by scraping into a byte-exact index CSV and reports the byte lengths the
generated label needs.

The public API is three functions plus two frozen dataclasses.
:func:`~pds4indextools.csv_writer.build_plan` sorts the rows, analyzes
per-column quoting and byte lengths, and returns an immutable
:class:`~pds4indextools.csv_writer.CsvWritePlan` describing exactly what will
be written. :func:`~pds4indextools.csv_writer.write_csv` renders that plan to
disk atomically. :func:`~pds4indextools.csv_writer.sort_rows` applies the
``output.sort_by`` ordering.

Quoting is decided per COLUMN, not per cell (R-CSV-040): a column is quoted
iff any data value in it contains a comma, and then every data cell in that
column is wrapped in double quotes while the header stays unquoted
(R-CSV-050..R-CSV-052). Because scraped values are ASCII (R-VAL-030), a
value's byte length equals its character length (R-CSV-080). The line
terminator (``b'\\n'`` or ``b'\\r\\n'``) comes from the config (R-CSV-003),
no trailing comma is ever written (R-CSV-005), and identical inputs always
produce byte-identical output (R-IDX-001).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pds4indextools._io import _atomic_writes
from pds4indextools.config import OutputSection, parse_sort_key
from pds4indextools.errors import ConfigError

__all__ = [
    'ColumnStat',
    'CsvWritePlan',
    'build_plan',
    'sort_rows',
    'write_csv',
]

# CSV structural bytes (R-CSV-004, R-CSV-050). The field delimiter is always a
# comma and the only quote character is the double quote; neither is
# configurable.
_FIELD_DELIMITER = ','
_QUOTE_CHARACTER = '"'

# Output text is ASCII by the R-VAL-030 guarantee, so byte length equals
# character length (R-CSV-080). Encoding as UTF-8 yields those same bytes with
# no BOM (R-CSV-002).
_TEXT_ENCODING = 'utf-8'

# Line terminators selected by ``output.line_ending`` (R-CSV-003).
_LINE_TERMINATORS: dict[str, bytes] = {'LF': b'\n', 'CRLF': b'\r\n'}


@dataclass(frozen=True, slots=True, kw_only=True)
class ColumnStat:
    """Per-column quoting and byte-length statistics for one output column.

    Parameters:
        name: The emitted column header.
        must_quote: ``True`` iff any data value in the column contains a
            comma, in which case every data cell in the column is quoted
            (R-CSV-040, R-CSV-050).
        max_byte_length: The maximum written byte length of any data cell in
            the column, including the two surrounding quote bytes when
            ``must_quote`` is ``True`` (R-CSV-070, R-CSV-080). Zero when the
            column has no data or every value is empty (R-CSV-073).
        is_auto_column: ``True`` iff this column was selected by an
            auto-column token rather than an XPath (R-AUTO-001); carried
            through for the label writer.
        auto_column_token: The auto-column token (e.g. ``'lid'``) when
            ``is_auto_column`` is ``True``, else ``None``.

    Implements R-CSV-040, R-CSV-050, R-CSV-070, and R-CSV-080.
    """

    name: str
    must_quote: bool
    max_byte_length: int
    is_auto_column: bool
    auto_column_token: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CsvWritePlan:
    """An immutable description of the exact bytes the index CSV will contain.

    The plan holds the sorted rows, the parallel column headers and
    statistics, and the byte lengths the generated label needs. Building a
    plan performs no I/O; :func:`write_csv` renders it deterministically so
    that the same plan always yields the same file (R-IDX-001).

    Parameters:
        rows: The sorted data rows, each keyed by emitted column header.
        columns: The emitted column headers in mapping order.
        stats: The per-column statistics, parallel to ``columns``.
        line_terminator: The record terminator bytes, ``b'\\n'`` or
            ``b'\\r\\n'`` (R-CSV-003).
        fixed_width: ``True`` selects the fixed-width layout (R-CSV-070);
            ``False`` the variable-width layout (R-CSV-060).
        header_row_length: The header row's byte length including the line
            terminator (R-CSV-071).
        max_record_length: The largest data-row byte length including the
            line terminator, or ``0`` when there are no rows.
        total_byte_length: The full file size in bytes once written.

    Implements R-CSV-003, R-CSV-060, R-CSV-070, and R-CSV-080.
    """

    rows: tuple[dict[str, str], ...]
    columns: tuple[str, ...]
    stats: tuple[ColumnStat, ...]
    line_terminator: bytes
    fixed_width: bool
    header_row_length: int
    max_record_length: int
    total_byte_length: int


def sort_rows(
    rows: Sequence[dict[str, str]],
    output_section: OutputSection,
) -> list[dict[str, str]]:
    """Order the rows per ``output.sort_by`` (R-SORT-010..R-SORT-030).

    An empty ``sort_by`` performs NO re-sort: the rows are returned in their
    incoming discovery order, which is already ``filespec``-sorted
    (R-SORT-010, R-DISC-020). A non-empty ``sort_by`` sorts the rows with a
    stable multi-key sort, applying each key in listed order; a leading ``-``
    on a key sorts that column descending (R-SORT-020). Comparisons are plain
    string comparisons on the cell value as written to the CSV (R-SORT-030).

    Every listed column MUST appear in the emitted column set, i.e. among the
    row dictionaries' keys; an unknown column is a configuration error, not a
    fail-slow-eligible label error (R-SORT-020).

    Parameters:
        rows: The data rows to order, each keyed by emitted column header.
        output_section: The output configuration supplying ``sort_by``.

    Returns:
        A new list of the rows in the chosen order; the input is not mutated.

    Raises:
        ConfigError: If a ``sort_by`` key names a column not present in the
            emitted column set (R-SORT-020).
    """
    if len(output_section.sort_by) == 0:
        return list(rows)
    specs = [parse_sort_key(spec) for spec in output_section.sort_by]
    known_columns = set(rows[0].keys()) if len(rows) > 0 else set()
    for column, _descending in specs:
        if column not in known_columns:
            raise ConfigError(f'sort_by references unknown column {column!r}') from None
    result = list(rows)
    for column, descending in reversed(specs):
        result = sorted(result, key=_column_key(column), reverse=descending)
    return result


def _column_key(name: str) -> Callable[[dict[str, str]], str]:
    """Return a ``sorted`` key function reading one column's value.

    Parameters:
        name: The emitted column header to read from each row.

    Returns:
        A callable mapping a row to its ``name`` cell value, for use as the
        ``key`` argument to :func:`sorted` (R-SORT-030).
    """

    def key(row: dict[str, str]) -> str:
        return row[name]

    return key


def _render_header(columns: Sequence[str], line_terminator: bytes) -> bytes:
    """Render the unquoted header row as bytes (R-CSV-010..R-CSV-012).

    Parameters:
        columns: The emitted column headers in order.
        line_terminator: The record terminator bytes.

    Returns:
        The header line, comma-joined, unquoted, unpadded, and terminated
        (R-CSV-012, R-CSV-071).
    """
    line = _FIELD_DELIMITER.join(columns)
    return line.encode(_TEXT_ENCODING) + line_terminator


def _render_cell(value: str, stat: ColumnStat, fixed_width: bool) -> str:
    """Render one data cell with quoting and optional fixed-width padding.

    Parameters:
        value: The raw cell value as written to the CSV.
        stat: The owning column's statistics.
        fixed_width: Whether the fixed-width layout is selected.

    Returns:
        The cell text, wrapped in double quotes when the column
        ``must_quote`` (R-CSV-050), and right-padded with ASCII spaces to the
        column's ``max_byte_length`` when ``fixed_width`` is ``True``
        (R-CSV-070). An all-empty fixed-width column pads to zero and yields
        an empty string (R-CSV-073).
    """
    cell = f'{_QUOTE_CHARACTER}{value}{_QUOTE_CHARACTER}' if stat.must_quote else value
    if fixed_width:
        cell = cell.ljust(stat.max_byte_length)
    return cell


def _render_record(
    row: Mapping[str, str],
    stats: Sequence[ColumnStat],
    *,
    fixed_width: bool,
    line_terminator: bytes,
) -> bytes:
    """Render one data row as bytes with no trailing comma (R-CSV-005).

    Parameters:
        row: The data row keyed by emitted column header.
        stats: The per-column statistics in emitted order.
        fixed_width: Whether the fixed-width layout is selected.
        line_terminator: The record terminator bytes.

    Returns:
        The comma-joined, terminated record; each cell quoted and/or padded
        per :func:`_render_cell` (R-CSV-050, R-CSV-060, R-CSV-070).
    """
    cells = [_render_cell(row[stat.name], stat, fixed_width) for stat in stats]
    line = _FIELD_DELIMITER.join(cells)
    return line.encode(_TEXT_ENCODING) + line_terminator


def _column_stat(
    name: str,
    rows: Sequence[dict[str, str]],
    *,
    is_auto_column: bool,
    auto_column_token: str | None,
) -> ColumnStat:
    """Compute the quoting and byte-length statistics for one column.

    Parameters:
        name: The emitted column header.
        rows: The sorted data rows.
        is_auto_column: Whether this column was selected by an auto token.
        auto_column_token: The auto token, or ``None`` for an XPath column.

    Returns:
        The column's :class:`ColumnStat`. ``must_quote`` is ``True`` iff any
        value contains a comma (R-CSV-040); ``max_byte_length`` is the widest
        written cell, counting quote bytes when quoted (R-CSV-070, R-CSV-080).
    """
    must_quote = any(_FIELD_DELIMITER in row[name] for row in rows)
    quote_bytes = 2 if must_quote else 0
    max_byte_length = 0
    for row in rows:
        cell_length = len(row[name]) + quote_bytes
        if cell_length > max_byte_length:
            max_byte_length = cell_length
    return ColumnStat(
        name=name,
        must_quote=must_quote,
        max_byte_length=max_byte_length,
        is_auto_column=is_auto_column,
        auto_column_token=auto_column_token,
    )


def build_plan(
    *,
    rows: Sequence[dict[str, str]],
    columns: Sequence[str],
    column_is_auto: Mapping[str, bool],
    auto_tokens: Mapping[str, str],
    output_section: OutputSection,
) -> CsvWritePlan:
    """Sort, analyze, and measure the rows into a :class:`CsvWritePlan`.

    The rows are first ordered by :func:`sort_rows` (R-SORT-010..R-SORT-030).
    Each column then gets a :class:`ColumnStat` recording per-column quoting
    (R-CSV-040) and byte lengths (R-CSV-070, R-CSV-080). Finally the header,
    per-record, and total byte lengths are computed by rendering exactly the
    bytes :func:`write_csv` will emit, so the plan's lengths always match the
    written file.

    Parameters:
        rows: The in-memory data rows, each keyed by emitted column header.
        columns: The emitted column headers in mapping order.
        column_is_auto: Maps each header to whether it is an auto column.
        auto_tokens: Maps each auto-column header to its token; XPath columns
            are absent from this mapping.
        output_section: The output configuration (fixed width, sort keys,
            line ending).

    Returns:
        The assembled plan describing the exact file to be written.

    Raises:
        ConfigError: If ``output.sort_by`` references an unknown column
            (propagated from :func:`sort_rows`, R-SORT-020).

    Implements R-CSV-003, R-CSV-040, R-CSV-060, R-CSV-070, and R-CSV-080.
    """
    sorted_rows = sort_rows(rows, output_section)
    columns_tuple = tuple(columns)
    stats = tuple(
        _column_stat(
            name,
            sorted_rows,
            is_auto_column=column_is_auto[name],
            auto_column_token=auto_tokens.get(name),
        )
        for name in columns_tuple
    )
    line_terminator = _LINE_TERMINATORS[output_section.line_ending]
    fixed_width = output_section.fixed_width

    header_row_length = len(_render_header(columns_tuple, line_terminator))
    max_record_length = 0
    total_byte_length = header_row_length
    rows_tuple = tuple(sorted_rows)
    for row in rows_tuple:
        record_length = len(
            _render_record(
                row,
                stats,
                fixed_width=fixed_width,
                line_terminator=line_terminator,
            )
        )
        if record_length > max_record_length:
            max_record_length = record_length
        total_byte_length += record_length

    return CsvWritePlan(
        rows=rows_tuple,
        columns=columns_tuple,
        stats=stats,
        line_terminator=line_terminator,
        fixed_width=fixed_width,
        header_row_length=header_row_length,
        max_record_length=max_record_length,
        total_byte_length=total_byte_length,
    )


def write_csv(plan: CsvWritePlan, csv_path: Path) -> None:
    """Write ``plan`` to ``csv_path`` as byte-exact CSV, atomically.

    The bytes are written to a sibling temporary file and atomically renamed
    into place so an interrupted run never leaves a partial index at the
    final path (R-ERR-002). The header row is written first, unquoted
    (R-CSV-012), followed by one record per row in ``plan.rows`` order. Each
    data cell is quoted when its column ``must_quote`` (R-CSV-050) and, in
    fixed-width mode, right-padded to the column width (R-CSV-070); no row
    carries a trailing comma (R-CSV-005). The plan's ``line_terminator`` ends
    every row (R-CSV-003).

    Parameters:
        plan: The write plan produced by :func:`build_plan`.
        csv_path: The destination path for the index CSV.

    Raises:
        OutputError: If the atomic rename into ``csv_path`` fails (R-ERR-002).

    Implements R-CSV-001..R-CSV-005, R-CSV-010..R-CSV-012, R-CSV-050,
    R-CSV-060, R-CSV-070, and R-IDX-001.
    """
    temp_path = csv_path.parent / f'{csv_path.name}.tmp'
    with _atomic_writes((temp_path, csv_path)), open(temp_path, 'wb') as handle:
        handle.write(_render_header(plan.columns, plan.line_terminator))
        for row in plan.rows:
            handle.write(
                _render_record(
                    row,
                    plan.stats,
                    fixed_width=plan.fixed_width,
                    line_terminator=plan.line_terminator,
                )
            )
