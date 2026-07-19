"""Unit tests for :mod:`pds4indextools.csv_writer`.

These tests pin down the CSV output contract of spec section 13
(R-CSV-001..R-CSV-080) and the sort contract (R-SORT-010..R-SORT-030):
per-column quoting driven only by data (never headers), variable-width and
fixed-width layouts with no trailing comma, LF/CRLF terminators taken from
the config, byte-length accounting that feeds the generated label, and a
stable multi-key string sort that rejects unknown columns as a
:exc:`~pds4indextools.errors.ConfigError`.

Every test drives only the public functions ``build_plan``, ``write_csv``,
and ``sort_rows`` and the public ``ColumnStat`` / ``CsvWritePlan``
dataclasses; private helpers are exercised through them. Written files use
``tmp_path`` and are compared with ``read_bytes()`` so the assertions are on
exact on-disk bytes.
"""

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from pds4indextools.config import OutputSection
from pds4indextools.csv_writer import (
    ColumnStat,
    CsvWritePlan,
    build_plan,
    sort_rows,
    write_csv,
)
from pds4indextools.errors import ConfigError


def _make_plan(
    rows: Sequence[dict[str, str]],
    columns: Sequence[str],
    *,
    fixed_width: bool = False,
    line_ending: str = 'LF',
    sort_by: Sequence[str] | None = None,
    column_is_auto: Mapping[str, bool] | None = None,
    auto_tokens: Mapping[str, str] | None = None,
) -> CsvWritePlan:
    """Build a :class:`~pds4indextools.csv_writer.CsvWritePlan` for tests.

    Parameters:
        rows: The in-memory data rows, keyed by emitted column header.
        columns: The emitted column headers in mapping order.
        fixed_width: Whether the fixed-width layout is selected.
        line_ending: Either ``'LF'`` or ``'CRLF'``.
        sort_by: Optional sort-key list for the output section.
        column_is_auto: Optional per-column auto flag; defaults to all False.
        auto_tokens: Optional per-column auto-token map; defaults to empty.

    Returns:
        The assembled write plan.
    """
    output_section = OutputSection(
        fixed_width=fixed_width,
        line_ending=line_ending,  # type: ignore[arg-type]
        sort_by=list(sort_by) if sort_by is not None else [],
    )
    is_auto = column_is_auto if column_is_auto is not None else dict.fromkeys(columns, False)
    tokens = auto_tokens if auto_tokens is not None else {}
    return build_plan(
        rows=rows,
        columns=columns,
        column_is_auto=is_auto,
        auto_tokens=tokens,
        output_section=output_section,
    )


def _stat_for(plan: CsvWritePlan, name: str) -> ColumnStat:
    """Return the :class:`ColumnStat` in ``plan`` whose ``name`` matches.

    Parameters:
        plan: The write plan to search.
        name: The column header to look up.

    Returns:
        The matching column statistic.
    """
    for stat in plan.stats:
        if stat.name == name:
            return stat
    raise KeyError(name)


def _data_lines(data: bytes, terminator: bytes) -> list[bytes]:
    """Split ``data`` on ``terminator`` and drop the header and trailing empty.

    Parameters:
        data: The full file bytes.
        terminator: The line terminator that separates records.

    Returns:
        The data-row lines with the header row and final empty element removed.
    """
    parts = data.split(terminator)
    if len(parts) > 0 and parts[-1] == b'':
        parts = parts[:-1]
    return parts[1:]


def test_build_plan_quoting_column_with_comma_marks_must_quote_true() -> None:
    """A comma in any cell marks the column ``must_quote`` (T-CSV-001, R-CSV-040)."""
    plan = _make_plan([{'a': 'x,y'}, {'a': 'z'}], ['a'])
    assert _stat_for(plan, 'a').must_quote is True


def test_build_plan_quoting_column_without_comma_marks_must_quote_false() -> None:
    """A comma-free column is not marked ``must_quote`` (T-CSV-002, R-CSV-051)."""
    plan = _make_plan([{'a': 'x'}, {'a': 'z'}], ['a'])
    assert _stat_for(plan, 'a').must_quote is False


