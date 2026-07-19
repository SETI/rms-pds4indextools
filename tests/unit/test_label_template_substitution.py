"""Unit tests for :mod:`pds4indextools.label_writer` (Phase 9, spec section 14).

These tests exercise the four public symbols of the label writer:
:func:`~pds4indextools.label_writer.build_substitution_dict`,
:func:`~pds4indextools.label_writer.normalize_modification_detail`,
:func:`~pds4indextools.label_writer.write_label`, and
:func:`~pds4indextools.label_writer.load_packaged_template`. They cover the
PdsTemplate variable contract (R-LBL-012, R-LBL-020), the modification-history
normalization (R-LBL-090/091), and the PdsTemplate 2.4.0 invocation boundary
(R-LBL-040, R-LBL-060), including the library/CLI output boundary.
"""

import importlib.resources
import os
from pathlib import Path
from typing import Literal, NamedTuple, TypedDict, cast
from unittest import mock

import pytest
from pdstemplate import TemplateError

from pds4indextools.config import ColumnSpec, LabelContents, ModificationDetail
from pds4indextools.csv_writer import ColumnStat, CsvWritePlan
from pds4indextools.errors import OutputError, Pds4IndexError
from pds4indextools.label_writer import (
    build_substitution_dict,
    load_packaged_template,
    normalize_modification_detail,
    write_label,
)


class _Column(NamedTuple):
    """A single test column description used to build parallel writer inputs."""

    header: str
    xpath: str
    data_type: str
    width: int
    auto_token: str | None = None


class _BuildKwargs(TypedDict):
    """The fully typed keyword inputs for ``build_substitution_dict``."""

    label_contents: LabelContents
    plan: CsvWritePlan
    column_specs: list[ColumnSpec]
    column_types: dict[str, str]
    column_xpaths: dict[str, str]
    csv_absolute_path: Path


def _make_plan(
    *,
    columns: list[str],
    stats: list[ColumnStat],
    rows: tuple[dict[str, str], ...] = (),
    fixed_width: bool = False,
    line_terminator: bytes = b'\n',
    header_row_length: int = 0,
    max_record_length: int = 0,
    total_byte_length: int = 0,
) -> CsvWritePlan:
    """Build a :class:`CsvWritePlan` with sensible defaults for tests."""
    return CsvWritePlan(
        rows=rows,
        columns=tuple(columns),
        stats=tuple(stats),
        line_terminator=line_terminator,
        fixed_width=fixed_width,
        header_row_length=header_row_length,
        max_record_length=max_record_length,
        total_byte_length=total_byte_length,
    )


def _make_inputs(
    columns: list[_Column],
    *,
    fixed_width: bool = False,
    product_class: Literal['Product_Ancillary', 'Product_Metadata_Supplemental'] = (
        'Product_Ancillary'
    ),
    rows: tuple[dict[str, str], ...] = (),
    line_terminator: bytes = b'\n',
    csv_path: Path = Path('/data/holdings/index.csv'),
    label_contents: LabelContents | None = None,
    header_row_length: int = 0,
    max_record_length: int = 0,
    total_byte_length: int = 0,
) -> _BuildKwargs:
    """Assemble the parallel keyword inputs for ``build_substitution_dict``."""
    specs: list[ColumnSpec] = []
    stats: list[ColumnStat] = []
    column_types: dict[str, str] = {}
    column_xpaths: dict[str, str] = {}
    for column in columns:
        is_auto = column.auto_token is not None
        if is_auto:
            specs.append(ColumnSpec(auto=column.auto_token, name=column.header))
        else:
            specs.append(ColumnSpec(xpath=column.xpath, name=column.header))
        stats.append(
            ColumnStat(
                name=column.header,
                must_quote=False,
                max_byte_length=column.width,
                is_auto_column=is_auto,
                auto_column_token=column.auto_token,
            )
        )
        column_types[column.header] = column.data_type
        column_xpaths[column.header] = column.xpath
    plan = _make_plan(
        columns=[column.header for column in columns],
        stats=stats,
        rows=rows,
        fixed_width=fixed_width,
        line_terminator=line_terminator,
        header_row_length=header_row_length,
        max_record_length=max_record_length,
        total_byte_length=total_byte_length,
    )
    if label_contents is None:
        label_contents = LabelContents(
            logical_identifier='urn:nasa:pds:test:index',
            product_class=product_class,
        )
    return {
        'label_contents': label_contents,
        'plan': plan,
        'column_specs': specs,
        'column_types': column_types,
        'column_xpaths': column_xpaths,
        'csv_absolute_path': csv_path,
    }


