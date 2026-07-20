"""Integration stress suite over the heterogeneous ``stress`` bundle.

The bundle (``tests/data/bundles/stress/``, see its ``MANIFEST.md``) holds 20
labels that differ along many axes at once. These tests reuse that one bundle
across variable-width, fixed-width, column-selection, renumbering, nil/absent,
and sorting scenarios, and validate results three independent ways:

1. ``rms-pdstable`` round-trip: an external PDS4 reader reconstructs each cell
   from the label's declared byte offsets (fixed-width) or delimiter
   (variable-width). No shared assumptions with the code under test.
2. Python ``csv`` module: honors RFC-4180 quoting (which pdstable's delimited
   reader does not), so it validates comma-quoted variable-width output.
3. Property assertions that need no golden: sort is a permutation, the column
   set equals the ``generate_xpath_list`` union, fixed and variable widths carry
   identical values.

The trusted expected VALUE table in ``expected_values.json`` was derived
independently of the tool (see the stress plan) and is cross-checked here
against both the tool's CSV and pdstable.
"""

from __future__ import annotations

import csv
import io
import json
import warnings
from pathlib import Path

import pytest

from pds4indextools import cli as cli_mod
from pds4indextools.errors import ConfigError, SchemaResolutionError

pytestmark = pytest.mark.integration

DATA = Path(__file__).resolve().parent.parent / 'data'
BUNDLE = DATA / 'bundles' / 'stress'
EXPECTED_JSON = DATA / 'expected' / 'stress' / 'expected_values.json'

PdsTable = pytest.importorskip('pdstable').PdsTable

# --- Column blocks ----------------------------------------------------------
_R = 'pds:Product_Observational<1>/pds:Observation_Area<1>'
_ID = 'pds:Product_Observational<1>/pds:Identification_Area<1>'

# (header, selector-yaml-value, is_auto). Order matters: it is the emitted order.
FULL_COLUMNS: list[tuple[str, str, bool]] = [
    ('LID', 'lid', True),
    ('LIDVID', 'lidvid', True),
    ('FILE_NAME', 'filename', True),
    ('FILE_SPEC', 'filespec', True),
    ('BUNDLE', 'bundle_name', True),
    ('TITLE', f'{_ID}/pds:title<1>', False),
    ('TARGET', f'{_R}/pds:Target_Identification<1>/pds:target_name<1>', False),
    ('OBSID', f'{_R}/pds:Observation_Parameters<1>/pds:observation_id<1>', False),
    ('EXPOSURE', f'{_R}/pds:Observation_Parameters<1>/pds:exposure_duration<1>', False),
    ('START', f'{_R}/pds:Time_Coordinates<1>/pds:start_date_time<1>', False),
    ('STOP', f'{_R}/pds:Time_Coordinates<1>/pds:stop_date_time<1>', False),
    ('OS1', f'{_R}/pds:Observing_System<1>/pds:name<1>', False),
    ('OS2', f'{_R}/pds:Observing_System<2>/pds:name<1>', False),
    ('OS3', f'{_R}/pds:Observing_System<3>/pds:name<1>', False),
    ('METHOD', f'{_R}/geom:Geometry<1>/geom:method<1>', False),
    ('FRAME', f'{_R}/geom:Geometry<1>/geom:reference_frame<1>', False),
    ('RING', f'{_R}/rings:Ring<1>/rings:ring_name<1>', False),
    ('FEATURE', f'{_R}/rings:Ring<1>/rings:feature_type<1>', False),
    ('PURPOSE', f'{_R}/pds:Observation_Parameters<1>/pds:purpose<1>', False),
    ('COMMENT', f'{_R}/pds:Observation_Parameters<1>/pds:comment<1>', False),
]

# Columns whose values contain a comma in this bundle. pdstable's delimited
# reader cannot parse quoted delimiters, so the variable-width pdstable check
# uses a config that omits these entirely (the CSV then needs no quoting).
COMMA_HEADERS = {'TITLE', 'PURPOSE'}


def _columns_yaml(columns: list[tuple[str, str, bool]]) -> str:
    lines = ['columns:']
    for header, selector, is_auto in columns:
        key = 'auto' if is_auto else 'xpath'
        lines.append(f'  - {key}: {selector}')
        lines.append(f'    name: {header}')
    return '\n'.join(lines) + '\n'


