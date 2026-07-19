"""Unit tests for :mod:`pds4indextools.config`.

These tests pin down configuration loading, deep-merging, and pydantic
validation of spec section 15 (R-CFG-010..R-CFG-052) together with the
column-selection schema of section 7 (R-MAP-*), the auto-column tokens
(R-AUTO-001), reserved BASE-variable rejection (R-LBL-012), the
product-class literal (R-LBL-010), and sort-key parsing (R-SORT-010/020).

Per the plan's section 3.2 boundary rule (critique skill section 20) every
test in this file imports ONLY public names from
:mod:`pds4indextools.config`; private helpers are exercised exclusively
through :func:`~pds4indextools.config.load_config` and the public models.
The three-YAML merge tests write their inputs inline via ``tmp_path``; the
remaining tests use the committed ``tests/data/configs/`` fixtures accessed
through the ``data_root`` fixture from ``conftest``.
"""

import os
from pathlib import Path

import pytest
import yaml

from pds4indextools.config import (
    AUTO_COLUMN_TOKENS,
    IndexConfig,
    ModificationDetail,
    load_config,
    parse_sort_key,
)
from pds4indextools.errors import ConfigError

_VALID_LABEL_CONTENTS = (
    'label_contents:\n'
    '  logical_identifier: urn:nasa:pds:test:test:test_index\n'
    '  product_class: Product_Ancillary\n'
)

_RESERVED_LABEL_CONTENT_KEYS = [
    'index_file_name',
    'Field_Content',
    'fields',
    'records',
    'Table_Character',
    'Table_Delimited',
    'Product_Ancillary',
    'Product_Metadata_Supplemental',
    'object_length_h',
    'object_length_t',
    'maximum_record_length',
]


@pytest.fixture
def configs_dir(data_root: Path) -> Path:
    """Absolute path to the committed ``tests/data/configs`` fixture directory."""
    return data_root / 'configs'


def _write_config(directory: Path, name: str, content: str) -> Path:
    """Write ``content`` to ``directory/name`` and return the absolute path.

    Parameters:
        directory: The directory to write into (typically ``tmp_path``).
        name: The file name to create.
        content: The YAML text to write.

    Returns:
        The absolute :class:`~pathlib.Path` of the written file.
    """
    path = directory / name
    path.write_text(content, encoding='utf-8')
    return path


# --- Default config and top-level shape -----------------------------------


def test_load_default_only_is_valid_modulo_missing_label_contents() -> None:
    """Merging zero user configs fails naming both required label fields.

    T-ID: R-CFG-030, R-CFG-031.
    """
    with pytest.raises(ConfigError) as exc_info:
        load_config([])
    message = str(exc_info.value)
    assert 'logical_identifier' in message
    assert 'product_class' in message


def test_load_default_has_nillable_defaults(configs_dir: Path) -> None:
    """The packaged default supplies the six nillable data types after merge.

    Verified through the public API (a config with no ``nillable`` block
    inherits exactly the packaged defaults). T-ID: spec section 15.6.
    """
    config = load_config([configs_dir / 'minimal.yaml'])
    expected = {
        'pds:ASCII_Date_YMD',
        'pds:ASCII_Date_Time_YMD',
        'pds:ASCII_Date_Time_YMD_UTC',
        'pds:ASCII_Integer',
        'pds:ASCII_Real',
        'pds:ASCII_Short_String_Collapsed',
    }
    assert set(config.nillable.keys()) == expected


def test_load_yaml_scalar_top_level_rejected(tmp_path: Path) -> None:
    """A scalar at the YAML top level is rejected. T-ID: T-CFG-001, R-CFG-011."""
    path = _write_config(tmp_path, 'scalar.yaml', 'hello\n')
    with pytest.raises(ConfigError, match='must be a mapping'):
        load_config([path])


def test_load_yaml_list_top_level_rejected(tmp_path: Path) -> None:
    """A list at the YAML top level is rejected. T-ID: R-CFG-011."""
    path = _write_config(tmp_path, 'list.yaml', '[]\n')
    with pytest.raises(ConfigError, match='must be a mapping'):
        load_config([path])