_ONE_XPATH_COLUMN = [_Column('lid_col', '<lid>', 'pds:ASCII_LID', 21)]

_SEVEN_KEYS = {
    'name',
    'field_number',
    'field_location',
    'data_type',
    'field_length',
    'maximum_field_length',
    'xpath',
}


def test_build_substitution_dict_includes_index_file_name_absolute() -> None:
    """R-LBL-012: ``index_file_name`` is the absolute path of the CSV."""
    csv_path = Path('/data/holdings/index.csv')
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, csv_path=csv_path))
    assert result['index_file_name'] == str(csv_path)


def test_build_substitution_dict_index_file_name_is_absolute_path() -> None:
    """R-LBL-012: the ``index_file_name`` value parses as an absolute path."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN))
    assert Path(str(result['index_file_name'])).is_absolute()


def test_build_substitution_dict_field_content_one_entry_per_column() -> None:
    """T-LBL-010, R-LBL-020: one ``Field_Content`` entry per output column."""
    columns = [
        _Column('a', '<a>', 'pds:ASCII_LID', 3),
        _Column('b', '<b>', 'pds:ASCII_Real', 5),
    ]
    result = build_substitution_dict(**_make_inputs(columns))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    assert len(field_content) == 2


def test_build_substitution_dict_field_content_each_entry_has_seven_keys() -> None:
    """T-LBL-011, R-LBL-020: each ``Field_Content`` entry has exactly 7 keys."""
    columns = [
        _Column('a', '<a>', 'pds:ASCII_LID', 3),
        _Column('b', '<b>', 'pds:ASCII_Real', 5),
    ]
    result = build_substitution_dict(**_make_inputs(columns))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    for entry in field_content:
        assert set(entry.keys()) == _SEVEN_KEYS


def test_build_substitution_dict_field_content_field_number_and_name() -> None:
    """R-LBL-020: ``field_number`` is 1-based sequential and ``name`` is the header."""
    columns = [
        _Column('a', '<a>', 'pds:ASCII_LID', 3),
        _Column('b', '<b>', 'pds:ASCII_Real', 5),
        _Column('c', '<c>', 'pds:ASCII_Real', 7),
    ]
    result = build_substitution_dict(**_make_inputs(columns))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    assert [entry['field_number'] for entry in field_content] == list(
        range(1, len(field_content) + 1)
    )
    assert [entry['name'] for entry in field_content] == ['a', 'b', 'c']


def test_build_substitution_dict_data_type_namespace_stripped() -> None:
    """Spec section 11.3: ``pds:ASCII_LID`` is emitted as ``ASCII_LID``."""
    columns = [_Column('a', '<a>', 'pds:ASCII_LID', 3)]
    result = build_substitution_dict(**_make_inputs(columns))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    assert field_content[0]['data_type'] == 'ASCII_LID'


def test_build_substitution_dict_table_character_when_fixed_width_true() -> None:
    """R-LBL-012: fixed width sets ``Table_Character`` true, ``Table_Delimited`` false."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, fixed_width=True))
    assert result['Table_Character'] is True


def test_build_substitution_dict_table_character_false_when_delimited() -> None:
    """R-LBL-012: delimited output sets ``Table_Character`` false."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, fixed_width=False))
    assert result['Table_Character'] is False


def test_build_substitution_dict_table_delimited_when_fixed_width_false() -> None:
    """R-LBL-012: delimited output sets ``Table_Delimited`` true."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, fixed_width=False))
    assert result['Table_Delimited'] is True