def test_build_plan_header_not_in_must_quote_calculation() -> None:
    """A comma in the HEADER never triggers quoting; only data does (R-CSV-052)."""
    # Hand ``build_plan`` a comma-containing header directly, bypassing config
    # validation, with comma-free data. The header's comma must not mark the
    # column ``must_quote``.
    plan = _make_plan(
        [{'a,b': 'plain'}, {'a,b': 'also-plain'}],
        ['a,b'],
        column_is_auto={'a,b': False},
        auto_tokens={},
    )
    assert _stat_for(plan, 'a,b').must_quote is False


def test_write_csv_variable_width_no_trailing_comma_per_row(tmp_path: Path) -> None:
    """No row ends with a comma in variable-width mode (T-CSV-010, R-CSV-005)."""
    plan = _make_plan([{'a': '1', 'b': '2'}, {'a': '3', 'b': '4'}], ['a', 'b'])
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    for line in out.read_bytes().split(b'\n'):
        if line != b'':
            assert line[-1:] != b','


def test_write_csv_header_unquoted_when_column_quoted(tmp_path: Path) -> None:
    """The header stays unquoted even when its column is quoted (T-CSV-003, R-CSV-012)."""
    plan = _make_plan([{'name': 'x,y'}], ['name'])
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    header_line = out.read_bytes().split(b'\n')[0]
    assert header_line == b'name'


def test_write_csv_data_cell_quoted_when_must_quote_true(tmp_path: Path) -> None:
    """Every data cell in a comma-bearing column is quoted (T-CSV-001, R-CSV-050)."""
    plan = _make_plan([{'a': 'x,y'}, {'a': 'z'}], ['a'])
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    lines = _data_lines(out.read_bytes(), b'\n')
    assert lines == [b'"x,y"', b'"z"']


def test_write_csv_data_cells_unquoted_when_must_quote_false(tmp_path: Path) -> None:
    """A comma-free column produces no quote bytes anywhere (T-CSV-002, R-CSV-051)."""
    plan = _make_plan([{'a': 'x', 'b': 'y'}, {'a': 'z', 'b': 'w'}], ['a', 'b'])
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    assert b'"' not in out.read_bytes()


def test_write_csv_fixed_width_pads_each_data_cell(tmp_path: Path) -> None:
    """Fixed-width cells are right-padded to the column width (T-CSV-020, R-CSV-070)."""
    plan = _make_plan(
        [{'a': 'x', 'b': 'yy'}, {'a': 'zzz', 'b': 'w'}],
        ['a', 'b'],
        fixed_width=True,
    )
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    lines = _data_lines(out.read_bytes(), b'\n')
    # Neither fixed-width row ends with a trailing comma after the last column
    # (R-CSV-072).
    assert lines == [b'x  ,yy', b'zzz,w ']


def test_write_csv_fixed_width_header_not_padded(tmp_path: Path) -> None:
    """Fixed-width headers are written unpadded (T-CSV-021, R-CSV-071)."""
    plan = _make_plan(
        [{'a': 'x', 'b': 'yy'}, {'a': 'zzz', 'b': 'w'}],
        ['a', 'b'],
        fixed_width=True,
    )
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    header_line = out.read_bytes().split(b'\n')[0]
    assert header_line == b'a,b'


def test_write_csv_fixed_width_quoted_column_width_includes_quotes() -> None:
    """A quoted column's fixed width counts the two quote bytes (T-CSV-022, R-CSV-070)."""
    plan = _make_plan([{'a': 'x,y'}, {'a': 'z'}], ['a'], fixed_width=True)
    assert _stat_for(plan, 'a').max_byte_length == 5


def test_write_csv_fixed_width_zero_length_column_writes_back_to_back_commas(
    tmp_path: Path,
) -> None:
    """An all-empty fixed-width column collapses to adjacent commas (T-CSV-023, R-CSV-073)."""
    plan = _make_plan([{'a': 'v0', 'b': '', 'c': 'v2'}], ['a', 'b', 'c'], fixed_width=True)
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    assert _data_lines(out.read_bytes(), b'\n') == [b'v0,,v2']


def test_write_csv_crlf_terminator(tmp_path: Path) -> None:
    """A CRLF config terminates every record with ``\\r\\n`` (T-CSV-030, R-CSV-003)."""
    plan = _make_plan([{'a': '1'}, {'a': '2'}], ['a'], line_ending='CRLF')
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    # One header row ('a') is written before any data row (R-CSV-010).
    assert out.read_bytes() == b'a\r\n1\r\n2\r\n'