def test_load_yaml_null_top_level_rejected(tmp_path: Path) -> None:
    """A null document at the YAML top level is rejected. T-ID: R-CFG-011."""
    path = _write_config(tmp_path, 'null.yaml', 'null\n')
    with pytest.raises(ConfigError, match='must be a mapping'):
        load_config([path])


def test_top_level_extra_key_rejected(configs_dir: Path) -> None:
    """An unknown top-level key is rejected by name. T-ID: T-CFG-010, R-CFG-020."""
    with pytest.raises(ConfigError, match='unrecognized_top_level_key'):
        load_config([configs_dir / 'test_config_invalid_top.yaml'])


def test_output_extra_key_rejected(configs_dir: Path) -> None:
    """An unknown key inside ``output`` is rejected. T-ID: T-CFG-011, R-CFG-021."""
    with pytest.raises(ConfigError, match='bogus'):
        load_config([configs_dir / 'test_config_invalid_output.yaml'])


def test_label_contents_extra_key_accepted(configs_dir: Path) -> None:
    """An unknown ``label_contents`` key passes through as an extra.

    T-ID: T-CFG-012, R-CFG-022.
    """
    config = load_config([configs_dir / 'test_config_extras.yaml'])
    assert config.label_contents.model_extra is not None
    assert config.label_contents.model_extra['custom_var'] == 'hello world'


def test_nillable_extra_nilreason_rejected(configs_dir: Path) -> None:
    """An unknown nilReason key inside a ``nillable`` entry is rejected.

    T-ID: T-CFG-013, R-CFG-023.
    """
    with pytest.raises(ConfigError, match='frobnicate'):
        load_config([configs_dir / 'test_config_invalid_nillable.yaml'])


def test_nillable_custom_dtype_accepted(configs_dir: Path) -> None:
    """A custom ``nillable`` data type with all four nilReasons is accepted.

    T-ID: T-CFG-014, R-CFG-023.
    """
    config = load_config([configs_dir / 'minimal.yaml', configs_dir / 'test_config_partial_c.yaml'])
    assert 'pds:ASCII_NonNegative_Integer' in config.nillable


# --- Required fields and product-class literal ----------------------------


def test_missing_logical_identifier_rejected(tmp_path: Path) -> None:
    """A ``label_contents`` without ``logical_identifier`` is rejected by name.

    T-ID: T-CFG-020, R-CFG-030.
    """
    content = 'label_contents:\n  product_class: Product_Ancillary\n'
    path = _write_config(tmp_path, 'no_lid.yaml', content)
    with pytest.raises(ConfigError, match='logical_identifier'):
        load_config([path])


def test_missing_product_class_rejected(tmp_path: Path) -> None:
    """A ``label_contents`` without ``product_class`` is rejected by name.

    T-ID: T-CFG-021, R-CFG-031.
    """
    content = 'label_contents:\n  logical_identifier: urn:nasa:pds:test:test:test_index\n'
    path = _write_config(tmp_path, 'no_pc.yaml', content)
    with pytest.raises(ConfigError, match='product_class'):
        load_config([path])


def test_product_class_invalid_literal_rejected(tmp_path: Path) -> None:
    """A ``product_class`` outside the two literals is rejected.

    T-ID: T-LBL-022, R-LBL-010.
    """
    content = (
        'label_contents:\n'
        '  logical_identifier: urn:nasa:pds:test:test:test_index\n'
        '  product_class: Product_Bogus\n'
    )
    path = _write_config(tmp_path, 'bad_pc.yaml', content)
    with pytest.raises(ConfigError, match='product_class'):
        load_config([path])