def test_build_substitution_dict_table_delimited_false_when_fixed_width() -> None:
    """R-LBL-012: fixed width sets ``Table_Delimited`` false."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, fixed_width=True))
    assert result['Table_Delimited'] is False


def test_build_substitution_dict_product_ancillary_when_class_matches() -> None:
    """T-LBL-020, R-LBL-010: ``Product_Ancillary`` class sets the boolean true."""
    result = build_substitution_dict(
        **_make_inputs(_ONE_XPATH_COLUMN, product_class='Product_Ancillary')
    )
    assert result['Product_Ancillary'] is True


def test_build_substitution_dict_product_metadata_false_for_ancillary() -> None:
    """T-LBL-020, R-LBL-010: the metadata boolean is false for an ancillary product."""
    result = build_substitution_dict(
        **_make_inputs(_ONE_XPATH_COLUMN, product_class='Product_Ancillary')
    )
    assert result['Product_Metadata_Supplemental'] is False


def test_build_substitution_dict_product_metadata_supplemental_when_class_matches() -> None:
    """T-LBL-021, R-LBL-010: the metadata class sets its boolean true."""
    result = build_substitution_dict(
        **_make_inputs(_ONE_XPATH_COLUMN, product_class='Product_Metadata_Supplemental')
    )
    assert result['Product_Metadata_Supplemental'] is True


def test_build_substitution_dict_product_ancillary_false_for_metadata() -> None:
    """T-LBL-021, R-LBL-010: the ancillary boolean is false for a metadata product."""
    result = build_substitution_dict(
        **_make_inputs(_ONE_XPATH_COLUMN, product_class='Product_Metadata_Supplemental')
    )
    assert result['Product_Ancillary'] is False


def test_build_substitution_dict_label_contents_passthrough_preserves_extras() -> None:
    """T-LBL-040, R-CFG-022: an extra ``label_contents`` key survives to the dict."""
    label_contents = LabelContents.model_validate(
        {
            'logical_identifier': 'urn:nasa:pds:test:index',
            'product_class': 'Product_Ancillary',
            'custom_var': 'hello',
        }
    )
    result = build_substitution_dict(
        **_make_inputs(_ONE_XPATH_COLUMN, label_contents=label_contents)
    )
    assert result['custom_var'] == 'hello'


def test_build_substitution_dict_passes_no_creation_date_value() -> None:
    """R-LBL-080: the tool computes/passes no creation-date value into the dict.

    Given a ``LabelContents`` with no user-supplied creation timestamp, the
    assembled substitution dict carries no key naming a creation date, and the
    ``File_Area_*`` holders the template reads a creation date from are ``None``.
    The template's ``$IF(File_Area_Ancillary['creation_date_time'])`` therefore
    stays false and the label's ``<creation_date_time>`` comes only from the
    ``$FILE_ZULU(...)$`` time macro rather than any value the tool injected.
    """
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN))
    assert [key for key in result if 'creation' in key.lower()] == []
    assert result['File_Area_Ancillary'] is None
    assert result['File_Area_Metadata'] is None


def test_build_substitution_dict_records_equals_row_count() -> None:
    """R-LBL-012: ``records`` equals the number of data rows in the plan."""
    rows = ({'lid_col': 'a'}, {'lid_col': 'b'}, {'lid_col': 'c'})
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, rows=rows))
    assert result['records'] == 3


def test_build_substitution_dict_fields_equals_column_count() -> None:
    """R-LBL-012: ``fields`` equals the number of output columns."""
    columns = [
        _Column('a', '<a>', 'pds:ASCII_LID', 3),
        _Column('b', '<b>', 'pds:ASCII_Real', 5),
        _Column('c', '<c>', 'pds:ASCII_Real', 5),
    ]
    result = build_substitution_dict(**_make_inputs(columns))
    assert result['fields'] == 3


def test_build_substitution_dict_object_length_h_matches_plan() -> None:
    """R-LBL-012: ``object_length_h`` echoes the plan header-row byte length."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, header_row_length=17))
    assert result['object_length_h'] == 17


def test_build_substitution_dict_object_length_t_matches_plan() -> None:
    """R-LBL-012: ``object_length_t`` echoes the plan total byte length."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, total_byte_length=123))
    assert result['object_length_t'] == 123


def test_build_substitution_dict_maximum_record_length_matches_plan() -> None:
    """R-LBL-012: ``maximum_record_length`` echoes the plan value."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, max_record_length=44))
    assert result['maximum_record_length'] == 44


