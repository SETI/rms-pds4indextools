# Integration Stress-Test Suite — Implementation Plan

## Motivation

The current test suite favors tiny, homogeneous cases: 7 of 9 golden cases have a
single data row, the maximum anywhere is 3 rows, every value is unique per column,
no golden value contains a comma, every fixed-width label is single-row, and every
multi-row label is delimited. As a result, interactions that only appear with a
*variety* of heterogeneous labels are invisible. This hole was left when the
original plan's 1000+ generated-label bundle was cut; this plan fills it with a
much smaller (~20 label) but deliberately heterogeneous bundle.

The `record_character` → `Record_Character` bug (an invalid-PDS4 element name baked
into every fixed-width golden) demonstrated the failure mode: golden files copied
from tool output enshrine bugs instead of catching them. The overriding principle
of this plan is therefore: **expected files are derived independently of the tool's
output**, and validated by an independent PDS4 reader (`rms-pdstable`).

## Confirmed decisions

1. ~20 labels in one shared `tests/data/bundles/stress/` bundle.
2. Extending the synthetic seed XSDs (adding leaf-element declarations) is approved.
3. `rms-pdstable` is added as a test-only dependency; round-trip oracle runs in CI.
4. Execution uses fresh subagents per phase; the independent-derivation and
   critique agents are kept strictly separate from the authoring agent and never
   see tool output.
5. Both fixed-width **and** variable-width tables are round-tripped through pdstable.
6. Comments use multiline `ASCII_Text_Preserved` values with leading padding on
   each line.

## Axes of variation (the fixture must exercise all of these)

Requested by the user:
- Columns renamed vs not, in different combinations.
- Columns omitted vs included, in different combinations.
- Fields repeated in some labels and not others; 2 instances in one label, 3 in
  another (renumbering).
- Multiline padded comments.
- Sorting many ways, including complex multi-field sorts mixing ascending and
  descending keys.
- The same input labels reused for variable-width, fixed-width, and different
  column choices.

Added in this plan:
- **Nested subdirectories at varying depths** → exercises `filespec` / `filename`
  / `lidvid` auto-columns (all current bundles are flat — a real hole).
- **Value width variety** where each column's maximum width is driven by a
  *different* label (real fixed-width padding, not uniform columns).
- **Commas and leading/trailing spaces in values** → RFC-4180 quoting in
  variable-width, quoted-then-padded in fixed-width.
- **Numeric-looking values** (`observation_id` = 2/10/100; real `exposure_duration`)
  → string-sort semantics (`'10' < '2'`) and numeric-field padding.
- **nil / present / absent / present-but-blank** four-way states on one column.
- **Multiple nilReasons** (`missing`, `unknown`, `inapplicable`) with distinct
  configured substitutions.
- **Per-label namespace sets differ** (geom only / rings only / both / neither).
- **LID token-count variety** (4 / 5 / 7 tokens).
- **Same selector listed twice under different names** (duplicate-column edge).
- **CRLF vs LF**, with the label byte math (record_length / object_length)
  including the terminator, validated by pdstable.
- **sort_by referencing a renamed header vs an original selector** (behavior to be
  pinned from the spec in Phase 2).

Deliberately **excluded** from the shared happy-path bundle (kept as separate
targeted negative tests, since they abort a run): non-ASCII values (R-VAL-030),
malformed XML, quote character in a variable-width value (R-VAL-040).

## Phases

### Phase 0 — Extend the seed schemas (enabler)
Add ~10 leaf `<xs:element>` declarations across `pds_v1_basic.xsd`, `geom_v1.xsd`,
`rings_v1.xsd`, reusing existing simple types (`ASCII_Integer`, `ASCII_Real`,
`ASCII_Date_YMD`, `ASCII_File_Specification_Name`, string/text types). Every leaf a
stress label uses must be resolvable so runs don't abort. No container types are
needed (the resolver resolves leaf types only). Verify each new element resolves
before authoring labels.

### Phase 1 — Author the stress bundle + manifest
Author ~20 `.lblx` under `tests/data/bundles/stress/`, in nested subdirectories,
covering every axis above. Produce `tests/data/bundles/stress/MANIFEST.md`
documenting, per label: path/depth, LID shape, which optional elements are
present/absent/nil/blank, repeat counts, namespace set, notable value widths, and
comma/multiline content. The manifest is the human-readable spec of the fixture and
the sole reference for independent derivation.