def test_label_contents_citation_and_modification_round_trip(tmp_path: Path) -> None:
    """A ``Citation_Information`` and ``Modification_Detail`` block loads intact.

    Exercises the otherwise-untested optional label sub-models through the
    public API, asserting the parsed values are accessible on the model.
    T-ID: R-CFG-022, R-LBL-090.
    """
    content = (
        _VALID_LABEL_CONTENTS + '  Citation_Information:\n'
        '    author_list: [Smith, Jones]\n'
        '    publication_year: 2026\n'
        '    description: A test index citation.\n'
        '  Modification_Detail:\n'
        '    modification_date: "2026-07-18"\n'
        '    version_id: "1.0"\n'
        '    description: Initial version.\n'
    )
    path = _write_config(tmp_path, 'citation.yaml', content)
    config = load_config([path])
    citation = config.label_contents.Citation_Information
    assert citation is not None
    assert citation.author_list == ['Smith', 'Jones']
    assert citation.publication_year == 2026
    assert citation.description == 'A test index citation.'
    modification = config.label_contents.Modification_Detail
    assert isinstance(modification, ModificationDetail)
    assert modification.modification_date == '2026-07-18'
    assert modification.version_id == '1.0'
    assert modification.description == 'Initial version.'


# --- Path fields ----------------------------------------------------------


def test_relative_path_in_xsd_cache_dir_rejected(configs_dir: Path) -> None:
    """A relative ``xsd_cache_dir`` is rejected naming the path.

    T-ID: T-CFG-030, R-CFG-040.
    """
    config_path = configs_dir / 'test_config_relative_path.yaml'
    with pytest.raises(ConfigError) as exc_info:
        load_config([config_path])
    message = str(exc_info.value)
    assert 'must be absolute' in message
    assert 'relative/cache' in message
    # A single-path load attaches the offending config path to the error
    # (validation-error file_path, deviation c).
    assert exc_info.value.file_path == config_path


@pytest.mark.parametrize(
    ('os_name', 'abspath'),
    [
        ('posix', '/tmp/xsd_cache'),
        ('nt', r'C:\xsd_cache'),
    ],
)
def test_absolute_path_in_xsd_cache_dir_accepted(
    os_name: str, abspath: str, tmp_path: Path
) -> None:
    """An absolute ``xsd_cache_dir`` is accepted. T-ID: R-CFG-040, R-CFG-024."""
    if os.name != os_name:
        pytest.skip(f'path syntax is specific to os.name == {os_name!r}')
    content = _VALID_LABEL_CONTENTS + f'xsd_cache_dir: {abspath}\n'
    path = _write_config(tmp_path, 'abs_cache.yaml', content)
    config = load_config([path])
    assert config.xsd_cache_dir == Path(abspath)


# --- Merge / overlay semantics (inline three-YAML tests) ------------------


def test_three_config_merge_order(tmp_path: Path) -> None:
    """The last config in the chain wins for a scalar. T-ID: T-CFG-040, R-CFG-050.

    Chosen to be discriminating: the packaged default and config A both set
    ``fixed_width: false``, so a ``True`` final value can only come from config
    C winning over B (which also sets True) -- proving later configs override
    earlier ones rather than the default merely leaking through.
    """
    config_a = _write_config(
        tmp_path, 'a.yaml', _VALID_LABEL_CONTENTS + 'output:\n  fixed_width: false\n'
    )
    config_b = _write_config(tmp_path, 'b.yaml', 'output:\n  fixed_width: true\n')
    config_c = _write_config(tmp_path, 'c.yaml', 'output:\n  fixed_width: true\n')
    config = load_config([config_a, config_b, config_c])
    assert config.output.fixed_width is True


def test_three_config_merge_dict_deep_merge(tmp_path: Path) -> None:
    """Nested dicts deep-merge, keeping keys from both configs.

    T-ID: T-CFG-040, R-CFG-050.
    """
    config_a = _write_config(
        tmp_path,
        'a.yaml',
        _VALID_LABEL_CONTENTS + 'nillable:\n  pds:ASCII_Real:\n    inapplicable: -1.0\n',
    )
    config_b = _write_config(
        tmp_path,
        'b.yaml',
        'nillable:\n  pds:ASCII_Real:\n    missing: -2.0\n',
    )
    config = load_config([config_a, config_b])
    assert config.nillable['pds:ASCII_Real'].inapplicable == -1.0
    assert config.nillable['pds:ASCII_Real'].missing == -2.0


