"""Unit tests for the ``pds4indextools.cli`` package (Phase 10, §10.4).

These tests invoke :func:`pds4indextools.cli.main` in-process and exercise
the programmatic ``run_*`` entry points directly. Argparse ``SystemExit``
and help text are captured with ``capsys`` (argparse writes to
``sys.stderr`` directly); logger content is captured with ``caplog`` at the
``pds4indextools`` namespace, matching the ``_handle_exception`` body which
routes every error message through the logging handler (critique skill §21).
"""

import dataclasses
import logging
import os
import sys
from pathlib import Path

import pytest

from pds4indextools.cli import (
    CopyDefaultConfigResult,
    GenerateIndexFileArgs,
    GenerateIndexFileResult,
    GenerateXpathListArgs,
    GenerateXpathListResult,
    cli_entrypoint,
    main,
    run_generate_index_file,
    run_generate_xpath_list,
)
from pds4indextools.cli import _dispatch as dispatch_mod
from pds4indextools.cli import _runners as runners_mod
from pds4indextools.errors import (
    CliError,
    ConfigError,
    FailSlowAggregateError,
    LabelError,
    LidError,
    OutputError,
    ParseError,
    Pds4IndexError,
    SchemaError,
)
from pds4indextools.label_writer import build_substitution_dict
from pds4indextools.scraper import ScrapeResult

TESTS_DIR = Path(__file__).resolve().parents[1]
DATA = TESTS_DIR / 'data'
CONFIGS = DATA / 'configs'
BUNDLES = DATA / 'bundles'
SIMPLE_BUNDLE = BUNDLES / 'simple_pds_only'
MULTI_BUNDLE = BUNDLES / 'multi_namespace'
SIMPLE_CFG = CONFIGS / 'simple.yaml'


@pytest.fixture(autouse=True)
def _reset_pkg_logger() -> None:
    """Clear the package logger's handlers so each test binds a fresh stream.

    ``setup_logging`` is idempotent and never re-points its stream handler,
    so a handler attached during an earlier test would still target that
    test's captured ``sys.stderr``. Clearing before every test forces
    ``main`` to attach a handler bound to the current ``capsys`` buffer.
    """
    logging.getLogger('pds4indextools').handlers.clear()


def _index_argv(
    bundle_root: Path,
    *patterns: str,
    config_files: tuple[Path, ...] = (),
    output_file: Path | None = None,
    extra: tuple[str, ...] = (),
) -> list[str]:
    """Assemble a ``generate_index_file`` argv list for ``main``."""
    argv = ['generate_index_file', '--bundle-root', str(bundle_root)]
    for config_file in config_files:
        argv += ['--config-file', str(config_file)]
    if output_file is not None:
        argv += ['--output-file', str(output_file)]
    argv += list(extra)
    argv += list(patterns)
    return argv


def _dummy_scrape_result(label_path: Path) -> ScrapeResult:
    """Return a minimal, valid :class:`ScrapeResult` for monkeypatched scrapes."""
    return ScrapeResult(
        label_path=label_path,
        canonical_root_tag='pds:Product_Observational',
        rows={},
        auto_columns={
            'lid': 'urn:x',
            'lidvid': 'urn:x::1.0',
            'filespec': label_path.name,
            'filename': label_path.name,
            'bundle_name': 'x',
        },
        lid='urn:nasa:pds:x:y:z',
        version_id='1.0',
        namespaces={},
        schema_urls=(),
    )


# ---------------------------------------------------------------------------
# Version, no-subcommand, aliases
# ---------------------------------------------------------------------------


def test_version_flag_prints_version_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-001, R-CLI-003: ``--version`` prints the version and exits 0."""
    from pds4indextools import __version__

    assert main(['--version']) == 0
    out = capsys.readouterr().out
    assert 'pds4_create_xml_index' in out
    assert __version__ in out


def test_no_subcommand_exits_2_and_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-002, R-CLI-005: no subcommand prints help to stderr and exits 2."""
    assert main([]) == 2
    assert 'usage:' in capsys.readouterr().err