def test_build_substitution_dict_record_delimiter_line_feed_for_lf() -> None:
    """R-LBL-060: an LF plan yields ``RECORD_DELIMITER == 'Line-Feed'``."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, line_terminator=b'\n'))
    assert result['RECORD_DELIMITER'] == 'Line-Feed'


def test_build_substitution_dict_record_delimiter_crlf_for_crlf() -> None:
    """R-LBL-060: a CRLF plan yields the carriage-return line-feed delimiter name."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN, line_terminator=b'\r\n'))
    assert result['RECORD_DELIMITER'] == 'Carriage-Return Line-Feed'


def test_normalize_modification_detail_single_dict_to_list() -> None:
    """T-LBL-030, R-LBL-091: a single entry is wrapped in a one-element list."""
    detail = ModificationDetail(
        modification_date='2024-01-01', version_id='1.0', description='First.'
    )
    result = normalize_modification_detail(detail)
    assert result == [
        {'modification_date': '2024-01-01', 'version_id': '1.0', 'description': 'First.'}
    ]


def test_normalize_modification_detail_list_passthrough() -> None:
    """R-LBL-091: a list of three entries passes through in declared order."""
    details = [
        ModificationDetail(modification_date='2024-01-01', version_id='1.0', description='a'),
        ModificationDetail(modification_date='2024-02-01', version_id='2.0', description='b'),
        ModificationDetail(modification_date='2024-03-01', version_id='3.0', description='c'),
    ]
    result = normalize_modification_detail(details)
    assert [entry['version_id'] for entry in result] == ['1.0', '2.0', '3.0']


def test_normalize_modification_detail_none_generates_default_entry(
    frozen_time: None,
) -> None:
    """Owner decision #3: ``None`` yields exactly one dated default entry."""
    result = normalize_modification_detail(None)
    assert result == [
        {
            'modification_date': '2026-05-14',
            'version_id': '1.0',
            'description': 'Initial version.',
        }
    ]


def test_normalize_modification_detail_none_uses_fallback_version_id(
    frozen_time: None,
) -> None:
    """Owner decision #3: the fallback version id populates the default entry."""
    result = normalize_modification_detail(None, fallback_version_id='2.0')
    assert result[0]['version_id'] == '2.0'


def test_build_substitution_dict_default_modification_detail_when_config_omits_it(
    frozen_time: None,
) -> None:
    """Owner decision #3: an omitted history becomes the label-versioned default."""
    label_contents = LabelContents(
        logical_identifier='urn:nasa:pds:test:index',
        product_class='Product_Ancillary',
        version_id='7.3',
    )
    result = build_substitution_dict(
        **_make_inputs(_ONE_XPATH_COLUMN, label_contents=label_contents)
    )
    assert result['Modification_Detail'] == [
        {
            'modification_date': '2026-05-14',
            'version_id': '7.3',
            'description': 'Initial version.',
        }
    ]


def test_build_substitution_dict_optional_fields_present_as_none() -> None:
    """R-LBL-001, R-LBL-040: every optional label field is present, valued ``None``."""
    result = build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN))
    optional_names = [
        'version_id',
        'title',
        'Citation_Information',
        'Internal_Reference',
        'External_Reference',
        'Source_Product_Internal',
        'Source_Product_External',
        'File_Area_Ancillary',
        'File_Area_Metadata',
    ]
    for name in optional_names:
        assert result[name] is None


