"""Integration tests for the ``generate_xpath_list`` pipeline (§11.2).

The byte-golden tests compare against the committed
``tests/data/expected/xpath_lists/<bundle>.yaml`` files (LF terminators);
the remaining tests exercise output-path resolution and fail-slow behavior.
Every run appends ``seeded_cache_overlay`` as the last config for
zero-network schema resolution.
"""

import logging
from pathlib import Path

import pytest
import yaml

from pds4indextools import (
    GenerateXpathListArgs,
    GenerateXpathListResult,
    load_config,
)
from pds4indextools.cli import _runners as runners_mod
from pds4indextools.cli import main
from pds4indextools.errors import FailSlowAggregateError

DATA = Path(__file__).resolve().parents[1] / 'data'
BUNDLES = DATA / 'bundles'
CONFIGS = DATA / 'configs'
EXPECTED = DATA / 'expected' / 'xpath_lists'
PDS_1L00_URL = 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd'


def _run(
    bundle: Path, configs: tuple[Path, ...], output_file: Path | None
) -> GenerateXpathListResult:
    """Run the xpath-list pipeline programmatically."""
    return runners_mod.run_generate_xpath_list(
        GenerateXpathListArgs(
            bundle_root=bundle,
            patterns=('**/*.lblx',),
            config_files=configs,
            output_file=output_file,
        )
    )


def _xpath_argv(
    bundle: Path,
    *patterns: str,
    configs: tuple[Path, ...],
    output_file: Path | None = None,
) -> list[str]:
    """Assemble a ``generate_xpath_list`` argv list for ``main``."""
    argv = ['generate_xpath_list', '--bundle-root', str(bundle)]
    for config in configs:
        argv += ['--config-file', str(config)]
    if output_file is not None:
        argv += ['--output-file', str(output_file)]
    argv += list(patterns)
    return argv


def _write_label(directory: Path, name: str, *, lid: str) -> None:
    """Write a minimal single-product label with the given LID."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"\n'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        ' xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 '
        f'{PDS_1L00_URL}">\n'
        '    <Identification_Area>\n'
        f'        <logical_identifier>{lid}</logical_identifier>\n'
        '        <version_id>1.0</version_id>\n'
        '    </Identification_Area>\n'
        '</Product_Observational>\n',
        encoding='utf-8',
    )


def test_xpath_list_emits_yaml_columns_block(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """T-XPL-001, R-XPL-020: the emitted YAML matches the committed golden bytes."""
    out = tmp_path / 'columns.yaml'
    _run(BUNDLES / 'simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert out.read_bytes() == (EXPECTED / 'simple_pds_only.yaml').read_bytes()


def test_xpath_list_first_occurrence_order_across_alphabetically_sorted_labels(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-XPL-002, R-XPL-010: first-occurrence order over alphabetized labels."""
    out = tmp_path / 'columns.yaml'
    _run(BUNDLES / 'multi_namespace', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert out.read_bytes() == (EXPECTED / 'multi_namespace.yaml').read_bytes()
    text = out.read_text(encoding='utf-8')
    entries = [line for line in text.splitlines() if line.startswith('  - xpath:')]
    assert len(entries) == 5
    assert entries[0].endswith('pds:Identification_Area<1>/pds:logical_identifier<1>')
    assert entries[1].endswith('pds:Identification_Area<1>/pds:version_id<1>')
    assert entries[2].endswith('pds:Identification_Area<1>/pds:title<1>')


def test_xpath_list_output_is_loadable_as_config(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """Spec-amendment #12: the emitted block round-trips through load_config."""
    out = tmp_path / 'columns.yaml'
    _run(BUNDLES / 'simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    loaded = yaml.safe_load(out.read_text(encoding='utf-8'))
    assert isinstance(loaded['columns'], list)
    config = load_config((CONFIGS / 'minimal.yaml', out))
    assert config.columns is not None
    assert len(config.columns) == len(loaded['columns'])


def test_xpath_list_emits_canonical_form_with_predicate_one(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-XPL-004, R-XP-002: every emitted XPath carries explicit <1> predicates."""
    out = tmp_path / 'columns.yaml'
    _run(BUNDLES / 'simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    xpaths = [
        line.split('xpath:', 1)[1].strip()
        for line in out.read_text(encoding='utf-8').splitlines()
        if line.startswith('  - xpath:')
    ]
    assert xpaths
    for xpath in xpaths:
        for segment in xpath.split('/'):
            assert segment.endswith('<1>')


def test_xpath_list_failslow_behaves_like_index_file(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """T-XPL-010, R-FSLOW-100: fail-slow accumulates a bad LID and writes no output."""
    bundle = tmp_path / 'bundle'
    _write_label(bundle, 'good.lblx', lid='urn:nasa:pds:t:c:good')
    _write_label(bundle, 'bad.lblx', lid='not-a-urn')
    out = tmp_path / 'columns.yaml'
    with pytest.raises(FailSlowAggregateError) as exc_info:
        runners_mod.run_generate_xpath_list(
            GenerateXpathListArgs(
                bundle_root=bundle,
                patterns=('**/*.lblx',),
                config_files=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
                output_file=out,
                fail_slow=True,
            )
        )
    assert len(exc_info.value.errors) == 1
    assert not out.exists()


def test_xpath_list_output_path_defaults_columns_yaml(
    seeded_cache_overlay: Path, chdir_tmp: Path
) -> None:
    """R-CLI-022: the default output path is ``./columns.yaml``."""
    argv = _xpath_argv(
        BUNDLES / 'simple_pds_only',
        '**/*.lblx',
        configs=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
    )
    assert main(argv) == 0
    assert (chdir_tmp / 'columns.yaml').is_file()


def test_xpath_list_auto_numbers_when_default_exists(
    seeded_cache_overlay: Path, chdir_tmp: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """R-CLI-022: an existing default name is auto-numbered to ``columns_1.yaml``."""
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    (chdir_tmp / 'columns.yaml').write_bytes(b'OLD')
    argv = _xpath_argv(
        BUNDLES / 'simple_pds_only',
        '**/*.lblx',
        configs=(CONFIGS / 'simple.yaml', seeded_cache_overlay),
    )
    assert main(argv) == 0
    assert (chdir_tmp / 'columns_1.yaml').is_file()
    assert (chdir_tmp / 'columns.yaml').read_bytes() == b'OLD'
    assert 'columns_1' in caplog.text


def test_xpath_list_specified_path_overwrites_with_warning(
    seeded_cache_overlay: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """R-CLI-022: an explicit existing target is overwritten with a warning."""
    caplog.set_level(logging.WARNING, logger='pds4indextools')
    out = tmp_path / 'cols.yaml'
    out.write_bytes(b'OLD')
    result = _run(BUNDLES / 'simple_pds_only', (CONFIGS / 'simple.yaml', seeded_cache_overlay), out)
    assert len(result.warnings) == 1
    assert 'overwriting' in result.warnings[0]
    assert out.read_bytes() != b'OLD'


def test_xpath_list_specified_path_no_extension_appends_yaml(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """R-CLI-022: an extensionless ``--output-file`` gains a ``.yaml`` suffix."""
    result = _run(
        BUNDLES / 'simple_pds_only',
        (CONFIGS / 'simple.yaml', seeded_cache_overlay),
        tmp_path / 'foo',
    )
    assert result.output_path == (tmp_path / 'foo.yaml').resolve()
    assert (tmp_path / 'foo.yaml').is_file()
