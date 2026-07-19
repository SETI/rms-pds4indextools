"""Regenerate every tests/data/expected/<feature>/ output byte-for-byte.

Run once in Phase 11; re-run manually only when an intentional
output-format change requires new goldens. Golden-comparison
integration tests detect any drift on every pytest run.

This script is the binding source of truth for the golden bytes.
"""

import hashlib
import os
import tempfile
from pathlib import Path

from freezegun import freeze_time

from pds4indextools import (
    GenerateIndexFileArgs,
    GenerateXpathListArgs,
    run_generate_index_file,
    run_generate_xpath_list,
)


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'tests' / 'data'
EXPECTED = DATA / 'expected'
FROZEN_MTIME = 1778716800  # 2026-05-14T00:00:00Z (POSIX seconds, UTC); equals conftest._FROZEN_MTIME_EPOCH


def _freeze_csv_mtime(csv_path: Path) -> None:
    os.utime(csv_path, (FROZEN_MTIME, FROZEN_MTIME))


# MUST stay in sync with tests/conftest.py::_FIXTURE_SCHEMA_URLS.
_FIXTURE_SCHEMA_URLS: dict[str, str] = {
    'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd': 'pds_v1_basic.xsd',
    'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1K00.xsd': 'pds_v1_basic.xsd',
    'https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1L00_2000.xsd': 'geom_v1.xsd',
    'https://pds.nasa.gov/pds4/rings/v1/PDS4_RINGS_1L00_1G00.xsd': 'rings_v1.xsd',
}

# Set once in main(); appended to every config chain so schema
# resolution runs against the seeded cache with zero network.
_OVERLAY: Path


def _build_seeded_cache_overlay(work: Path) -> Path:
    """Seed a cache dir from the committed XSD seeds; return overlay YAML."""
    cache = work / 'xsd_cache'
    cache.mkdir(parents=True, exist_ok=True)
    for url, seed in _FIXTURE_SCHEMA_URLS.items():
        digest = hashlib.sha256(url.encode('utf-8')).hexdigest()
        (cache / f'{digest}.xsd').write_bytes(
            (DATA / 'xsd_cache_seed' / seed).read_bytes()
        )
    overlay = work / 'xsd_cache_overlay.yaml'
    overlay.write_text(f'xsd_cache_dir: {cache}\n', encoding='utf-8')
    return overlay


# Every feature with an expected/<feature>/ directory in
# tests/data/expected/. Feature variants reuse the source bundles
# (owner decision #8): the first element names the expected/ directory,
# the second names the bundle directory actually scraped.
_INDEX_FEATURES: tuple[tuple[str, str, str], ...] = (
    # (expected_dir, bundle_name, config_file_or_first_of_chain)
    ('simple_pds_only',       'simple_pds_only', 'simple.yaml'),
    ('multi_namespace',       'multi_namespace', 'multi_namespace.yaml'),
    ('nilled',                'nilled',          'nilled.yaml'),
    ('quote_in_value',        'quote_in_value',  'quote_in_value_fixed.yaml'),
    ('fixed_width',           'simple_pds_only', 'fixed_width.yaml'),
    ('crlf',                  'simple_pds_only', 'crlf.yaml'),
    ('multi_config',          'simple_pds_only', 'multi_config_a.yaml'),
    ('mapping_full_features', 'multi_namespace', 'mapping_full_features.yaml'),
)

# Bundles whose runs always raise (no expected/ directory; the integration
# tests assert on exceptions). The generator script does NOT regenerate
# anything for these — listed here for documentation completeness.
_FAILING_BUNDLES: tuple[str, ...] = (
    'nilled_bad',
    'multi_lid',
    'bom',
    'non_ascii_value',
    'version_mismatch',
    'no_schema_location',
    # repeated_tags: its columns reference pds:name, which the committed
    # seed XSD (Appendix A.11) does not define, so type resolution raises
    # SchemaResolutionError and no golden index.{csv,lblx} can be produced.
    # R-XP-020 (canonical-form renumbering) is verified directly against
    # scrape_label in test_generate_index_file.py.
    'repeated_tags',
    # non_monotone: no bundle directory exists; R-XP-021 is unit-tested directly.
)


def _regen_index_feature(expected_dir: str, bundle: str, cfg: str) -> None:
    """Run the index pipeline for one feature; commit bytes to expected/."""
    out_dir = EXPECTED / expected_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    args = GenerateIndexFileArgs(
        bundle_root=DATA / 'bundles' / bundle,
        patterns=('**/*.lblx',),
        config_files=_configs_for(expected_dir, cfg),
        output_file=out_dir / 'index.csv',
        fail_slow=False,
        verbosity=0,
        csv_post_write_hook=_freeze_csv_mtime,
    )
    run_generate_index_file(args)


def _configs_for(expected_dir: str, primary: str) -> tuple[Path, ...]:
    if expected_dir == 'multi_config':
        return (DATA / 'configs' / 'multi_config_a.yaml',
                DATA / 'configs' / 'multi_config_b.yaml',
                DATA / 'configs' / 'multi_config_c.yaml',
                _OVERLAY)
    return (DATA / 'configs' / primary, _OVERLAY)


def _regen_xpath_list(name: str) -> None:
    """Run the xpath-list pipeline for the given bundle."""
    out_dir = EXPECTED / 'xpath_lists'
    out_dir.mkdir(parents=True, exist_ok=True)
    args = GenerateXpathListArgs(
        bundle_root=DATA / 'bundles' / name,
        patterns=('**/*.lblx',),
        config_files=(DATA / 'configs' / 'simple.yaml', _OVERLAY),
        output_file=out_dir / f'{name}.yaml',
        fail_slow=False,
        verbosity=0,
    )
    run_generate_xpath_list(args)


def main() -> int:
    """Regenerate all expected outputs deterministically (zero network)."""
    global _OVERLAY
    os.environ['TZ'] = 'UTC'
    work = Path(tempfile.mkdtemp(prefix='pds4index_golden_'))
    _OVERLAY = _build_seeded_cache_overlay(work)
    with freeze_time('2026-05-14T00:00:00Z'):
        for expected_dir, bundle, cfg in _INDEX_FEATURES:
            _regen_index_feature(expected_dir, bundle, cfg)
        for name in ('simple_pds_only', 'multi_namespace'):
            _regen_xpath_list(name)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