def _write_config(
    tmp_path: Path,
    columns: list[tuple[str, str, bool]],
    *,
    fixed_width: bool = False,
    sort_by: list[str] | None = None,
    tag: str = 'cfg',
) -> Path:
    head = (
        'label_contents:\n'
        '  logical_identifier: urn:nasa:pds:stress:document:index\n'
        '  product_class: Product_Metadata_Supplemental\n'
        "  version_id: '1.0'\n"
        '  title: Stress index\n'
    )
    out = ['output:']
    if fixed_width:
        out.append('  fixed_width: true')
    if sort_by is not None:
        out.append('  sort_by:')
        out.extend(f'    - {key}' for key in sort_by)
    output_block = ('\n'.join(out) + '\n') if len(out) > 1 else ''
    cfg = tmp_path / f'{tag}.yaml'
    cfg.write_text(head + output_block + _columns_yaml(columns), encoding='utf-8')
    return cfg


def _run(
    seeded_cache_overlay: Path,
    tmp_path: Path,
    columns: list[tuple[str, str, bool]],
    *,
    fixed_width: bool = False,
    sort_by: list[str] | None = None,
    patterns: tuple[str, ...] = ('**/*.lblx',),
    tag: str = 'cfg',
) -> tuple[Path, Path]:
    cfg = _write_config(tmp_path, columns, fixed_width=fixed_width, sort_by=sort_by, tag=tag)
    out = tmp_path / f'{tag}.csv'
    result = cli_mod.run_generate_index_file(
        cli_mod.GenerateIndexFileArgs(
            bundle_root=BUNDLE,
            patterns=patterns,
            config_files=(cfg, seeded_cache_overlay),
            output_file=out,
        )
    )
    return out, Path(str(result.label_path))


def _parse_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    reader = list(csv.reader(io.StringIO(path.read_text(encoding='utf-8'))))
    header = reader[0]
    rows = [dict(zip(header, r, strict=True)) for r in reader[1:]]
    return header, rows


def _pdstable_rows(lblx: Path) -> list[dict[str, str]]:
    # pdstable's numpy path emits warnings that the repo's filterwarnings=error
    # would promote; suppress them for the external reader only.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        table = PdsTable(str(lblx))
        raw = table.dicts_by_row()
    rows: list[dict[str, str]] = []
    for r in raw:
        clean: dict[str, str] = {}
        for key, value in r.items():
            if key.endswith('_mask'):
                continue
            if isinstance(value, str):
                clean[key] = value.strip().strip('"').strip()
            elif value is None:
                clean[key] = ''
            else:
                clean[key] = str(value)
        rows.append(clean)
    return rows