def test_write_csv_lf_terminator(tmp_path: Path) -> None:
    """The default LF config emits ``\\n`` and no carriage return (T-CSV-031, R-CSV-003)."""
    plan = _make_plan([{'a': '1'}, {'a': '2'}], ['a'])
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    assert b'\r' not in out.read_bytes()


def test_write_csv_field_delimiter_always_comma(tmp_path: Path) -> None:
    """Fields are separated by a comma (R-CSV-004)."""
    plan = _make_plan([{'a': '1', 'b': '2'}], ['a', 'b'])
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    # Variable-width row: each value plus a comma except after the last, then
    # the terminator (R-CSV-060).
    assert _data_lines(out.read_bytes(), b'\n') == [b'1,2']


def test_write_csv_no_byte_order_mark_emitted(tmp_path: Path) -> None:
    """The file begins with the header, never a UTF-8 BOM (R-CSV-002)."""
    plan = _make_plan([{'a': '1'}], ['a'])
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    assert out.read_bytes()[:3] != b'\xef\xbb\xbf'


def test_write_csv_output_matches_python_csv_module_byte_for_byte(tmp_path: Path) -> None:
    """A single mixed row matches ``csv.writer`` byte-for-byte (R-CSV-001)."""
    rows = [{'a': 'has,comma', 'b': 'nocomma'}]
    columns = ['a', 'b']
    plan = _make_plan(rows, columns)
    out1 = tmp_path / 'tool.csv'
    write_csv(plan, out1)

    out2 = tmp_path / 'stdlib.csv'
    with open(out2, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(
            handle,
            quoting=csv.QUOTE_MINIMAL,
            quotechar='"',
            lineterminator='\n',
        )
        writer.writerow(columns)
        writer.writerow([rows[0][name] for name in columns])

    assert out1.read_bytes() == out2.read_bytes()


def test_sort_rows_default_empty_sort_by_preserves_input_order() -> None:
    """An empty ``sort_by`` leaves discovery order untouched (T-CSV-060, R-SORT-010)."""
    rows = [{'lid': 'c'}, {'lid': 'a'}, {'lid': 'b'}]
    result = sort_rows(rows, OutputSection())
    assert result == [{'lid': 'c'}, {'lid': 'a'}, {'lid': 'b'}]


def test_sort_rows_explicit_lid_ascending() -> None:
    """``sort_by=['lid']`` sorts ascending (T-CSV-060, R-SORT-020)."""
    rows = [{'lid': 'c'}, {'lid': 'a'}, {'lid': 'b'}]
    result = sort_rows(rows, OutputSection(sort_by=['lid']))
    assert [row['lid'] for row in result] == ['a', 'b', 'c']


def test_sort_rows_explicit_lid_descending() -> None:
    """``sort_by=['-lid']`` sorts descending (T-CSV-060, R-SORT-020)."""
    rows = [{'lid': 'c'}, {'lid': 'a'}, {'lid': 'b'}]
    result = sort_rows(rows, OutputSection(sort_by=['-lid']))
    assert [row['lid'] for row in result] == ['c', 'b', 'a']


def test_sort_rows_unknown_column_raises_configerror() -> None:
    """An unknown sort column is a ``ConfigError`` (T-CSV-061, R-SORT-020)."""
    rows = [{'lid': 'a'}]
    with pytest.raises(ConfigError) as exc_info:
        sort_rows(rows, OutputSection(sort_by=['unknown']))
    assert "'unknown'" in str(exc_info.value)


def test_sort_rows_multi_key_secondary_key_breaks_tie() -> None:
    """A tie on the first key is broken by the second key (R-SORT-020)."""
    rows = [
        {'k1': 'a', 'k2': '2'},
        {'k1': 'a', 'k2': '1'},
        {'k1': 'b', 'k2': '0'},
    ]
    result = sort_rows(rows, OutputSection(sort_by=['k1', 'k2']))
    assert [row['k2'] for row in result] == ['1', '2', '0']


def test_sort_rows_multi_key_stable() -> None:
    """Rows equal on ALL sort keys keep their input order (stable sort, R-SORT-020)."""
    rows = [
        {'k1': 'a', 'k2': 'x', 'tag': 'first'},
        {'k1': 'a', 'k2': 'x', 'tag': 'second'},
        {'k1': 'a', 'k2': 'x', 'tag': 'third'},
    ]
    result = sort_rows(rows, OutputSection(sort_by=['k1', 'k2']))
    assert [row['tag'] for row in result] == ['first', 'second', 'third']


def test_sort_rows_empty_rows_returns_empty_without_raising() -> None:
    """Sorting zero rows returns ``[]`` and never validates columns (R-SORT-020)."""
    result = sort_rows([], OutputSection(sort_by=['anything']))
    assert result == []


def test_build_plan_empty_rows_valid_sort_by_does_not_raise() -> None:
    """A ``sort_by`` in the emitted columns is valid at zero rows (R-SORT-020)."""
    plan = _make_plan([], ['a', 'b'], sort_by=['a'])
    assert plan.rows == ()


def test_build_plan_empty_rows_invalid_sort_by_raises_configerror() -> None:
    """A ``sort_by`` outside the emitted columns still raises at zero rows (R-SORT-020)."""
    with pytest.raises(ConfigError) as exc_info:
        _make_plan([], ['a', 'b'], sort_by=['c'])
    assert "'c'" in str(exc_info.value)


def test_sort_rows_string_comparison_on_post_normalization_value() -> None:
    """Sorting compares cell strings, so ``'10' < '2'`` (R-SORT-030)."""
    rows = [{'lid': '2'}, {'lid': '10'}, {'lid': '1'}]
    result = sort_rows(rows, OutputSection(sort_by=['lid']))
    assert [row['lid'] for row in result] == ['1', '10', '2']


def test_build_plan_record_length_includes_terminator() -> None:
    """``max_record_length`` counts the line terminator bytes (structural)."""
    plan = _make_plan([{'a': 'hi'}], ['a'], line_ending='CRLF')
    assert plan.max_record_length == 4


def test_build_plan_header_row_length_includes_terminator() -> None:
    """``header_row_length`` counts the line terminator bytes (structural)."""
    plan = _make_plan([{'a': 'hi', 'b': 'yo'}], ['a', 'b'], line_ending='CRLF')
    assert plan.header_row_length == 5


def test_build_plan_total_byte_length_matches_file_size_after_write(tmp_path: Path) -> None:
    """``total_byte_length`` equals the written file size (R-LBL feeding bytes)."""
    plan = _make_plan(
        [{'a': 'x,y', 'b': 'z'}, {'a': 'q', 'b': 'w'}],
        ['a', 'b'],
        fixed_width=True,
        line_ending='CRLF',
    )
    out = tmp_path / 'out.csv'
    write_csv(plan, out)
    assert plan.total_byte_length == len(out.read_bytes())


def test_build_plan_carries_auto_column_metadata() -> None:
    """Auto-column flag and token are carried onto the stat (R-IDX-001 plumbing)."""
    plan = _make_plan(
        [{'LID': 'a', 'x': '1'}],
        ['LID', 'x'],
        column_is_auto={'LID': True, 'x': False},
        auto_tokens={'LID': 'lid'},
    )
    assert _stat_for(plan, 'LID').auto_column_token == 'lid'


def test_build_plan_non_auto_column_token_is_none() -> None:
    """A non-auto column carries a ``None`` token (R-IDX-001 plumbing)."""
    plan = _make_plan(
        [{'LID': 'a', 'x': '1'}],
        ['LID', 'x'],
        column_is_auto={'LID': True, 'x': False},
        auto_tokens={'LID': 'lid'},
    )
    assert _stat_for(plan, 'x').auto_column_token is None


@pytest.mark.parametrize('fixed_width', [False, True], ids=['variable', 'fixed'])
@pytest.mark.parametrize('line_ending', ['LF', 'CRLF'])
@pytest.mark.parametrize('with_comma', [False, True], ids=['plain', 'comma'])
def test_write_csv_byte_identical_across_runs(
    tmp_path: Path,
    fixed_width: bool,
    line_ending: str,
    with_comma: bool,
) -> None:
    """Two identical builds write byte-identical files (R-IDX-001)."""
    first_a = 'x,y' if with_comma else 'x'
    rows = [{'a': first_a, 'b': 'longer'}, {'a': 'q', 'b': 'w'}]
    columns = ['a', 'b']

    out1 = tmp_path / 'run1.csv'
    out2 = tmp_path / 'run2.csv'
    write_csv(
        _make_plan(rows, columns, fixed_width=fixed_width, line_ending=line_ending),
        out1,
    )
    write_csv(
        _make_plan(rows, columns, fixed_width=fixed_width, line_ending=line_ending),
        out2,
    )
    assert out1.read_bytes() == out2.read_bytes()
