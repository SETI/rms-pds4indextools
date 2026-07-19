"""Integration tests for the ``generate_index_file`` pipeline (§11.2).

These exercise the full scrape-to-CSV-and-label pipeline against the
committed fixture bundles. Byte-golden tests run ``run_generate_index_file``
programmatically under ``frozen_time`` with a ``csv_post_write_hook`` that
freezes the CSV mtime, exactly mirroring the golden generator (Appendix I);
CLI byte tests go through ``main`` and mask only the single
``<creation_date_time>`` line. Every non-live test appends
``seeded_cache_overlay`` as the last config so schema resolution is
zero-network.
"""

import hashlib
import logging
import os
from pathlib import Path

import pytest
import responses

from pds4indextools import (
    GenerateIndexFileArgs,
    GenerateIndexFileResult,
    SchemaNetworkError,
    SchemaResolutionError,
)
from pds4indextools.cli import _runners as runners_mod
from pds4indextools.cli import main
from pds4indextools.errors import (
    ConfigError,
    FailSlowAggregateError,
    LidError,
    ParseError,
    SchemaVersionError,
    ScrapedValueError,
)

DATA = Path(__file__).resolve().parents[1] / 'data'
BUNDLES = DATA / 'bundles'
CONFIGS = DATA / 'configs'
EXPECTED = DATA / 'expected'

PDS_1L00_URL = 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd'


def _index_argv(
    bundle: Path,
    *patterns: str,
    configs: tuple[Path, ...],
    output_file: Path | None = None,
    extra: tuple[str, ...] = (),
) -> list[str]:
    """Assemble a ``generate_index_file`` argv list for ``main``."""
    argv = ['generate_index_file', '--bundle-root', str(bundle)]
    for config in configs:
        argv += ['--config-file', str(config)]
    if output_file is not None:
        argv += ['--output-file', str(output_file)]
    argv += list(extra)
    argv += list(patterns)
    return argv


def _run(
    bundle: str,
    configs: tuple[Path, ...],
    output_file: Path,
    *,
    fail_slow: bool = False,
    frozen_csv_mtime: int | None = None,
) -> GenerateIndexFileResult:
    """Run the index pipeline programmatically against a committed bundle."""
    hook = None
    if frozen_csv_mtime is not None:
        mtime = frozen_csv_mtime

        def hook(path: Path) -> None:
            os.utime(path, (mtime, mtime))

    return runners_mod.run_generate_index_file(
        GenerateIndexFileArgs(
            bundle_root=BUNDLES / bundle,
            patterns=('**/*.lblx',),
            config_files=configs,
            output_file=output_file,
            fail_slow=fail_slow,
            csv_post_write_hook=hook,
        )
    )


def _mask_creation_date(data: bytes) -> tuple[bytes, int]:
    """Drop every ``<creation_date_time>`` line; return the rest and the count."""
    lines = data.split(b'\n')
    count = sum(1 for line in lines if b'<creation_date_time>' in line)
    kept = b'\n'.join(line for line in lines if b'<creation_date_time>' not in line)
    return kept, count


def _write_label(directory: Path, name: str, *, lid: str, version_id: str | None) -> Path:
    """Write a minimal single-product label with the given LID/version."""
    body = f'        <logical_identifier>{lid}</logical_identifier>\n'
    if version_id is not None:
        body += f'        <version_id>{version_id}</version_id>\n'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"\n'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        ' xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 '
        f'{PDS_1L00_URL}">\n'
        '    <Identification_Area>\n'
        f'{body}'
        '    </Identification_Area>\n'
        '</Product_Observational>\n',
        encoding='utf-8',
    )
    return path


# --- Happy paths -------------------------------------------------------------