def test_three_config_merge_list_replacement(tmp_path: Path) -> None:
    """A list is replaced wholesale, not concatenated. T-ID: T-CFG-040, R-CFG-050."""
    config_a = _write_config(
        tmp_path, 'a.yaml', _VALID_LABEL_CONTENTS + "output:\n  sort_by: ['a']\n"
    )
    config_b = _write_config(tmp_path, 'b.yaml', "output:\n  sort_by: ['b', 'c']\n")
    config = load_config([config_a, config_b])
    assert config.output.sort_by == ['b', 'c']


def test_partial_individual_configs_accepted_after_merge(configs_dir: Path) -> None:
    """Individual configs may be partial as long as the merge is complete.

    T-ID: T-CFG-050, R-CFG-052.
    """
    config = load_config(
        [
            configs_dir / 'test_config_partial_a.yaml',
            configs_dir / 'test_config_partial_b.yaml',
            configs_dir / 'test_config_partial_c.yaml',
        ]
    )
    assert config.label_contents.logical_identifier == (
        'urn:nasa:pds:test_bundle:partial:test_index'
    )


# --- Reserved BASE-variable keys (R-LBL-012) ------------------------------


def test_reserved_label_contents_key_rejected_index_file_name(
    configs_dir: Path,
) -> None:
    """A reserved ``index_file_name`` key in ``label_contents`` is rejected.

    T-ID: R-LBL-012.
    """
    with pytest.raises(ConfigError, match='index_file_name'):
        load_config([configs_dir / 'test_config_reserved_key.yaml'])


def test_reserved_label_contents_key_rejected_field_content(tmp_path: Path) -> None:
    """A reserved ``Field_Content`` key in ``label_contents`` is rejected.

    T-ID: R-LBL-012.
    """
    content = _VALID_LABEL_CONTENTS + '  Field_Content: something\n'
    path = _write_config(tmp_path, 'reserved.yaml', content)
    with pytest.raises(ConfigError, match='Field_Content'):
        load_config([path])


@pytest.mark.parametrize('reserved_key', _RESERVED_LABEL_CONTENT_KEYS)
def test_reserved_label_contents_keys_parametrized_full_set(
    reserved_key: str, tmp_path: Path
) -> None:
    """Every one of the eleven reserved BASE variable names is rejected.

    T-ID: R-LBL-012.
    """
    content = _VALID_LABEL_CONTENTS + f'  {reserved_key}: something\n'
    path = _write_config(tmp_path, 'reserved.yaml', content)
    with pytest.raises(ConfigError, match=reserved_key):
        load_config([path])


# --- Error wrapping and boundary validation -------------------------------


def test_yaml_parse_error_wrapped_in_configerror(tmp_path: Path) -> None:
    """Malformed YAML is wrapped in a :exc:`ConfigError`. T-ID: R-CFG-010."""
    path = _write_config(tmp_path, 'bad.yaml', 'foo: [1, 2\n')
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    assert isinstance(exc_info.value.__cause__, yaml.YAMLError)
    assert exc_info.value.file_path == path
    assert 'parse' in str(exc_info.value).lower()


def test_load_config_nonexistent_file_raises(tmp_path: Path) -> None:
    """A non-existent config path raises with the offending path.

    T-ID: codebase-analysis section 7.
    """
    path = tmp_path / 'does_not_exist.yaml'
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    assert 'does not exist' in str(exc_info.value)
    assert exc_info.value.file_path == path


def test_load_config_directory_path_raises(tmp_path: Path) -> None:
    """A directory passed as a config path is rejected.

    T-ID: codebase-analysis section 7.
    """
    with pytest.raises(ConfigError, match='not a regular file'):
        load_config([tmp_path])