### Phase 2 — Resolve behavioral questions from the spec (not the tool)
From `IMPLEMENTATION-pds4_create_xml_index.md` and `.cursor` rules, pin down:
1. Config maps `name<1..3>` but a label has 1 occurrence → cols 2,3 blank?
2. A label has MORE occurrences than mapped → extra dropped silently, or error?
3. `generate_xpath_list` union column count = max occurrences across labels?
   First-occurrence ordering when the first label lacks later columns?
4. nil vs absent vs present-blank — distinct or conflated?
5. `sort_by` keys reference the emitted header name or the raw selector?
6. Fixed-width sort: blank cell sorts as empty string (first)?
7. Duplicate selector under two names — both columns emitted?
Any question the spec does not answer is escalated as a critical question, not
guessed.

### Phase 3 — Independent expected-file derivation (separate agent, NO tool output)
A dedicated agent, given only the labels, configs, spec, manifest, and Phase-2
answers — and forbidden from running the tool or reading its output — computes each
expected CSV and the flagship `.lblx` byte layout by independent reasoning. These
become the committed golden files.

### Phase 4 — Author the integration tests (the scenario matrix)
Configs over the one bundle (see matrix below). Each test asserts the byte-golden
CSV (and `.lblx` where applicable), plus the oracle checks (Phase 6 mechanisms).

### Phase 5 — Independent critique of expected files (separate agent, NO tool output)
A second agent reviews every committed expected file against labels + config + spec
+ manifest and flags anything that looks copied from the implementation rather than
independently correct. It never sees tool output. Phase 3 / Phase 5 disagreements
are resolved from the spec.

### Phase 6 — Run and triage
Run the suite. Every tool-vs-expected mismatch is triaged as EITHER an
expected-file error OR a tool bug (as `record_character` was). Bugs are reported
before any expected file is changed to match the tool.

### Phase 7 — Fold in targeted unit gaps
- csv_writer byte-level tests: quoted-then-padded fixed-width; multi-key mixed
  asc/desc sort; descending-sort stability.
- Schema-resolution collision test (two registered schemas sharing a leaf
  local-name with different base types) to confirm/deny suspected bug S1.

## Scenario matrix (configs over the shared bundle)

- **Selection/renaming:** all columns (xpath headers); all renamed; subset with
  some renamed and some not, ordered unlike document order; auto-columns interleaved
  with xpath columns; a column absent from every label (empty column) between
  populated ones; the same selector twice under two names.
- **Renumbering:** map `Observing_System<1..3>/name` over labels with 0/1/2/3
  occurrences; nested repeats; `generate_xpath_list` union over the heterogeneous
  bundle (paste-ability of the emitted YAML is asserted).
- **nil/absent/blank:** four-way column; multiple nilReasons with distinct
  substitutions.
- **Output format (same columns, both layouts):** variable-width (RFC-4180 quoting
  on comma values) and fixed-width (per-column max padding from different labels,
  quoted-then-padded, an all-empty width-0 column, LF and CRLF).
- **Sorting:** single asc/desc; multi-key all-ascending with primary-key ties;
  multi-key MIXED asc/desc where all keys are needed to determine order;
  numeric-looking string sort; stability on ties; sorting with blanks present; sort
  by an auto-column; sort referencing a renamed header.
- **Flagship "everything" runs:** all ~20 labels, many columns (auto + xpath +
  repeated + nil + optional + empty + duplicate), fixed-width AND variable-width,
  complex mixed multi-key sort, comma and multiline values → one big golden CSV +
  golden `.lblx` each, with full pdstable round-trip.

## Oracle mechanisms (no shared assumptions with the code under test)

1. **Independent hand-derivation** (Phase 3) + **independent critique** (Phase 5).
2. **`rms-pdstable` round-trip**, both fixed-width (`Table_Character`) and
   variable-width (`Table_Delimited`): the external reader slices the CSV by the
   label's declared offsets/delimiter; extracted values must equal the scraped
   truth. Also confirms pdstable honors our RFC-4180 quoting. Run pdstable probes
   with a scoped `filterwarnings="ignore"` (its numpy path trips
   `filterwarnings=error`).
3. **Differential / property assertions** needing no golden: variable-width and
   fixed-width runs of the same columns yield identical stripped values in identical
   row order; sorted output is a permutation (same multiset) of unsorted; the column
   set equals `generate_xpath_list`'s union; the variable-width CSV re-parses
   byte-identically under Python's `csv` module.

## Deliverable
A single PR against `index_tools_rewrite` containing: the seed-schema extension, the
stress bundle + manifest, the independently-derived golden files, the new
integration and unit tests, the `rms-pdstable` test dependency, any tool bug fixes
surfaced (including the already-made `Record_Character` fix), and this plan file.
