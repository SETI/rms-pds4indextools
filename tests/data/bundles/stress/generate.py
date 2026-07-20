#!/usr/bin/env python3
"""Deterministically generate the heterogeneous ``stress`` fixture bundle.

This is NOT a random generator: every label's content comes from the explicit
``LABELS`` design table below, hand-chosen so the ~20 labels differ from one
another along many axes simultaneously (see ``TEST-SUITE-STRESS-PLAN.md``). The
script exists so the fixture is reproducible and auditable, and so the companion
``MANIFEST.md`` is guaranteed consistent with the emitted XML.

Run from the repository root::

    ./venv/bin/python tests/data/bundles/stress/generate.py

It (re)writes the ``.lblx`` files under this directory and ``MANIFEST.md``.

Value conventions in the table:
    None            -> element entirely absent from the label
    ''              -> element present but empty (present-but-blank)
    ('nil', reason) -> element present with xsi:nil="true" nilReason="reason"
    other str/num   -> element present with that text value
    os is a list of Observing_System systems; each system is a list of names
    (so ``[['A', 'B']]`` is one system with two <name> children -> nested repeat).
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent

# The canonical XPath prefix each configured column is addressed from.
ROOT = 'pds:Product_Observational<1>/pds:Observation_Area<1>'

# --- The design table -------------------------------------------------------
# Each dict is one label. Keys map to the container structure documented in the
# manifest. Order of keys here is irrelevant; the emitter fixes element order.
LABELS: list[dict] = [
    # ---- Moon (target tie group; obsid varies; imaging; geom) ----
    dict(key='img0001', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:img0001', vid='1.0',
         title='Wide-field mosaic, sequence 1', target='Moon', obsid=2,
         exposure='1.5', start='2023-05-01', stop=None,
         os=[['Camera A']], method='centered', frame='J2000',
         ring=None, feature=None, purpose='Survey', comment=None),
    dict(key='img0002', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:img0002', vid='1.0',
         title='Moon', target='Moon', obsid=10, exposure='12.0',
         start=('nil', 'unknown'), stop=None,
         os=[['Camera A'], ['Camera B']], method='centered', frame=None,
         ring=None, feature=None, purpose=None, comment=None),
    dict(key='img0003', subdir='data/imaging/highres', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:img0003', vid='2.0',
         title='High-resolution close-up of crater rim, north polar region, frame 3',
         target='Moon', obsid=100, exposure='0.25', start='2023-05-03', stop=None,
         os=[['Cam A'], ['Cam B'], ['Cam C']], method='offset', frame='J2000',
         ring=None, feature=None, purpose=None,
         comment='Observation notes:\n  target acquired\n    tracking nominal'),
    dict(key='img0004', subdir='data/imaging/highres', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:img0004', vid='1.0',
         title=None, target='Moon', obsid=7, exposure=None,
         start=('nil', 'missing'), stop=None,
         os=[], method='centered', frame=None,
         ring=None, feature=None, purpose=None, comment=None),
    # Long product-id suffix (same 6-token product LID format), also Moon
    dict(key='img0007sub', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:img0007_subframe_alpha', vid='1.0',
         title='Subframe, quadrant a', target='Moon', obsid=4, exposure=None,
         start='2023-05-07', stop=None,
         os=[['Camera A']], method='centered', frame=None,
         ring=None, feature=None, purpose=None, comment=None),

    # ---- Saturn (target tie group; obsid has a 5/5 tie; spectra; rings) ----
    dict(key='spec01', subdir='data/spectra', coll='spectra',
         lid='urn:nasa:pds:stress:spectra:spec01', vid='1.0',
         title='Spectrum A', target='Saturn', obsid=55, exposure='3.5',
         start='2022-11-15', stop='2022-11-16',
         os=[['Spectrometer 1']], method=None, frame=None,
         ring='B Ring', feature='gap', purpose='Science, calibration',
         comment=None),
    dict(key='spec02', subdir='data/spectra', coll='spectra',
         lid='urn:nasa:pds:stress:spectra:spec02', vid='1.0',
         title='Spectrum B, extended', target='Saturn', obsid=5, exposure='30.0',
         start=('nil', 'inapplicable'), stop=None,
         os=[['Spectrometer 1'], ['Spectrometer 2']], method=None, frame=None,
         ring='A Ring', feature=None, purpose=None, comment=None),
    dict(key='spec03', subdir='data/spectra', coll='spectra',
         lid='urn:nasa:pds:stress:spectra:spec03', vid='3.0',
         title=None, target='Saturn', obsid=5, exposure=None,
         start='2022-01-01', stop=None,
         os=[], method=None, frame=None,
         ring='C Ring', feature='ringlet', purpose=None,
         comment='  leading padded first line\n  second padded line'),
    dict(key='spec04', subdir='data/spectra', coll='spectra',
         lid='urn:nasa:pds:stress:spectra:spec04', vid='1.0',
         title='S', target='Saturn', obsid=60, exposure=None,
         start=None, stop=None,
         os=[], method=None, frame=None,
         ring='F Ring', feature='strand', purpose=None, comment=None),

    # ---- Jupiter (target tie group; obsid has a 3/3 tie; geom) ----
    dict(key='jup01', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:jup01', vid='1.0',
         title='Jupiter, band survey', target='Jupiter', obsid=3, exposure='2.0',
         start='2021-06-01', stop=None,
         os=[['Camera A']], method='centered', frame='IAU_JUPITER',
         ring=None, feature=None, purpose=None, comment=None),
    dict(key='jup02', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:jup02', vid='1.0',
         title='Jupiter GRS', target='Jupiter', obsid=30, exposure=None,
         start='2021-06-02', stop=None,
         os=[['Camera A'], ['Camera B'], ['Camera C']], method='offset',
         frame=None, ring=None, feature=None, purpose=None, comment=None),
    dict(key='jup03', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:jup03', vid='2.0',
         title=None, target='Jupiter', obsid=3, exposure=None,
         start=None, stop=None,
         os=[], method=None, frame='IAU_JUPITER',
         ring=None, feature=None, purpose=None, comment=None),

    # ---- Titan (obsid 12/12 tie; nested-repeat os; spectra) ----
    dict(key='titan1', subdir='data/spectra', coll='spectra',
         lid='urn:nasa:pds:stress:spectra:titan1', vid='1.0',
         title='Titan haze layers, limb, north', target='Titan', obsid=12,
         exposure='45.0', start='2019-03-03', stop=None,
         os=[['Spectrometer 1', 'Spectrometer 2']], method='centered', frame=None,
         ring=None, feature=None, purpose=None, comment=None),
    # Irregular internal whitespace in the title -> must collapse to single spaces
    dict(key='titan2', subdir='data/spectra', coll='spectra',
         lid='urn:nasa:pds:stress:spectra:titan2', vid='1.0',
         title='Titan   flyby,  pass 2', target='Titan', obsid=12, exposure=None,
         start=('nil', 'unknown'), stop=None,
         os=[], method=None, frame=None,
         ring=None, feature=None, purpose=None, comment=None),

    # ---- Enceladus (both geom+rings; rings-only) ----
    dict(key='ence1', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:ence1', vid='1.0',
         title='Enceladus plumes', target='Enceladus', obsid=8, exposure='6.5',
         start='2018-07-07', stop=None,
         os=[['Camera A']], method='centered', frame='IAU_ENCELADUS',
         ring='E Ring', feature='plume', purpose=None,
         comment='Plume activity observed\nnear the south pole\nduring closest approach.'),
    dict(key='ence2', subdir='data/imaging', coll='imaging',
         lid='urn:nasa:pds:stress:imaging:ence2', vid='1.0',
         title='Enceladus, south polar terrain, tiger stripes',
         target='Enceladus', obsid=80, exposure=None,
         start='2018-07-08', stop=None,
         os=[], method=None, frame=None,
         ring='E Ring', feature=None, purpose=None, comment=None),

    # ---- No target (blank target; calibration; minimal; bundle-level) ----
    dict(key='cal_a', subdir='calibration', coll='calibration',
         lid='urn:nasa:pds:stress:calibration:cal_a', vid='1.0',
         title='Calibration frame, dark', target=None, obsid=1, exposure='0.0',
         start='2020-01-01', stop=None,
         os=[['Cal Unit']], method=None, frame=None,
         ring=None, feature=None, purpose='Calibration', comment=None),
    dict(key='cal_b', subdir='calibration', coll='calibration',
         lid='urn:nasa:pds:stress:calibration:cal_b', vid='1.0',
         title=None, target=None, obsid=None, exposure=None,
         start=('nil', 'missing'), stop=None,
         os=[], method=None, frame=None,
         ring=None, feature=None, purpose=None, comment=None),
    # Root-level file (depth-0 filespec); present-but-blank start
    dict(key='overview', subdir='', coll='document',
         lid='urn:nasa:pds:stress:document:overview', vid='1.0',
         title='Bundle-level overview', target=None, obsid=None, exposure=None,
         start='', stop=None,
         os=[['Overview Unit']], method=None, frame=None,
         ring=None, feature=None, purpose=None,
         comment='Top-level product.\n  See collection labels\n    for details.'),
    dict(key='plain', subdir='calibration', coll='calibration',
         lid='urn:nasa:pds:stress:calibration:plain', vid='1.0',
         title='Plain', target=None, obsid=None, exposure=None,
         start=None, stop=None,
         os=[], method=None, frame=None,
         ring=None, feature=None, purpose=None, comment=None),
]

PDS_NS = 'http://pds.nasa.gov/pds4/pds/v1'
GEOM_NS = 'http://pds.nasa.gov/pds4/geom/v1'
RINGS_NS = 'http://pds.nasa.gov/pds4/rings/v1'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'

PDS_XSD = 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd'
GEOM_XSD = 'https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1L00_2000.xsd'
RINGS_XSD = 'https://pds.nasa.gov/pds4/rings/v1/PDS4_RINGS_1L00_1G00.xsd'


def _leaf(tag: str, value, indent: str) -> str:
    """Render one leaf element from a table value (handles None/''/nil/text)."""
    if value is None:
        return ''
    if isinstance(value, tuple) and value and value[0] == 'nil':
        return f'{indent}<{tag} xsi:nil="true" nilReason="{value[1]}"/>\n'
    if value == '':
        return f'{indent}<{tag}></{tag}>\n'
    return f'{indent}<{tag}>{escape(str(value))}</{tag}>\n'


def build_xml(rec: dict) -> str:
    uses_geom = rec['method'] is not None or rec['frame'] is not None
    uses_rings = rec['ring'] is not None or rec['feature'] is not None

    ns = [f'xmlns="{PDS_NS}"', f'xmlns:xsi="{XSI}"']
    schema_loc = [f'{PDS_NS} {PDS_XSD}']
    if uses_geom:
        ns.append(f'xmlns:geom="{GEOM_NS}"')
        schema_loc.append(f'{GEOM_NS} {GEOM_XSD}')
    if uses_rings:
        ns.append(f'xmlns:rings="{RINGS_NS}"')
        schema_loc.append(f'{RINGS_NS} {RINGS_XSD}')
    ns_str = '\n '.join(ns)
    sl_str = '\n                      '.join(schema_loc)

    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append(f'<Product_Observational {ns_str}\n'
               f' xsi:schemaLocation="{sl_str}">')

    # Identification_Area
    out.append('    <Identification_Area>')
    out.append(f'        <logical_identifier>{escape(rec["lid"])}</logical_identifier>')
    out.append(f'        <version_id>{escape(rec["vid"])}</version_id>')
    if rec['title'] is not None:
        out.append(_leaf('title', rec['title'], '        ').rstrip('\n'))
    out.append('    </Identification_Area>')

    # Observation_Area
    oa: list[str] = []
    tc = _leaf('start_date_time', rec['start'], '            ') + \
        _leaf('stop_date_time', rec['stop'], '            ')
    if tc:
        oa.append('        <Time_Coordinates>\n' + tc + '        </Time_Coordinates>')
    if rec['target'] is not None:
        oa.append('        <Target_Identification>\n'
                  + _leaf('target_name', rec['target'], '            ')
                  + '        </Target_Identification>')
    op = (_leaf('observation_id', rec['obsid'], '            ')
          + _leaf('exposure_duration', rec['exposure'], '            ')
          + _leaf('purpose', rec['purpose'], '            ')
          + _leaf('comment', rec['comment'], '            '))
    if op:
        oa.append('        <Observation_Parameters>\n' + op
                  + '        </Observation_Parameters>')
    for system in rec['os']:
        names = ''.join(_leaf('name', n, '            ') for n in system)
        oa.append('        <Observing_System>\n' + names + '        </Observing_System>')
    if uses_geom:
        g = _leaf('geom:method', rec['method'], '            ') \
            + _leaf('geom:reference_frame', rec['frame'], '            ')
        oa.append('        <geom:Geometry>\n' + g + '        </geom:Geometry>')
    if uses_rings:
        r = _leaf('rings:ring_name', rec['ring'], '            ') \
            + _leaf('rings:feature_type', rec['feature'], '            ')
        oa.append('        <rings:Ring>\n' + r + '        </rings:Ring>')

    if oa:
        out.append('    <Observation_Area>')
        out.append('\n'.join(oa))
        out.append('    </Observation_Area>')
    out.append('</Product_Observational>\n')
    return '\n'.join(out)


def rel_path(rec: dict) -> Path:
    sub = rec['subdir']
    name = f'{rec["key"]}.lblx'
    return Path(sub) / name if sub else Path(name)


def _fmt(value) -> str:
    if value is None:
        return 'absent'
    if isinstance(value, tuple) and value[0] == 'nil':
        return f'nil({value[1]})'
    if value == '':
        return 'blank'
    return str(value)


def build_manifest() -> str:
    lines = [
        '# Stress bundle manifest',
        '',
        'Generated by `generate.py` from an explicit design table. This file is the',
        'human-readable specification of the fixture and the sole reference for',
        'independently deriving expected outputs (do NOT derive expectations from tool',
        'output). Regenerate with `./venv/bin/python tests/data/bundles/stress/generate.py`.',
        '',
        '## Container structure and XPaths',
        '',
        'All labels share this nesting (containers emitted only when they have content):',
        '',
        '```',
        'Product_Observational<1>',
        '  Identification_Area<1>: logical_identifier, version_id, title?',
        '  Observation_Area<1>',
        '    Time_Coordinates<1>: start_date_time?, stop_date_time?',
        '    Target_Identification<1>: target_name?',
        '    Observation_Parameters<1>: observation_id?, exposure_duration?, purpose?, comment?',
        '    Observing_System<n>: name<m>   (repeatable; nested name repeats possible)',
        '    geom:Geometry<1>: geom:method?, geom:reference_frame?',
        '    rings:Ring<1>: rings:ring_name?, rings:feature_type?',
        '```',
        '',
        'Example column XPaths (prefix `pds:Product_Observational<1>/pds:Observation_Area<1>/`):',
        '',
        '- title: `pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>`',
        '- start_date_time: `…/pds:Time_Coordinates<1>/pds:start_date_time<1>`',
        '- target_name: `…/pds:Target_Identification<1>/pds:target_name<1>`',
        '- observation_id: `…/pds:Observation_Parameters<1>/pds:observation_id<1>`',
        '- comment: `…/pds:Observation_Parameters<1>/pds:comment<1>`',
        '- 1st system name: `…/pds:Observing_System<1>/pds:name<1>`',
        '- 3rd system name: `…/pds:Observing_System<3>/pds:name<1>`',
        '- geom method: `…/geom:Geometry<1>/geom:method<1>`',
        '- rings ring_name: `…/rings:Ring<1>/rings:ring_name<1>`',
        '',
        '## Labels',
        '',
        '| file | LID | vid | title | target | obsid | exp | start | stop | Observing_System (names) | geom method/frame | rings ring/feature | purpose | comment |',
        '|------|-----|-----|-------|--------|-------|-----|-------|------|--------------------------|-------------------|--------------------|---------|---------|',
    ]
    for rec in LABELS:
        os_desc = '; '.join('+'.join(s) for s in rec['os']) if rec['os'] else '—'
        geom = f"{_fmt(rec['method'])}/{_fmt(rec['frame'])}" if (rec['method'] or rec['frame']) else '—'
        rings = f"{_fmt(rec['ring'])}/{_fmt(rec['feature'])}" if (rec['ring'] or rec['feature']) else '—'
        cmt = 'multiline' if (rec['comment'] and '\n' in rec['comment']) else _fmt(rec['comment'])
        title = _fmt(rec['title'])
        if rec['title'] and ',' in rec['title']:
            title += ' [comma]'
        lines.append(
            f"| `{rel_path(rec)}` | {rec['lid']} | {rec['vid']} | {title} | "
            f"{_fmt(rec['target'])} | {_fmt(rec['obsid'])} | {_fmt(rec['exposure'])} | "
            f"{_fmt(rec['start'])} | {_fmt(rec['stop'])} | {os_desc} | {geom} | {rings} | "
            f"{_fmt(rec['purpose'])} | {cmt} |"
        )
    lines += [
        '',
        '## Axis coverage notes',
        '',
        '- **Directory depth** varies (root, `calibration/`, `data/imaging/`, `data/imaging/highres/`, `data/spectra/`) to exercise filespec/filename auto-columns; scenarios can also use different **glob patterns** (e.g. `data/imaging/**/*.lblx`) to include different label subsets from this one bundle.',
        '- **LID format** is the real PDS4 6-token product form `urn:nasa:pds:stress:<collection>:<product>` for every label (the token count never varies — only suffix lengths do); bundle_name is therefore always `stress`, and lidvid varies with lid+vid.',
        '- **title**: absent (img0004, spec03, jup03, cal_b), 1-char (`S`), up to ~65 chars (img0003); commas in several (quoting).',
        '- **target_name** tie groups: Moon×5, Saturn×4, Jupiter×3, Titan×2, Enceladus×2, absent×4.',
        '- **observation_id** in-group ties: Saturn 5/5, Jupiter 3/3, Titan 12/12 (need a tertiary sort key to break).',
        '- **start_date_time** four-way: real dates, nil(missing/unknown/inapplicable), absent, present-blank (overview).',
        '- **Observing_System** counts: 0, 1, 2, 3 systems across labels; `titan1` has one system with two `name` children (nested repeat).',
        '- **Namespaces** differ per label: geom-only, rings-only, both (ence1), neither.',
        '- **Whitespace/newlines**: `titan2` title has irregular internal spacing; `img0003`/`spec03`/`overview` comments are multiline with leading padding; `ence1` comment is a sentence wrapped across lines. Per R-VAL-010 the tool collapses ALL whitespace (tabs/newlines/space runs) to single spaces, so none of these preserve line breaks in the CSV — even though the PDS4 standard marks `ASCII_Text_Preserved` as whiteSpace=preserve.',
    ]
    return '\n'.join(lines) + '\n'


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
    for rec in LABELS:
        path = target / rel_path(rec)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_xml(rec), encoding='utf-8')
    (target / 'MANIFEST.md').write_text(build_manifest(), encoding='utf-8')
    print(f'Wrote {len(LABELS)} labels + MANIFEST.md under {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