def test_build_substitution_dict_reserved_key_collision_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-LBL-012: a reserved BASE-variable collision raises ``Pds4IndexError``.

    Config validation (R-LBL-012) normally rejects a reserved key in
    ``label_contents``, so this forces the belt-and-braces invariant by
    patching ``model_dump`` to smuggle the reserved ``records`` name through.
    """
    monkeypatch.setattr(LabelContents, 'model_dump', lambda self, **kwargs: {'records': 5})
    with pytest.raises(Pds4IndexError) as exc_info:
        build_substitution_dict(**_make_inputs(_ONE_XPATH_COLUMN))
    assert 'reserved key collision' in str(exc_info.value)


def test_load_packaged_template_returns_packaged_xml_path() -> None:
    """R-LBL-001: the yielded path is the packaged template resource path."""
    expected = importlib.resources.files('pds4indextools.templates') / 'index_label_template.xml'
    with load_packaged_template() as template_path:
        assert str(template_path) == str(expected)


def test_load_packaged_template_path_is_file() -> None:
    """R-LBL-001: the yielded path points at an existing regular file."""
    with load_packaged_template() as template_path:
        assert template_path.is_file() is True


def test_write_label_invokes_pdstemplate_with_crlf_true_when_line_ending_crlf(
    tmp_path: Path,
) -> None:
    """R-LBL-040, R-LBL-060: ``line_ending='CRLF'`` passes ``crlf=True``."""
    output_path = tmp_path / 'out.lblx'
    with mock.patch('pds4indextools.label_writer.PdsTemplate') as mock_template_cls:
        mock_template_cls.return_value.write.return_value = (0, 0)
        write_label(tmp_path / 'tpl.xml', {}, output_path, line_ending='CRLF')
    assert mock_template_cls.call_args.kwargs['crlf'] is True


def test_write_label_invokes_pdstemplate_with_crlf_false_when_line_ending_lf(
    tmp_path: Path,
) -> None:
    """R-LBL-060: ``line_ending='LF'`` passes ``crlf=False``."""
    output_path = tmp_path / 'out.lblx'
    with mock.patch('pds4indextools.label_writer.PdsTemplate') as mock_template_cls:
        mock_template_cls.return_value.write.return_value = (0, 0)
        write_label(tmp_path / 'tpl.xml', {}, output_path, line_ending='LF')
    assert mock_template_cls.call_args.kwargs['crlf'] is False


def test_write_label_writes_to_supplied_output_path(tmp_path: Path) -> None:
    """R-LBL-040: the supplied output path is passed to ``template.write``."""
    output_path = tmp_path / 'out.lblx'
    with mock.patch('pds4indextools.label_writer.PdsTemplate') as mock_template_cls:
        mock_write = mock_template_cls.return_value.write
        mock_write.return_value = (0, 0)
        write_label(tmp_path / 'tpl.xml', {}, output_path, line_ending='LF')
    assert mock_write.call_args.args[1] == output_path


def test_write_label_pdstemplate_failure_wrapped_in_outputerror(tmp_path: Path) -> None:
    """Spec section 17: a ``TemplateError`` is wrapped as ``OutputError``."""
    output_path = tmp_path / 'out.lblx'
    with (
        mock.patch('pds4indextools.label_writer.PdsTemplate', side_effect=TemplateError('boom')),
        pytest.raises(OutputError) as exc_info,
    ):
        write_label(tmp_path / 'tpl.xml', {}, output_path, line_ending='LF')
    assert 'PdsTemplate failed' in str(exc_info.value)


def test_write_label_pdstemplate_failure_preserves_cause(tmp_path: Path) -> None:
    """Spec section 17: the wrapped ``OutputError`` chains the original cause."""
    output_path = tmp_path / 'out.lblx'
    with (
        mock.patch('pds4indextools.label_writer.PdsTemplate', side_effect=TemplateError('boom')),
        pytest.raises(OutputError) as exc_info,
    ):
        write_label(tmp_path / 'tpl.xml', {}, output_path, line_ending='LF')
    assert 'boom' in str(exc_info.value.__cause__)


def test_write_label_nonzero_error_count_raises_outputerror(tmp_path: Path) -> None:
    """Belt-and-braces: a nonzero error count raises ``OutputError``."""
    output_path = tmp_path / 'out.lblx'
    with mock.patch('pds4indextools.label_writer.PdsTemplate') as mock_template_cls:
        mock_template_cls.return_value.write.return_value = (2, 0)
        with pytest.raises(OutputError) as exc_info:
            write_label(tmp_path / 'tpl.xml', {}, output_path, line_ending='LF')
        assert '2 error(s)' in str(exc_info.value)


def test_write_label_passes_raise_exceptions_true(tmp_path: Path) -> None:
    """Verified 2.4.0 behavior: ``write`` is called with ``raise_exceptions=True``."""
    output_path = tmp_path / 'out.lblx'
    with mock.patch('pds4indextools.label_writer.PdsTemplate') as mock_template_cls:
        mock_write = mock_template_cls.return_value.write
        mock_write.return_value = (0, 0)
        write_label(tmp_path / 'tpl.xml', {}, output_path, line_ending='LF')
    assert mock_write.call_args.kwargs['raise_exceptions'] is True


def test_write_label_routes_pdstemplate_logging_off_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    frozen_time: None,
    frozen_csv_mtime: int,
) -> None:
    """Library/CLI output boundary: a real render prints nothing to stdout."""
    csv_path = tmp_path / 'index.csv'
    csv_path.write_text('lid_col\nurn:nasa:pds:test\n', encoding='utf-8')
    os.utime(csv_path, (frozen_csv_mtime, frozen_csv_mtime))
    label_contents = LabelContents(
        logical_identifier='urn:nasa:pds:test:index',
        product_class='Product_Ancillary',
        version_id='1.0',
        title='Test index',
    )
    rows = ({'lid_col': 'urn:nasa:pds:test'},)
    substitution_dict = build_substitution_dict(
        **_make_inputs(
            _ONE_XPATH_COLUMN,
            label_contents=label_contents,
            rows=rows,
            csv_path=csv_path,
        )
    )
    output_path = tmp_path / 'index.lblx'
    with load_packaged_template() as template_path:
        write_label(template_path, substitution_dict, output_path, line_ending='LF')
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize(
    ('widths', 'expected_offsets'),
    [
        ([5, 3, 7], [1, 7, 11]),
        ([1], [1]),
        ([0, 3], [1, 2]),
        ([10, 10, 10, 10], [1, 12, 23, 34]),
        ([255, 255], [1, 257]),
    ],
)
def test_field_location_fixed_width_byte_offset_parametrized(
    widths: list[int],
    expected_offsets: list[int],
) -> None:
    """R-LBL-020: fixed-width ``field_location`` is the 1-based byte offset."""
    columns = [
        _Column(f'col{index}', f'<c{index}>', 'pds:ASCII_LID', width)
        for index, width in enumerate(widths)
    ]
    result = build_substitution_dict(**_make_inputs(columns, fixed_width=True))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    offsets = [entry['field_location'] for entry in field_content]
    assert offsets == expected_offsets


def test_field_location_delimited_column_position() -> None:
    """R-LBL-020: delimited ``field_location`` is the 1-based column position."""
    columns = [
        _Column('a', '<a>', 'pds:ASCII_LID', 5),
        _Column('b', '<b>', 'pds:ASCII_Real', 3),
        _Column('c', '<c>', 'pds:ASCII_Real', 7),
    ]
    result = build_substitution_dict(**_make_inputs(columns, fixed_width=False))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    offsets = [entry['field_location'] for entry in field_content]
    assert offsets == [1, 2, 3]


def test_field_content_field_length_fixed_width_uses_max_byte_length() -> None:
    """R-LBL-020: ``field_length`` equals the column ``max_byte_length``."""
    columns = [_Column('a', '<a>', 'pds:ASCII_LID', 42)]
    result = build_substitution_dict(**_make_inputs(columns, fixed_width=True))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    assert field_content[0]['field_length'] == 42


def test_field_content_maximum_field_length_delimited_uses_max_byte_length() -> None:
    """R-LBL-020: ``maximum_field_length`` equals the column ``max_byte_length``."""
    columns = [_Column('a', '<a>', 'pds:ASCII_LID', 42)]
    result = build_substitution_dict(**_make_inputs(columns, fixed_width=False))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    assert field_content[0]['maximum_field_length'] == 42


def test_field_content_xpath_key_uses_raw_canonical_xpath_for_mapped() -> None:
    """R-LBL-020: a mapped column carries its raw canonical XPath in ``xpath``."""
    columns = [_Column('a', '<Product>/<lid>', 'pds:ASCII_LID', 5)]
    result = build_substitution_dict(**_make_inputs(columns))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    assert field_content[0]['xpath'] == '<Product>/<lid>'


def test_field_content_xpath_key_uses_auto_token_for_auto_columns() -> None:
    """R-LBL-020: an auto column carries its token (e.g. ``lid``) in ``xpath``."""
    columns = [_Column('lid', 'lid', 'pds:ASCII_LID', 5, auto_token='lid')]
    result = build_substitution_dict(**_make_inputs(columns))
    field_content = cast(list[dict[str, object]], result['Field_Content'])
    assert field_content[0]['xpath'] == 'lid'