def test_subcommand_underscore_form_accepted(capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-003, R-CLI-002: the underscored subcommand name is accepted."""
    assert main(['generate_index_file', '--help']) == 0
    assert 'usage:' in capsys.readouterr().out


def test_subcommand_hyphen_form_accepted(capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-003, R-CLI-002: the hyphenated subcommand alias is accepted."""
    assert main(['generate-index-file', '--help']) == 0
    assert 'usage:' in capsys.readouterr().out


def test_subcommand_underscore_and_hyphen_produce_identical_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T-CLI-003, R-CLI-002: both spellings render identical help text."""
    assert main(['generate_index_file', '--help']) == 0
    out_underscore = capsys.readouterr().out
    assert main(['generate-index-file', '--help']) == 0
    out_hyphen = capsys.readouterr().out
    assert out_underscore == out_hyphen


@pytest.mark.parametrize('name', ['generate_xpath_list', 'generate-xpath-list'])
def test_xpathlist_underscore_and_hyphen_accepted(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """T-CLI-004, R-CLI-002: both spellings of ``generate_xpath_list`` parse."""
    assert main([name, '--help']) == 0
    assert 'usage:' in capsys.readouterr().out


@pytest.mark.parametrize('name', ['copy_default_config', 'copy-default-config'])
def test_copy_default_config_underscore_and_hyphen_accepted(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """T-CLI-005, R-CLI-002: both spellings of ``copy_default_config`` parse."""
    assert main([name, '--help']) == 0
    assert 'usage:' in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Bundle and pattern validation
# ---------------------------------------------------------------------------


def test_generate_index_file_no_bundle_root_exits_2_argparse(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T-CLI-010: a missing ``--bundle-root`` is an argparse error (exit 2)."""
    assert main(['generate_index_file', 'somepattern']) == 2
    assert 'bundle-root' in capsys.readouterr().err


def test_generate_index_file_nonexistent_bundle_exits_1(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-CLI-011, R-CLI-010: a nonexistent bundle path exits 1."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    assert main(_index_argv(tmp_path / 'nope', 'x')) == 1


def test_generate_index_file_bundle_root_is_file_exits_1(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-CLI-012: a ``--bundle-root`` pointing at a regular file exits 1."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    afile = tmp_path / 'afile'
    afile.write_text('x', encoding='utf-8')
    assert main(_index_argv(afile, 'x')) == 1


def test_generate_index_file_bundle_root_symlink_to_dir_works(
    seeded_cache_overlay: Path, chdir_tmp: Path, tmp_path: Path
) -> None:
    """T-CLI-013, R-FS-002: a symlink to a directory is followed and works."""
    link = tmp_path / 'bundle_link'
    link.symlink_to(SIMPLE_BUNDLE, target_is_directory=True)
    argv = _index_argv(link, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 0


def test_two_patterns_dedup_to_one_row(seeded_cache_overlay: Path, chdir_tmp: Path) -> None:
    """T-CLI-020, R-FS-004: two patterns matching one file yield one row."""
    argv = _index_argv(
        SIMPLE_BUNDLE,
        'row1.lblx',
        '**/*.lblx',
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
    )
    assert main(argv) == 0
    lines = (chdir_tmp / 'index.csv').read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2  # header + one data row


def test_empty_pattern_union_exits_1(caplog: pytest.LogCaptureFixture) -> None:
    """T-CLI-021, R-DISC-010: an empty pattern union exits 1 and lists patterns."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    assert main(_index_argv(SIMPLE_BUNDLE, 'nomatch1*.zzz', 'nomatch2*.zzz')) == 1
    assert 'nomatch1' in caplog.text
    assert 'nomatch2' in caplog.text


@pytest.mark.skipif(os.name == 'nt', reason='POSIX absolute-path semantics')
def test_absolute_posix_pattern_rejected(caplog: pytest.LogCaptureFixture) -> None:
    """T-CLI-022 (POSIX leg), R-CLI-011: an absolute pattern is rejected."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    assert main(_index_argv(SIMPLE_BUNDLE, '/abs/path/*.lblx')) == 1
    assert 'relative' in caplog.text


@pytest.mark.skipif(os.name != 'nt', reason='Windows absolute-path semantics')
def test_absolute_windows_pattern_rejected(caplog: pytest.LogCaptureFixture) -> None:
    """T-CLI-022 (Windows leg), R-CLI-011: a drive-absolute pattern is rejected."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    assert main(_index_argv(SIMPLE_BUNDLE, r'C:\abs\path\*.lblx')) == 1
    assert 'relative' in caplog.text


# ---------------------------------------------------------------------------
# Config chain and columns
# ---------------------------------------------------------------------------


def test_three_config_files_merged_in_order(
    seeded_cache_overlay: Path, chdir_tmp: Path, tmp_path: Path
) -> None:
    """T-CLI-030, R-CFG-051: the last config file in the chain wins."""
    label_contents = (
        'label_contents:\n'
        '  logical_identifier: urn:nasa:pds:test_simple:index:index\n'
        '  product_class: Product_Ancillary\n'
        "  version_id: '1.0'\n"
        '  title: T\n'
    )
    title_xpath = 'pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>'
    c1 = tmp_path / 'c1.yaml'
    c1.write_text(label_contents + 'columns:\n  - {auto: lid, name: LID}\n', encoding='utf-8')
    c2 = tmp_path / 'c2.yaml'
    c2.write_text(
        'columns:\n  - {auto: lid, name: LID}\n  - {auto: filename, name: FN}\n',
        encoding='utf-8',
    )
    c3 = tmp_path / 'c3.yaml'
    c3.write_text(
        'columns:\n'
        '  - {auto: lid, name: LID}\n'
        '  - {auto: filename, name: FN}\n'
        f"  - {{xpath: '{title_xpath}', name: TITLE}}\n",
        encoding='utf-8',
    )
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(c1, c2, c3, seeded_cache_overlay))
    assert main(argv) == 0
    header = (chdir_tmp / 'index.csv').read_text(encoding='utf-8').splitlines()[0]
    assert header == 'LID,FN,TITLE'


def test_generate_index_file_without_columns_exits_1(caplog: pytest.LogCaptureFixture) -> None:
    """Owner decision #10: a config chain with no columns exits 1."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(CONFIGS / 'minimal.yaml',))
    assert main(argv) == 1
    assert 'no columns defined' in caplog.text
    assert 'generate_xpath_list' in caplog.text


# ---------------------------------------------------------------------------
# Label template
# ---------------------------------------------------------------------------


def test_label_template_default_packaged_path_used(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """T-CLI-050, R-CLI-014, R-LBL-001: the packaged template is used by default."""
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 0
    label_text = (chdir_tmp / 'index.lblx').read_text(encoding='utf-8')
    assert 'information_model_version' in label_text


def test_custom_label_template_honored(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """T-LBL-002, R-LBL-002: a supplied ``--label-template`` is rendered."""
    template = tmp_path / 'custom.xml'
    template.write_text('CUSTOM-TEMPLATE-SENTINEL\n', encoding='utf-8')
    out = tmp_path / 'out.csv'
    argv = _index_argv(
        SIMPLE_BUNDLE,
        'row1.lblx',
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
        extra=('--label-template', str(template)),
    )
    assert main(argv) == 0
    assert 'CUSTOM-TEMPLATE-SENTINEL' in (tmp_path / 'out.lblx').read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# Output-path resolution
# ---------------------------------------------------------------------------


def test_default_output_paths_used(seeded_cache_overlay: Path, chdir_tmp: Path) -> None:
    """T-CLI-060, R-CLI-015: the default output paths are ``index.csv``/``.lblx``."""
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 0
    assert (chdir_tmp / 'index.csv').is_file()
    assert (chdir_tmp / 'index.lblx').is_file()


def test_default_output_auto_numbers_when_present(
    seeded_cache_overlay: Path, chdir_tmp: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-CLI-061, R-CLI-015: an existing default name is auto-numbered."""
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    (chdir_tmp / 'index.csv').write_bytes(b'OLD')
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 0
    assert (chdir_tmp / 'index_1.csv').is_file()
    assert (chdir_tmp / 'index_1.lblx').is_file()
    assert (chdir_tmp / 'index.csv').read_bytes() == b'OLD'
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert 'index_1' in warnings[0].getMessage()


def test_default_output_auto_numbers_finds_lowest_free_integer(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """R-CLI-015: auto-numbering picks the lowest free integer."""
    (chdir_tmp / 'index.csv').write_bytes(b'OLD')
    (chdir_tmp / 'index_1.csv').write_bytes(b'OLD1')
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 0
    assert (chdir_tmp / 'index_2.csv').is_file()
    assert (chdir_tmp / 'index_2.lblx').is_file()


def test_default_output_auto_numbers_considers_both_csv_and_lblx(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """R-CLI-015: auto-numbering considers both the CSV and the label name."""
    (chdir_tmp / 'index.lblx').write_bytes(b'OLDLBL')
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 0
    assert (chdir_tmp / 'index_1.csv').is_file()
    assert (chdir_tmp / 'index_1.lblx').is_file()


def test_specified_output_csv_overwrites_with_warning(
    seeded_cache_overlay: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    frozen_time: None,
) -> None:
    """T-CLI-062, R-OUT-013: an existing explicit target is overwritten with a warning."""
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    out = tmp_path / 'foo.csv'
    out.write_bytes(b'OLD')
    args = GenerateIndexFileArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
    )
    result = run_generate_index_file(args)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert 'overwriting' in warnings[0].getMessage()
    assert str(out.resolve()) in warnings[0].getMessage()
    assert len(result.warnings) == 1
    assert 'overwriting' in result.warnings[0]
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


def test_specified_output_tab_extension_uses_tab_for_data_and_lblx_for_label(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-CLI-063, R-OUT-012: a ``.tab`` extension is honored for the data file."""
    out = tmp_path / 'foo.tab'
    argv = _index_argv(
        SIMPLE_BUNDLE,
        'row1.lblx',
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
    )
    assert main(argv) == 0
    assert (tmp_path / 'foo.tab').is_file()
    assert (tmp_path / 'foo.lblx').is_file()


def test_specified_output_no_extension_appends_csv(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-CLI-065, R-OUT-011: a bare stem gets ``.csv`` for data and ``.lblx`` for label."""
    out = tmp_path / 'foo'
    argv = _index_argv(
        SIMPLE_BUNDLE,
        'row1.lblx',
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
    )
    assert main(argv) == 0
    assert (tmp_path / 'foo.csv').is_file()
    assert (tmp_path / 'foo.lblx').is_file()


def test_specified_output_csv_replaces_only_csv_extension_for_label(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-CLI-064, R-OUT-010: a ``.csv`` target keeps the stem for the ``.lblx`` label."""
    out = tmp_path / 'foo.csv'
    argv = _index_argv(
        SIMPLE_BUNDLE,
        'row1.lblx',
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
    )
    assert main(argv) == 0
    assert (tmp_path / 'foo.csv').is_file()
    assert (tmp_path / 'foo.lblx').is_file()


def test_output_file_path_resolved_to_absolute_for_index_file_name_substitution(
    monkeypatch: pytest.MonkeyPatch, seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """Spec §14.2: the ``index_file_name`` substitution path is absolute."""
    captured: dict[str, Path] = {}

    def spy(**kwargs: object) -> dict[str, object]:
        captured['csv'] = kwargs['csv_absolute_path']  # type: ignore[assignment]
        return build_substitution_dict(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(runners_mod, 'build_substitution_dict', spy)
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 0
    assert captured['csv'].is_absolute()


# ---------------------------------------------------------------------------
# Help epilogs
# ---------------------------------------------------------------------------


def test_top_level_help_epilog_has_example(capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-070, R-CLI-040: the top-level help carries example invocations."""
    assert main(['--help']) == 0
    out = capsys.readouterr().out
    assert 'Example' in out or out.count('pds4_create_xml_index') >= 2


@pytest.mark.parametrize(
    'sub', ['generate_index_file', 'generate_xpath_list', 'copy_default_config']
)
def test_each_subcommand_help_has_examples(sub: str, capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-071, R-CLI-040: every subcommand help carries examples."""
    assert main([sub, '--help']) == 0
    assert 'Example' in capsys.readouterr().out


def test_xpath_list_rejects_label_template_arg(capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-081, R-CLI-021: ``generate_xpath_list`` rejects ``--label-template``."""
    argv = ['generate_xpath_list', '--bundle-root', 'x', '--label-template', 'foo.xml', 'p']
    assert main(argv) == 2
    assert 'unrecognized' in capsys.readouterr().err


# ---------------------------------------------------------------------------
# copy_default_config
# ---------------------------------------------------------------------------


def test_copy_default_config_rejects_bundle_root(capsys: pytest.CaptureFixture[str]) -> None:
    """T-CLI-090, R-CLI-032: ``copy_default_config`` rejects ``--bundle-root``."""
    argv = ['copy_default_config', '--output-file', 'o.yaml', '--bundle-root', 'x']
    assert main(argv) == 2
    assert 'unrecognized' in capsys.readouterr().err


def test_copy_default_config_without_output_file_exits_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T-CLI-091, R-CLI-030: a missing ``--output-file`` is an argparse error."""
    assert main(['copy_default_config']) == 2
    assert 'output-file' in capsys.readouterr().err


def test_copy_default_config_existing_dest_without_force_exits_1(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-CLI-092, R-CLI-031: an existing destination without ``--force`` exits 1."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    dest = tmp_path / 'exists.yaml'
    dest.write_text('x', encoding='utf-8')
    assert main(['copy_default_config', '--output-file', str(dest)]) == 1
    assert 'destination exists' in caplog.text


def test_copy_default_config_existing_dest_with_force_overwrites_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-CLI-093, R-CLI-031: ``--force`` overwrites an existing destination with a warning."""
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    dest = tmp_path / 'exists.yaml'
    dest.write_text('x', encoding='utf-8')
    assert main(['copy_default_config', '--output-file', str(dest), '--force']) == 0
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    assert 'Default configuration' in dest.read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# Verbosity
# ---------------------------------------------------------------------------


def _assert_verbosity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, flags: tuple[str, ...], expected: int
) -> None:
    """Run a benign command and assert ``setup_logging`` saw ``expected``."""
    calls: list[int] = []
    monkeypatch.setattr(dispatch_mod, 'setup_logging', lambda v: calls.append(v))
    argv = ['copy_default_config', '--output-file', str(tmp_path / 'c.yaml'), *flags]
    assert main(argv) == 0
    assert calls == [expected]


def test_verbosity_none_warning_level(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T-CLI-100, R-CLI-017: no ``-v`` maps to verbosity 0 (WARNING)."""
    _assert_verbosity(monkeypatch, tmp_path, (), 0)


def test_verbosity_v_info_level(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T-CLI-100, R-CLI-017: ``-v`` maps to verbosity 1 (INFO)."""
    _assert_verbosity(monkeypatch, tmp_path, ('-v',), 1)


def test_verbosity_vv_debug_level(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T-CLI-100, R-CLI-017: ``-vv`` maps to verbosity 2 (DEBUG)."""
    _assert_verbosity(monkeypatch, tmp_path, ('-vv',), 2)


def test_verbosity_vvv_debug_clamped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T-CLI-100, R-CLI-017: ``-vvv`` clamps to verbosity 3 (DEBUG)."""
    _assert_verbosity(monkeypatch, tmp_path, ('-vvv',), 3)


# ---------------------------------------------------------------------------
# Fail-slow, KeyboardInterrupt, exception mapping
# ---------------------------------------------------------------------------


def test_fail_slow_collects_multiple_filespec_overlength_errors(
    monkeypatch: pytest.MonkeyPatch, seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-AUTO-060, R-FSLOW-110: fail-slow accumulates two of three label errors."""

    def fake_scrape(label_path: Path, **_kwargs: object) -> ScrapeResult:
        if label_path.name in ('a.lblx', 'b.lblx'):
            raise LabelError('filespec exceeds 255 bytes', file_path=label_path)
        return _dummy_scrape_result(label_path)

    monkeypatch.setattr(runners_mod, 'scrape_label', fake_scrape)
    args = GenerateIndexFileArgs(
        bundle_root=MULTI_BUNDLE,
        patterns=('*.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=tmp_path / 'index.csv',
        fail_slow=True,
    )
    with pytest.raises(FailSlowAggregateError) as excinfo:
        run_generate_index_file(args)
    assert len(excinfo.value.errors) == 2


def test_keyboard_interrupt_returns_130_and_cleans_temp_files(
    monkeypatch: pytest.MonkeyPatch, seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """T-FSLOW-020, R-ERR-002: a mid-scrape SIGINT exits 130 and leaves no files."""

    def fake_scrape(_label_path: Path, **_kwargs: object) -> ScrapeResult:
        raise KeyboardInterrupt

    monkeypatch.setattr(runners_mod, 'scrape_label', fake_scrape)
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    assert main(argv) == 130
    assert not (chdir_tmp / 'index.csv').exists()
    assert not (chdir_tmp / 'index.lblx').exists()
    assert list(chdir_tmp.glob('*.tmp')) == []


@pytest.mark.parametrize(
    ('exc_cls', 'expected_exit_code'),
    [
        (CliError, 1),
        (ConfigError, 1),
        (LabelError, 2),
        (SchemaError, 2),
        (OutputError, 2),
        (FailSlowAggregateError, 2),
    ],
)
def test_pds4indexerror_subclass_caught_and_mapped_to_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    exc_cls: type[Pds4IndexError],
    expected_exit_code: int,
) -> None:
    """R-API-004: each error subclass maps to its pinned exit code and is logged."""
    if exc_cls is FailSlowAggregateError:
        exc: Pds4IndexError = FailSlowAggregateError(
            [LidError('msg-XYZ', file_path=Path('/tmp/foo'), lineno=42)]
        )
    else:
        exc = exc_cls('msg-XYZ', file_path=Path('/tmp/foo'), lineno=42)

    def boom(_args: object) -> object:
        raise exc

    monkeypatch.setattr(dispatch_mod, 'run_generate_index_file', boom)
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    argv = ['generate_index_file', '--bundle-root', str(tmp_path), 'x']
    assert main(argv) == expected_exit_code
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert any('msg-XYZ' in r.getMessage() for r in error_records)
    assert any('/tmp/foo:42' in r.getMessage() for r in error_records)


def test_unhandled_exception_returns_3_and_prints_traceback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Spec §17.2: an unexpected error exits 3 and prints a traceback to stderr."""

    def boom(_args: object) -> object:
        raise RuntimeError('intentional-test-token')

    monkeypatch.setattr(dispatch_mod, 'run_generate_index_file', boom)
    argv = ['generate_index_file', '--bundle-root', str(tmp_path), 'x']
    assert main(argv) == 3
    err = capsys.readouterr().err
    assert 'Traceback' in err
    assert 'RuntimeError' in err
    assert 'intentional-test-token' in err
    assert 'Pds4IndexError' not in err


def test_failslow_aggregate_summary_printed_to_stderr(
    monkeypatch: pytest.MonkeyPatch,
    seeded_cache_overlay: Path,
    chdir_tmp: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """T-FSLOW-002 (CLI leg), R-FSLOW-120: the summary names every failed label."""

    def fake_scrape(label_path: Path, **_kwargs: object) -> ScrapeResult:
        raise LidError('bad lid', file_path=label_path)

    monkeypatch.setattr(runners_mod, 'scrape_label', fake_scrape)
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    argv = _index_argv(
        MULTI_BUNDLE,
        'a.lblx',
        'b.lblx',
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        extra=('--fail-slow',),
    )
    assert main(argv) == 2
    assert 'a.lblx' in caplog.text
    assert 'b.lblx' in caplog.text


# ---------------------------------------------------------------------------
# Programmatic API contract
# ---------------------------------------------------------------------------


def test_run_generate_index_file_returns_result_dataclass(
    seeded_cache_overlay: Path, chdir_tmp: Path, frozen_time: None
) -> None:
    """R-API-003: the programmatic API returns a fully-populated result dataclass."""
    args = GenerateIndexFileArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
    )
    result = run_generate_index_file(args)
    assert isinstance(result, GenerateIndexFileResult)
    assert result.rows_written == 1
    assert result.columns_written == 3
    assert result.warnings == ()
    assert result.csv_path == (chdir_tmp / 'index.csv').resolve()
    assert result.label_path == (chdir_tmp / 'index.lblx').resolve()
    assert dataclasses.is_dataclass(result)
    assert {f.name for f in dataclasses.fields(result)} == {
        'csv_path',
        'label_path',
        'rows_written',
        'columns_written',
        'warnings',
    }


def test_run_generate_index_file_raises_failslowaggregateerror(
    monkeypatch: pytest.MonkeyPatch, seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-FSLOW-004, R-API-004: two bad labels under fail-slow raise, no files written."""

    def fake_scrape(label_path: Path, **_kwargs: object) -> ScrapeResult:
        raise LidError('bad lid', file_path=label_path)

    monkeypatch.setattr(runners_mod, 'scrape_label', fake_scrape)
    args = GenerateIndexFileArgs(
        bundle_root=MULTI_BUNDLE,
        patterns=('a.lblx', 'b.lblx'),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=tmp_path / 'index.csv',
        fail_slow=True,
    )
    with pytest.raises(FailSlowAggregateError):
        run_generate_index_file(args)
    assert not (tmp_path / 'index.csv').exists()
    assert not (tmp_path / 'index.lblx').exists()


def test_run_generate_index_file_result_warnings_contains_overwrite_messages_only(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None
) -> None:
    """T-FSLOW-005, R-API-004: result warnings hold only overwrite messages."""
    out = tmp_path / 'foo.csv'
    out.write_bytes(b'OLD')
    args = GenerateIndexFileArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
    )
    result = run_generate_index_file(args)
    assert len(result.warnings) == 1
    assert all('overwriting' in w for w in result.warnings)


def test_run_generate_index_file_temp_files_cleaned_on_failure(
    monkeypatch: pytest.MonkeyPatch, seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-ERR-002: an injected scrape failure leaves no temp files behind."""

    def fake_scrape(label_path: Path, **_kwargs: object) -> ScrapeResult:
        raise LabelError('boom', file_path=label_path)

    monkeypatch.setattr(runners_mod, 'scrape_label', fake_scrape)
    out = tmp_path / 'index.csv'
    args = GenerateIndexFileArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
        fail_slow=False,
    )
    with pytest.raises(LabelError):
        run_generate_index_file(args)
    assert list(tmp_path.glob('*.tmp')) == []


def test_main_returns_int_exit_code_not_calls_sys_exit(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """API contract: ``main`` returns an integer exit code."""
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    result = main(argv)
    assert isinstance(result, int)


def test_main_does_not_mutate_cwd(seeded_cache_overlay: Path, chdir_tmp: Path) -> None:
    """Codebase-analysis §6: ``main`` never changes the process working directory."""
    before = os.getcwd()
    argv = _index_argv(SIMPLE_BUNDLE, 'row1.lblx', config_files=(SIMPLE_CFG, seeded_cache_overlay))
    main(argv)
    assert os.getcwd() == before


def test_main_does_not_call_sys_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Library/CLI boundary: ``main`` never calls ``sys.exit``."""
    monkeypatch.setattr(sys, 'exit', lambda code=0: pytest.fail(f'main called sys.exit({code})'))
    main(['copy_default_config', '--output-file', str(tmp_path / 'c.yaml')])


# ---------------------------------------------------------------------------
# generate_xpath_list, cli_entrypoint (coverage of remaining surface)
# ---------------------------------------------------------------------------


def test_run_generate_xpath_list_writes_yaml(seeded_cache_overlay: Path, chdir_tmp: Path) -> None:
    """R-XPL-020: ``generate_xpath_list`` writes a ``columns:`` YAML block."""
    argv = [
        'generate_xpath_list',
        '--bundle-root',
        str(SIMPLE_BUNDLE),
        '--config-file',
        str(SIMPLE_CFG),
        '--config-file',
        str(seeded_cache_overlay),
        'row1.lblx',
    ]
    assert main(argv) == 0
    text = (chdir_tmp / 'columns.yaml').read_text(encoding='utf-8')
    assert 'columns:' in text
    assert 'xpath:' in text
    assert 'name:' in text


def test_run_generate_xpath_list_returns_result(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """R-API: ``run_generate_xpath_list`` returns its result dataclass."""
    args = GenerateXpathListArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
    )
    result = run_generate_xpath_list(args)
    assert isinstance(result, GenerateXpathListResult)
    assert result.xpath_count >= 1
    assert result.output_path == (chdir_tmp / 'columns.yaml').resolve()


def test_run_generate_xpath_list_auto_numbers(seeded_cache_overlay: Path, chdir_tmp: Path) -> None:
    """R-CLI-022: the default ``columns.yaml`` name is auto-numbered when taken."""
    (chdir_tmp / 'columns.yaml').write_text('old', encoding='utf-8')
    (chdir_tmp / 'columns_1.yaml').write_text('old1', encoding='utf-8')
    args = GenerateXpathListArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
    )
    result = run_generate_xpath_list(args)
    assert result.output_path == (chdir_tmp / 'columns_2.yaml').resolve()
    assert (chdir_tmp / 'columns.yaml').read_text(encoding='utf-8') == 'old'


def test_cli_entrypoint_calls_sys_exit_with_main_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-CLI-001: ``cli_entrypoint`` forwards ``main``'s return value to ``sys.exit``."""
    monkeypatch.setattr(dispatch_mod, 'main', lambda argv=None: 7)
    codes: list[int] = []
    monkeypatch.setattr(sys, 'exit', codes.append)
    cli_entrypoint()
    assert codes == [7]


def test_run_copy_default_config_writes_default(tmp_path: Path) -> None:
    """R-CLI-030: ``copy_default_config`` writes the packaged default config."""
    dest = tmp_path / 'fresh.yaml'
    assert main(['copy_default_config', '--output-file', str(dest)]) == 0
    assert isinstance(CopyDefaultConfigResult(output_path=dest), CopyDefaultConfigResult)
    assert 'Default configuration' in dest.read_text(encoding='utf-8')


def test_copy_default_config_write_to_directory_raises_outputerror(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A destination that cannot be written (a directory) exits 2 (OutputError)."""
    caplog.set_level(logging.ERROR, logger='pds4indextools')
    dest = tmp_path / 'adir'
    dest.mkdir()
    assert main(['copy_default_config', '--output-file', str(dest), '--force']) == 2


def test_csv_post_write_hook_invoked(
    seeded_cache_overlay: Path, tmp_path: Path, frozen_time: None
) -> None:
    """Appendix H: ``csv_post_write_hook`` runs with the final CSV path."""
    seen: list[Path] = []
    args = GenerateIndexFileArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=tmp_path / 'index.csv',
        csv_post_write_hook=seen.append,
    )
    run_generate_index_file(args)
    assert seen == [(tmp_path / 'index.csv').resolve()]


def test_write_index_outputs_cleans_csv_on_label_failure(
    monkeypatch: pytest.MonkeyPatch, seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-ERR-002: a failure after the CSV is written removes it and any temp."""

    def boom(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError('label-phase-failure')

    monkeypatch.setattr(runners_mod, 'build_substitution_dict', boom)
    out = tmp_path / 'index.csv'
    args = GenerateIndexFileArgs(
        bundle_root=SIMPLE_BUNDLE,
        patterns=('row1.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
    )
    with pytest.raises(RuntimeError):
        run_generate_index_file(args)
    assert not out.exists()
    assert list(tmp_path.glob('*.tmp')) == []


def test_register_label_parse_error_raises(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """R-PARSE-002: a malformed label surfaces as a ParseError before writing."""
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    (bundle / 'bad.lblx').write_text('<not-well-formed', encoding='utf-8')
    args = GenerateIndexFileArgs(
        bundle_root=bundle,
        patterns=('*.lblx',),
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=tmp_path / 'index.csv',
    )
    with pytest.raises(ParseError):
        run_generate_index_file(args)


def test_specified_output_lblx_extension_uses_csv_for_data(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-OUT-010: an ``.lblx`` target writes the CSV on the same stem."""
    out = tmp_path / 'foo.lblx'
    argv = _index_argv(
        SIMPLE_BUNDLE,
        'row1.lblx',
        config_files=(SIMPLE_CFG, seeded_cache_overlay),
        output_file=out,
    )
    assert main(argv) == 0
    assert (tmp_path / 'foo.csv').is_file()
    assert (tmp_path / 'foo.lblx').is_file()


def test_run_generate_xpath_list_explicit_output(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-CLI-022: an explicit xpath-list output appends ``.yaml`` and warns on reuse."""
    out = tmp_path / 'mycols'
    first = run_generate_xpath_list(
        GenerateXpathListArgs(
            bundle_root=SIMPLE_BUNDLE,
            patterns=('row1.lblx',),
            config_files=(SIMPLE_CFG, seeded_cache_overlay),
            output_file=out,
        )
    )
    assert first.output_path == (tmp_path / 'mycols.yaml').resolve()
    assert (tmp_path / 'mycols.yaml').is_file()
    second = run_generate_xpath_list(
        GenerateXpathListArgs(
            bundle_root=SIMPLE_BUNDLE,
            patterns=('row1.lblx',),
            config_files=(SIMPLE_CFG, seeded_cache_overlay),
            output_file=tmp_path / 'mycols.yaml',
        )
    )
    assert len(second.warnings) == 1
    assert 'overwriting' in second.warnings[0]