def test_simple_pds_only_happy_path(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """R-IDX-001, R-LBL-001, R-CSV-061: a single-label bundle writes CSV+label."""
    out = tmp_path / 'index.csv'
    result = _run('simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert result.rows_written == 1
    assert result.columns_written == 3
    assert out.is_file()
    assert out.with_suffix('.lblx').is_file()
    # The header row values are the ``name`` of each config columns entry (R-CSV-011).
    assert out.read_text(encoding='utf-8').splitlines()[0] == 'LID,FILE_NAME,TITLE'


def test_simple_pds_only_byte_identical_to_expected(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """Golden CSV+lblx comparison for the ``simple_pds_only`` bundle."""
    out = tmp_path / 'index.csv'
    _run(
        'simple_pds_only',
        (CONFIGS / 'simple.yaml', seeded_cache_overlay),
        out,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    assert out.read_bytes() == (EXPECTED / 'simple_pds_only' / 'index.csv').read_bytes()
    assert (
        out.with_suffix('.lblx').read_bytes()
        == (EXPECTED / 'simple_pds_only' / 'index.lblx').read_bytes()
    )


def test_default_output_paths_byte_golden(
    chdir_tmp: Path, frozen_time: None, data_root: Path, seeded_cache_overlay: Path
) -> None:
    """T-CLI-060 (bytes leg), R-CLI-015, R-LBL-080: default-path CLI output matches golden.

    The label carries exactly one ``<creation_date_time>`` line, produced by a
    PdsTemplate timestamp macro rather than any tool-computed value; masking it
    is what lets the rest of the label match golden byte-for-byte (R-LBL-080).
    """
    argv = _index_argv(
        BUNDLES / 'simple_pds_only',
        '**/*.lblx',
        configs=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
    )
    assert main(argv) == 0
    assert (chdir_tmp / 'index.csv').read_bytes() == (
        data_root / 'expected' / 'simple_pds_only' / 'index.csv'
    ).read_bytes()
    produced_masked, produced_count = _mask_creation_date((chdir_tmp / 'index.lblx').read_bytes())
    golden_masked, golden_count = _mask_creation_date(
        (data_root / 'expected' / 'simple_pds_only' / 'index.lblx').read_bytes()
    )
    assert produced_count == 1
    assert golden_count == 1
    assert produced_masked == golden_masked


def test_multi_namespace_three_labels_render_geom_and_rings_prefixes(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-XP-011, R-SCH-040, R-CSV-020: three labels resolve pds/geom/rings prefixes.

    One data row is written per scraped label, so a three-label bundle yields
    exactly three data rows (R-CSV-020).
    """
    out = tmp_path / 'index.csv'
    result = _run('multi_namespace', (CONFIGS / 'multi_namespace.yaml', seeded_cache_overlay), out)
    assert result.rows_written == 3
    assert out.read_bytes() == (EXPECTED / 'multi_namespace' / 'index.csv').read_bytes()
    text = out.read_text(encoding='utf-8')
    assert 'row_a_method' in text
    assert 'row_c_ring' in text


def test_nilled_label_substitutes_config_defaults(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-NIL-001, R-NIL-010, R-NIL-020: a nilled leaf takes the config default."""
    out = tmp_path / 'index.csv'
    _run('nilled', (CONFIGS / 'nilled.yaml', seeded_cache_overlay), out)
    assert out.read_text(encoding='utf-8').splitlines()[1].split(',')[1] == '0002-01-01'


# --- Renumbering ------------------------------------------------------------


def test_repeated_tags_renumbered_in_canonical_form(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """T-XP-020, R-XP-020: sibling blocks renumber to dense <1>,<2>,<3> keys.

    ``repeated_tags.yaml`` maps three columns (OS1/OS2/OS3) at the
    renumbered ``pds:Observing_System<1..3>/pds:name<1>`` XPaths; a
    byte-golden comparison through the full pipeline proves the canonical
    renumbering feeds the CSV and label.
    """
    out = tmp_path / 'index.csv'
    _run(
        'repeated_tags',
        (CONFIGS / 'repeated_tags.yaml', seeded_cache_overlay),
        out,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    # The data-row field order matches the header order column for column
    # (R-CSV-021): header LID,OS1,OS2,OS3 aligns with the data cells below it.
    assert out.read_text(encoding='utf-8').splitlines() == [
        'LID,OS1,OS2,OS3',
        'urn:nasa:pds:test_rep:index:row1,OS_1,OS_2,OS_3',
    ]
    assert out.read_bytes() == (EXPECTED / 'repeated_tags' / 'index.csv').read_bytes()
    assert (
        out.with_suffix('.lblx').read_bytes()
        == (EXPECTED / 'repeated_tags' / 'index.lblx').read_bytes()
    )


# --- Failure paths that abort the run ----------------------------------------


def test_nilled_bad_nilreason_aborts_with_exit_2(
    seeded_cache_overlay: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-NIL-010, R-NIL-010: an unrecognized nilReason aborts with exit 2."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    argv = _index_argv(
        BUNDLES / 'nilled_bad', '**/*.lblx', configs=(CONFIGS / 'nilled.yaml', seeded_cache_overlay)
    )
    assert main(argv) == 2
    assert 'bogus' in caplog.text


def test_multi_lid_two_labels_share_lid_aborts_with_exit_2(
    seeded_cache_overlay: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-LID-050, R-LID-020: two labels sharing a LID abort with exit 2."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    argv = _index_argv(
        BUNDLES / 'multi_lid', '**/*.lblx', configs=(CONFIGS / 'simple.yaml', seeded_cache_overlay)
    )
    assert main(argv) == 2
    assert 'duplicate LID' in caplog.text


def test_multi_lid_under_failslow_aborts_before_write(
    seeded_cache_overlay: Path, chdir_tmp: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-LID-051, R-LID-020, R-FSLOW-110/120: fail-slow still aborts, no output."""
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    argv = _index_argv(
        BUNDLES / 'multi_lid',
        '**/*.lblx',
        configs=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
        extra=('--fail-slow',),
    )
    assert main(argv) == 2
    assert not (chdir_tmp / 'index.csv').exists()
    assert not (chdir_tmp / 'index.lblx').exists()


def test_bom_label_rejected_with_parseerror(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """R-PARSE-001: a UTF-8 BOM label is rejected with ParseError."""
    with pytest.raises(ParseError, match='BOM'):
        _run('bom', (CONFIGS / 'simple.yaml', seeded_cache_overlay), tmp_path / 'index.csv')


def test_non_ascii_value_label_rejected_with_scrapedvalueerror(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-CSV-040, R-VAL-030: a non-ASCII value is rejected with ScrapedValueError."""
    with pytest.raises(ScrapedValueError, match='non-ASCII'):
        _run(
            'non_ascii_value',
            (CONFIGS / 'simple.yaml', seeded_cache_overlay),
            tmp_path / 'index.csv',
        )


def test_quote_in_value_variable_width_rejected(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """R-VAL-040: a quote in a variable-width value is rejected."""
    with pytest.raises(ScrapedValueError):
        _run(
            'quote_in_value',
            (CONFIGS / 'quote_in_value_var.yaml', seeded_cache_overlay),
            tmp_path / 'index.csv',
        )


def test_quote_in_value_fixed_width_passes_through(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """R-VAL-040: a quote in a fixed-width value passes through unquoted."""
    out = tmp_path / 'index.csv'
    _run(
        'quote_in_value',
        (CONFIGS / 'quote_in_value_fixed.yaml', seeded_cache_overlay),
        out,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    assert out.read_bytes() == (EXPECTED / 'quote_in_value' / 'index.csv').read_bytes()
    assert 'R"ow 1' in out.read_text(encoding='utf-8')


def test_version_mismatch_two_labels_aborts(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """T-SCH-020, R-SCH-040: two labels binding a namespace to differing URLs abort."""
    with pytest.raises(SchemaVersionError, match='already bound'):
        _run(
            'version_mismatch',
            (CONFIGS / 'simple.yaml', seeded_cache_overlay),
            tmp_path / 'index.csv',
        )


def test_no_schema_location_label_raises_schemaresolutionerror(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-SCH-030, R-SCH-050: a label without xsi:schemaLocation is rejected."""
    with pytest.raises(SchemaResolutionError, match='schemaLocation'):
        _run(
            'no_schema_location',
            (CONFIGS / 'simple.yaml', seeded_cache_overlay),
            tmp_path / 'index.csv',
        )


# --- Fixed-width / line-ending features --------------------------------------


def test_fixed_width_config_byte_identical_to_expected(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """R-CSV-070, R-CSV-071: the fixed-width run matches the golden bytes."""
    out = tmp_path / 'index.csv'
    _run(
        'simple_pds_only',
        (CONFIGS / 'fixed_width.yaml', seeded_cache_overlay),
        out,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    assert out.read_bytes() == (EXPECTED / 'fixed_width' / 'index.csv').read_bytes()
    assert (
        out.with_suffix('.lblx').read_bytes()
        == (EXPECTED / 'fixed_width' / 'index.lblx').read_bytes()
    )


def test_fixed_width_lblx_uses_table_character(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """R-LBL-020, R-LBL-060: the fixed-width label uses Table_Character fields."""
    out = tmp_path / 'index.csv'
    _run('simple_pds_only', (CONFIGS / 'fixed_width.yaml', seeded_cache_overlay), out)
    label = out.with_suffix('.lblx').read_text(encoding='utf-8')
    assert '<Table_Character>' in label
    assert '<record_length unit="byte">' in label
    assert '<field_location unit="byte">' in label
    assert '<field_length unit="byte">' in label


def test_crlf_config_writes_crlf_csv_and_label_record_delimiter(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """T-CSV-030, R-CSV-003, R-LBL-060: CRLF config writes CRLF CSV and label."""
    out = tmp_path / 'index.csv'
    _run(
        'simple_pds_only',
        (CONFIGS / 'crlf.yaml', seeded_cache_overlay),
        out,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    assert out.read_bytes() == (EXPECTED / 'crlf' / 'index.csv').read_bytes()
    assert b'\r\n' in out.read_bytes()
    assert '<record_delimiter>Carriage-Return Line-Feed</record_delimiter>' in (
        out.with_suffix('.lblx').read_text(encoding='utf-8')
    )


def test_lf_config_writes_lf_record_delimiter(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """T-CSV-031, R-LBL-060: the default LF config writes an LF record delimiter."""
    out = tmp_path / 'index.csv'
    _run('simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert b'\r\n' not in out.read_bytes()
    assert '<record_delimiter>Line-Feed</record_delimiter>' in (
        out.with_suffix('.lblx').read_text(encoding='utf-8')
    )


def test_multi_config_three_yamls_merge_in_order(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """T-CFG-040, R-CFG-050, R-CFG-051: three configs merge in order to the golden."""
    out = tmp_path / 'index.csv'
    _run(
        'simple_pds_only',
        (
            CONFIGS / 'multi_config_a.yaml',
            CONFIGS / 'multi_config_b.yaml',
            CONFIGS / 'multi_config_c.yaml',
            seeded_cache_overlay,
        ),
        out,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    assert out.read_bytes() == (EXPECTED / 'multi_config' / 'index.csv').read_bytes()
    assert b'\r\n' not in out.read_bytes()


# --- Column mapping ----------------------------------------------------------


def test_mapping_full_features_byte_identical_to_expected_csv(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """T-MAP-090, R-MAP-300/320, R-AUTO-010: every columns-entry shape matches golden."""
    out = tmp_path / 'index.csv'
    _run(
        'multi_namespace',
        (CONFIGS / 'mapping_full_features.yaml', seeded_cache_overlay),
        out,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    assert out.read_bytes() == (EXPECTED / 'mapping_full_features' / 'index.csv').read_bytes()


def test_mapping_xpath_not_in_any_label_produces_empty_column(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-MAP-080, T-NIL-040, R-MAP-311, R-MISS-010: an absent XPath yields empty cells.

    The committed ``xpath_not_in_label.yaml`` targets ``pds:description``,
    which the seed XSD types successfully but which is absent from every
    ``multi_namespace`` label, so the missing-value path is exercised
    faithfully through the full pipeline.
    """
    out = tmp_path / 'index.csv'
    _run(
        'multi_namespace',
        (
            CONFIGS / 'multi_namespace.yaml',
            CONFIGS / 'xpath_not_in_label.yaml',
            seeded_cache_overlay,
        ),
        out,
    )
    lines = out.read_text(encoding='utf-8').splitlines()
    assert lines[0] == 'LID,GONE'
    assert all(line.endswith(',') for line in lines[1:])
    assert len(lines) == 4


def test_missing_xpath_empty_even_when_present_in_another_label(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-MISS-020: a label missing a mapped XPath yields an empty cell even when
    another label in the same run supplies that XPath.

    Two labels are scraped: ``a_with_title.lblx`` carries a ``title`` element,
    ``b_no_title.lblx`` omits it. ``simple.yaml`` maps ``title`` to the TITLE
    column. The row for the title-less label must be empty in TITLE despite the
    other row supplying a value for the same XPath.
    """
    bundle = tmp_path / 'bundle'
    bundle.mkdir()

    def _label(name: str, lid: str, *, title: str | None) -> None:
        title_line = f'        <title>{title}</title>\n' if title is not None else ''
        (bundle / name).write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"\n'
            ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
            ' xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 '
            f'{PDS_1L00_URL}">\n'
            '    <Identification_Area>\n'
            f'        <logical_identifier>{lid}</logical_identifier>\n'
            '        <version_id>1.0</version_id>\n'
            f'{title_line}'
            '    </Identification_Area>\n'
            '</Product_Observational>\n',
            encoding='utf-8',
        )

    _label('a_with_title.lblx', 'urn:nasa:pds:t:c:a', title='Present')
    _label('b_no_title.lblx', 'urn:nasa:pds:t:c:b', title=None)
    out = tmp_path / 'index.csv'
    runners_mod.run_generate_index_file(
        GenerateIndexFileArgs(
            bundle_root=bundle,
            patterns=('**/*.lblx',),
            config_files=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
            output_file=out,
        )
    )
    lines = out.read_text(encoding='utf-8').splitlines()
    assert lines[0] == 'LID,FILE_NAME,TITLE'
    assert lines[1] == 'urn:nasa:pds:t:c:a,a_with_title.lblx,Present'
    assert lines[2] == 'urn:nasa:pds:t:c:b,b_no_title.lblx,'


def test_columns_not_listing_an_observed_xpath_drops_it(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-MAP-081, R-MAP-310: an observed XPath absent from columns is dropped."""
    out = tmp_path / 'index.csv'
    result = _run(
        'simple_pds_only',
        (CONFIGS / 'simple.yaml', CONFIGS / 'columns_only_lid.yaml', seeded_cache_overlay),
        out,
    )
    data = out.read_bytes()
    assert data.split(b'\n', 1)[0] + b'\n' == b'LID\n'
    rows = out.read_text(encoding='utf-8').splitlines()[1:]
    assert len(rows) == 1
    assert ',' not in rows[0]
    assert result.columns_written == 1
    assert b'Row 1' not in data
    assert b'1.0' not in data


def test_missing_columns_exits_1_with_guidance(
    seeded_cache_overlay: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Owner decision #10: a config chain with no columns exits 1 with guidance."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    argv = _index_argv(
        BUNDLES / 'simple_pds_only',
        '**/*.lblx',
        configs=(CONFIGS / 'minimal.yaml', seeded_cache_overlay),
    )
    assert main(argv) == 1
    assert 'no columns defined' in caplog.text
    assert 'generate_xpath_list' in caplog.text


def test_empty_columns_list_aborts(
    seeded_cache_overlay: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-MAP-082, R-MAP-312: an empty ``columns`` list aborts at config load."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    overlay = tmp_path / 'empty_columns.yaml'
    overlay.write_text('columns: []\n', encoding='utf-8')
    argv = _index_argv(
        BUNDLES / 'simple_pds_only',
        '**/*.lblx',
        configs=(CONFIGS / 'simple.yaml', overlay, seeded_cache_overlay),
    )
    assert main(argv) == 1
    assert 'columns list must not be empty' in caplog.text


# --- Programmatic API surface ------------------------------------------------


def test_run_generate_index_file_programmatic_returns_result(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-API-003: the runner returns a populated result dataclass."""
    out = tmp_path / 'index.csv'
    result = _run('simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert isinstance(result, GenerateIndexFileResult)
    assert result.csv_path == out.resolve()
    # The label path is ``<csv_stem>.lblx`` next to the CSV (R-LBL-050).
    assert result.label_path == out.with_suffix('.lblx').resolve()
    assert result.rows_written == 1
    assert result.columns_written == 3
    assert result.warnings == ()


def test_run_generate_index_file_programmatic_raises_failslowaggregateerror(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-FSLOW-004, R-API-004: fail-slow with two bad LIDs raises an aggregate."""
    bundle = tmp_path / 'bundle'
    _write_label(bundle, 'a.lblx', lid='not-a-urn', version_id='1.0')
    _write_label(bundle, 'b.lblx', lid='also-bad', version_id='1.0')
    with pytest.raises(FailSlowAggregateError) as exc_info:
        runners_mod.run_generate_index_file(
            GenerateIndexFileArgs(
                bundle_root=bundle,
                patterns=('**/*.lblx',),
                config_files=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
                output_file=tmp_path / 'index.csv',
                fail_slow=True,
            )
        )
    assert len(exc_info.value.errors) == 2


def test_run_generate_index_file_programmatic_success_warnings_overwrite_only(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-FSLOW-005, R-API-004: a successful overwrite reports only a warning."""
    out = tmp_path / 'index.csv'
    out.write_bytes(b'OLD')
    result = _run('simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert len(result.warnings) == 1
    assert 'overwriting' in result.warnings[0]
    assert out.read_text(encoding='utf-8').splitlines()[0] == 'LID,FILE_NAME,TITLE'


def test_run_generate_index_file_keyboardinterrupt_propagates_with_temp_cleanup(
    seeded_cache_overlay: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-FSLOW-020, R-ERR-002: a KeyboardInterrupt propagates leaving no output."""

    def _boom(*args: object, **kwargs: object) -> object:
        raise KeyboardInterrupt

    monkeypatch.setattr(runners_mod, 'scrape_label', _boom)
    out = tmp_path / 'index.csv'
    with pytest.raises(KeyboardInterrupt):
        _run('simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert not out.exists()
    assert not out.with_suffix('.lblx').exists()


def test_generate_index_file_with_fixed_width_renders_label_table_character(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-LBL product-class booleans: fixed width renders a Table_Character label."""
    out = tmp_path / 'index.csv'
    _run('simple_pds_only', (CONFIGS / 'fixed_width.yaml', seeded_cache_overlay), out)
    label = out.with_suffix('.lblx').read_text(encoding='utf-8')
    assert '<Table_Character>' in label
    assert '<Table_Delimited>' not in label
    assert '<product_class>Product_Ancillary</product_class>' in label


# --- Progress bar / cache reuse ----------------------------------------------


def test_progress_bar_disabled_in_non_tty(
    seeded_cache_overlay: Path,
    tmp_path: Path,
    deterministic_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R-LOG-020, R-LOG-021: a non-TTY run emits no progress-bar control bytes."""
    _run(
        'multi_namespace',
        (CONFIGS / 'multi_namespace.yaml', seeded_cache_overlay),
        tmp_path / 'index.csv',
    )
    err = capsys.readouterr().err
    assert '\r' not in err
    assert '%|' not in err


@responses.activate
def test_no_xsd_redownload_within_session(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """R-SCH-020, R-TST-021: two runs hit the seeded cache with zero downloads."""
    for index in range(2):
        _run(
            'multi_namespace',
            (CONFIGS / 'multi_namespace.yaml', seeded_cache_overlay),
            tmp_path / f'index_{index}.csv',
        )
    assert len(responses.calls) == 0


# --- md5 / record-delimiter consistency --------------------------------------


def test_generate_index_file_md5_matches_csv(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """T-LBL-050, R-LBL-070: the label md5_checksum matches the CSV bytes."""
    out = tmp_path / 'index.csv'
    _run('simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    digest = hashlib.md5(out.read_bytes()).hexdigest()
    assert f'<md5_checksum>{digest}</md5_checksum>' in (
        out.with_suffix('.lblx').read_text(encoding='utf-8')
    )


def test_generate_index_file_record_delimiter_matches_csv_bytes_lf(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-LBL-060, R-LBL-060: an LF CSV declares a Line-Feed record delimiter."""
    out = tmp_path / 'index.csv'
    _run('simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert b'\r\n' not in out.read_bytes()
    assert '<record_delimiter>Line-Feed</record_delimiter>' in (
        out.with_suffix('.lblx').read_text(encoding='utf-8')
    )


def test_generate_index_file_record_delimiter_matches_csv_bytes_crlf(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-LBL-060, R-LBL-060: a CRLF CSV declares a Carriage-Return Line-Feed delimiter."""
    out = tmp_path / 'index.csv'
    _run('simple_pds_only', (CONFIGS / 'crlf.yaml', seeded_cache_overlay), out)
    assert b'\r\n' in out.read_bytes()
    assert '<record_delimiter>Carriage-Return Line-Feed</record_delimiter>' in (
        out.with_suffix('.lblx').read_text(encoding='utf-8')
    )


# --- Fail-fast / fail-slow accumulation --------------------------------------


def test_single_bad_lid_fail_fast_exits_2_no_output(
    seeded_cache_overlay: Path, chdir_tmp: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-FSLOW-001, R-ERR-001: one bad LID aborts fail-fast with no output."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    bundle = chdir_tmp / 'bundle'
    _write_label(bundle, 'a.lblx', lid='not-a-urn', version_id='1.0')
    argv = _index_argv(bundle, '**/*.lblx', configs=(CONFIGS / 'simple.yaml', seeded_cache_overlay))
    assert main(argv) == 2
    assert not (chdir_tmp / 'index.csv').exists()
    assert not (chdir_tmp / 'index.lblx').exists()


def test_three_bad_lids_fail_slow_accumulates_three(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """T-FSLOW-002, R-FSLOW-110/120: three bad LIDs accumulate to an aggregate of 3."""
    bundle = chdir_tmp / 'bundle'
    for name in ('a.lblx', 'b.lblx', 'c.lblx'):
        _write_label(bundle, name, lid='not-a-urn', version_id='1.0')
    with pytest.raises(FailSlowAggregateError) as exc_info:
        runners_mod.run_generate_index_file(
            GenerateIndexFileArgs(
                bundle_root=bundle,
                patterns=('**/*.lblx',),
                config_files=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
                output_file=chdir_tmp / 'index.csv',
                fail_slow=True,
            )
        )
    assert len(exc_info.value.errors) == 3
    assert not (chdir_tmp / 'index.csv').exists()


def test_bad_lid_and_missing_version_id_accumulated_under_fail_slow(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-LID-040, R-FSLOW-110/120: a bad LID and a missing version_id accumulate."""
    bundle = tmp_path / 'bundle'
    _write_label(bundle, 'a.lblx', lid='not-a-urn', version_id='1.0')
    _write_label(bundle, 'b.lblx', lid='urn:nasa:pds:t:c:p', version_id=None)
    with pytest.raises(FailSlowAggregateError) as exc_info:
        runners_mod.run_generate_index_file(
            GenerateIndexFileArgs(
                bundle_root=bundle,
                patterns=('**/*.lblx',),
                config_files=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
                output_file=tmp_path / 'index.csv',
                fail_slow=True,
            )
        )
    assert len(exc_info.value.errors) == 2
    assert all(isinstance(err, LidError) for err in exc_info.value.errors)


def test_fail_slow_all_good_writes_normally(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None, frozen_csv_mtime: int
) -> None:
    """T-FSLOW-003, R-FSLOW-130: an all-good fail-slow run matches the normal run."""
    normal_dir = tmp_path / 'normal'
    slow_dir = tmp_path / 'slow'
    normal_dir.mkdir()
    slow_dir.mkdir()
    normal = normal_dir / 'index.csv'
    slow = slow_dir / 'index.csv'
    _run(
        'simple_pds_only',
        (CONFIGS / 'simple.yaml', seeded_cache_overlay),
        normal,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    _run(
        'simple_pds_only',
        (CONFIGS / 'simple.yaml', seeded_cache_overlay),
        slow,
        fail_slow=True,
        frozen_csv_mtime=frozen_csv_mtime,
    )
    assert slow.read_bytes() == normal.read_bytes()
    assert slow.with_suffix('.lblx').read_bytes() == normal.with_suffix('.lblx').read_bytes()


def test_network_failure_not_masked_by_fail_slow(tmp_path: Path) -> None:
    """T-FSLOW-010, R-SCH-060, R-FSLOW-100: a network error is not collected by fail-slow."""
    empty_cache = tmp_path / 'empty_cache'
    empty_cache.mkdir()
    overlay = tmp_path / 'empty_cache_overlay.yaml'
    overlay.write_text(f'xsd_cache_dir: {empty_cache}\n', encoding='utf-8')
    with responses.RequestsMock() as mock:
        mock.add(responses.GET, PDS_1L00_URL, status=500)
        with pytest.raises(SchemaNetworkError):
            runners_mod.run_generate_index_file(
                GenerateIndexFileArgs(
                    bundle_root=BUNDLES / 'simple_pds_only',
                    patterns=('**/*.lblx',),
                    config_files=(CONFIGS / 'simple.yaml', overlay),
                    output_file=tmp_path / 'index.csv',
                    fail_slow=True,
                )
            )


def test_non_ascii_value_under_fail_slow_accumulates_then_aborts(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """T-CSV-041, R-FSLOW-110/120: a non-ASCII value accumulates then aborts, no output."""
    with pytest.raises(FailSlowAggregateError) as exc_info:
        runners_mod.run_generate_index_file(
            GenerateIndexFileArgs(
                bundle_root=BUNDLES / 'non_ascii_value',
                patterns=('**/*.lblx',),
                config_files=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
                output_file=chdir_tmp / 'index.csv',
                fail_slow=True,
            )
        )
    assert any(isinstance(err, ScrapedValueError) for err in exc_info.value.errors)
    assert not (chdir_tmp / 'index.csv').exists()


# --- Sorting -----------------------------------------------------------------


def _sort_overlay(tmp_path: Path, keys: str) -> Path:
    """Write a tmp overlay setting ``output.sort_by`` to ``keys``."""
    overlay = tmp_path / 'sort_overlay.yaml'
    overlay.write_text(f'output:\n  sort_by: [{keys}]\n', encoding='utf-8')
    return overlay


def test_sort_by_lid_ascending(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """T-CSV-060: sort_by ['LID'] orders rows by LID ascending."""
    overlay = _sort_overlay(tmp_path, "'LID'")
    out = tmp_path / 'index.csv'
    _run('multi_namespace', (CONFIGS / 'multi_namespace.yaml', overlay, seeded_cache_overlay), out)
    lids = [line.split(',')[0] for line in out.read_text(encoding='utf-8').splitlines()[1:]]
    assert lids == sorted(lids)


def test_sort_by_lid_descending(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """T-CSV-060: sort_by ['-LID'] orders rows by LID descending."""
    overlay = _sort_overlay(tmp_path, "'-LID'")
    out = tmp_path / 'index.csv'
    _run('multi_namespace', (CONFIGS / 'multi_namespace.yaml', overlay, seeded_cache_overlay), out)
    lids = [line.split(',')[0] for line in out.read_text(encoding='utf-8').splitlines()[1:]]
    assert lids == sorted(lids, reverse=True)


def test_sort_by_unknown_column_aborts_with_configerror(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-CSV-061, R-SORT-020: sort_by naming an unknown column aborts."""
    overlay = _sort_overlay(tmp_path, "'unknown'")
    with pytest.raises(ConfigError, match='unknown column'):
        _run(
            'multi_namespace',
            (CONFIGS / 'multi_namespace.yaml', overlay, seeded_cache_overlay),
            tmp_path / 'index.csv',
        )