@pytest.mark.skipif(os.name == 'nt', reason='POSIX permission bits required')
def test_load_config_unreadable_file_raises(tmp_path: Path) -> None:
    """An unreadable config file is rejected. T-ID: codebase-analysis section 7."""
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        pytest.skip('root bypasses file permission bits')
    path = _write_config(tmp_path, 'locked.yaml', _VALID_LABEL_CONTENTS)
    path.chmod(0o000)
    try:
        with pytest.raises(ConfigError, match='not readable'):
            load_config([path])
    finally:
        path.chmod(0o644)


# --- parse_sort_key (R-SORT-020) ------------------------------------------


def test_parse_sort_key_no_sign_defaults_ascending() -> None:
    """An unsigned key parses as ascending. T-ID: R-SORT-020."""
    assert parse_sort_key('lid') == ('lid', False)


def test_parse_sort_key_minus_descending() -> None:
    """A ``-`` prefix parses as descending. T-ID: R-SORT-020."""
    assert parse_sort_key('-lid') == ('lid', True)


def test_parse_sort_key_plus_ascending() -> None:
    """A ``+`` prefix parses as ascending. T-ID: R-SORT-020."""
    assert parse_sort_key('+lid') == ('lid', False)


def test_parse_sort_key_double_sign_rejected() -> None:
    """A doubled sign is rejected. T-ID: R-SORT-020."""
    with pytest.raises(ValueError, match='invalid sort key'):
        parse_sort_key('--lid')


def test_parse_sort_key_empty_rejected() -> None:
    """An empty sort key is rejected. T-ID: R-SORT-020."""
    with pytest.raises(ValueError, match='empty'):
        parse_sort_key('')


def test_load_config_invalid_sort_by_rejected(tmp_path: Path) -> None:
    """A malformed ``output.sort_by`` key is rejected during load.

    Exercises the config-integration path (``OutputSection._validate_sort_by``
    reaching :func:`parse_sort_key`), not just the standalone parser.
    T-ID: R-SORT-020.
    """
    content = _VALID_LABEL_CONTENTS + "output:\n  sort_by: ['--x']\n"
    path = _write_config(tmp_path, 'bad_sort.yaml', content)
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    message = str(exc_info.value)
    assert 'invalid sort key' in message
    assert "'--x'" in message


# --- Purity, path, and error-context sanity checks ------------------------