# --- Oracle: fixed-width via pdstable (byte-offset sliced) -------------------
def test_fixed_width_pdstable_reconstructs_every_cell(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """pdstable slices the fixed-width CSV by the label's declared byte offsets;
    every reconstructed cell must equal the tool's own CSV cell (R-LBL byte math).
    Catches cumulative field_location / record_length errors across 20 columns
    and 20 rows — the class of bug the record_character fix exposed."""
    out, lblx = _run(seeded_cache_overlay, tmp_path, FULL_COLUMNS, fixed_width=True, tag='fw')
    header, tool_rows = _parse_csv(out)
    p_rows = _pdstable_rows(lblx)
    assert len(p_rows) == len(tool_rows) == 20
    for i, (tool_row, p_row) in enumerate(zip(tool_rows, p_rows, strict=True)):
        for col in header:
            assert p_row[col] == tool_row[col].strip(), (
                f'row {i} col {col!r}: pdstable={p_row[col]!r} tool={tool_row[col]!r}'
            )


# --- Oracle: variable-width via pdstable (comma-free columns) ----------------
def test_variable_width_pdstable_reconstructs_comma_free_cells(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """pdstable's delimited reader (naive split, no quote handling) reads a
    comma-free variable-width index; every cell must match the tool's CSV."""
    cols = [c for c in FULL_COLUMNS if c[0] not in COMMA_HEADERS]
    out, lblx = _run(seeded_cache_overlay, tmp_path, cols, tag='vw_nc')
    header, tool_rows = _parse_csv(out)
    p_rows = _pdstable_rows(lblx)
    assert len(p_rows) == len(tool_rows) == 20
    for i, (tool_row, p_row) in enumerate(zip(tool_rows, p_rows, strict=True)):
        for col in header:
            assert p_row[col] == tool_row[col], (
                f'row {i} col {col!r}: pdstable={p_row[col]!r} tool={tool_row[col]!r}'
            )


# --- Oracle: variable-width RFC-4180 quoting via csv module ------------------
def test_variable_width_csv_module_roundtrip_honors_quoting(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """The full variable-width CSV (with quoted comma values) must be valid
    RFC-4180 that Python's csv module parses into uniform-width rows, recovering
    the comma-containing values intact (no ragged rows from mis-quoting)."""
    out, _ = _run(seeded_cache_overlay, tmp_path, FULL_COLUMNS, tag='vw')
    parsed = list(csv.reader(io.StringIO(out.read_text(encoding='utf-8'))))
    assert len(parsed) == 21  # header + 20
    ncols = len(FULL_COLUMNS)
    assert all(len(row) == ncols for row in parsed), 'ragged rows -> mis-quoting'
    # A value that embeds the delimiter must survive the quoted round-trip.
    by_lid = {row[0]: row for row in parsed[1:]}
    title_idx = [h for h, _s, _a in FULL_COLUMNS].index('TITLE')
    assert by_lid['urn:nasa:pds:stress:calibration:cal_a'][title_idx] == 'Calibration frame, dark'
    purpose_idx = [h for h, _s, _a in FULL_COLUMNS].index('PURPOSE')
    assert by_lid['urn:nasa:pds:stress:spectra:spec01'][purpose_idx] == 'Science, calibration'


# --- Property: sort is a permutation ----------------------------------------
def test_multikey_mixed_sort_is_a_permutation(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """A complex multi-key mixed asc/desc sort must reorder — not add, drop, or
    mutate — rows: the sorted multiset equals the unsorted multiset."""
    unsorted_out, _ = _run(seeded_cache_overlay, tmp_path, FULL_COLUMNS, tag='u')
    sorted_out, _ = _run(
        seeded_cache_overlay,
        tmp_path,
        FULL_COLUMNS,
        sort_by=['TARGET', '-OBSID', 'LID'],
        tag='s',
    )
    _, u_rows = _parse_csv(unsorted_out)
    _, s_rows = _parse_csv(sorted_out)

    def multiset(rows: list[dict[str, str]]) -> list[tuple[tuple[str, str], ...]]:
        return sorted(tuple(sorted(r.items())) for r in rows)

    assert multiset(u_rows) == multiset(s_rows)
    # And the order actually changed (the sort did something).
    assert [r['LID'] for r in u_rows] != [r['LID'] for r in s_rows]


def test_multikey_mixed_sort_orders_by_string_comparison(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """Verify the exact ordering rule: TARGET asc, then OBSID *string*-descending,
    then LID asc. String comparison means OBSID '100' precedes '2' under desc only
    by string order, and an empty TARGET sorts first."""
    out, _ = _run(
        seeded_cache_overlay,
        tmp_path,
        FULL_COLUMNS,
        sort_by=['TARGET', '-OBSID', 'LID'],
        tag='s2',
    )
    _, rows = _parse_csv(out)
    triples = [(r['TARGET'], r['OBSID'], r['LID']) for r in rows]
    expected = sorted(triples, key=lambda t: (t[0], _NegStr(t[1]), t[2]))
    assert triples == expected


class _NegStr:
    """Reverse-ordering wrapper for stable string descending comparison."""

    __slots__ = ('s',)

    def __init__(self, s: str) -> None:
        self.s = s

    def __lt__(self, other: _NegStr) -> bool:
        return self.s > other.s

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _NegStr) and self.s == other.s


# --- Property: fixed and variable width carry identical values --------------
def test_fixed_and_variable_width_carry_identical_values(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """The same columns emitted fixed-width vs variable-width must contain the
    identical logical values in the identical row order (only padding differs)."""
    vw_out, _ = _run(seeded_cache_overlay, tmp_path, FULL_COLUMNS, tag='v')
    fw_out, _ = _run(seeded_cache_overlay, tmp_path, FULL_COLUMNS, fixed_width=True, tag='f')
    _, vw_rows = _parse_csv(vw_out)
    _, fw_rows = _parse_csv(fw_out)
    assert len(vw_rows) == len(fw_rows) == 20
    for i, (v, f) in enumerate(zip(vw_rows, fw_rows, strict=True)):
        for col, _sel, _auto in FULL_COLUMNS:
            assert v[col] == f[col].strip(), (
                f'row {i} col {col!r}: variable={v[col]!r} fixed={f[col].strip()!r}'
            )


# --- Property: column set equals the generate_xpath_list union --------------
def test_columns_cover_full_xpath_list_union(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """Every non-auto selector in FULL_COLUMNS must appear in the union of
    canonical XPaths that generate_xpath_list discovers over the bundle, so the
    stress config is not silently missing (or inventing) columns."""
    # generate_xpath_list still validates the full config, so it needs a
    # label_contents block even though it never uses it (noted as a usability
    # wart). Supply a minimal one alongside the cache overlay.
    minimal = tmp_path / 'minimal.yaml'
    minimal.write_text(
        'label_contents:\n'
        '  logical_identifier: urn:nasa:pds:stress:document:index\n'
        '  product_class: Product_Metadata_Supplemental\n',
        encoding='utf-8',
    )
    out = tmp_path / 'xpaths.yaml'
    cli_mod.run_generate_xpath_list(
        cli_mod.GenerateXpathListArgs(
            bundle_root=BUNDLE,
            patterns=('**/*.lblx',),
            config_files=(minimal, seeded_cache_overlay),
            output_file=out,
        )
    )
    discovered = set()
    for line in out.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if stripped.startswith('- xpath:'):
            discovered.add(stripped[len('- xpath:') :].strip())
    selectors = {sel for _h, sel, is_auto in FULL_COLUMNS if not is_auto}
    missing = selectors - discovered
    assert not missing, f'selectors absent from generate_xpath_list union: {missing}'


# --- Scenario: per-functionality value assertions (derived from the manifest) --
def _rows_by_lid(out: Path) -> dict[str, dict[str, str]]:
    _header, rows = _parse_csv(out)
    return {r['LID']: r for r in rows}


def test_renumbering_repeated_observing_system(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """Observing_System<1..3>/name across labels with 0/1/2/3 systems and a
    nested (one system, two names) case fills present occurrences and blanks the
    rest — exact per-label renumbering."""
    cols = [c for c in FULL_COLUMNS if c[0] in {'LID', 'OS1', 'OS2', 'OS3'}]
    out, _ = _run(seeded_cache_overlay, tmp_path, cols, tag='renum')
    by = _rows_by_lid(out)
    pfx = 'urn:nasa:pds:stress:'
    # 3 systems -> all three filled
    assert (
        by[pfx + 'imaging:img0003']['OS1'],
        by[pfx + 'imaging:img0003']['OS2'],
        by[pfx + 'imaging:img0003']['OS3'],
    ) == ('Cam A', 'Cam B', 'Cam C')
    # 2 systems -> OS3 blank
    assert by[pfx + 'imaging:img0002']['OS2'] == 'Camera B'
    assert by[pfx + 'imaging:img0002']['OS3'] == ''
    # nested: ONE system with two names -> OS1 filled, OS2/OS3 blank (a second
    # name does NOT create a second Observing_System)
    assert by[pfx + 'spectra:titan1']['OS1'] == 'Spectrometer 1'
    assert by[pfx + 'spectra:titan1']['OS2'] == ''
    assert by[pfx + 'spectra:titan1']['OS3'] == ''
    # 0 systems -> all blank
    assert (
        by[pfx + 'imaging:img0004']['OS1'],
        by[pfx + 'imaging:img0004']['OS2'],
        by[pfx + 'imaging:img0004']['OS3'],
    ) == ('', '', '')


def test_nil_absent_and_blank_start_date_time(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """One column, four states across labels: real date, nil (three reasons ->
    three distinct date substitutions), entirely absent, and present-but-blank."""
    cols = [c for c in FULL_COLUMNS if c[0] in {'LID', 'START'}]
    out, _ = _run(seeded_cache_overlay, tmp_path, cols, tag='nil')
    by = _rows_by_lid(out)
    pfx = 'urn:nasa:pds:stress:'
    assert by[pfx + 'imaging:img0001']['START'] == '2023-05-01'  # real
    assert by[pfx + 'calibration:cal_b']['START'] == '0002-01-01'  # nil missing
    assert by[pfx + 'imaging:img0002']['START'] == '0003-01-01'  # nil unknown
    assert by[pfx + 'spectra:spec02']['START'] == '0001-01-01'  # nil inapplicable
    assert by[pfx + 'calibration:plain']['START'] == ''  # absent
    assert by[pfx + 'document:overview']['START'] == ''  # present-blank


def test_auto_columns_reflect_path_and_identifier(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """filespec/filename vary by directory depth; lidvid concatenates lid+vid;
    bundle_name is the 4th LID token."""
    cols = [
        c for c in FULL_COLUMNS if c[0] in {'LID', 'LIDVID', 'FILE_NAME', 'FILE_SPEC', 'BUNDLE'}
    ]
    out, _ = _run(seeded_cache_overlay, tmp_path, cols, tag='auto')
    by = _rows_by_lid(out)
    deep = by['urn:nasa:pds:stress:imaging:img0003']
    assert deep['FILE_NAME'] == 'img0003.lblx'
    assert deep['FILE_SPEC'] == 'data/imaging/highres/img0003.lblx'
    assert deep['LIDVID'] == 'urn:nasa:pds:stress:imaging:img0003::2.0'
    assert deep['BUNDLE'] == 'stress'
    # root-level file -> filespec is just the basename
    root = by['urn:nasa:pds:stress:document:overview']
    assert root['FILE_SPEC'] == 'overview.lblx'


def test_glob_pattern_selects_label_subset(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """A narrower glob includes a different label subset from the same bundle."""
    cols = [c for c in FULL_COLUMNS if c[0] == 'LID']
    out, _ = _run(
        seeded_cache_overlay, tmp_path, cols, patterns=('data/spectra/*.lblx',), tag='glob'
    )
    lids = set(_rows_by_lid(out))
    assert all(':spectra:' in lid for lid in lids)
    assert 'urn:nasa:pds:stress:spectra:spec01' in lids
    assert 'urn:nasa:pds:stress:imaging:img0001' not in lids
    assert len(lids) == 6  # spec01-04, titan1, titan2


def test_column_omission_and_selective_renaming(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """A subset of columns, some renamed and some left at their selector text,
    in an order unrelated to document order: header row is exactly as configured."""
    columns = [
        ('TARGET', f'{_R}/pds:Target_Identification<1>/pds:target_name<1>', False),
        ('LID', 'lid', True),
        # left un-renamed: header falls back to the raw selector text
        (f'{_ID}/pds:title<1>', f'{_ID}/pds:title<1>', False),
    ]
    out, _ = _run(seeded_cache_overlay, tmp_path, columns, tag='omit')
    header, _rows = _parse_csv(out)
    assert header == ['TARGET', 'LID', f'{_ID}/pds:title<1>']


def test_duplicate_selector_is_rejected(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """The same selector under two different names is a config error (a column
    set may not address one canonical XPath twice)."""
    title_sel = f'{_ID}/pds:title<1>'
    columns = [
        ('LID', 'lid', True),
        ('TITLE_A', title_sel, False),
        ('TITLE_B', title_sel, False),
    ]
    with pytest.raises(ConfigError, match='duplicate column selector'):
        _run(seeded_cache_overlay, tmp_path, columns, tag='dup')


def test_empty_column_for_resolvable_selector_absent_from_all_labels(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """A selector whose leaf type resolves but which no label contains yields a
    real column that is empty in every row, without disturbing neighbours."""
    # 'description' is defined in the seed schema but used by no stress label.
    ghost = f'{_ID}/pds:description<1>'
    columns = [
        ('LID', 'lid', True),
        ('GHOST', ghost, False),
        ('TARGET', f'{_R}/pds:Target_Identification<1>/pds:target_name<1>', False),
    ]
    out, _ = _run(seeded_cache_overlay, tmp_path, columns, tag='ghost')
    header, rows = _parse_csv(out)
    assert header == ['LID', 'GHOST', 'TARGET']
    assert all(r['GHOST'] == '' for r in rows)
    assert any(r['TARGET'] == 'Moon' for r in rows)  # neighbour still populated


def test_selector_with_unknown_leaf_type_is_rejected(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """A selector whose leaf element is defined in no schema is a schema error,
    not a silent empty column."""
    ghost = f'{_R}/pds:Observation_Parameters<1>/pds:nonexistent_element<1>'
    columns = [('LID', 'lid', True), ('GHOST', ghost, False)]
    with pytest.raises(SchemaResolutionError, match='no PDS4 base type'):
        _run(seeded_cache_overlay, tmp_path, columns, tag='unkleaf')


def test_whitespace_and_newlines_are_collapsed(seeded_cache_overlay: Path, tmp_path: Path) -> None:
    """R-VAL-010: irregular internal whitespace and multiline padded/wrapped
    comments are collapsed to single spaces (newlines never preserved)."""
    cols = [
        ('LID', 'lid', True),
        ('TITLE', f'{_ID}/pds:title<1>', False),
        ('COMMENT', f'{_R}/pds:Observation_Parameters<1>/pds:comment<1>', False),
    ]
    out, _ = _run(seeded_cache_overlay, tmp_path, cols, tag='ws')
    by = _rows_by_lid(out)
    pfx = 'urn:nasa:pds:stress:'
    # irregular internal spaces collapsed
    assert by[pfx + 'spectra:titan2']['TITLE'] == 'Titan flyby, pass 2'
    # multiline padded comment collapsed (no newlines, single spaces)
    assert (
        by[pfx + 'imaging:img0003']['COMMENT']
        == 'Observation notes: target acquired tracking nominal'
    )
    # wrapped-sentence comment collapsed
    assert (
        by[pfx + 'imaging:ence1']['COMMENT']
        == 'Plume activity observed near the south pole during closest approach.'
    )


# --- Trusted independent oracle: expected_values.json -----------------------
# Derived from the labels + spec WITHOUT running the tool (see the stress plan
# and its independent critique). Both the tool's CSV and pdstable are checked
# against it, so a bug in the tool cannot hide behind a golden copied from tool
# output.
_EXPECTED = json.loads(EXPECTED_JSON.read_text(encoding='utf-8'))


def test_variable_width_values_match_independent_oracle(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """Every cell of the full variable-width run equals the independently
    derived expected value, in the independently derived row order."""
    out, _ = _run(seeded_cache_overlay, tmp_path, FULL_COLUMNS, tag='oracle_vw')
    _header, rows = _parse_csv(out)
    assert [r['LID'] for r in rows] == _EXPECTED['row_order']
    for row in rows:
        want = _EXPECTED['values'][row['LID']]
        for header, _sel, _auto in FULL_COLUMNS:
            assert row[header] == want[header], (
                f'{row["LID"]} col {header!r}: tool={row[header]!r} oracle={want[header]!r}'
            )


def test_fixed_width_pdstable_values_match_independent_oracle(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """pdstable's reconstruction of the fixed-width label equals the independently
    derived expected values — two independent derivations agreeing, neither being
    the tool's CSV writer."""
    _out, lblx = _run(
        seeded_cache_overlay, tmp_path, FULL_COLUMNS, fixed_width=True, tag='oracle_fw'
    )
    p_rows = _pdstable_rows(lblx)
    assert [r['LID'] for r in p_rows] == _EXPECTED['row_order']
    for p_row in p_rows:
        want = _EXPECTED['values'][p_row['LID']]
        for header, _sel, _auto in FULL_COLUMNS:
            assert p_row[header] == want[header], (
                f'{p_row["LID"]} col {header!r}: pdstable={p_row[header]!r} oracle={want[header]!r}'
            )


def test_mixed_sort_order_matches_independent_oracle(
    seeded_cache_overlay: Path, tmp_path: Path
) -> None:
    """The tool's row order under sort_by=[TARGET, -OBSID, LID] equals the
    independently derived sorted order (string comparison, mixed directions)."""
    out, _ = _run(
        seeded_cache_overlay,
        tmp_path,
        FULL_COLUMNS,
        sort_by=['TARGET', '-OBSID', 'LID'],
        tag='oracle_sort',
    )
    _header, rows = _parse_csv(out)
    assert [r['LID'] for r in rows] == _EXPECTED['sort_TARGET_OBSID_desc_LID']