def test_load_config_relative_path_resolved_at_call_site(
    configs_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``load_config`` accepts whatever ``Path`` the caller resolves.

    T-ID: R-FS-001.
    """
    monkeypatch.chdir(configs_dir)
    config = load_config([Path('minimal.yaml').absolute()])
    assert isinstance(config, IndexConfig)
    assert config.label_contents.logical_identifier == 'urn:nasa:pds:test_bundle:test:test_index'


def test_load_config_error_includes_file_path_attribute(tmp_path: Path) -> None:
    """A raised :exc:`ConfigError` carries the offending YAML path.

    T-ID: spec error-model.
    """
    path = _write_config(tmp_path, 'bad.yaml', 'foo: [1, 2\n')
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    assert exc_info.value.file_path == path


def test_load_config_error_uses_raise_from(configs_dir: Path) -> None:
    """A validation failure chains the underlying ``ValidationError``.

    T-ID: python.mdc section 2.
    """
    from pydantic import ValidationError

    with pytest.raises(ConfigError) as exc_info:
        load_config([configs_dir / 'test_config_invalid_top.yaml'])
    assert isinstance(exc_info.value.__cause__, ValidationError)


def test_load_config_with_freezegun_mtime_unaffected(configs_dir: Path) -> None:
    """Loading the same config twice under different clocks is deterministic.

    T-ID: critique skill section 15.
    """
    from freezegun import freeze_time

    first = load_config([configs_dir / 'minimal.yaml'])
    with freeze_time('2030-01-01T00:00:00Z'):
        second = load_config([configs_dir / 'minimal.yaml'])
    assert first == second


# --- Columns schema (R-MAP-*, R-AUTO-001) ---------------------------------


def test_columns_missing_is_allowed_at_load(configs_dir: Path) -> None:
    """A config with no ``columns`` block loads with ``columns is None``.

    T-ID: spec-amendment 9.
    """
    config = load_config([configs_dir / 'minimal.yaml'])
    assert config.columns is None


def test_columns_empty_list_rejected(tmp_path: Path) -> None:
    """An explicitly empty ``columns`` list is rejected. T-ID: R-MAP-312."""
    content = _VALID_LABEL_CONTENTS + 'columns: []\n'
    path = _write_config(tmp_path, 'empty_cols.yaml', content)
    with pytest.raises(ConfigError, match='empty'):
        load_config([path])


@pytest.mark.parametrize(
    'columns_block',
    [
        '  - xpath: pds:A<1>\n    auto: lid\n',
        '  - name: NAMED\n',
    ],
    ids=['both-set', 'neither-set'],
)
def test_columns_entry_requires_exactly_one_selector(columns_block: str, tmp_path: Path) -> None:
    """Each entry sets exactly one of ``xpath``/``auto``, citing the index.

    T-ID: spec-amendment 9 (R-MAP-300).
    """
    content = _VALID_LABEL_CONTENTS + 'columns:\n  - auto: lid\n    name: OK\n' + columns_block
    path = _write_config(tmp_path, 'bad_selector.yaml', content)
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    message = str(exc_info.value)
    assert 'exactly one' in message
    assert 'columns.1' in message


def test_columns_unknown_auto_token_rejected(tmp_path: Path) -> None:
    """An unknown ``auto`` token is rejected naming the typo and valid tokens.

    T-ID: R-MAP-013 diagnostics.
    """
    content = _VALID_LABEL_CONTENTS + 'columns:\n  - auto: filenmae\n    name: X\n'
    path = _write_config(tmp_path, 'bad_auto.yaml', content)
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    message = str(exc_info.value)
    assert 'filenmae' in message
    assert ', '.join(sorted(AUTO_COLUMN_TOKENS)) in message


@pytest.mark.parametrize('token', ['lid', 'lidvid', 'filespec', 'filename', 'bundle_name'])
def test_columns_auto_all_five_accepted(token: str, tmp_path: Path) -> None:
    """All five auto-column tokens are accepted. T-ID: R-AUTO-001."""
    content = _VALID_LABEL_CONTENTS + f'columns:\n  - auto: {token}\n    name: X\n'
    path = _write_config(tmp_path, 'auto.yaml', content)
    config = load_config([path])
    assert config.columns is not None
    assert config.columns[0].auto == token


@pytest.mark.parametrize(
    ('columns_block', 'expected_header'),
    [
        ('columns:\n  - auto: lid\n', 'lid'),
        (
            'columns:\n  - xpath: pds:A<1>/pds:b<1>\n    name: "   "\n',
            'pds:A<1>/pds:b<1>',
        ),
    ],
    ids=['omitted-name', 'blank-name'],
)
def test_columns_name_defaults_to_selector(
    columns_block: str, expected_header: str, tmp_path: Path
) -> None:
    """An omitted or blank ``name`` falls back to the selector text.

    T-ID: R-MAP-012.1.
    """
    path = _write_config(tmp_path, 'defname.yaml', _VALID_LABEL_CONTENTS + columns_block)
    config = load_config([path])
    assert config.columns is not None
    assert config.columns[0].header == expected_header


@pytest.mark.parametrize(
    'columns_block',
    [
        'columns:\n  - xpath: pds:A<1>\n    name: A\n  - xpath: pds:A<1>\n    name: B\n',
        'columns:\n  - auto: lid\n    name: A\n  - auto: lid\n    name: B\n',
    ],
    ids=['dup-xpath', 'dup-auto'],
)
def test_columns_duplicate_selector_rejected(columns_block: str, tmp_path: Path) -> None:
    """Two entries with the same selector are rejected citing both indexes.

    T-ID: R-MAP-030.
    """
    path = _write_config(tmp_path, 'dupsel.yaml', _VALID_LABEL_CONTENTS + columns_block)
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    message = str(exc_info.value)
    # Assert the exact both-index phrasing the validator emits ("...in entries
    # 0 and 1") rather than the bare '1', which the 'pds:A<1>' selector text in
    # the dup-xpath case would satisfy vacuously.
    assert 'entries 0 and 1' in message


def test_columns_duplicate_name_rejected(tmp_path: Path) -> None:
    """Two entries resolving to the same header are rejected citing both indexes.

    T-ID: R-MAP-031.
    """
    columns_block = 'columns:\n  - auto: lid\n    name: SAME\n  - auto: filename\n    name: SAME\n'
    path = _write_config(tmp_path, 'dupname.yaml', _VALID_LABEL_CONTENTS + columns_block)
    with pytest.raises(ConfigError) as exc_info:
        load_config([path])
    message = str(exc_info.value)
    assert '0' in message
    assert '1' in message


@pytest.mark.parametrize(
    ('bad_name', 'expected_reason'),
    [
        ('has"quote', 'must not contain a double-quote'),
        ('has,comma', 'must not contain a comma'),
        ('ctrl\x07char', 'non-printable or non-ASCII character'),
        ('accenté', 'non-printable or non-ASCII character'),
    ],
    ids=['double-quote', 'comma', 'control', 'non-ascii'],
)
def test_columns_name_charset_enforced(bad_name: str, expected_reason: str, tmp_path: Path) -> None:
    """A ``name`` outside printable ASCII (or with comma/quote) is rejected.

    T-ID: R-MAP-043.
    """
    config_dict = {
        'label_contents': {
            'logical_identifier': 'urn:nasa:pds:test:test:test_index',
            'product_class': 'Product_Ancillary',
        },
        'columns': [{'auto': 'lid', 'name': bad_name}],
    }
    path = _write_config(tmp_path, 'badname.yaml', yaml.safe_dump(config_dict))
    with pytest.raises(ConfigError, match=expected_reason):
        load_config([path])


def test_columns_xpath_internal_whitespace_rejected(tmp_path: Path) -> None:
    """An ``xpath`` selector with internal whitespace is rejected.

    T-ID: R-MAP-040 analog.
    """
    content = _VALID_LABEL_CONTENTS + 'columns:\n  - xpath: "pds:A <1>"\n    name: X\n'
    path = _write_config(tmp_path, 'wsxpath.yaml', content)
    with pytest.raises(ConfigError, match='whitespace'):
        load_config([path])


def test_columns_entry_extra_key_rejected(tmp_path: Path) -> None:
    """An unknown per-column key is rejected by name. T-ID: future-proofing."""
    content = (
        _VALID_LABEL_CONTENTS + 'columns:\n  - xpath: pds:A<1>\n    name: X\n    frobnicate: 1\n'
    )
    path = _write_config(tmp_path, 'extracol.yaml', content)
    with pytest.raises(ConfigError, match='frobnicate'):
        load_config([path])


def test_columns_order_preserved(tmp_path: Path) -> None:
    """Column declaration order is preserved. T-ID: R-MAP-320."""
    columns_block = (
        'columns:\n'
        '  - auto: lid\n    name: FIRST\n'
        '  - auto: filename\n    name: SECOND\n'
        '  - xpath: pds:A<1>\n    name: THIRD\n'
    )
    path = _write_config(tmp_path, 'order.yaml', _VALID_LABEL_CONTENTS + columns_block)
    config = load_config([path])
    assert config.columns is not None
    assert [entry.header for entry in config.columns] == ['FIRST', 'SECOND', 'THIRD']


def test_columns_list_replaced_wholesale_on_merge(configs_dir: Path) -> None:
    """A later config replaces the ``columns`` list wholesale. T-ID: R-CFG-050."""
    config = load_config([configs_dir / 'simple.yaml', configs_dir / 'columns_only_lid.yaml'])
    assert config.columns is not None
    assert len(config.columns) == 1
