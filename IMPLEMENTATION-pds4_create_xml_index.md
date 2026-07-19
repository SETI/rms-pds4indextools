# Implementation Plan — pds4_create_xml_index Rewrite

## Context

The repository `/seti/all_repos/rms-pds4indextools` ships an aging single-file
1,847-line tool at `legacy/pds4indextools/pds4_create_xml_index.py` that scans
PDS4 XML labels and emits a tabular index plus a paired `.lblx` PDS4 label. The
project owner has authored a clean-slate design specification at
`specs/SPECS-pds4_create_xml_index.md` (1,870 lines, all numbered `R-*`
requirements with `T-*` test mappings in §24). The legacy code is preserved at
`legacy/` and is **read-only**; the new code is written at `src/pds4indextools/`
and tested at `tests/`. Both `src/pds4indextools/` and `tests/` are currently
empty.

Goal: a complete, tested, documented Python library + CLI that is
PyPI-publishable as `rms-pds4indextools` and that satisfies every `R-*`
requirement in the spec. Every test in §24's `T-*` inventory must exist and
pass. Every check in `scripts/run-all-checks.sh` must pass when run with the
defaults this plan sets in `pyproject.toml`.

The spec is the single source of truth. **This plan never restates the spec; it
points at exact R-IDs and T-IDs.** The implementer reads the spec section
referenced from each plan step and produces code/tests that satisfy it.

## Owner decisions (2026-07-18) that this plan revision incorporates

1. All test label fixtures (and temporary labels written by tests) use the
   `.lblx` suffix, not `.xml`; glob patterns in tests, docs examples, and
   the golden-bytes generator therefore use `**/*.lblx`. NOTE: `.xml`
   remains a perfectly valid historical label suffix for USERS — label
   discovery is entirely pattern-driven and the tool attaches no meaning
   to the suffix (a user passing `'**/*.xml'` gets identical behavior).
   The `.lblx`-only rule governs the files THIS repo creates (fixtures,
   docs examples, generated index labels), nothing else — and it applies
   only to labels, not to other file types (config `.yaml`, etc.).
2. `bandit` stays disabled; `vulture` is ENABLED (dev dependency,
   `[tool.vulture]` config, `ENABLE_VULTURE=true`).
3. When the user supplies no `Modification_Detail` data, the tool
   GENERATES a default single-entry modification history rather than
   emitting an empty one (see Phase 9). **Spec impact:** R-LBL-090/091
   currently say "None becomes an empty list"; the spec needs a matching
   update.
4. The repo template at `/seti/all_repos/rms-devenv/repo_template`
   (`REPONAME = rms-pds4indextools`, `MODULENAME = pds4indextools`) is the
   basis for all repo-level organization and files. The plan invents NO
   new repo-wide files, rules, skills, CI actions, or PR/issue templates.
   See Phase 0 §0.0.
5. The ASCII-only rules apply ONLY where the spec says they do (scraped
   values R-VAL-020/030, column `name` values R-MAP-043).
   They do NOT extend to XML element names; the earlier draft's
   ASCII-only element-name check in `xpath_norm` is removed (Phase 5).
6. There is no project logo; the plan carries no logo file.
7. Unit-test file names are descriptive of the behavior under test, not
   bare module names.
8. Byte-identical duplicate fixture files (bundle copies) are removed;
   feature-variant tests reuse the source bundles with different configs.
9. The 1,000-label `large_synthetic` bundle is removed entirely.
   (spec impact continues in the amendments section below)
10. **Columns move into the YAML config (supersedes the separate
    mapping-file design).** The line-oriented mapping `.txt` format,
    the `--mapping-file` option, and `MappingFileError` are all
    REMOVED. Column selection/renaming is a `columns:` list in the
    config schema (Phase 3), whose per-column dict entries
    (`xpath`/`auto` + `name`, `extra='forbid'`) leave room for future
    per-column customization keys. A merged config with a missing or
    empty `columns` list is a hard `ConfigError` for
    `generate_index_file` (there is NO all-columns fallback — no one
    legitimately wants an index with every column; the stern-warning
    machinery is deleted). `generate_xpath_list` now WRITES ITS OUTPUT
    AS YAML: a paste-ready `columns:` block covering every observed
    XPath, with `name:` defaulted for the user to edit.
   **Spec impact:** the `large_synthetic` row in spec §24.15 (and its
   T-IDs) and the reused-copy bundle rows need matching spec updates;
   the affected R-IDs (R-IDX-002 perturbation, R-LOG-021, R-SCH-020
   session caching) are covered by smaller bundles instead.

## Required spec amendments (apply in Phase 0, own commit)

The spec remains the single source of truth for R-/T-IDs, but the owner
decisions above supersede it in the places listed here. Phase 0 includes
one commit that amends `specs/SPECS-pds4_create_xml_index.md` so spec
and plan agree BEFORE implementation begins; `scripts/verify_test_coverage.py`
runs against the amended spec. The amendments (each traceable to an
owner decision or a template-first consequence):

1. R-LBL-090/R-LBL-091: `Modification_Detail` absent/None → a default
   single-entry history is GENERATED (Phase 9), not an empty list.
2. §24.15 bundle table: 11 bundles; remove the `large_synthetic` row,
   the `non_monotone` bundle row (unit-test-only, no directory),
   the copy-bundle rows (`fixed_width`, `crlf`, `multi_config`,
   `mapping_full_features` become config/mapping feature variants of
   existing bundles), and their dedicated T-IDs.
3. §23 R-CI-001..R-CI-005: rewrite to describe the template
   `run-tests.yml` (Ubuntu-only matrix over Python 3.10–3.13; lint job
   runs ruff/mypy/sphinx/pymarkdown; no pip-audit job; no separate docs
   job). R-CI-002's `pyroma --min=10` becomes `--min=9`.
4. §19.1/§19.2 + R-PKG-010: `cli/` and `scraper/` are sub-packages;
   unit-test files use descriptive behavior names (owner decision #7),
   not module-mirror names.
5. §20/§20.1: the root `__all__` is the list pinned in Phase 10 §10.2
   (spec §20's shorter sketch is superseded); `GenerateIndexFileArgs`
   gains the `csv_post_write_hook` field (Appendix H).
6. §21.2 dev dependencies: as Appendix A.1 (drop `pip-audit`; add
   `freezegun`, `responses`, `pytest-timeout`, `vulture`, `lxml-stubs`,
   `types-requests`, `types-PyYAML`).
7. R-DEP-001: dependencies are unpinned (bare names) so installs pull
   the latest compatible releases; a minimum lower bound is kept only
   where an API demands it (`pydantic>=2`, `rms-pdstemplate>=2.4`). No
   upper bounds.
8. R-TST-030: integration tests run against the pre-seeded XSD cache by
   default (no network); real-download tests carry `@pytest.mark.live`.
9. §7 (mapping file) is rewritten as the `columns:` config-schema
   section (owner decision #10): the line-format R-IDs (R-MAP-001/002,
   R-MAP-010..014, R-MAP-020, R-MAP-040..042) and the no-mapping-file
   R-IDs (R-MAP-101/102/110) are RETIRED; the semantic R-IDs survive
   with their numbers — R-MAP-030 (duplicate selectors), R-MAP-031
   (duplicate names), R-MAP-043 (name charset), R-MAP-300 (projection
   matches selectors by exact string equality), R-MAP-310/311/312
   (projection/empty-column/empty-list), R-MAP-320 (declared order).
   A new requirement: a merged config without a non-empty `columns`
   list is a hard `ConfigError` for `generate_index_file`.
10. §17.1: `MappingFileError` is removed from the exception hierarchy
    (column errors are `ConfigError`s).
11. §3/§5/§20.1: the `--mapping-file` option and the `mapping_file`
    dataclass field are removed everywhere; R-CLI-021's "xpath_list
    rejects `--mapping-file`" clause is dropped (the flag no longer
    exists on any subcommand; the `--label-template` rejection stays).
12. R-SORT-010: amended to "an unset/empty `sort_by` performs NO
    re-sort — rows keep discovery order, which is already
    filespec-sorted per R-DISC-020" (matches Phase 8's `sort_rows`
    contract).
13. R-TST-042: the `mapping_files/<feature>.txt` fixture-directory
    requirement is removed (no such directory exists).
14. §5 (R-XPL-020) + R-CLI-022: `generate_xpath_list` emits a YAML
    `columns:` block (one entry per first-occurrence XPath, `name:`
    defaulted to the XPath); the default output file becomes
    `./columns.yaml` (auto-numbered `columns_1.yaml`, … when present);
    a user-supplied `--output-file` without extension gets `.yaml`
    appended, any explicit extension is honored.

Scrub rule: every RETIRED R-ID token is deleted wherever it appears in
the spec — including the §24 T-ID tables and the §26 index — otherwise
`scripts/verify_test_coverage.py` re-collects the token and its
tripwire fails.

## How to use this plan

1. Read the spec end-to-end before opening this plan. This plan assumes you have
   §3–§26 mentally indexed and quotes R-/T-IDs without re-stating their text.
2. Execute phases in the order given. Each phase is a self-contained TDD cycle
   (write failing tests → implement → green → lint).
3. The "Phase exit criteria" subsection of each phase is the binary checklist
   that says whether you can move on. **Do not** move to phase N+1 until every
   exit-criterion bullet for phase N is `[x]`.
4. Run `scripts/run-all-checks.sh -c` after every phase to keep
   regressions local (every test present at a phase's exit is GREEN —
   no phase leaves RED tests behind). Docs checks (`-d`) join at
   Phase 12: the template docs skeleton does not pass `sphinx -W`
   until C.2's toctree delta lands. Run with no arguments before
   declaring the whole rewrite done.

## Execution model (BINDING): one integration branch, one PR per phase, one subagent per PR

- **Integration branch.** All work lands on the single integration
  branch `index_tools_rewrite` (already created). `main` receives
  NOTHING until the entire plan is complete and Phase 14 is green; the
  final step is one PR from `index_tools_rewrite` to `main`.
- **One PR per phase.** Each phase (0, 1, 2, 3, 5, 6, 7, 7.5, 8, 9,
  10, 11, 12, 13, 14 — Phase 4 is absorbed into 3) is executed as its
  OWN pull request targeting `index_tools_rewrite`: branch
  `rewrite/phase-<N>-<short-slug>` off the current tip of
  `index_tools_rewrite`; implement the phase to its exit criteria;
  open the PR with the phase's exit-criteria checklist reproduced (and
  checked) in the PR body. Squash-merge when green. Use the `gh` REST
  interface for PR operations — the high-level `gh pr` subcommands may
  lack access in this environment:
  `gh api repos/SETI/rms-pds4indextools/pulls -f title=... -f head=<branch> -f base=index_tools_rewrite -f body=...`
  to open, and
  `gh api -X PUT repos/SETI/rms-pds4indextools/pulls/<N>/merge -f merge_method=squash`
  to merge. Phases are
  strictly sequential: no phase starts until the previous phase's PR
  has merged.
- **One fresh subagent per PR.** Each phase-PR is implemented by a
  FRESH subagent whose ONLY inputs are: this plan, the amended spec,
  the repo's `.cursor/` rules and skills, and the repository at the
  integration branch's tip. Subagents share no conversational context
  — everything a phase needs MUST be in this plan or the spec (this is
  why the plan pins bytes and enumerates deltas). The orchestrator
  passes the subagent exactly: the phase number, the path to this
  plan, and the instruction to satisfy that phase's exit criteria.
- **Per-PR gate.** Before a phase PR merges: (a)
  `scripts/run-all-checks.sh -c` green locally (plus `-d` from
  Phase 12 onward; no-argument full run for Phases 13–14); (b) every
  exit-criteria box for the phase checked; (c) a REVIEW pass by a
  separate reviewer subagent that did not write the code, given the
  plan section + the diff, reporting pass/fail against the exit
  criteria — findings are fixed on the same PR branch before merge.
- **CI caveat.** The template `run-tests.yml` triggers only on
  pushes/PRs to `main`, so phase PRs into `index_tools_rewrite` get NO
  hosted CI; the local `run-all-checks.sh` gate substitutes. Hosted CI
  validates once, on the final `index_tools_rewrite` → `main` PR
  (Phase 13's verification task).
- **Phase 0's PR** contains, as its FIRST commit, the spec-amendments
  commit (see "Required spec amendments" above), so every later
  subagent reads an already-consistent spec.

## Authoritative external references

These are referenced by file path, not duplicated:

- Spec: `specs/SPECS-pds4_create_xml_index.md`
- Python rules: `.cursor/rules/python.mdc` and `.cursor/rules/python_testing.mdc`
- Doc rules: `.cursor/rules/documentation.mdc`
- Test critique criteria: `.cursor/skills/critique-test-suite/SKILL.md`
- Codebase analysis criteria: `.cursor/skills/python-codebase-analysis/SKILL.md`
- Master checker script: `scripts/run-all-checks.sh`
- Repo template (basis for ALL repo-level files; see Phase 0 §0.0):
  `/seti/all_repos/rms-devenv/repo_template`
- Legacy reference implementation: `legacy/pds4indextools/pds4_create_xml_index.py`
  (algorithm reference only; do NOT copy-paste — rewrite per the new module
  layout)

## Glossary of plan-level conventions

- **Module file**: `src/pds4indextools/<name>.py`
- **Unit test file**: `tests/unit/test_<behavior>.py` — the file name
  describes the behavior under test (e.g.
  `test_xpath_canonicalization_and_renumbering.py`), never just the
  module name. Each phase names its file explicitly.
- **Integration test file**: `tests/integration/test_<feature>.py`
- **Fixture path**: `tests/data/<subdir>/<name>.<ext>` (subdirs: `bundles/`,
  `configs/`, `expected/`, `xsd_cache_seed/`)
- **`R-*-NNN`**: Requirement ID from the spec. The spec is the binding text.
- **`T-*-NNN`**: Test ID from the spec §24. Each appears exactly once.
- **GREEN**: `pytest -n auto --strict-markers --strict-config tests/ -q` exits
  zero, ruff + mypy clean.
- **RED**: tests written, exit non-zero, no implementation yet committed.
- **Parameter style**: Every new function follows `python.mdc`
  §2: at most 3 positional parameters before `*`; all additional parameters
  are keyword-only. When a function takes or returns more than a few related
  values, use the Receive-an-Object/Return-an-Object pattern with a frozen
  `@dataclass(frozen=True, slots=True, kw_only=True)`.
- **Docstring section headings**: Every Google-style docstring uses
  `Parameters:` (NOT `Args:`), plus `Returns:` (iff the symbol returns a
  non-None value) and `Raises:` (iff any code path raises). Enforced by a
  unit test in `tests/unit/test_documentation_conventions.py` (Phase 12);
  the template's ruff rule set is NOT extended with the `D` category.
  Binding per `python.mdc` §6 / `documentation.mdc` §4.
- **Docstring line length**: All docstring text wraps at 90 columns
  (`python.mdc` §6 / `documentation.mdc` §4). Editor rulers
  at 80/90 are visual guides; the code line limit is 100.
- **No builtin shadowing**: Per `python.mdc` §1, no local
  variable, parameter, attribute, function, or class may share a name with
  a Python built-in (`id`, `type`, `filter`, `list`, `format`, `dict`,
  `bytes`, etc.). Use the trailing-underscore form (`id_`, `type_`) if the
  name is unavoidable. Ruff category `A` catches violations.
- **No `getattr` on argparse namespaces**: `python.mdc` §1
  forbids `getattr(ns, 'bundle_root')` when the attribute name is a
  constant string. Use direct attribute access (`ns.bundle_root`).
- **Module size cap**: All implementation modules MUST stay under 1000
  lines (`python.mdc` §2). If a module approaches that
  boundary during implementation, split into a sub-package immediately.
  `cli.py` and `scraper.py` are split UP-FRONT into sub-packages per
  Phases 7 and 10 (codebase-analysis §1: do not defer the split).
- **No `from __future__ import annotations`**: Python 3.10+ supports
  PEP 604 union syntax natively. Do NOT include the future import
  unless a specific incompatibility forces it (`python.mdc`
  §5). All sample code in this plan has it stripped.

## Authoritative bindings that apply across all phases

These rules apply to every phase; phase bodies do NOT restate them.

### Exception handling

- Every conversion from one exception type to another MUST use `raise
  NewError(...) from original` (or `from None` for clean truncation).
  Binding per `python.mdc` §2.
- Every `pytest.raises(...)` usage MUST assert on the exception message
  contents (`match=...` parameter OR `assert "substring" in
  str(exc_info.value)`), not only on the exception type. Binding per
  `python_testing.mdc` §7 and critique-skill §12.
- `assert` is FORBIDDEN in library code (`src/pds4indextools/**`) for
  runtime invariants; assertions can be stripped under `python -O`. Use
  real exceptions instead (`python.mdc` §2).
- Each `assert` statement in test code tests exactly one condition; no
  `and` in asserts. Compound checks become parametrized rows or
  separate tests (`python_testing.mdc` §7).

### Library/CLI output boundary (codebase-analysis §2)

- `run_generate_index_file`, `run_generate_xpath_list`,
  `run_copy_default_config` are LIBRARY functions and part of the public
  programmatic API (R-API-003). They MUST NOT call `print()`, `sys.exit`,
  `os._exit`, or write directly to `sys.stdout`/`sys.stderr`. They log via
  `pds4indextools.<module>` loggers and RAISE on error. Advisory warnings
  (e.g. overwrite) are appended to the returned
  `*Result.warnings` tuple AND emitted via `logger.warning(...)`.
- `main(argv: list[str] | None = None) -> int` is also library-callable
  programmatically and MUST NEVER call `sys.exit`; it returns an integer.
- Only the `cli_entrypoint()` console-script wrapper calls `sys.exit`.
  Implementation:
  ```python
  def cli_entrypoint() -> NoReturn:
      """Console-script wrapper; calls ``sys.exit`` so shells see the code."""
      import sys
      sys.exit(main())
  ```
- A Phase 14 grep tripwire confirms zero `print(` occurrences in
  `src/pds4indextools/**` and exactly two `sys.exit` occurrences (the
  `cli_entrypoint()` wrapper and the `__main__.py` guard). Argparse handles `--version`/`--help` itself; no `print`
  call ever appears in source.

### File-IO conventions (codebase-analysis §2)

- Every text-mode `open()` MUST pass `encoding='utf-8'`. Prefer
  `pathlib.Path.read_text(encoding='utf-8')` /
  `Path.write_text(encoding='utf-8')`.
- CSV bytes (Phase 8) are written via `open(path, 'wb')` (binary mode);
  line-terminator control (R-CSV-003) requires explicit bytes.
- `Path` is the type used everywhere paths cross a module boundary; raw
  strings are accepted only at the argparse-CLI boundary and converted
  to `Path` immediately.
- Prefer `pathlib` over `os.path` throughout. (The template's ruff rule
  set is kept as-is — no `PTH` category is added — so this is a review
  convention, not a lint gate.)

### Module dependency graph (no cycles; codebase-analysis §1)

Imports OUT of each module are listed below; imports INTO a module may
come ONLY from modules listed above it. If a forward reference is
unavoidable, gate the import behind `if TYPE_CHECKING:`.

```text
errors                  ← stdlib only
_io                     ← errors            (provides _atomic_rename; wraps OSError into OutputError)
_logging                ← errors
xpath_norm              ← errors
schema_types            ← errors, _logging
config                  ← errors            (owns ColumnSpec + AUTO_COLUMN_TOKENS; no scraper, no csv_writer)
csv_writer              ← errors, config, _io
scraper/ (package)      ← errors, _logging, xpath_norm, schema_types, config
label_writer            ← errors, config, csv_writer, _io
cli/ (package)          ← every other module
```

`scraper/` and `cli/` are sub-packages (mandatory split — see Phases 7
and 10). Internal submodules of `scraper/` and `cli/` import each other
freely but follow the outer dependency graph above.

### Per-phase docstring + docs hygiene (documentation.mdc §6)

After each implementation phase (1-10), the implementer:

1. Updates docstrings on every public class/method/function/module
   added or modified in that phase (`documentation.mdc` §6).
2. Updates the README if any user-visible behavior changed; if no
   user-visible change, the commit message states "no README impact".
3. Records any new `__all__` name in a running note; `docs/module.rst`
   itself is updated once, in Phase 12 (§0.0 defers template-file edits
   there; `documentation.mdc` §3 Module-index row).
4. From Phase 12 onward, runs `sphinx-build -W -n -b html docs
   docs/_build/html` after any docs-affecting change and confirms ZERO
   warnings (`documentation.mdc` §1, §5). Before Phase 12 the template
   docs skeleton is not `-W`-clean, so no per-phase Sphinx gate
   applies.
5. If any public symbol was renamed in this phase, every cross-reference
   to the old name across `docs/`, `README.md`, `CONTRIBUTING.md`, and
   docstrings is updated in the SAME commit (`documentation.mdc` §5).

### Plan text vs. delivered docs

The narrative prose in this plan uses bare CamelCase (e.g.
`Pds4IndexError`) for brevity. When implementers copy plan text into
docstrings, `.rst` files, README, or any other delivered documentation,
every bare CamelCase / dotted symbol MUST be converted to the proper
Sphinx cross-reference role per `documentation.mdc` §5 (e.g.
`` :class:`~pds4indextools.errors.Pds4IndexError` ``,
`` :exc:`~pds4indextools.errors.LabelError` `` for exceptions). Plan text
is NOT a documentation deliverable.

## Docstring contract (applies to every public symbol in Phases 1-10)

Per `documentation.mdc` §4 and `python.mdc` §6, every class,
method, function, and module that appears in any `__all__` MUST have a
docstring with:

1. One-line summary written in American-English with one space after the
   terminating period (`documentation.mdc` §2).
2. Optional one-paragraph extended description.
3. `Parameters:` block (NOT `Args:`) listing every parameter with type and
   description.
4. `Returns:` block IFF the symbol returns a non-`None` value.
5. `Raises:` block IFF any code path raises (cross-reference exception
   classes via `:exc:`).
6. Behavioral notes paragraph sufficient to write a black-box test
   WITHOUT referencing the internal implementation (R-DOC-010).
7. Spec R-ID citation(s) the symbol implements (R-ID citation is a
   contract reference, not an implementation detail).
8. Text wrapped at 90 characters.

The phase-specific module-behavior subsections do NOT restate this
contract; the contract here binds them all.

## Build/test commands the plan assumes

`scripts/run-all-checks.sh` requires the virtualenv at `./venv` (or
pointed to by `$VENV`); one already exists at the repo root,
provisioned with the full A.1 dependency set (create with
`python -m venv venv` if absent). ORDERING WARNING for Phase 0: the
committed template `pyproject.toml` CANNOT be editable-installed —
its placeholder `dependencies = ["TODO"]` resolves to a junk PyPI
package named `todo`, and the dev extra's self-reference
`pds4indextools` does not exist on PyPI. Rewrite `pyproject.toml` to
Appendix A.1 FIRST; only then run `pip install -e ".[dev,docs]"`.

```bash
python -m pip install -e ".[dev,docs]"
scripts/run-all-checks.sh                 # full default suite
scripts/run-all-checks.sh -c              # code checks only
scripts/run-all-checks.sh -d              # docs only
scripts/run-all-checks.sh --pytest        # only pytest
scripts/run-all-checks.sh --mypy          # only mypy
scripts/run-all-checks.sh --ruff-check    # only ruff check
scripts/run-all-checks.sh --ruff-format   # only ruff format --check
scripts/run-all-checks.sh --pyroma        # only pyroma
scripts/run-all-checks.sh --sphinx        # only sphinx build
scripts/run-all-checks.sh --pymarkdown    # only pymarkdown
```

`bandit` remains disabled (commented out in `pyproject.toml`;
`ENABLE_BANDIT=false` in `scripts/run-all-checks.sh`). `vulture` is
ENABLED: Phase 0 uncomments the `vulture` dev dependency and the
`[tool.vulture]` block in `pyproject.toml` and sets
`ENABLE_VULTURE=true` in `scripts/run-all-checks.sh`.

## Phase plan (top-level table of contents)

| Phase | Subject | Module(s) added | Tests added |
|-------|---------|-----------------|-------------|
| 0 | Project skeleton: `pyproject.toml` delta on the template, vulture toggle, `conftest.py`, fixture tree | (none) | `test_package_layout_and_metadata.py`, `test_fixture_integrity.py` |
| 1 | `errors.py` exception hierarchy | `errors.py` | `test_errors_hierarchy_and_formatting.py` |
| 2 | `_logging.py` log setup + tqdm wiring | `_logging.py` | `test_logging_configuration_and_progress.py` |
| 3 | `config.py` pydantic models (incl. `columns:`), YAML load+merge | `config.py` | `test_config_loading_and_merging.py` |
| 4 | (absorbed into Phase 3 — the mapping-file format is removed; owner decision #10) | (none) | (none) |
| 5 | `xpath_norm.py` namespace alias + renumber + canonicalize | `xpath_norm.py` | `test_xpath_canonicalization_and_renumbering.py` |
| 6 | `schema_types.py` XSD download/cache + type resolver | `schema_types.py` | `test_schema_cache_and_type_resolution.py` |
| 7 | `scraper/` lxml walk, value extraction, nil | `scraper/` (package split) | `test_label_scraping_and_validation.py` |
| 7.5 | `_io.py` atomic-write helpers | `_io.py` | `test_atomic_file_writes.py` |
| 8 | `csv_writer.py` quoting analysis, var/fixed writers | `csv_writer.py` | `test_csv_writing_quoting_and_sorting.py` |
| 9 | `label_writer.py` PdsTemplate variable assembly | `label_writer.py` | `test_label_template_substitution.py` |
| 10 | `cli/` argparse, subparser dispatch, `run_*` APIs, `__init__.py` | `cli/` (package split), `__init__.py`, `__main__.py` | `test_cli_parsing_dispatch_and_exit_codes.py` |
| 11 | Integration tests + fixture bundles | (none) | `tests/integration/*.py` |
| 12 | Documentation (Sphinx) | (docs only) | `test_documentation_conventions.py` |
| 13 | CI verification (template workflows, unchanged) | (none) | (no tests; workflows run on push) |
| 14 | Final verification | (none) | full `scripts/run-all-checks.sh` |

Each phase below carries: deliverable file list, exact behavior expected
(quoted by R-ID), exact tests required (quoted by T-ID), and a phase-exit
checklist.

---

## Phase 0 — Project skeleton

### 0.0 Template-first ground rule (BINDING for every phase)

The repository was initialized from
`/seti/all_repos/rms-devenv/repo_template` (commit "Repo template") with
`REPONAME = rms-pds4indextools` and `MODULENAME = pds4indextools`
substituted. That template is the basis for ALL repo-level organization
and files. This plan MUST NOT invent new general repo files, rules,
skills, CI actions, PR/issue templates, or other repo-wide files that
are not part of the code, tests, or documentation. Concretely:

- **Kept byte-identical to the template (never touched by this plan):**
  `.github/` (the three workflows `run-tests.yml`, `publish_to_pypi.yml`,
  `publish_to_test_pypi.yml`; issue templates; PR template),
  `.readthedocs.yaml`, `.gitignore`, `codecov.yml`, `LICENSE`,
  `requirements.txt`, `docs/Makefile`, `docs/make.bat`,
  `docs/code_of_conduct.md`, `docs/contributing.rst`,
  `scripts/read-docs.sh`, `.vscode/`, `.cursor/` (as committed in this
  repo).
- **Template files this plan modifies, minimally and only as needed:**
  `pyproject.toml` (Appendix A.1 — template content plus an enumerated
  delta), `scripts/run-all-checks.sh` (the `ENABLE_BANDIT`/
  `ENABLE_VULTURE` default toggles only, §0.1), `README.md`,
  `CONTRIBUTING.md`, `docs/conf.py`, `docs/index.rst`, `docs/module.rst`
  (Phase 12 / Appendix C).
- **New files are limited to** code (`src/`), tests (`tests/`),
  documentation pages (`docs/*.rst`), and project-specific scripts
  (`scripts/verify_test_coverage.py`, `scripts/verify_public_api.py`,
  `scripts/generate_expected_outputs.py`).
- There is **no `MANIFEST.in`** (the template has none; setuptools-scm's
  git file-finder governs sdist contents, as in every other RMS template
  repo), **no new CI workflows** (the previously drafted `ci.yml` and
  `pip_audit.yml` are dropped), and **no logo file** (this project has
  no logo; the template README does not reference one).

### 0.1 Deliverables

- `pyproject.toml` — apply the delta described in §0.2 to the committed
  template-derived file; [Appendix A.1](#a1-pyprojecttoml) shows the
  complete resulting file.
- `scripts/run-all-checks.sh` — the committed script already enables
  ruff-format and mypy (`ENABLE_RUFF_FORMAT:=true`, `ENABLE_MYPY:=true`)
  on top of the template defaults; keep that. The required end state
  for the enable-toggle defaults is: `ENABLE_RUFF_FORMAT=true`,
  `ENABLE_MYPY=true`, `ENABLE_VULTURE=true`, `ENABLE_BANDIT=false`.
  The committed script already has all four toggles at these values —
  VERIFY rather than edit; zero changes are expected. No other edits;
  no new flags or check functions are added to this script.
- `src/pds4indextools/__init__.py` — minimal stub (Phase 10 replaces it
  with the full public surface). Exact Phase 0 content:

  ```python
  """Tools for generating index files and PDS4 labels from PDS4 XML labels."""

  from pds4indextools._version import __version__

  __all__ = ['__version__']
  ```

  (`_version.py` is generated by the editable install's setuptools-scm
  hook, so this imports cleanly from Phase 0 on and the §0.3 smoke
  tests are GREEN immediately.)
- `src/pds4indextools/py.typed` — empty file (PEP 561 marker).
- `src/pds4indextools/templates/` — directory.
- `src/pds4indextools/templates/default_config.yaml` — content in
  [Appendix A.4](#a4-default_configyaml).
- `src/pds4indextools/templates/index_label_template.xml` — content in
  [Appendix A.5](#a5-index_label_templatexml).
- `tests/__init__.py` — empty (allows mypy to typecheck tests).
- `tests/conftest.py` — content in [Appendix A.6](#a6-tests-conftestpy).
- `tests/unit/__init__.py`, `tests/integration/__init__.py` — empty.
- `tests/data/` — directory tree per [Appendix A.7](#a7-tests-data-tree),
  populated according to Appendix B. EXCEPTION: the `expected/`
  subdirectories are created but stay EMPTY until Phase 11 runs the
  golden-bytes generator (their content cannot exist before the
  pipeline does); every golden-comparison test is a Phase 11
  deliverable for the same reason. There are NO duplicate fixture
  files: feature-variant integration tests (fixed-width, CRLF,
  multi-config, mapping-full-features) point `--bundle-root` at the
  existing `simple_pds_only` / `multi_namespace` bundles and vary only
  the config files. All label fixtures use the `.lblx` suffix.
- `tests/unit/test_fixture_integrity.py` — a Phase 0 deliverable with
  one test:
  - `test_bom_file_starts_with_bom_bytes` — asserts
    `(DATA_ROOT / 'bundles' / 'bom' / 'bom.lblx').read_bytes().startswith(b'\xef\xbb\xbf')`
    using the module-level `DATA_ROOT` from `tests/conftest.py`
    (absolute path — correct under any cwd) (per Appendix B.8).
- `src/pds4indextools/_io.py` — empty stub here; populated in
  Phase 7.5.
- There is NO `non_monotone` bundle directory (git cannot track an
  empty directory); Appendix B.6 explains the synthetic-call-only test
  path for R-XP-021.
- `tests/data/bundles/bom/bom.lblx` — generated by the Phase 0 one-liner
  in Appendix B.8.
- `scripts/verify_test_coverage.py` — content per
  [Appendix A.13](#a13-scriptsverify_test_coveragepy).
- `scripts/verify_public_api.py` — content per
  [Appendix F](#appendix-f--scriptsverify_public_apipy).
- `scripts/generate_expected_outputs.py` — content per
  [Appendix I.1](#i1-scriptsgenerate_expected_outputspy). (Phase 11
  executes the script; Phase 0 commits the source.)
- Everything else at the repo level (`.github/`, `.readthedocs.yaml`,
  `.gitignore`, `codecov.yml`, `requirements.txt`, docs skeleton) is
  already in place from the template and is NOT touched (§0.0).

### 0.2 Required behavior in `pyproject.toml`

`pyproject.toml` starts from the committed template-derived file and
applies ONLY the delta below (Appendix A.1 shows the complete resulting
file; everything not listed here stays byte-identical to the template):

- Fill the template's TODO placeholders: `description`, `keywords`, and
  `[project.dependencies]` (the spec §21.1 list; dependencies are
  unpinned bare names except `pydantic>=2` and `rms-pdstemplate>=2.4`,
  the two API-necessary minimum bounds — 2.4.0 verified against source).
- `[project.scripts]` register `pds4_create_xml_index =
  "pds4indextools.cli:cli_entrypoint"` (R-CLI-001), replacing the
  template's commented-out TODO entry. `cli_entrypoint()` is a thin
  wrapper around `main()` that calls `sys.exit(main())`; see the
  "Library/CLI output boundary" binding above. `main()` itself MUST
  NEVER call `sys.exit`.
- `[project.optional-dependencies].dev` — template list with:
  - `mypy` uncommented;
  - `vulture` uncommented (owner decision #2);
  - `bandit` left commented out;
  - additions needed by the test suite: `freezegun`,
    `responses`, `pytest-timeout` (bound runaway tests,
    critique skill §10/§15);
  - type-stub packages required for `mypy strict` on our imports:
    `lxml-stubs`, `types-requests`, `types-PyYAML` (tqdm ships no type
    stubs, so it is covered by the `tqdm.*` mypy override below;
    pydantic/platformdirs are typed);
  - the template's self-referential extras `MODULENAME` /
    `MODULENAME[docs]` corrected to the actual distribution name
    `rms-pds4indextools` / `rms-pds4indextools[docs]` (the bare module
    name would resolve to a different PyPI package).
- `[project.optional-dependencies].docs` — template list unchanged.
- `[tool.pytest.ini_options]` — keep the template's `pythonpath =
  ["src"]`, `testpaths`, and `addopts` base (`-n auto --cov=src
  --strict-markers --strict-config`), adding only `--cov-branch`,
  `--timeout=60`, `--timeout-method=thread`; the template's
  `# TODO Update desired parallelism` comment is removed (parallelism
  is decided: `-n auto`). Register exactly two
  markers, `live` and `integration`, and add the `filterwarnings` block
  (leading `"error"` plus the enumerated ignores; each ignore line MUST
  carry a comment citing the upstream issue or expected removal date —
  critique skill §16. `-W error` is deliberately NOT in addopts; the
  warnings policy lives entirely in `filterwarnings`).
- `[tool.ruff]` — template configuration kept EXACTLY (same `select`,
  same `extend-ignore`, same `quote-style = "single"`). No `D`, no
  `PTH`.
  If the setuptools-scm-generated `_version.py` ever trips ruff, add it
  to the template's `exclude` placeholder — that is the file's purpose.
- `[tool.mypy]` — template `strict = true` block and the
  `pds4indextools._version` override kept; add one override with
  `module = ["pdstemplate.*", "requests_file.*", "tqdm.*"]` and
  `ignore_missing_imports = true` (untyped third-party imports).
  `tests/` IS included in every mypy invocation
  (`python_testing.mdc` §2/§4).
- `[tool.coverage.run]` / `[tool.coverage.report]` — template blocks
  kept (`fail_under = 90`), with one correction: the template's
  `_version.py` omit entry becomes `*/_version.py` so it actually
  matches `src/pds4indextools/_version.py` under the `--cov=src` run.
- `[tool.setuptools.package-data]` — extend the template entry to
  `["py.typed", "templates/*.yaml", "templates/*.xml"]`.
- `[tool.setuptools_scm]` — template block unchanged.
- `[tool.vulture]` — uncomment the template's block exactly as written
  (`paths = ["src"]`, `exclude = ["tests/"]`, `min_confidence = 70`);
  its introductory "Uncomment when enabling vulture" comment line is
  deleted. NOTE: the checker script invokes `python -m vulture src
  tests` with explicit paths, so `tests/` IS scanned (test files then
  count as uses, which reduces false positives); the config supplies
  `min_confidence`. If vulture flags legitimately dynamic names
  (pydantic validators, fixtures), raise `min_confidence` is NOT the
  fix — annotate the specific code with `# noqa`-style vulture ignore
  comments (`# vulture: ignore`) instead.
- `[tool.pymarkdown.*]` — template blocks unchanged (md013 disabled,
  md033 disabled).

### 0.3 Phase 0 tests (skeleton-only smoke)

Create `tests/unit/test_package_layout_and_metadata.py` with these exact test functions
(implementation matches the requirement; no assertions on TODOs):

- `test_package_imports() -> None` — `import pds4indextools; assert
  pds4indextools.__version__`.
- `test_py_typed_marker_present() -> None` — uses
  `importlib.resources.files('pds4indextools').joinpath('py.typed').is_file()`.
- `test_default_config_packaged() -> None` — same check for
  `templates/default_config.yaml`.
- `test_label_template_packaged() -> None` — same for
  `templates/index_label_template.xml`.

All four tests are GREEN from Phase 0 on (the §0.1 `__init__.py` stub
already exports `__version__`, and the package-data settings ship
`py.typed` and the templates). NO phase in this plan leaves RED tests
behind at phase exit.

### 0.4 Phase 0 exit criteria

- [ ] `pyproject.toml` matches Appendix A.1 byte-for-byte. (A.1 is
      the single authority per the global appendix-wins rule; the §0.2
      delta list is descriptive commentary on it.)
- [ ] `scripts/run-all-checks.sh` differs from the template script
      ONLY in the pre-existing REPONAME substitutions and the four
      enable-toggle defaults (`ENABLE_RUFF_FORMAT=true`,
      `ENABLE_MYPY=true`, `ENABLE_VULTURE=true`,
      `ENABLE_BANDIT=false`).
- [ ] `pip install -e ".[dev,docs]"` completes without errors.
- [ ] `scripts/run-all-checks.sh --pyroma` passes (the script runs
      `python -m pyroma .`); additionally `python -m pyroma --min=9 .`
      exits 0 (run manually; the script itself is not modified).
- [ ] `tests/data/` skeleton tree exists per A.7 (`expected/` dirs
      empty until Phase 11); every label fixture
      file name ends in `.lblx`; no fixture file is a byte-for-byte
      copy of another.
- [ ] `tests/conftest.py` matches Appendix A.6.
- [ ] No `pytest.ini`, `pytest.toml`, `.pytest.ini`, `.pytest.toml`,
      `tox.ini [pytest]`, or `setup.cfg [tool:pytest]` exists anywhere
      in the repo. Pytest config discovery uses the FIRST matching file
      in a fixed precedence order and `pyproject.toml` is precedence #5;
      a stray higher-precedence file silently overrides our settings
      (critique skill §22). Verified by
      `find . -maxdepth 3 \( -name pytest.ini -o -name pytest.toml -o -name .pytest.ini -o -name .pytest.toml \) -not -path './venv/*' -not -path './.venv/*' -print` returning empty,
      and by grepping `tox.ini` / `setup.cfg` (if present) for pytest sections.

---

## Phase 1 — `errors.py`

### 1.1 Module behavior

Implement the exception hierarchy of spec §17.1 EXACTLY:

```
Pds4IndexError
├── CliError
├── ConfigError
├── LabelError
│   ├── ParseError
│   ├── LidError
│   ├── XPathError
│   ├── NilError
│   └── ScrapedValueError
├── SchemaError
│   ├── SchemaResolutionError
│   ├── SchemaVersionError
│   ├── SchemaNetworkError
│   └── SchemaCacheError
├── OutputError
└── FailSlowAggregateError
```

Rules (every one MUST hold or unit tests fail):

- `Pds4IndexError` is `class Pds4IndexError(Exception):`. Its `__init__` takes
  `(self, message: str, *, file_path: Path | None = None, lineno: int | None = None)`
  and stores `self.message`, `self.file_path`, `self.lineno`. `__str__`
  returns the formatted form: `f"{file_path}:{lineno}: {message}"` when both
  `file_path` and `lineno` are set; `f"{file_path}: {message}"` when only
  `file_path` is set; `message` alone when neither is set. This guarantees
  that `logger.exception(...)` and `repr(exc)` both surface diagnostic
  context (codebase-analysis §2). `self.message` retains the raw text for
  callers that need it. `file_path` is the actual `pathlib.Path` (or
  `None`); never coerce to `str`.
- Every subclass inherits the same constructor signature unchanged.
- `FailSlowAggregateError` overrides `__init__`:
  `(self, errors: Sequence[Pds4IndexError])`. Stores `self.errors: list[Pds4IndexError]`
  as a defensive copy. `__str__` returns the count prefix (e.g.
  `"2 errors"`) followed by each sub-error's `str(e)` joined with
  `\n`. Raises `ValueError("FailSlowAggregateError requires at least one error")`
  if `errors` is empty.
- Every class and the module itself carries a PEP 257 + Google-style
  docstring per the global Docstring contract; each docstring cites the
  spec R-IDs the class implements (R-ID citations are a contract
  reference, not internal-implementation detail; documentation.mdc §4).
- Module-level constant `EXIT_USER_ERROR = 1`, `EXIT_RUNTIME_ERROR = 2`,
  `EXIT_INTERNAL_ERROR = 3`, `EXIT_SIGINT = 130`. `__all__` enumerates every
  symbol intended for public consumption (the 16 exception classes plus
  the four exit-code constants — `MappingFileError` no longer exists
  per owner decision #10 / spec-amendment #10); private helpers prefix
  with `_`.
- The R-ERR-001 fail-slow eligibility flag lives on the class as
  `FAIL_SLOW_ELIGIBLE: ClassVar[bool]`. Each class definition carries an
  inline comment giving the rationale for its value
  (`python.mdc` §4):
  - `False` on `Pds4IndexError`, `CliError`, `ConfigError`,
    `OutputError`, `SchemaNetworkError`,
    `SchemaCacheError`, `FailSlowAggregateError` — these signal
    user-input or infrastructure failures that cannot be skipped per
    label.
  - `True` on `LabelError`, `ParseError`, `LidError`, `XPathError`,
    `NilError`, `ScrapedValueError`, `SchemaError`,
    `SchemaResolutionError`, `SchemaVersionError` — per-label content
    errors that `--fail-slow` accumulates.
    (`SchemaNetworkError`/`SchemaCacheError` override back to `False`
    because they reflect environment, not label content.)

### 1.2 Unit tests — `tests/unit/test_errors_hierarchy_and_formatting.py`

Every test function is fully typed (R-TST-001..R-TST-053). Each `assert`
tests one condition (R-TST-050). Each exception test uses `pytest.raises`
as a context manager and asserts on message content (R-TST-051).

Tests required (full list — implementer writes one function per row):

| Test function | Verifies |
|---|---|
| `test_pds4indexerror_is_exception_subclass` | `issubclass(Pds4IndexError, Exception)` |
| `test_pds4indexerror_constructor_stores_message_attribute` | `err.message == "msg"` |
| `test_pds4indexerror_default_file_path_is_none` | `err.file_path is None` (constructed without `file_path=`) |
| `test_pds4indexerror_default_lineno_is_none` | `err.lineno is None` (constructed without `lineno=`) |
| `test_pds4indexerror_str_with_path_and_lineno` | `str(Pds4IndexError("msg", file_path=Path("foo.lblx"), lineno=42)) == "foo.lblx:42: msg"` |
| `test_pds4indexerror_str_with_path_only` | `str(Pds4IndexError("msg", file_path=Path("foo.lblx"))) == "foo.lblx: msg"` |
| `test_pds4indexerror_str_no_path` | `str(Pds4IndexError("msg")) == "msg"` |
| `test_pds4indexerror_file_path_kept_as_path_object` | `isinstance(err.file_path, Path)` for a Path-constructed error |
| `test_all_subclasses_inherit_from_pds4indexerror` | parametrize over the 15 subclasses |
| `test_subclass_hierarchy_label_error_subclasses` | parametrize ParseError, LidError, XPathError, NilError, ScrapedValueError each `issubclass(LabelError)` |
| `test_subclass_hierarchy_schema_error_subclasses` | parametrize 4 schema subclasses each `issubclass(SchemaError)` |
| `test_fail_slow_eligible_flag_label_errors_true` | parametrize 6 LabelError-tree classes; `FAIL_SLOW_ELIGIBLE is True` |
| `test_fail_slow_eligible_flag_schema_subclasses` | SchemaError itself, SchemaResolutionError, and SchemaVersionError True; SchemaNetworkError + SchemaCacheError False |
| `test_fail_slow_eligible_flag_user_errors_false` | parametrize Pds4IndexError, CliError, ConfigError, OutputError, FailSlowAggregateError each False |
| `test_failslowaggregateerror_stores_errors_list` | passes a `[LidError, ParseError]` list; checks list equality |
| `test_failslowaggregateerror_empty_list_raises_valueerror` | empty list → `ValueError`; assert `"at least one"` substring in message |
| `test_failslowaggregateerror_errors_is_defensive_copy` | mutating input list does not mutate `err.errors` |
| `test_failslowaggregateerror_str_starts_with_count_prefix` | aggregate of 2 sub-errors → `str(...).startswith("2 errors")` |
| `test_failslowaggregateerror_str_contains_first_sub_message` | aggregate `str(...)` substring contains first sub-error's formatted form |
| `test_failslowaggregateerror_str_contains_second_sub_message` | same for second sub-error |
| `test_failslowaggregateerror_str_separates_messages_with_newline` | aggregate `str(...)` contains `"\n"` between sub-error messages |
| `test_exit_code_constants` | parametrize EXIT_USER_ERROR==1, EXIT_RUNTIME_ERROR==2, EXIT_INTERNAL_ERROR==3, EXIT_SIGINT==130 |
| `test_all_exports_match_module_public_surface` | `set(errors.__all__) == {public names}` |
| `test_raise_from_chains_traceback` | raising `ParseError(...)` with `raise ParseError("x") from ValueError("y")` preserves `__cause__`, and `str(exc_info.value.__cause__).startswith("y")` |
| `test_pds4indexerror_message_attribute_preserves_raw_text` | `Pds4IndexError("raw", file_path=Path("x"), lineno=3).message == "raw"` |
| `test_subclass_str_format_inherited` | `LidError("msg", file_path=Path("a"), lineno=7)` formats as `"a:7: msg"` |

### 1.3 Phase 1 exit criteria

- [ ] `pytest tests/unit/test_errors_hierarchy_and_formatting.py` GREEN.
- [ ] `ruff check src tests` clean.
- [ ] `ruff format --check src tests` clean.
- [ ] `mypy src tests` clean.
- [ ] `coverage report --include="src/pds4indextools/errors.py"` shows 100%
      line+branch.

---

## Phase 2 — `_logging.py`

### 2.1 Module behavior

Implements R-LOG-001..R-LOG-021. The module is `_logging` because
`setup_logging` and `library_setup` are package-internal (only
`cli/_dispatch.py:main` invokes them). The single PUBLIC symbol
`module_logger` is re-exported from `pds4indextools/__init__.py` so
consumer modules can `from pds4indextools import module_logger` rather
than reach into the private `_logging` module. `_logging.__all__` is
empty; `__init__.py.__all__` includes `module_logger`.

The `pds4indextools` logger keeps `propagate = True` (spec R-LOG-003:
library users inherit the root-logger configuration; ALSO required for
pytest's `caplog`, whose capture handler sits on the ROOT logger — with
propagation off, no `caplog` assertion in this plan could ever see a
record). Duplicate-handler protection comes from `setup_logging`'s
idempotence check, not from disabling propagation. Tests that use
`caplog` still call
`caplog.set_level(logging.DEBUG, logger='pds4indextools')` to open the
level gate (critique skill §21).

Public symbols (none in this module's `__all__` since the file is private;
`module_logger` is re-exported from the package init):

- `setup_logging(verbosity: int) -> None`: configures the root
  `pds4indextools` logger. `verbosity` in {0,1,2,3} maps to {WARNING, INFO,
  DEBUG, DEBUG} (R-CLI-017, R-LOG-010). Values outside {0,1,2,3} raise
  `ValueError(f"verbosity must be 0..3, got {verbosity}")`. argparse
  caps `-v` counts at 3 (passing 4+ `v`s yields verbosity=4 which the
  CLI clamps to 3 before calling `setup_logging`; see Phase 10). The
  CLI's `_dispatch` clamps explicitly:
  `verbosity = min(ns.verbose, 3)`.
  Idempotent — calling twice does not duplicate handlers. The rendered
  format is `LEVEL [module] message` with the SHORT module name
  (R-LOG-002: `[cli]`, `[scraper]` — not `[pds4indextools.cli]`),
  implemented with a private formatter:

  ```python
  class _ShortNameFormatter(logging.Formatter):
      """Render ``LEVEL [module] message`` with the short module name."""

      def format(self, record: logging.LogRecord) -> str:
          record.shortname = record.name.removeprefix('pds4indextools.')
          return super().format(record)
  ```

  constructed as
  `_ShortNameFormatter('%(levelname)s [%(shortname)s] %(message)s')`.
  Handlers attach a single `logging.StreamHandler(sys.stderr)`
  (R-LOG-001/002). Sets the root `pds4indextools` logger level; does
  NOT call `logging.basicConfig`.
- `library_setup() -> None`: called once at module import time (from
  `pds4indextools/__init__.py`). Attaches a `logging.NullHandler` to the
  `pds4indextools` logger IFF no `NullHandler` is already attached
  (idempotent: re-import / module reload does not stack handlers).
  Implementation:

  ```python
  logger = logging.getLogger('pds4indextools')
  if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
      logger.addHandler(logging.NullHandler())
  ```

  Propagation is left enabled (R-LOG-003); the `NullHandler` only
  silences the "No handlers could be found" fallback for library
  consumers.

  Library consumers see no output if they have not configured logging
  (`.cursor/rules/logging.mdc` library-logging rule).
- `progress_bar(total: int, *, description: str) -> tqdm`: returns a
  `tqdm` instance configured per R-LOG-020/021. `disable` is forced True
  when `not sys.stderr.isatty()`. The caller is responsible for `with` /
  `close()` lifecycle.
- `module_logger(name: str) -> logging.Logger`: shorthand for
  `logging.getLogger(f'pds4indextools.{name}')`.

### 2.2 Unit tests — `tests/unit/test_logging_configuration_and_progress.py`

Use `caplog` to capture log records (critique skill §21). Each test that
mutates logger state uses `monkeypatch` to restore on teardown (critique skill
§14 cleanup rule).

| Test function | Verifies |
|---|---|
| `test_setup_logging_verbosity_parametrized` | parametrize (verbosity, expected_level) over (0, WARNING), (1, INFO), (2, DEBUG), (3, DEBUG); call `setup_logging(v)`; assert `logging.getLogger('pds4indextools').getEffectiveLevel() == expected_level`; assert a child logger `pds4indextools.test` inherits the same effective level |
| `test_setup_logging_verbosity_negative_raises` | `ValueError` with `"verbosity"` in message |
| `test_setup_logging_verbosity_4_raises` | `ValueError` |
| `test_setup_logging_idempotent` | calling twice does not duplicate `StreamHandler` instances |
| `test_setup_logging_format_string` | call `setup_logging(0)`; use `caplog.set_level(WARNING, logger='pds4indextools')`; emit `module_logger('test').warning('msg')`; assert exactly one record with `record.levelname == 'WARNING'`, `record.name == 'pds4indextools.test'`, `record.getMessage() == 'msg'`; assert formatted stderr (via `capsys`) equals `"WARNING [test] msg\n"` byte-for-byte (short module name per R-LOG-002) |
| `test_setup_logging_emits_to_stderr` | uses `capsys`; record body appears in `capsys.readouterr().err` and not `out` |
| `test_setup_logging_keeps_propagation_enabled` | after `setup_logging(0)`, `logging.getLogger('pds4indextools').propagate is True` (R-LOG-003; `caplog` capture depends on root propagation) |
| `test_library_setup_attaches_nullhandler` | after import (no `setup_logging` call), `pds4indextools` logger has at least one `NullHandler` |
| `test_library_setup_does_not_affect_root_logger` | `logging.getLogger().handlers` unchanged |
| `test_progress_bar_tty_enabled` | `monkeypatch.setattr(sys, 'stderr', <delegating wrapper whose isatty() returns True>)` (mirror of A.6's `_NonTtyStream`; patching `isatty` directly on a real `TextIOWrapper` raises `AttributeError`); `progress_bar(...).disable is False` |
| `test_progress_bar_non_tty_disabled` | same wrapper with `isatty() -> False`; `.disable is True` |
| `test_progress_bar_total_set` | `progress_bar(5, description='x').total == 5` |
| `test_module_logger_namespacing` | `module_logger('scraper').name == 'pds4indextools.scraper'` |
| `test_module_logger_inherits_from_root_pds4_logger` | child logger's `parent.name == 'pds4indextools'` |

### 2.3 Phase 2 exit criteria

- [ ] `pytest tests/unit/test_logging_configuration_and_progress.py` GREEN.
- [ ] Lint+mypy clean.
- [ ] Coverage on `_logging.py` ≥ 95% line+branch.

---

## Phase 3 — `config.py`

### 3.1 Module behavior

Implements §15 (R-CFG-010..R-CFG-052) plus `IndexConfig` and friends per
§15.2. The pydantic models match the spec sketch but are real classes with
docstrings and explicit `Annotated[]` types. Public symbols enumerated in
`__all__` (re-exported from package `__init__` per Phase 10):

- `IndexConfig`, `LabelContents`, `OutputSection`, `NillableEntry`,
  `CitationInformation`, `ModificationDetail`, `ColumnSpec`,
  `AUTO_COLUMN_TOKENS`.
- `AbsolutePath = Annotated[Path, AfterValidator(_require_absolute)]`.
- `load_config(paths: Sequence[Path]) -> IndexConfig` — entry point.
  Loads each YAML in order onto the packaged default; deep-merges;
  validates; returns `IndexConfig`. Raises `ConfigError` (subclass per
  §17.1) wrapping any `pydantic.ValidationError` or YAML parse error via
  `raise ... from`. Each `ConfigError` carries `file_path` (the offending
  YAML) and `lineno` (best-effort; pydantic errors usually have `loc`
  not lineno, so set `lineno=None`).

  Boundary validation (codebase-analysis §7): for each `path` in `paths`:
  - `if not path.exists(): raise ConfigError(f"config file does not exist: {path}", file_path=path) from None`
  - `if not path.is_file(): raise ConfigError(f"config file is not a regular file: {path}", file_path=path) from None`
  - `if not os.access(path, os.R_OK): raise ConfigError(f"config file is not readable: {path}", file_path=path) from None`
  Validation happens at the function boundary; all subsequent code may
  assume the path is openable.
- `_deep_merge(base: dict, overlay: dict) -> dict` (private, R-CFG-050).
- `_require_absolute(p: Path) -> Path` raises `ValueError` (consumed by
  pydantic) if `not p.is_absolute()`. Message includes `str(p)`.
- `_load_default_config() -> dict` reads
  `templates/default_config.yaml` via `importlib.resources` (R-CFG-201
  uses the same file).
- `_reserved_label_content_keys() -> frozenset[str]` returns the set listed
  in R-LBL-012 (eleven names). `LabelContents` has a `@model_validator(mode='after')`
  that raises `ValueError("reserved BASE variable name '{k}' must not appear in label_contents")`
  if any reserved key is in the model's `__pydantic_extra__`.

**Columns configuration** (owner decision #10; spec-amendment #9 —
this replaces the former mapping-file format):

```python
AUTO_COLUMN_TOKENS: frozenset[str] = frozenset({
    'lid', 'lidvid', 'filespec', 'filename', 'bundle_name',
})  # R-AUTO-001


class ColumnSpec(BaseModel):
    model_config = {'extra': 'forbid'}  # future per-column keys are added deliberately
    xpath: str | None = None  # canonical XPath selector
    auto: str | None = None   # one of AUTO_COLUMN_TOKENS
    name: str | None = None   # emitted header; None/blank -> selector text
```

Binding rules:

- Exactly ONE of `xpath`/`auto` per entry (model validator; the error
  names the offending entry's zero-based index).
- `auto` must be a member of `AUTO_COLUMN_TOKENS`; the error message
  names the bad token AND lists the five valid tokens (covers the old
  R-MAP-013 typo diagnostics).
- `xpath` must contain no internal whitespace (R-MAP-040 analog).
- `ColumnSpec.header` property: `name.strip()` when non-blank, else
  the selector text verbatim (R-MAP-012.1 analog: an omitted rename
  uses the raw XPath/auto token as the header).
- `name` charset per R-MAP-043: printable ASCII 0x20–0x7E only, no
  comma, no `"`.
- `IndexConfig.columns: list[ColumnSpec] | None = None` — OPTIONAL at
  load time (`generate_xpath_list` / `copy_default_config` runs need no
  columns). `run_generate_index_file` raises
  `ConfigError("no columns defined in config; run generate_xpath_list to produce a starter columns block")`
  when the merged value is `None` (Phase 10). An explicitly EMPTY list
  is rejected at validation time (R-MAP-312).
- List-level validator: duplicate selectors (R-MAP-030) and duplicate
  resulting headers (R-MAP-031) are `ConfigError`s citing both entry
  indexes.
- Merging: like every list, `columns` is replaced WHOLESALE by a later
  config file in the chain (R-CFG-050).
- Emitted column order is declaration order (R-MAP-320).

`OutputSection.sort_by` validation: each entry is a string `"+col"`, `"-col"`,
or `"col"` (leading sign optional). A separate helper
`parse_sort_key(spec: str) -> tuple[str, bool]` returns `(column_name,
descending)`. Empty list keeps default `[]` (R-SORT-010). The
`OutputSection` validator only checks string shape; column-existence is
checked later by `csv_writer.sort_rows` (R-SORT-020) which raises
`ConfigError`.

`LabelContents.Modification_Detail` normalization happens at the boundary
between config load and template substitution (Phase 9, `label_writer`),
NOT in the pydantic model. The pydantic field accepts
`list[ModificationDetail] | ModificationDetail | None`. The field is
entirely OPTIONAL in user configs; when it is absent (or `None`),
Phase 9's `normalize_modification_detail` GENERATES a default
single-entry modification history (owner decision #3) — the config
layer performs no defaulting itself.

### 3.2 Unit tests — `tests/unit/test_config_loading_and_merging.py`

Every test in this file imports ONLY public names from
`pds4indextools.config` (critique skill §20); private helpers are
exercised exclusively through `load_config` and the public models. The
same boundary rule applies to
`test_xpath_canonicalization_and_renumbering.py`,
`test_csv_writing_quoting_and_sorting.py`,
`test_label_template_substitution.py`, and
`test_label_scraping_and_validation.py`.

| Test function | Verifies | T-ID |
|---|---|---|
| `test_load_default_only_is_valid_modulo_missing_label_contents` | merging zero user configs leaves `label_contents` missing → `ConfigError` w/ "logical_identifier" and "product_class" both in message | R-CFG-030, R-CFG-031 |
| `test_load_default_has_nillable_defaults` | direct `_load_default_config()['nillable']` contains the 6 dtypes per A.4 | spec §15.6 |
| `test_load_yaml_scalar_top_level_rejected` | YAML `"hello"` → `ConfigError` w/ "must be a mapping" | T-CFG-001, R-CFG-011 |
| `test_load_yaml_list_top_level_rejected` | YAML `[]` → `ConfigError` | R-CFG-011 |
| `test_load_yaml_null_top_level_rejected` | YAML `null` → `ConfigError` | R-CFG-011 |
| `test_top_level_extra_key_rejected` | top-level key `foo: bar` → ConfigError naming `foo` | T-CFG-010, R-CFG-020 |
| `test_output_extra_key_rejected` | `output.bogus: 1` → `ConfigError` | T-CFG-011, R-CFG-021 |
| `test_label_contents_extra_key_accepted` | `label_contents.custom_var: "x"` accepted; appears in `model.label_contents.model_extra` | T-CFG-012, R-CFG-022 |
| `test_nillable_extra_nilreason_rejected` | `nillable.pds:ASCII_Integer.frobnicate: 5` → `ConfigError` | T-CFG-013, R-CFG-023 |
| `test_nillable_custom_dtype_accepted` | adding `pds:ASCII_NonNegative_Integer` with all 4 nilreasons accepted | T-CFG-014, R-CFG-023 |
| `test_missing_logical_identifier_rejected` | `label_contents:` w/o `logical_identifier` → `ConfigError` naming the field | T-CFG-020, R-CFG-030 |
| `test_missing_product_class_rejected` | same w/o `product_class` → `ConfigError` | T-CFG-021, R-CFG-031 |
| `test_product_class_invalid_literal_rejected` | `product_class: Product_Bogus` → `ConfigError` w/ literal-mismatch msg | T-LBL-022, R-LBL-010 |
| `test_relative_path_in_xsd_cache_dir_rejected` | `xsd_cache_dir: ./cache` → `ConfigError` w/ "must be absolute" and the path text | T-CFG-030, R-CFG-040 |
| `test_absolute_path_in_xsd_cache_dir_accepted` | `xsd_cache_dir: /tmp/xsd_cache` (POSIX) or `C:\xsd_cache` (Win) accepted; parametrized by `os.name` | R-CFG-040, R-CFG-024 |
| `test_three_config_merge_order` | three YAMLs: A sets `output.fixed_width: false`, B sets it true, C sets it false → final value False | T-CFG-040, R-CFG-050 |
| `test_three_config_merge_dict_deep_merge` | A has `nillable.pds:ASCII_Real.inapplicable: -1.0`; B adds `nillable.pds:ASCII_Real.missing: -2.0` (deep merge keeps both keys) | T-CFG-040, R-CFG-050 |
| `test_three_config_merge_list_replacement` | A has `output.sort_by: ['a']`; B has `output.sort_by: ['b','c']` → final is `['b','c']` | T-CFG-040, R-CFG-050 |
| `test_partial_individual_configs_accepted_after_merge` | only B supplies `label_contents`; A and C don't → validation passes | T-CFG-050, R-CFG-052 |
| `test_reserved_label_contents_key_rejected_index_file_name` | `label_contents.index_file_name: "x"` → `ConfigError` naming `index_file_name` | R-LBL-012 |
| `test_reserved_label_contents_key_rejected_field_content` | same for `Field_Content` | R-LBL-012 |
| `test_reserved_label_contents_keys_parametrized_full_set` | parametrize all 11 reserved names | R-LBL-012 |
| `test_yaml_parse_error_wrapped_in_configerror` | invalid YAML `"x:\n y: z\n  q"` → `ConfigError`. Assert (a) `isinstance(exc_info.value.__cause__, yaml.YAMLError)`, (b) `exc_info.value.file_path == Path(test_yaml_path)`, (c) `"yaml"` or `"parse"` substring in `str(exc_info.value)` | R-CFG-010 |
| `test_load_config_nonexistent_file_raises` | path doesn't exist → `ConfigError`; assert `"does not exist"` in message and `exc_info.value.file_path == path` | codebase-analysis §7 |
| `test_load_config_directory_path_raises` | path is a directory → `ConfigError`; assert `"not a regular file"` in message | codebase-analysis §7 |
| `test_load_config_unreadable_file_raises` | use `chmod 000`; assert `"not readable"` in message; restore permissions in teardown (skip on Windows) | codebase-analysis §7 |
| `test_parse_sort_key_no_sign_defaults_ascending` | `parse_sort_key('lid') == ('lid', False)` | R-SORT-020 |
| `test_parse_sort_key_minus_descending` | `parse_sort_key('-lid') == ('lid', True)` | R-SORT-020 |
| `test_parse_sort_key_plus_ascending` | `parse_sort_key('+lid') == ('lid', False)` | R-SORT-020 |
| `test_parse_sort_key_double_sign_rejected` | `parse_sort_key('--lid')` → `ValueError`; assert `"invalid sort key"` substring in `str(exc_info.value)` | R-SORT-020 |
| `test_parse_sort_key_empty_rejected` | `parse_sort_key('')` → `ValueError`; assert `"empty"` in `str(exc_info.value)` | R-SORT-020 |
| `test_load_config_relative_path_resolved_at_call_site` | this is NOT a config validation concern; `load_config` accepts whatever `Path` is passed (caller resolves via `Path.absolute()`). Add a sanity test that `load_config([Path('relative.yaml').absolute()])` works given a fixture file. | R-FS-001 |
| `test_load_config_error_includes_file_path_attribute` | bad YAML → raised `ConfigError.file_path == Path(bad_yaml_path)` | spec error-model |
| `test_load_config_error_uses_raise_from` | `ConfigError.__cause__` is the underlying pydantic ValidationError or YAMLError | python.mdc §2 |
| `test_load_config_with_freezegun_mtime_unaffected` | use freezegun to advance time; reload same file; result equal — proves load is pure | critique skill §15 |
| `test_columns_missing_is_allowed_at_load` | config without `columns` loads; `IndexConfig.columns is None` (the required-for-index check lives in Phase 10) | spec-amendment #9 |
| `test_columns_empty_list_rejected` | `columns: []` → ConfigError; `"empty"` in message | R-MAP-312 |
| `test_columns_entry_requires_exactly_one_selector` | parametrize: both `xpath` and `auto` set → ConfigError; neither set → ConfigError; each names the entry index | spec-amendment #9 |
| `test_columns_unknown_auto_token_rejected` | `auto: filenmae` → ConfigError containing the typo AND the five valid tokens | R-MAP-013 diagnostics |
| `test_columns_auto_all_five_accepted` | parametrize `lid,lidvid,filespec,filename,bundle_name` | R-AUTO-001 |
| `test_columns_name_defaults_to_selector` | entry without `name` (and entry with `name: '   '`) → `header` equals the selector text | R-MAP-012.1 |
| `test_columns_duplicate_selector_rejected` | two entries with the same `xpath` (and two with the same `auto`) → ConfigError citing both indexes | R-MAP-030 |
| `test_columns_duplicate_name_rejected` | two entries resolving to the same header → ConfigError citing both indexes | R-MAP-031 |
| `test_columns_name_charset_enforced` | parametrize bad names: contains `"`; contains `,`; contains `\x07`; contains `é` → ConfigError each | R-MAP-043 |
| `test_columns_xpath_internal_whitespace_rejected` | `xpath: 'pds:A <1>'` → ConfigError | R-MAP-040 analog |
| `test_columns_entry_extra_key_rejected` | `{xpath: ..., name: ..., frobnicate: 1}` → ConfigError naming `frobnicate` (extra='forbid'; future per-column keys are added deliberately) | future-proofing |
| `test_columns_order_preserved` | three entries → `IndexConfig.columns` order matches declaration order | R-MAP-320 |
| `test_columns_list_replaced_wholesale_on_merge` | config A: 3 columns; config B: 1 column → merged has exactly B's 1 | R-CFG-050 |

Fixture files needed: see Appendix A.10 for full YAML content (nine
`test_config_*` snippets plus the feature configs). Place at
`tests/data/configs/`. The three-YAML merge tests
(`test_three_config_merge_*`) write their input YAMLs inline via
`tmp_path` rather than using committed fixtures.

### 3.3 Phase 3 exit criteria

- [ ] `pytest tests/unit/test_config_loading_and_merging.py` GREEN.
- [ ] Coverage on `config.py` ≥ 95% line+branch.
- [ ] mypy strict clean.

---

## Phase 4 — (absorbed into Phase 3)

The separate mapping-file format is REMOVED (owner decision #10;
spec-amendments #9–#12). There is no `mapping.py` module and no
mapping-file parser: column selection and renaming are the `columns:`
section of the config schema, delivered and tested in Phase 3. Phase
numbering is kept stable so cross-references remain valid; proceed
directly from Phase 3 to Phase 5.

---

## Phase 5 — `xpath_norm.py`

### 5.1 Module behavior

Implements §10 (R-XP-001..R-XP-030). Public functions:

- `canonicalize_xpath(raw: str, nsmap: Mapping[str, str | None]) -> str`
  — converts an lxml-native XPath (e.g.
  `/{http://pds.nasa.gov/pds4/pds/v1}Product_Observational[2]/{http://...}foo[1]`)
  into the canonical form. Returns the canonical string. R-XP-001..R-XP-003,
  R-XP-010..R-XP-013. Raises `ParseError` if the default namespace is not
  declared in `nsmap` (R-XP-013).
- `renumber_xpaths(xpaths: Sequence[str]) -> dict[str, str]` — takes a list of
  already-canonicalized XPaths in **walk order** (pre-order DOM traversal,
  see §9.2) and returns a `dict` mapping each input to its renumbered form.
  R-XP-020..R-XP-030. Raises `XPathError` on non-monotone interleave
  (R-XP-021) citing the offending XPath and the prior conflicting key.

Helper namedtuple (private):

```python
@dataclass(frozen=True, slots=True)
class _XPathPart:
    raw_segment: str       # e.g. "{ns}Tag[2]"
    namespace_uri: str     # e.g. "http://pds.nasa.gov/pds4/pds/v1"
    local_name: str        # e.g. "Tag"
    raw_index: int         # the [n] from lxml; 1 if absent
```

Algorithm for `canonicalize_xpath`:

1. Split `raw` on `/` (after stripping a leading `/`).
2. For each segment parse `_XPathPart` via a tightly-scoped regex
   `_SEGMENT_RE = re.compile(r'^\{(?P<ns>[^}]+)\}(?P<name>[^{}/\[\]]+)(?:\[(?P<idx>\d+)\])?$')`.
   The element NAME is deliberately NOT constrained to ASCII: lxml has
   already validated every parsed element as a legal XML name, and XML
   names may contain non-ASCII characters. The spec's ASCII-only rules
   apply ONLY to scraped values (R-VAL-020/030) and column `name`
   values (R-MAP-043); they do NOT extend to
   element names, and the canonicalizer MUST NOT reject a label because
   a tag name contains a non-ASCII character (owner decision #5). The
   regex rejects only structurally malformed segments (missing `{ns}`
   braces, empty name, malformed `[n]` predicate) →
   `ParseError("malformed lxml xpath segment ...")`.
3. Map each `namespace_uri` to a prefix via the **inverse** of `nsmap`. The
   default namespace (`nsmap[None]`) becomes prefix `pds:` (R-XP-010). If
   `nsmap[None] is None` raise `ParseError("label root element declares no default namespace")`.
4. Compose `f"{prefix}:{local_name}<{raw_index}>"`.
5. Return forward-slash join (R-XP-003).

Algorithm for `renumber_xpaths`:

The grouping key, called `bucket_key`, is the tuple
`(parent_canonical_path, prefix_local_name)` where:
- `parent_canonical_path` is the entire canonical XPath string up to
  (but not including) the segment being renumbered, e.g. for
  `pds:A<1>/pds:B<2>/pds:C<5>` the parent of `pds:C<5>` is
  `"pds:A<1>/pds:B<2>"` and for `pds:A<1>` the parent is `""`.
- `prefix_local_name` is the segment's `prefix:local_name` text without
  the `<n>` predicate, e.g. `"pds:C"`.

Steps:

1. Iterate input keys in walk-order (preserving insertion order).
2. For each key, split into segments. For each prefix-of-segments
   (from left to right), construct `bucket_key`.
3. For each `bucket_key`, build an ordered list of distinct
   `raw_index` values in first-seen order. The renumber map is
   `{raw_index: position_in_list + 1}`.
4. **Non-monotone detection (R-XP-021), precise rule:** for each
   `bucket_key`, track `bucket_max: dict[bucket_key, int]`, the largest
   `raw_index` seen so far in that bucket, plus the XPath key that set
   it. While iterating in walk order, a segment whose `raw_index` is
   STRICTLY LESS than its bucket's current `bucket_max` raises
   `XPathError(f"non-monotone interleave at {xpath}; conflicts with {prior_xpath}")`
   (where `prior_xpath` is the key that set `bucket_max`). Indexes
   EQUAL to an already-seen value are fine (every descendant key
   repeats its ancestors' segments); strictly increasing values are
   fine. This matches pre-order DOM traversal, which can never revisit
   a lower sibling index after advancing past it.
5. Build the renumbered XPath by applying the per-bucket renumber map
   to every segment.

A worked example for the unit-test anchor:

- Input: `['pds:A<2>/pds:B<1>', 'pds:A<1>/pds:B<1>']`
- First key: `pds:A<2>/pds:B<1>` — bucket `("", "pds:A")` sees `2`;
  bucket `("pds:A<1>", "pds:B")` sees `1` (after renumbering A<2> to
  A<1>).
- Second key: `pds:A<1>/pds:B<1>` — bucket `("", "pds:A")` would now
  see `1`, but `2` was already seen (the bucket is "closed" because a
  higher index appeared before this one).
- The renumberer raises `XPathError`.

Concrete-output anchor for T-XP-020:
- Input: `['pds:A<2>', 'pds:A<5>', 'pds:A<7>']`
- Output dict: `{'pds:A<2>': 'pds:A<1>', 'pds:A<5>': 'pds:A<2>', 'pds:A<7>': 'pds:A<3>'}`.

### 5.2 Unit tests — `tests/unit/test_xpath_canonicalization_and_renumbering.py`

| Test function | Verifies | T-ID |
|---|---|---|
| `test_canonicalize_default_namespace_aliased_to_pds` | `/{pds_ns}Product_Observational[1]` → `pds:Product_Observational<1>` | T-XP-001, R-XP-010 |
| `test_canonicalize_non_default_namespace_prefix_preserved` | `geom` namespace → `geom:Foo<1>` | T-XP-002, R-XP-011 |
| `test_canonicalize_single_occurrence_emits_predicate_1` | absent `[n]` in input still produces `<1>` | T-XP-010, R-XP-002 |
| `test_canonicalize_nested_path_multiple_segments` | three-segment path canonicalizes all segments | R-XP-003 |
| `test_canonicalize_no_default_namespace_raises_parseerror` | `nsmap[None] is None` → ParseError w/ "no default namespace" | T-XP-022, R-XP-013 |
| `test_canonicalize_malformed_segment_raises_parseerror` | input `/foo[1]` (no namespace braces) → ParseError | edge case |
| `test_canonicalize_segment_with_dot_in_localname` | `{ns}Foo.Bar[1]` → `pds:Foo.Bar<1>` | regex coverage |
| `test_canonicalize_non_ascii_element_name_accepted` | `{ns}Résumé[1]` → `pds:Résumé<1>` — element names are NOT ASCII-restricted; only values/mapping files are | owner decision #5 |
| `test_renumber_three_siblings_2_5_7_to_1_2_3` | input `[a<2>, a<5>, a<7>]` → `<1>, <2>, <3>` | T-XP-020, R-XP-020 |
| `test_renumber_preserves_unique_indexes_when_already_monotone` | `[a<1>, b<1>, c<1>]` → unchanged | R-XP-020 |
| `test_renumber_handles_multiple_parents_independently` | two distinct parents each renumbered separately | R-XP-020 |
| `test_renumber_non_monotone_interleave_raises_xpatherror` | sequence triggering R-XP-021 | T-XP-021, R-XP-021 |
| `test_renumber_first_occurrence_order_preserved` | dict iteration order matches input order | T-XP-030, R-XP-030, R-XPL-010 |
| `test_renumber_input_output_invariants_parametrized` | parametrize over inputs ∈ {`[]`, `['pds:A<1>']`, `['pds:A<2>', 'pds:A<5>']`, `<already-renumbered output>`}; for each: assert (a) `set(out.keys()) == set(inputs)`, (b) `list(out.keys()) == list(inputs)` (order preserved), (c) feeding `list(out.values())` back through `renumber_xpaths` is its own identity (idempotence on renumbered form) | R-XP-020, R-XP-030 (critique skill §5+§9) |
| `test_canonicalize_xpath_with_single_segment` | root-only path `/{ns}Foo[1]` → `pds:Foo<1>` | edge case |

### 5.3 Phase 5 exit criteria

- [ ] All tests pass.
- [ ] Coverage ≥ 95%.
- [ ] mypy + ruff clean.

---

## Phase 6 — `schema_types.py`

### 6.1 Module behavior

Implements §11 (R-SCH-010..R-SCH-070) plus R-FS-005 (URL scheme handling).

Public surface:

- `class SchemaCache` — encapsulates cache directory + download.
  Constructor: `SchemaCache(cache_dir: Path | None = None, *, session: requests.Session | None = None, timeout: float = 30.0)`.
  `cache_dir is None` triggers
  `platformdirs.user_cache_dir('pds4indextools')` (R-SCH-020).
  **Import platformdirs as `import platformdirs` and call
  `platformdirs.user_cache_dir(...)` so it is patchable at one
  location.** Do NOT use `from platformdirs import user_cache_dir`
  (critique skill §7 — patch at lookup location).
  `session is None` triggers a fresh `requests.Session()` with:
  - a `requests_file.FileAdapter()` mounted on `file://` (R-FS-005);
  - `session.verify = True` (SSL on; not user-overridable);
  - `session.max_redirects = 5`;
  - `User-Agent` header set to `f"rms-pds4indextools/{__version__}"`;
  (codebase-analysis §7 security defaults).

  Methods:
  - `fetch(url: str) -> bytes` — returns the body bytes. Cache-miss
    download path; cache-hit reads the file. R-SCH-020, R-SCH-060,
    R-SCH-070. **Atomic write**: download to
    `<cache_dir>/<sha256>.xsd.tmp.<pid>` then `os.replace` to the final
    `<sha256>.xsd` so concurrent xdist workers cannot interleave or
    leave partial files (critique skill §6; ensures
    `test_no_xsd_redownload_within_session` is robust).
    Refuses to cache URLs containing user-info: if
    `urllib.parse.urlparse(url).username or .password`, raises
    `SchemaCacheError("URL contains userinfo; refuse to cache")`
    (codebase-analysis §7).
  - `parse_xsd(url: str) -> etree._Element` — `fetch` then
    `etree.fromstring`; raises `SchemaCacheError` on malformed cached
    XML (R-SCH-070), `SchemaNetworkError` on download failure
    (R-SCH-060). Module-level docstring notes the cache is
    single-threaded; concurrent in-process callers MUST serialize
    externally (codebase-analysis §5).
- `class SchemaTypeResolver` — encapsulates per-run XSD trees +
  namespace-URL bookkeeping. Constructor:
  `SchemaTypeResolver(cache: SchemaCache)`. Methods:
  - `register_label(label_path: Path, root: etree._Element) -> None` —
    parses `xsi:schemaLocation`, downloads/loads each XSD, enforces
    R-SCH-040 (one URL per namespace within a single run). Raises
    `SchemaVersionError` if the same namespace points to a new URL.
  - `resolve(xpath_leaf_tag: str) -> str` — runs the 22-query chain
    enumerated VERBATIM in [Appendix G](#appendix-g--22-xsd-resolution-xpath-queries).
    The namespace prefix is preserved exactly as it appears in the
    XSD; the consumer strips the prefix before writing into the label
    per spec §11.3. Raises
    `SchemaResolutionError(f"no PDS4 base type for {xpath_leaf_tag}")`
    if all queries return empty across all registered XSDs (R-SCH-050).
  - `auto_column_type(token: str) -> str` — returns the hard-coded
    type for one of the five auto-columns per §8.2; raises
    `KeyError` if token isn't one of the five (caller guarantees it).
- `_URL_SCHEMES_WITH_BUILTIN_ADAPTERS: tuple[str, ...] = ('http', 'https', 'file')`
  — module-level **private** constant; advisory (R-FS-005 says other
  schemes succeed iff the user registered an adapter). Underscored per
  `python.mdc` §1.
- `_DEFAULT_TIMEOUT_SECONDS = 30.0` — module-level constant (R-SCH-010).
- Private helper `_xsd_query(xsd_tree: etree._Element, target_name: str, namespaces: dict[str, str]) -> str | None` — implements the 22-query chain enumerated in [Appendix G](#appendix-g--22-xsd-resolution-xpath-queries). The module-level docstring reproduces the 22 query strings verbatim from Appendix G with one sentence per query stating its rationale.

Auto-column type table (R-AUTO-001/§8.2; module-level frozen mapping):

```python
from types import MappingProxyType
from collections.abc import Mapping

AUTO_COLUMN_TYPES: Mapping[str, str] = MappingProxyType({
    'lid':         'pds:ASCII_LID',
    'lidvid':      'pds:ASCII_LIDVID_LID',
    'filespec':    'pds:ASCII_File_Specification_Name',
    'filename':    'pds:ASCII_File_Name',
    'bundle_name': 'pds:ASCII_Text_Preserved',
})
# Frozen view prevents accidental mutation by callers (codebase-analysis §5).
```

### 6.2 Unit tests — `tests/unit/test_schema_cache_and_type_resolution.py`

Use the `responses` library (added to dev deps in Phase 0) to mock HTTP
GETs. Each test requests the `isolated_xsd_cache` fixture (function-
scoped per test, defined in `tests/conftest.py`). Real network is OFF
in ALL tests except those explicitly marked `live`: unit tests mock
HTTP with `responses`, and non-live integration tests resolve schemas
from the pre-seeded cache (`seeded_xsd_cache` / `seeded_cache_overlay`
in A.6). Only `@pytest.mark.live` tests hit pds.nasa.gov (R-TST-030 as
amended).

Provide minimal hand-curated XSD snippets as test fixtures under
`tests/data/xsd_cache_seed/` — full content in Appendix A.11. Each snippet
declares one or two simple types resolvable by the 22-query chain.

Sanctioned exception to the public-names test boundary: the
`test_schemacache_session_*` rows below inspect `cache._session`
defaults directly — the internally constructed session has no public
accessor and warrants none.

| Test function | Verifies | T-ID |
|---|---|---|
| `test_schemacache_cache_miss_downloads_and_caches` | first `fetch(url)` issues HTTP GET; cache file created at sha256(url).xsd; second call no HTTP GET | T-SCH-001, T-SCH-002, R-SCH-010, R-SCH-020 |
| `test_schemacache_uses_platformdirs_when_dir_none` | monkeypatch `platformdirs.user_cache_dir`; verify `SchemaCache().cache_dir` is the patched path | R-SCH-020 |
| `test_schemacache_network_failure_raises_schemanetworkerror` | responses returns 500 → `SchemaNetworkError`; `FAIL_SLOW_ELIGIBLE is False` on raised type | T-SCH-040, R-SCH-060 |
| `test_schemacache_connection_refused_raises_schemanetworkerror` | requests raises ConnectionError | R-SCH-060 |
| `test_schemacache_fetch_uses_30s_timeout` | construct `SchemaCache(session=mock_session)`; `fetch(url)` → `mock_session.get` called with `timeout=30.0` | R-SCH-010 |
| `test_schemacache_corrupt_cache_raises_schemacacheerror` | pre-create cache file with malformed XML; `parse_xsd(url)` → SchemaCacheError | T-SCH-050, R-SCH-070 |
| `test_schemacache_file_url_uses_filemount` | `fetch('file:///tmp/test.xsd')` reads from disk using requests-file adapter; no HTTP | R-FS-005 |
| `test_schemacache_url_to_path_uses_sha256` | the cache filename for a URL equals `sha256(url).hexdigest() + '.xsd'` | R-SCH-020 |
| `test_typeresolver_basic_resolution_logical_identifier` | resolves `logical_identifier` to `pds:ASCII_LID` using the seed XSD | T-SCH-010, R-SCH-030 |
| `test_typeresolver_unit_aware_wo_units_fallback` | resolves a `Wavelength_Range_WO_Units`-style element through the simpleContent/extension fallback queries (13+) | R-SCH-030 |
| `test_typeresolver_unresolved_xpath_raises_schemaresolutionerror` | element not in seed XSD → `SchemaResolutionError` with element name in message | T-SCH-030, R-SCH-050 |
| `test_typeresolver_cross_label_namespace_consistency_first_url_fixed` | register two labels with same `pds` URL → no error | R-SCH-040 |
| `test_typeresolver_cross_label_namespace_inconsistency_raises` | second label uses different URL for `pds` namespace → SchemaVersionError naming both URLs | T-SCH-020, R-SCH-040 |
| `test_typeresolver_no_schemalocation_raises_schemaresolutionerror` | label with `xsi:schemaLocation` missing or empty → `SchemaResolutionError("no xsi:schemaLocation declared in label")` | R-SCH-050 |
| `test_auto_column_types_all_five_keys_present` | parametrize 5 tokens; resolver returns mapped type | R-AUTO-001, §8.2 |
| `test_auto_column_types_unknown_token_keyerror` | `auto_column_type('frobnicate')`; `pytest.raises(KeyError) as exc_info`; assert `'frobnicate' in str(exc_info.value)` | internal contract |
| `test_schemacache_url_with_userinfo_refuses_to_cache` | `fetch('https://user:pw@example.com/x.xsd')` → `SchemaCacheError`; assert `'userinfo'` in message | codebase-analysis §7 |
| `test_schemacache_atomic_write_no_partial_file_on_kill` | simulate writer interruption (raise mid-write of `.tmp.<pid>`); verify final `<sha256>.xsd` does not exist; verify no `.tmp.<pid>` orphan after `fetch` retry | critique skill §6 |
| `test_schemacache_session_user_agent_set` | inspect `cache._session.headers['User-Agent']`; assert it contains `'rms-pds4indextools/'` | codebase-analysis §7 |
| `test_schemacache_session_ssl_verify_on` | `cache._session.verify is True` | codebase-analysis §7 |
| `test_schemacache_session_max_redirects` | `cache._session.max_redirects == 5` | codebase-analysis §7 |
| `test_register_label_parses_multiple_xsds_listed_in_schemalocation` | `xsi:schemaLocation` listing two URLs → both fetched | R-SCH-010 |
| `test_resolve_xpath_preserves_namespace_prefix` | resolver returns `'pds:ASCII_LID'` not `'ASCII_LID'` | spec §11.3 |
| `test_url_to_cache_filename_deterministic` | same URL → same cache filename across instances | R-IDX-001, R-IDX-002 |
| `test_register_label_with_non_default_scheme_uses_registered_adapter` | `xsi:schemaLocation` with `ftp://` — patched adapter on session returns valid XSD body | R-FS-005 |

### 6.3 Phase 6 exit criteria

- [ ] All tests pass.
- [ ] Coverage ≥ 95%.
- [ ] mypy + ruff clean.

---

## Phase 7 — `scraper/` package

### 7.1 Module behavior

Implements §8 (R-LID-001/010/020, R-FS-010), §9 (R-PARSE-*, R-SCRAPE-*,
R-VAL-*), §12 (R-NIL-*, R-MISS-*). The module composes
`xpath_norm` and `schema_types`.

**Mandatory package split** (codebase-analysis §1; do NOT defer):

```text
src/pds4indextools/scraper/
├── __init__.py      # re-exports ScrapeResult, scrape_label
├── _parse.py        # BOM check, etree.parse wrapper, nsmap validation, walk
├── _value.py        # normalize_value, R-VAL-010/020/030/040 checks
├── _nil.py          # nil-substitution lookup keyed on (data_type, nilReason)
├── _lid.py          # _LID_REGEX, validate_lid, validate_version_id,
│                    # auto-column derivation, filespec byte-length check,
│                    # cross-label LID dedup
└── _orchestrator.py # top-level scrape_label orchestrator
```

Import order (no cycles): `_parse` → `_value` → `_nil`; `_lid` is
independent; `_orchestrator` imports all four. Each file stays under
~500 lines.

A unit test `test_scraper_package_is_a_package_not_a_module` in
`tests/unit/test_package_layout_and_metadata.py` asserts the directory layout: the
test imports `pds4indextools.scraper` and asserts
`hasattr(pds4indextools.scraper, '__path__')` (modules don't have
`__path__`; packages do).

Public symbols:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ScrapeResult:
    label_path: Path
    canonical_root_tag: str
    rows: dict[str, str]                  # canonical_xpath -> normalized value
    auto_columns: dict[str, str]          # auto-col token -> value
    lid: str
    version_id: str
    namespaces: dict[str, str]            # nsmap with default aliased to 'pds'
    schema_urls: tuple[str, ...]          # in declared order
```

**Dict insertion-order contract**: `rows` and `auto_columns` are
`dict[str, str]` and the contract REQUIRES insertion order:
- `rows` is populated in pre-order DOM traversal order (the order
  used for R-XPL-010 first-occurrence aggregation in
  `generate_xpath_list`).
- `auto_columns` is populated in the order the five tokens are
  derived (`lid`, `lidvid`, `filespec`, `filename`, `bundle_name`).

Python 3.7+ guarantees insertion order for `dict`. The implementer MUST
NOT replace these fields with `frozenset`, `MappingProxyType`, or
pre-sort them. A unit test
`test_scrape_result_rows_order_is_dom_pre_order` asserts the contract
against a known fixture.

```python
def scrape_label(
    label_path: Path,
    *,
    bundle_root: Path,
    resolver: SchemaTypeResolver,
    nillable_config: Mapping[str, NillableEntry],
    fixed_width_mode: bool,
    seen_lids: dict[str, Path] | None = None,
) -> ScrapeResult: ...
```

`scrape_label` returns a `ScrapeResult` or raises a `LabelError` subclass.
The function:

1. Read first 3 bytes; if `EF BB BF` raise
   `ParseError("UTF-8 BOM not permitted", file_path=label_path)`
   (R-PARSE-001).
2. Parse with `etree.parse(str(label_path))` wrapped in `try`; catch
   `etree.XMLSyntaxError` and `raise ParseError(...) from e` (R-PARSE-002).
3. Validate root.nsmap default namespace presence (R-XP-013).
4. Walk pre-order; for each element with leaf text:
   - Build canonical XPath via `xpath_norm.canonicalize_xpath`.
   - Normalize value per R-VAL-010 (`' '.join(text.strip().split())`).
   - Apply R-VAL-020/030/040 checks; raise `ScrapedValueError` on hits.
     `R-VAL-040` is mode-dependent: pass `fixed_width_mode` in.
5. For nilled elements (R-NIL-001/010/020/030/040): look up
   `(data_type, nilReason)` in `nillable_config`. The data type comes
   from `resolver.resolve(local_tag)`. Substitution value comes from
   `NillableEntry`.
6. After full walk, renumber via `xpath_norm.renumber_xpaths`.
7. Validate LID per R-LID-001 (regex) and `version_id` per R-LID-010.
   Compute auto-columns per §8.2. R-FS-010 byte-length check on
   `filespec`.
8. Cross-label LID uniqueness (R-LID-020): if `seen_lids is not None` (the
   caller provides a shared mutable dict), check + insert; raise `LidError`
   on collision with both file paths. If `None`, skip check.
   `cli.run_generate_index_file` always passes a dict. The function
   docstring states explicitly that `seen_lids` is mutated by side-effect
   and is NOT thread-safe; the library currently documents itself as
   single-threaded (`python.mdc` §2: document mutable-state
   scope; codebase-analysis §5).
9. Return `ScrapeResult`.

LID regex constant (module-level): `_LID_REGEX = re.compile(r'^urn:[a-z0-9-]+:[a-z0-9-]+(?::[a-zA-Z0-9_.-]+){1,4}$')` (R-LID-001).

Value-content checks (both applied AFTER R-VAL-010 normalization):

- R-VAL-020 control characters: `_CONTROL_CHARS = re.compile(r'[\x00-\x1f\x7f]')`.
- R-VAL-030 non-ASCII: `not value.isascii()`. Do NOT use a character
  class like `[\x7f-\xff]` for this — in a Python `str` it matches only
  codepoints U+007F–U+00FF and silently misses every codepoint above
  U+00FF (e.g. `€`), while `str.isascii()` catches all codepoints
  ≥ 0x80 exactly as R-VAL-030 requires.

### 7.2 Unit tests — `tests/unit/test_label_scraping_and_validation.py`

Provide small inline XML strings via `tmp_path` — full content in
Appendix A.12. Every temporary label file a test writes uses the
`.lblx` suffix (e.g. `tmp_path / 'simple.lblx'`), matching the fixture
convention (owner decision #1).

For each test, fixture YAML for `nillable_config` is the default-config
nillable section (mock the resolver, or pass a real resolver pre-seeded
with a hand-curated XSD).

| Test function | Verifies | T-ID |
|---|---|---|
| `test_scrape_simple_label_returns_rows_dict` | one-element label scraped; result.rows has one key with the normalized value | R-SCRAPE-010, R-SCRAPE-020 |
| `test_scrape_is_suffix_agnostic_xml_and_lblx_identical` | write SIMPLE_LABEL to both `tmp_path/'a.lblx'` and `tmp_path/'a.xml'`; scrape each; results identical except `label_path`/`filespec`/`filename` (`.xml` is a valid historical label suffix; the scraper attaches no meaning to it) | owner decision #1 |
| `test_scrape_pre_order_traversal_visits_every_element` | nested label; result.rows contains every leaf XPath, none of the parents | R-SCRAPE-010, R-SCRAPE-030 |
| `test_scrape_attribute_not_scraped` | label with `unit="m"` → no key contains `unit` | R-SCRAPE-040 |
| `test_scrape_whitespace_collapsed` | text `"  a\n\tb  c "` → `"a b c"` | R-VAL-010 |
| `test_scrape_bom_rejected` | label starting with `\xef\xbb\xbfx` → ParseError "BOM" | R-PARSE-001 |
| `test_scrape_invalid_xml_raises_parseerror` | malformed XML → ParseError, `__cause__` is XMLSyntaxError | R-PARSE-002 |
| `test_scrape_no_default_namespace_raises_parseerror` | root has only prefixed `xmlns:pds=...`, no default → ParseError | T-XP-022, R-XP-013 |
| `test_scrape_non_ascii_byte_raises_scrapedvalueerror` | label with `é` in value → ScrapedValueError naming element XPath | T-CSV-040, R-VAL-030 |
| `test_scrape_non_ascii_above_u00ff_raises_scrapedvalueerror` | label with `€` (U+20AC) in value → ScrapedValueError (proves the `isascii()` check catches codepoints > U+00FF) | R-VAL-030 |
| `test_scrape_control_char_raises_scrapedvalueerror` | label with `\x07` in value → ScrapedValueError | T-CSV-050, R-VAL-020 |
| `test_scrape_tab_in_value_collapsed_not_error` | `\t` collapsed by R-VAL-010 before R-VAL-020 check → no error | T-CSV-050, R-VAL-010 |
| `test_scrape_quote_in_value_variable_width_raises` | `"` in value with `fixed_width_mode=False` → ScrapedValueError | R-VAL-040 |
| `test_scrape_quote_in_value_fixed_width_passes` | same input with `fixed_width_mode=True` → no error; value kept verbatim | R-VAL-040 |
| `test_scrape_valid_lid_accepted` | `urn:nasa:pds:bundle:collection:product` → result.lid set, no error | T-LID-001, R-LID-001 |
| `test_scrape_no_urn_prefix_lid_rejected` | `nasa:pds:bundle` → LidError | T-LID-010, R-LID-001 |
| `test_scrape_uppercase_lid_prefix_rejected` | `URN:NASA:PDS:b` → LidError | T-LID-011, R-LID-001 |
| `test_scrape_lid_with_only_three_tokens_rejected` | `urn:a:b` → LidError (raised at LID validation, before bundle_name extraction) | T-AUTO-050, R-LID-001 |
| `test_scrape_lid_with_seven_tokens_accepted` | full 7-token LID accepted | R-LID-001 |
| `test_scrape_missing_logical_identifier_raises_liderror` | no `<logical_identifier>` → LidError | T-LID-020, R-LID-001 |
| `test_scrape_duplicate_logical_identifier_raises_liderror` | two `<logical_identifier>` in same label → LidError | R-LID-001 |
| `test_scrape_missing_version_id_raises_liderror` | no `<version_id>` → LidError | T-LID-030, R-LID-010 |
| `test_scrape_duplicate_version_id_raises_liderror` | two `<version_id>` → LidError | R-LID-010 |
| `test_cross_label_lid_collision_raises` | two labels share LID; second call (passing shared seen_lids dict) → LidError naming both paths | T-LID-050, R-LID-020 |
| `test_filespec_byte_length_parametrized` | parametrize (byte_length, passes) ∈ {(1, True), (254, True), (255, True), (256, False), (257, False), (1024, False)}; passing rows assert `len(result.auto_columns['filespec'].encode('utf-8')) == byte_length`; failing rows use `pytest.raises(LabelError) as exc_info` and assert both `'filespec'` and `'255'` substrings in `str(exc_info.value)`. The error raised is `LabelError("filespec exceeds 255 bytes: ...")` directly (NOT `LidError`, since this is a path-length problem, not LID-content); `FAIL_SLOW_ELIGIBLE=True` is inherited from base `LabelError`. | T-AUTO-030, R-FS-010 (critique skill §9) |
| `test_auto_columns_filespec_uses_forward_slashes` | scrape via Windows-style backslash bundle path → as_posix() returns forward slashes | T-AUTO-020 |
| `test_auto_columns_lid_strips_whitespace` | `<logical_identifier>   urn:...   </logical_identifier>` → lid is stripped | T-AUTO-001, §8.2 |
| `test_auto_columns_lidvid_concatenates_correctly` | `urn:...` + `::` + version | T-AUTO-010 |
| `test_auto_columns_filename_is_basename` | `auto_columns['filename'] == label_path.name` | §8.2 |
| `test_auto_columns_bundle_name_extracts_4th_colon_token` | `urn:nasa:pds:bundle_x:coll:prod` → `bundle_x` | T-AUTO-040 |
| `test_nil_substitution_known_dtype` | `<x xsi:nil="true" nilReason="missing"/>` of type `pds:ASCII_Date_YMD` → cell `0002-01-01` | T-NIL-001, R-NIL-010, R-NIL-020 |
| `test_nil_substitution_bad_reason_raises_nilerror` | `nilReason="bogus"` → NilError naming reason | T-NIL-010, R-NIL-010 |
| `test_nil_missing_nilreason_raises_nilerror` | `xsi:nil="true"` without `nilReason` → NilError | R-NIL-010 |
| `test_nil_unknown_dtype_in_config_raises_nilerror` | resolved dtype not in `nillable_config` → NilError naming dtype | T-NIL-020, R-NIL-030 |
| `test_empty_text_no_nil_attribute_treated_as_absent` | `<x></x>` → XPath NOT in result.rows | T-NIL-030, R-NIL-040 |
| `test_renumber_applied_after_walk` | label with three sibling `<Observing_System>` blocks → result.rows has `<1>,<2>,<3>` | T-XP-020 |
| `test_namespaces_recorded` | `result.namespaces` has `pds` aliasing the default and any others preserved | §10 |
| `test_schema_urls_recorded_in_declared_order` | label declares two schema URLs; result.schema_urls = exact tuple in order | structural |
| `test_scrape_with_no_seen_lids_dict_skips_cross_label_check` | passing `seen_lids=None` does not raise even with duplicate LIDs across two consecutive calls | API contract |

### 7.3 Phase 7 exit criteria

- [ ] All tests pass.
- [ ] Coverage ≥ 95% line+branch.
- [ ] mypy + ruff clean.

---

## Phase 7.5 — `_io.py`

### 7.5.1 Module behavior

Implements R-ERR-002 atomic-write semantics. Used by `csv_writer`,
`label_writer`, and `cli/_paths.py`. Private module
(`__all__ = ()`).

```python
"""Atomic file-write helpers (private; not part of the public API).

Used by csv_writer, label_writer, and cli/_paths.py to guarantee
R-ERR-002 (SIGINT-safe writes: no partially-written file at the final
target).
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pds4indextools.errors import OutputError

__all__: tuple[str, ...] = ()


def _atomic_rename(temp: Path, final: Path) -> None:
    """Rename ``temp`` to ``final`` atomically.

    Uses ``os.replace``, which is atomic on the same filesystem on both
    POSIX and Windows. Raises :exc:`~pds4indextools.errors.OutputError`
    wrapping any underlying ``OSError`` (e.g., cross-filesystem rename,
    permission denied).

    Parameters:
        temp: Source path (must exist).
        final: Destination path.

    Raises:
        OutputError: If the rename fails.
    """
    try:
        os.replace(temp, final)
    except OSError as e:
        raise OutputError(
            f'atomic rename failed: {temp} -> {final}: {e}',
            file_path=final,
        ) from e


@contextmanager
def _atomic_writes(*pairs: tuple[Path, Path]) -> Iterator[None]:
    """Context manager that performs atomic writes for multiple file pairs.

    Each ``(temp, final)`` pair is renamed atomically after the body
    completes successfully. If the body raises, every temp file is
    removed (``unlink(missing_ok=True)``) and the exception propagates
    unchanged.

    Parameters:
        *pairs: One or more ``(temp_path, final_path)`` tuples.

    Yields:
        None — the caller writes to each ``temp_path`` inside the body.

    Raises:
        OutputError: From ``_atomic_rename`` if a rename fails.
    """
    try:
        yield
    except BaseException:
        for temp, _final in pairs:
            temp.unlink(missing_ok=True)
        raise
    for temp, final in pairs:
        _atomic_rename(temp, final)
```

### 7.5.2 Unit tests — `tests/unit/test_atomic_file_writes.py`

| Test function | Verifies |
|---|---|
| `test_atomic_rename_success_moves_bytes` | temp file written, `_atomic_rename(temp, final)` → final has bytes, temp gone |
| `test_atomic_rename_oserror_wrapped_in_outputerror` | use `monkeypatch.setattr(os, 'replace', lambda a, b: (_ for _ in ()).throw(OSError('boom')))`; assert `pytest.raises(OutputError, match="atomic rename failed")`; assert `__cause__` is `OSError` |
| `test_atomic_rename_outputerror_file_path_is_final` | the raised error's `.file_path == final` |
| `test_atomic_writes_happy_path_renames_all_pairs` | two pairs in one call; after `with _atomic_writes(...):` body exits normally, both finals exist with their bytes; both temps are gone |
| `test_atomic_writes_body_exception_unlinks_all_temps` | body raises `RuntimeError`; both temp files removed; neither final exists; `RuntimeError` propagates with its original message |
| `test_atomic_writes_missing_temp_file_is_ok` | body raises before writing the temp file; cleanup `unlink(missing_ok=True)` is silent |
| `test_atomic_writes_zero_pairs_is_no_op` | `with _atomic_writes(): pass` does not raise |
| `test_atomic_writes_keyboardinterrupt_unlinks_temps` | body raises `KeyboardInterrupt`; temps removed; `KeyboardInterrupt` propagates |

### 7.5.3 Phase 7.5 exit criteria

- [ ] `pytest tests/unit/test_atomic_file_writes.py` GREEN.
- [ ] Coverage on `_io.py` ≥ 95% line+branch.
- [ ] mypy + ruff clean.

---

## Phase 8 — `csv_writer.py`

### 8.1 Module behavior

Implements §13 (R-CSV-001..R-CSV-080, R-SORT-010..R-SORT-030).

Public symbols:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ColumnStat:
    name: str
    must_quote: bool
    max_byte_length: int        # includes quote bytes when must_quote
    is_auto_column: bool
    auto_column_token: str | None

@dataclass(frozen=True, slots=True, kw_only=True)
class CsvWritePlan:
    rows: tuple[dict[str, str], ...]
    columns: tuple[str, ...]                  # in mapping order
    stats: tuple[ColumnStat, ...]             # parallel to columns
    line_terminator: bytes
    fixed_width: bool
    header_row_length: int                    # bytes including line terminator
    max_record_length: int                    # bytes including line terminator
    total_byte_length: int                    # full file size when written

def build_plan(
    *,
    rows: Sequence[dict[str, str]],
    columns: Sequence[str],
    column_is_auto: Mapping[str, bool],
    auto_tokens: Mapping[str, str],
    output_section: OutputSection,
) -> CsvWritePlan: ...

def write_csv(plan: CsvWritePlan, csv_path: Path) -> None: ...

def sort_rows(rows: Sequence[dict[str, str]], output_section: OutputSection) -> list[dict[str, str]]: ...
```

`build_plan` performs:
- Sort rows via `sort_rows` (R-SORT-010..R-SORT-030).
- Per-column quoting analysis (R-CSV-040, R-CSV-050..R-CSV-052).
- Compute byte lengths (R-CSV-080 — byte length == char length given the
  ASCII-only guarantee from R-VAL-030).
- Compute fixed-width column widths (R-CSV-070).
- Compute header-row length (no padding per R-CSV-071), record lengths,
  total bytes.

`write_csv` writes the file deterministically:
- Open binary; write headers (unquoted, R-CSV-012); write each row.
- For each cell: quote if `must_quote`; in fixed-width mode pad right with
  spaces to `max_byte_length` (R-CSV-070); never trailing comma (R-CSV-005,
  R-CSV-072).
- Use the `line_terminator` from the plan (R-CSV-003).

`sort_rows` parses each `sort_by` spec via `config.parse_sort_key`.
Per spec R-SORT-020, each listed name MUST exist in the FINAL EMITTED
column set — i.e. the post-rename headers (`LID`, `FILE_NAME`, …)
declared by the config's `columns:` entries. Raises
`ConfigError("sort_by references unknown column '{name}'", ...) from
None` otherwise (a config error, NOT fail-slow eligible). The R-SORT-010
default (empty `sort_by`) performs no re-sort: rows already arrive in
filespec order from discovery (R-DISC-020), so no `filespec` column
need be emitted for the default to hold.
Every other exception conversion in this module uses `raise ... from e` to
preserve the originating traceback (`python.mdc` §2).

### 8.2 Unit tests — `tests/unit/test_csv_writing_quoting_and_sorting.py`

Use `tmp_path` for written files. Compare bytes via `read_bytes()`.

| Test function | Verifies | T-ID |
|---|---|---|
| `test_build_plan_quoting_column_with_comma_marks_must_quote_true` | one cell has comma → ColumnStat.must_quote True | T-CSV-001, R-CSV-040 |
| `test_build_plan_quoting_column_without_comma_marks_must_quote_false` | nope → False | T-CSV-002, R-CSV-051 |
| `test_build_plan_header_not_in_must_quote_calculation` | column has comma-free data but header literally `"a,b"`? — note this can't happen per R-MAP-043; but assert that build_plan doesn't even look at headers | R-CSV-052 |
| `test_write_csv_variable_width_no_trailing_comma_per_row` | inspect last byte before line terminator on each row | T-CSV-010, R-CSV-005 |
| `test_write_csv_header_unquoted_when_column_quoted` | column has comma data; header `name` (no comma) → header literal not quoted | T-CSV-003, R-CSV-012 |
| `test_write_csv_data_cell_quoted_when_must_quote_true` | column has comma; every data cell in that column wrapped in `"..."` | T-CSV-001, R-CSV-050 |
| `test_write_csv_data_cells_unquoted_when_must_quote_false` | no quotes anywhere | T-CSV-002, R-CSV-051 |
| `test_write_csv_fixed_width_pads_each_data_cell` | inspect column boundaries by byte offset | T-CSV-020, R-CSV-070 |
| `test_write_csv_fixed_width_header_not_padded` | header byte length matches unpadded width | T-CSV-021, R-CSV-071 |
| `test_write_csv_fixed_width_quoted_column_width_includes_quotes` | column max == max(len(value)+2 if must_quote) | T-CSV-022, R-CSV-070, R-CSV-050 |
| `test_write_csv_fixed_width_zero_length_column_writes_back_to_back_commas` | all-empty column → "v0,,v2" exactly | T-CSV-023, R-CSV-073 |
| `test_write_csv_crlf_terminator` | `OutputSection(line_ending='CRLF')` → bytes end in `\r\n` per row | T-CSV-030, R-CSV-003 |
| `test_write_csv_lf_terminator` | default → `\n` only | T-CSV-031, R-CSV-003 |
| `test_write_csv_field_delimiter_always_comma` | comma between fields | R-CSV-004 |
| `test_write_csv_no_byte_order_mark_emitted` | first 3 bytes of file ≠ BOM | R-CSV-002 |
| `test_write_csv_output_matches_python_csv_module_byte_for_byte` | ONE data row containing a comma-bearing cell and a comma-free cell (single row so per-column and per-cell quoting coincide — the tool quotes per COLUMN, `csv.QUOTE_MINIMAL` per CELL; multi-row mixed columns would legitimately differ); write via `csv_writer.write_csv(...)` AND via `csv.writer(open(out2, 'w', newline=''), quoting=csv.QUOTE_MINIMAL, quotechar='"', lineterminator='\n')`; assert identical bytes (verifies R-CSV-001 behaviorally) | R-CSV-001 |
| `test_sort_rows_default_empty_sort_by_preserves_input_order` | scrambled input rows; sort_by=[] → row order unchanged (discovery already sorted by filespec, R-DISC-020) | T-CSV-060, R-SORT-010 |
| `test_sort_rows_explicit_lid_ascending` | `OutputSection(sort_by=['lid'])` → ascending by lid | T-CSV-060, R-SORT-020 |
| `test_sort_rows_explicit_lid_descending` | `sort_by=['-lid']` → descending | T-CSV-060, R-SORT-020 |
| `test_sort_rows_unknown_column_raises_configerror` | `sort_by=['unknown']` → `ConfigError`; assert `"'unknown'"` in `str(exc_info.value)` | T-CSV-061, R-SORT-020 |
| `test_sort_rows_multi_key_stable` | two keys; tie on first; second key determines order | R-SORT-020 |
| `test_sort_rows_string_comparison_on_post_normalization_value` | sort sees `"1"` vs `"10"` as `"1" < "10"` (string compare) | R-SORT-030 |
| `test_build_plan_record_length_includes_terminator` | computed bytes match actual `write_csv` output length | structural |
| `test_build_plan_total_byte_length_matches_file_size_after_write` | golden | R-LBL-* (header/total bytes feed PdsTemplate) |

Plus a parametrized integration-style test
`test_write_csv_byte_identical_across_runs` that calls `build_plan` and
`write_csv` twice on the same inputs and asserts byte-identical output
(R-IDX-001).

### 8.3 Phase 8 exit criteria

- [ ] All tests pass.
- [ ] Coverage ≥ 95%.
- [ ] mypy + ruff clean.

---

## Phase 9 — `label_writer.py`

### 9.1 Module behavior

Implements §14 (R-LBL-001..R-LBL-091).

Public symbols:

```python
def build_substitution_dict(
    *,
    label_contents: LabelContents,
    plan: CsvWritePlan,
    column_specs: Sequence[ColumnSpec],       # parallel to plan.columns (config-declared order)
    column_types: Mapping[str, str],          # column header -> stripped data_type
    column_xpaths: Mapping[str, str],         # column header -> raw canonical XPath OR auto-token
    csv_absolute_path: Path,
) -> dict[str, object]: ...

def normalize_modification_detail(
    raw: ModificationDetail | list[ModificationDetail] | None,
    *,
    fallback_version_id: str | None = None,
) -> list[dict[str, object]]: ...

def write_label(
    template_path: Path,
    substitution_dict: Mapping[str, object],
    output_label_path: Path,
    *,
    line_ending: Literal['LF', 'CRLF'],
) -> None: ...

@contextmanager
def load_packaged_template() -> Iterator[Path]: ...
```

`build_substitution_dict`:
- Computes the 11 BASE variables from R-LBL-012. Reserved-key collision
  check happens in `config.py` already.
- Computes `Field_Content` (R-LBL-020): one dict per column with the
  7 keys. `field_location` for fixed-width: 1-based byte offset; for
  delimited: 1-based column position. Strip namespace prefix from
  `data_type` (§11.3).
- Starts the dict from `label_contents.model_dump(by_alias=False)`
  WITHOUT `exclude_none`, so every optional declared field
  (`version_id`, `title`, `Citation_Information`, `Internal_Reference`,
  `External_Reference`, `Source_Product_Internal`,
  `Source_Product_External`, `File_Area_Ancillary`,
  `File_Area_Metadata`) is present with value `None`. This is binding:
  the packaged template tests these names with `$IF(name)$`, and
  PdsTemplate treats an UNDEFINED name as a render error that would
  poison the golden lblx — defined-`None` is falsy and renders
  nothing. `Modification_Detail` is then replaced by
  `normalize_modification_detail(...)`. Then overlays the BASE
  variables — if any collision
  is found post-validation, raises `Pds4IndexError("internal invariant:
  reserved key collision; should have been rejected at config load")`.
  Do NOT use `assert`; assertions are stripped under `python -O` and
  library code must surface invariants as real exceptions
  (`python.mdc` §2).

`normalize_modification_detail` (owner decision #3 — supersedes the
"None becomes an empty list" wording of spec R-LBL-091; the spec needs
a matching update):

- A single `ModificationDetail` is wrapped into a one-element list.
- A list passes through unchanged (in declared order).
- `None` (the user supplied no `Modification_Detail` in any config)
  GENERATES a default single-entry history so the emitted
  `<Modification_History>` is always valid PDS4 (an empty
  `Modification_History` would not be):

  ```python
  [{
      'modification_date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'),
      'version_id': fallback_version_id or '1.0',
      'description': 'Initial version.',
  }]
  ```

  The date is the current UTC date (deterministic under the
  `frozen_time` fixture: `'2026-05-14'`). `build_substitution_dict`
  passes `fallback_version_id=label_contents.version_id` so the default
  entry's `version_id` matches the label's own `version_id` when the
  user set one, else `'1.0'`. Users who want anything else simply
  provide `Modification_Detail` in their config (which then passes
  through verbatim per R-LBL-090).

`write_label` (behavior verified against the rms-pdstemplate 1.0.0
source in `/seti/all_repos/rms-pdstemplate` on 2026-07-18):

- On first use (module-level, once), routes pdstemplate's logging into
  our tree: `pdstemplate.set_logger(logging.getLogger('pds4indextools.pdstemplate'))`.
  This is REQUIRED: pdstemplate's default `PdsLogger` has no handlers
  and therefore PRINTS to stdout, which would violate the library/CLI
  output boundary and break `capsys`-based CLI tests.
- Constructs `pdstemplate.PdsTemplate(template_path, crlf=(line_ending == 'CRLF'))`
  (`crlf` is a keyword-only constructor argument; passing an explicit
  bool overrides pdstemplate's inference from the template's own line
  endings).
- Calls `template.write(substitution_dict, output_label_path, raise_exceptions=True)`.
  `raise_exceptions=True` is REQUIRED: the default (`False`) does not
  raise — it logs errors and embeds them into the written label
  wrapped in `[[[`/`]]]`, which would silently poison golden bytes.
- `write` returns `(error_count, warning_count)`; as a belt-and-braces
  check, a nonzero `error_count` (possible if a non-raising validation
  path is ever taken) also raises `OutputError`.
- Exception wrapping: pdstemplate exports `TemplateError` (subclass of
  `pdslogger.LoggerError`; there is NO `PdsTemplateError` — the name
  the earlier draft probed for does not exist). With
  `raise_exceptions=True`, template-evaluation failures may also
  surface as the original evaluation exceptions. Module constant (no
  runtime probing):

  ```python
  from pdstemplate import TemplateError

  _PDSTEMPLATE_RAISES: tuple[type[BaseException], ...] = (
      TemplateError, KeyError, NameError, ValueError, TypeError, SyntaxError,
  )
  ```

  Implementation:

  ```python
  try:
      errors, _warnings = template.write(
          substitution_dict, output_label_path, raise_exceptions=True)
  except _PDSTEMPLATE_RAISES as e:
      raise OutputError(
          f'PdsTemplate failed: {e}',
          file_path=output_label_path,
      ) from e
  if errors:
      raise OutputError(
          f'PdsTemplate reported {errors} error(s)',
          file_path=output_label_path,
      )
  ```

  Require `rms-pdstemplate>=2.4` in `pyproject.toml` (2.4.0 verified);
  this minimum lower bound is API-necessary — the 1.x API is
  incompatible — and no upper bound is pinned.
  DO NOT catch bare `Exception` — programming bugs outside this
  enumerated set must surface as exit-code-3 unhandled exceptions.
- Macro audit (all verified present as `_PREDEFINED_FUNCTIONS` in
  1.0.0): `BASENAME`, `CURRENT_ZULU`, `DATETIME`, `FILE_MD5`,
  `FILE_ZULU`; the `$FOR(field, k=Field_Content)` custom-name syntax
  and `$IF`/`$ELSE_IF`/`$ELSE`/`$END_IF` are documented template
  headers. An UNDEFINED name inside `$IF(...)$` is an evaluation
  error — this is exactly why `build_substitution_dict` defines every
  optional field as `None` (see above).
- The function takes care of NOTHING else (no temp-file rename — that's
  the CLI's job, R-ERR-002).

`load_packaged_template`:
- Binding signature: `@contextmanager def load_packaged_template() -> Iterator[Path]`.
  (Public `__all__` exports this name; documentation cross-references it
  as `:func:`.)
- Implementation:
  ```python
  @contextmanager
  def load_packaged_template() -> Iterator[Path]:
      ref = importlib.resources.files('pds4indextools.templates') / 'index_label_template.xml'
      with importlib.resources.as_file(ref) as path:
          yield path
  ```
- Callers MUST use it as `with load_packaged_template() as tpl_path: ...`.
  The single function shape resolves the earlier inconsistency.

### 9.2 Unit tests — `tests/unit/test_label_template_substitution.py`

These tests do NOT need a live PdsTemplate run; use a tiny inline
template fixture per test where helpful. For tests that DO need
PdsTemplate end-to-end (e.g., MD5 macro), point at the packaged template
and a small generated CSV. **Every Phase 9 test that invokes
PdsTemplate MUST request the `frozen_time` fixture (defined in
`tests/conftest.py`) to deterministically fix `$FILE_ZULU(...)$` and
`$CURRENT_ZULU()$` output** (critique skill §15).

| Test function | Verifies | T-ID |
|---|---|---|
| `test_build_substitution_dict_includes_index_file_name_absolute` | result['index_file_name'] is absolute path of the CSV | R-LBL-* |
| `test_build_substitution_dict_field_content_one_entry_per_column` | len(result['Field_Content']) == len(plan.columns) | T-LBL-010, R-LBL-020 |
| `test_build_substitution_dict_field_content_each_entry_has_seven_keys` | every Field_Content dict's keys == {'name','field_number','field_location','data_type','field_length','maximum_field_length','xpath'} | T-LBL-011, R-LBL-020 |
| `test_build_substitution_dict_data_type_namespace_stripped` | input `pds:ASCII_LID` → emitted `'ASCII_LID'` | spec §11.3 |
| `test_build_substitution_dict_table_character_when_fixed_width_true` | `Table_Character=True, Table_Delimited=False` | R-LBL-* |
| `test_build_substitution_dict_table_delimited_when_fixed_width_false` | reverse | R-LBL-* |
| `test_build_substitution_dict_product_ancillary_when_class_matches` | product_class=Product_Ancillary → result['Product_Ancillary'] is True | T-LBL-020, R-LBL-010 |
| `test_build_substitution_dict_product_metadata_supplemental_when_class_matches` | reverse | T-LBL-021, R-LBL-010 |
| `test_build_substitution_dict_label_contents_passthrough_preserves_extras` | extra label_contents key 'custom_var' is in result | T-LBL-040, R-CFG-022 |
| `test_build_substitution_dict_records_equals_row_count` | rows count | R-LBL-* |
| `test_build_substitution_dict_fields_equals_column_count` | column count | R-LBL-* |
| `test_build_substitution_dict_object_lengths_match_plan` | header & total bytes echoed | R-LBL-* |
| `test_normalize_modification_detail_single_dict_to_list` | `ModificationDetail(...)` → `[dict]` | T-LBL-030, R-LBL-091 |
| `test_normalize_modification_detail_list_passthrough` | list of three → list of three (order preserved) | R-LBL-091 |
| `test_normalize_modification_detail_none_generates_default_entry` | under `frozen_time`: `normalize_modification_detail(None)` → exactly one entry with `modification_date == '2026-05-14'`, `version_id == '1.0'`, `description == 'Initial version.'` | owner decision #3 |
| `test_normalize_modification_detail_none_uses_fallback_version_id` | `normalize_modification_detail(None, fallback_version_id='2.0')` → entry's `version_id == '2.0'` | owner decision #3 |
| `test_build_substitution_dict_default_modification_detail_when_config_omits_it` | `label_contents` without `Modification_Detail` → `result['Modification_Detail']` is the one-entry default with `version_id == label_contents.version_id` | owner decision #3 |
| `test_build_substitution_dict_optional_fields_present_as_none` | config omitting every optional key → each of the nine optional names (`version_id` … `File_Area_Metadata`) is a key in the result with value `None` (PdsTemplate `$IF` requires defined names) | R-LBL-001, R-LBL-040 |
| `test_load_packaged_template_returns_packaged_xml_path` | returned path's string form equals `importlib.resources.files('pds4indextools.templates') / 'index_label_template.xml'` resolved to a filesystem path | R-LBL-001 |
| `test_load_packaged_template_path_is_file` | `Path.is_file()` returns `True` | R-LBL-001 |
| `test_write_label_invokes_pdstemplate_with_crlf_true_when_line_ending_crlf` | mock `pdstemplate.PdsTemplate` and assert kwargs | R-LBL-040, R-LBL-060 |
| `test_write_label_invokes_pdstemplate_with_crlf_false_when_line_ending_lf` | reverse | R-LBL-060 |
| `test_write_label_writes_to_supplied_output_path` | mock `template.write` and check first positional arg | R-LBL-040 |
| `test_write_label_pdstemplate_failure_wrapped_in_outputerror` | `mock.patch("pds4indextools.label_writer.PdsTemplate", side_effect=TemplateError("boom"))` (patch at the IMPORT site — critique skill §7); call `write_label(...)`; `pytest.raises(OutputError) as exc_info`; assert `"PdsTemplate failed"` in `str(exc_info.value)` AND `str(exc_info.value.__cause__)` contains `"boom"` | spec §17 |
| `test_write_label_nonzero_error_count_raises_outputerror` | mock `template.write` to return `(2, 0)` without raising → `OutputError` with `"2 error(s)"` in message | belt-and-braces |
| `test_write_label_passes_raise_exceptions_true` | mock `template.write`; assert called with `raise_exceptions=True` (default False would embed `[[[...]]]` error text into the label instead of raising) | verified 1.0.0 behavior |
| `test_write_label_routes_pdstemplate_logging_off_stdout` | after `write_label(...)` on the packaged template, `capsys.readouterr().out == ''` (pdstemplate's default logger prints to stdout unless `set_logger` is called) | library/CLI output boundary |
| `test_field_location_fixed_width_byte_offset_parametrized` | parametrize (widths, expected_offsets) over: `([5,3,7], [1,7,11])`, `([1], [1])`, `([0,3], [1,2])` (empty first column edge case), `([10,10,10,10], [1,12,23,34])`, `([255,255], [1,257])` (byte-boundary case); for each, assert `[entry['field_location'] for entry in result['Field_Content']] == expected_offsets` | R-LBL-020 (critique skill §9) |
| `test_field_location_delimited_column_position` | fixed_width=False → field_location[i] equals 1-based column index | R-LBL-020 |
| `test_field_content_field_length_fixed_width_uses_max_byte_length` | matches ColumnStat.max_byte_length | R-LBL-020 |
| `test_field_content_maximum_field_length_delimited_uses_max_byte_length` | same target value but in different key | R-LBL-020 |
| `test_field_content_xpath_key_uses_raw_canonical_xpath_for_mapped` | xpath has angle brackets | R-LBL-020 |
| `test_field_content_xpath_key_uses_auto_token_for_auto_columns` | xpath value == 'lid' (etc.) for the five auto-cols | R-LBL-020 |

The fixed-width `field_location` calculation: column N's offset is
`1 + sum(widths[:N]) + N` (one comma byte between columns).
Example: widths `[5,3,7]` → offsets `[1, 7, 11]` (5+1=6→7; 6+3+1=10→11).
Add a test specifically for this arithmetic to lock the contract.

### 9.3 Phase 9 exit criteria

- [ ] All tests pass.
- [ ] Coverage ≥ 95%.
- [ ] mypy + ruff clean.

---

## Phase 10 — `cli/` package + `__init__.py` + `__main__.py`

### 10.1 Module behavior — `cli/` package

Implements §3 (R-CLI-*), §4 (R-IDX-*), §5, §6,
§17.3 (R-FSLOW-*), §20 (R-API-*).

Public symbols (in `__all__` of the package init):

- `main(argv: list[str] | None = None) -> int` — top-level CLI entry. Returns
  exit code 0..130. Wraps everything in a `try` for `Pds4IndexError`/
  `KeyboardInterrupt`/other.
- `run_generate_index_file(args: GenerateIndexFileArgs) -> GenerateIndexFileResult`
- `run_generate_xpath_list(args: GenerateXpathListArgs) -> GenerateXpathListResult`
- `run_copy_default_config(args: CopyDefaultConfigArgs) -> CopyDefaultConfigResult`
- All six `@dataclass`es from spec §20.1 — full definitions (frozen,
  kw_only, slots) are in [Appendix H](#appendix-h--public-api-dataclass-definitions-phase-10-101).

**Mandatory package split** (codebase-analysis §1; do NOT defer):

```text
src/pds4indextools/cli/
├── __init__.py    # re-exports main, run_*, all 6 dataclasses, cli_entrypoint
├── _args.py       # GenerateIndexFileArgs/Result + two siblings (frozen, kw_only, slots)
├── _parser.py     # _build_parser, _normalize_subcommand, argparse epilog strings
├── _dispatch.py   # main, cli_entrypoint, _dispatch, _handle_exception,
│                  # _EXCEPTION_TO_EXIT_CODE
├── _paths.py      # _resolve_output_paths (imports _atomic_rename / _atomic_writes from pds4indextools._io)
└── _runners.py    # run_generate_index_file, run_generate_xpath_list,
                   # run_copy_default_config, _collect_warnings
```

(There is no `_warnings.py`: the stern-warning machinery died with the
mapping-file format — owner decision #10.)

All private helpers are `_`-prefixed. The package's `__init__.py`
re-exports only the public symbols. `_atomic_rename` lives in the
shared `pds4indextools/_io.py` module (NOT in `cli/_paths.py`) so that
`csv_writer`, `label_writer`, and `cli/_paths.py` can all import it
without creating a cycle (per the dependency graph above).
`_io.py.__all__ = ()` (no public exports); `_atomic_rename` is
intentionally module-private.

Internal helper signatures (live in the split files above):

- `_parse_args(argv: list[str] | None) -> argparse.Namespace | int` —
  wraps `parser.parse_args(argv)` in `try/except SystemExit as e:` and
  returns `int(e.code or 0)` on argparse-initiated exits (`--help`,
  `--version`, missing subcommand, parse errors). `main` checks
  `isinstance(result, int)` and returns it directly — this is how
  `main(['--version']) == 0` and `main([]) == 2` hold without `main`
  ever calling `sys.exit`.
- `_build_parser() -> argparse.ArgumentParser` — constructed with
  `prog='pds4_create_xml_index'` explicitly (in-process tests would
  otherwise inherit pytest's argv[0] in help/usage text). Top-level + 3
  subparsers.
  Subcommand aliases via `aliases=['generate-index-file']` etc.
  (R-CLI-002). All subparsers add `--config-file` with `action='append'`
  and `default=None` (NOT `default=[]` — argparse's class-level
  mutable default is a foot-gun that produces stale state across
  re-entrant `main()` calls). `_dispatch` converts `None` to an empty
  tuple before passing to the run function. Top-level adds `--version`.
  R-CLI-040 epilogs.
- `_normalize_subcommand(name: str) -> str` — maps hyphenated to
  underscored.
- `_dispatch(ns: argparse.Namespace) -> int`. Implementer references
  namespace attributes by direct attribute access (`ns.bundle_root`,
  `ns.output_file`); `getattr(ns, 'bundle_root')` with a constant
  attribute name is forbidden (`python.mdc` §1).
- `_handle_exception(exc: BaseException) -> int` — maps exception type to
  exit code via the `_EXCEPTION_TO_EXIT_CODE` tuple-of-tuples constant
  (defined below).
- `_atomic_rename` / `_atomic_writes` — re-imported from
  `pds4indextools._io` (defined in Phase 7.5; NOT redefined here).
- `_collect_warnings(*, fail_slow: bool) -> _WarningCollector` — context
  manager that captures fail-slow errors per R-FSLOW-110.
- `_resolve_output_paths(...) -> tuple[Path, Path]` — implements
  R-CLI-015 + R-OUT-010..R-OUT-013 + R-CLI-022 (for xpath list).
  Full extension table (BINDING; covers all corner cases including
  `--output-file foo.lblx` which the spec does not name explicitly):

  | `--output-file` ends in | data file | label file |
  |---|---|---|
  | `.csv` (e.g. `foo.csv`) | `foo.csv` | `foo.lblx` |
  | `.lblx` (e.g. `foo.lblx`) | `foo.csv` (same stem) | `foo.lblx` |
  | any other extension (e.g. `.tab`) | `foo.tab` | `foo.lblx` |
  | no extension (e.g. `foo`) | `foo.csv` | `foo.lblx` |

  In every case the label file is `<stem>.lblx`. The `xpath_list`
  subcommand produces only a YAML data file (no `.lblx`): default
  `./columns.yaml` (auto-numbered when present); an explicit extension
  is honored; no extension appends `.yaml` (spec-amendment #12).
- `cli_entrypoint() -> NoReturn` — console-script wrapper:
  `import sys; sys.exit(main())`. Other than the `__main__.py` guard
  (§10.3), the ONLY place in `src/` that calls `sys.exit`.

The exception-to-exit-code mapping is a single source of truth in
`cli/_dispatch.py`:

```python
_EXCEPTION_TO_EXIT_CODE: tuple[tuple[type[BaseException], int], ...] = (
    (CliError, EXIT_USER_ERROR),
    (ConfigError, EXIT_USER_ERROR),
    (FailSlowAggregateError, EXIT_RUNTIME_ERROR),
    (SchemaError, EXIT_RUNTIME_ERROR),
    (LabelError, EXIT_RUNTIME_ERROR),
    (OutputError, EXIT_RUNTIME_ERROR),
    (Pds4IndexError, EXIT_INTERNAL_ERROR),    # catch-all base
    (KeyboardInterrupt, EXIT_SIGINT),
)
```

`_handle_exception` walks the tuple top-to-bottom and returns the first
match's int; falls back to `EXIT_INTERNAL_ERROR` for anything else.
Order is significant: `FailSlowAggregateError` is matched before its
LabelError sub-errors. Tests parametrize over the tuple
(codebase-analysis §6).

`main` flow:
1. Parse argv. argparse handles `--version` and "no subcommand" (R-CLI-003,
   R-CLI-005).
2. `setup_logging(verbosity)` where `verbosity = min(ns.verbose, 3)` (R-LOG-010).
3. Dispatch to one of three `run_*`. The `run_*` functions catch their own
   `Pds4IndexError`s and turn them into return values? No — per R-API-004
   they MUST raise. So `main` catches them at this top level.
4. Catch:
   - `Pds4IndexError`: print formatted message; return code per
     `_EXCEPTION_TO_EXIT_CODE` mapping. For `FailSlowAggregateError`,
     print all sub-errors then 2 (R-FSLOW-120 CLI behavior).
   - `KeyboardInterrupt`: print `aborted by user`; cleanup temp files via
     a `try`/`finally` in the `run_*` (each run_* uses
     `with _atomic_writes((csv_tmp, csv_final), (lbl_tmp, lbl_final)):` to
     guarantee R-ERR-002); return 130.
   - any other exception: print traceback; return 3.

`run_generate_index_file` flow:
1. Resolve `bundle_root` to absolute (R-FS-001). Validate it is a
   directory (R-CLI-010, R-CLI-012); raise `CliError` if not.
2. Validate `patterns`: reject absolute patterns (R-CLI-011). For each
   pattern call `bundle_root.glob(pattern)`; union; dedup via
   `Path.resolve()` (R-FS-004). If empty → `CliError` with all patterns
   in message (R-DISC-010).
3. Sort by `filespec` (R-DISC-020).
4. Load config chain (R-CFG-051): `_load_default_config()` plus user
   YAMLs in order; validate via `config.load_config`.
5. Validate the merged config's columns (owner decision #10): if
   `config.columns is None`, raise
   `ConfigError("no columns defined in config; run generate_xpath_list to produce a starter columns block")`.
   (An explicitly empty list was already rejected at load time,
   R-MAP-312.)
6. Instantiate `SchemaCache(cache_dir=config.xsd_cache_dir)` and
   `SchemaTypeResolver(cache)`.
7. Compute output paths (R-CLI-015, R-OUT-010..R-OUT-013). Track whether
   any overwrite happened; record warnings.
8. Scrape every label, in order; if `fail_slow`, collect; otherwise raise
   first.
9. After scrape, if fail_slow collected ≥1 error → raise
   `FailSlowAggregateError(errors)` (R-FSLOW-120, R-API-004).
10. Project the scraped rows to the configured columns (R-MAP-310 as
    amended); an XPath column matching no label produces empty cells
    (R-MAP-311). There is NO all-columns fallback.
11. `csv_writer.sort_rows`, `build_plan`, `write_csv` (to a temp file in
    the target directory, then atomic rename).
11a. After the CSV is atomically renamed to its final path AND BEFORE
    step 12, if `args.csv_post_write_hook is not None` call
    `args.csv_post_write_hook(csv_final_path)`. Used by the
    golden-bytes generator (Appendix I.1) to freeze CSV mtime so the
    label's `$FILE_ZULU(...)$` macro renders a deterministic timestamp.
12. `label_writer.build_substitution_dict`, `write_label` (also via
    temp file + atomic rename).
13. Return `GenerateIndexFileResult`.

`run_generate_xpath_list` flow (§5.1):
- Same discovery/scrape steps but skip auto-column derivation;
- Aggregate canonical XPaths union preserving first-occurrence order
  (R-XPL-010); write a YAML `columns:` block (R-XPL-020 as amended,
  spec-amendment #12). Exact emitted shape — LF terminators, two-space
  indent, one `- xpath:`/`name:` pair per observed XPath in
  first-occurrence order, `name` pre-filled with the XPath so every
  entry is valid as-is and renaming is a one-line edit; auto-columns
  are NOT emitted (the user adds `auto:` entries by hand):

  ```yaml
  # Generated by pds4_create_xml_index generate_xpath_list.
  # Edit each `name:` (or delete unwanted entries), then merge this
  # `columns:` block into one of your --config-file YAMLs.
  columns:
    - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:logical_identifier<1>
      name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:logical_identifier<1>
  ```

- Resolves output path per R-CLI-022 as amended (default
  `./columns.yaml`, auto-numbered; no label file).

`run_copy_default_config` flow (§6):
- Read bytes from `importlib.resources.files('pds4indextools.templates') / 'default_config.yaml'`.
- If destination exists and `not args.force` → `CliError("destination exists; pass --force to overwrite")` (R-CLI-031).
- Write bytes verbatim; log WARNING if overwriting (R-CLI-031).

### 10.2 `__init__.py`

Defines the root `__all__` EXACTLY as the following 59 names (this
list is the binding authority; spec §20's shorter sketch is superseded
per spec-amendment #5). It is precisely the union of every submodule
`__all__` plus `module_logger`:

- from `errors` (20): `Pds4IndexError`, `CliError`, `ConfigError`,
  `LabelError`, `ParseError`, `LidError`,
  `XPathError`, `NilError`, `ScrapedValueError`, `SchemaError`,
  `SchemaResolutionError`, `SchemaVersionError`, `SchemaNetworkError`,
  `SchemaCacheError`, `OutputError`, `FailSlowAggregateError`,
  `EXIT_USER_ERROR`, `EXIT_RUNTIME_ERROR`, `EXIT_INTERNAL_ERROR`,
  `EXIT_SIGINT`
- from `config` (11): `IndexConfig`, `LabelContents`, `OutputSection`,
  `NillableEntry`, `CitationInformation`, `ModificationDetail`,
  `ColumnSpec`, `AbsolutePath`, `AUTO_COLUMN_TOKENS`, `load_config`,
  `parse_sort_key`
- from `xpath_norm` (2): `canonicalize_xpath`, `renumber_xpaths`
- from `schema_types` (3): `SchemaCache`, `SchemaTypeResolver`,
  `AUTO_COLUMN_TYPES`
- from `scraper` (2): `ScrapeResult`, `scrape_label`
- from `csv_writer` (5): `ColumnStat`, `CsvWritePlan`, `build_plan`,
  `write_csv`, `sort_rows`
- from `label_writer` (4): `build_substitution_dict`,
  `normalize_modification_detail`, `write_label`,
  `load_packaged_template`
- from `cli` (11): `main`, `cli_entrypoint`,
  `run_generate_index_file`, `run_generate_xpath_list`,
  `run_copy_default_config`, `GenerateIndexFileArgs`,
  `GenerateIndexFileResult`, `GenerateXpathListArgs`,
  `GenerateXpathListResult`, `CopyDefaultConfigArgs`,
  `CopyDefaultConfigResult`
- from `_logging` (1): `module_logger`

(`__version__` is exported as an attribute but, being a dunder, is not
listed in `__all__`.) Because the root list is the exact union of the
submodule `__all__`s, Phase 12's
`test_every_submodule_all_subset_of_root_all` holds by construction.
Imports symbols from
submodules. Calls `_logging.library_setup()` once at import. Reads
`_version.__version__` and re-exports as
`pds4indextools.__version__`. Carries a module-level docstring (one
paragraph) that satisfies the global Docstring contract.

Per `python.mdc` §3, ONLY names listed in
`pds4indextools.__all__` are part of the public API. Any symbol the
implementer adds (helpers, internal classes, etc.) MUST stay
prefix-underscored and absent from `__all__`. There is no blanket
`F401` ignore on `__init__.py`; ruff treats `__all__`-listed names as
used, so re-exports do not need lint suppression.

`module_logger` (from `_logging.py`) is re-exported from this `__init__`
so consumer modules can `from pds4indextools import module_logger`
rather than reach into the private `_logging` module.

### 10.3 `__main__.py`

Exactly:

```python
"""Entry point for ``python -m pds4indextools``.

Delegates to :func:`pds4indextools.cli.main` and propagates its integer
return value to :func:`sys.exit`.
"""

import sys

from pds4indextools.cli import main

if __name__ == '__main__':
    sys.exit(main())
```

(Module docstring + stdlib-before-local import order per
`python.mdc` §2 and §6.)

### 10.4 Unit tests — `tests/unit/test_cli_parsing_dispatch_and_exit_codes.py`

CLI unit tests invoke `main(['...args...'])` in-process; integration
tests (Phase 11) exercise full bundle pipelines.

**Capture mechanism rule** (critique skill §21): every CLI test that
asserts on stderr content MUST specify the capture mechanism: `capsys`
for argparse direct output (argparse writes via `sys.stderr` directly
when `--help` / parsing errors), `caplog` for `logger.warning` /
`logger.error` records (with explicit
`caplog.set_level(logging.WARNING, logger='pds4indextools')` and
`caplog.records` checks). The capture-mechanism choice MUST match the
`_handle_exception` body in `cli/_dispatch.py`. Since the
library/CLI-output boundary forbids `print()` in source, every error
message reaches stderr via the logging handler attached in
`setup_logging` — therefore tests use `caplog` for content checks and
`capsys` for argparse SystemExit-help text.

All CLI tests that write output files MUST use the `chdir_tmp` fixture
or pass an absolute `--output-file` rooted under `tmp_path` so xdist
workers cannot collide. Do not rely on `os.getcwd()` from outside the
fixture.

Every CLI test whose run must REACH label generation (i.e. succeed
past schema resolution) requests `seeded_cache_overlay` and appends
`'--config-file', str(seeded_cache_overlay)` as the LAST config file —
schema lookups are then served from the pre-seeded cache with zero
network. Failure-path tests that abort before schema resolution do not
need it.

| Test function | Verifies | T-ID |
|---|---|---|
| `test_version_flag_prints_version_and_exits_zero` | `main(['--version'])` → 0; stdout contains version string and 'pds4_create_xml_index' | T-CLI-001, R-CLI-003 |
| `test_no_subcommand_exits_2_and_prints_help` | `main([])` → 2; 'usage:' in stderr | T-CLI-002, R-CLI-005 |
| `test_subcommand_underscore_form_accepted` | `main(['generate_index_file', '--help'])` → 0 | T-CLI-003, R-CLI-002 |
| `test_subcommand_hyphen_form_accepted` | `main(['generate-index-file', '--help'])` → 0 | T-CLI-003, R-CLI-002 |
| `test_subcommand_underscore_and_hyphen_produce_identical_help` | both → same stdout | T-CLI-003, R-CLI-002 |
| `test_xpathlist_underscore_and_hyphen_accepted` | parametrize | T-CLI-004, R-CLI-002 |
| `test_copy_default_config_underscore_and_hyphen_accepted` | parametrize | T-CLI-005, R-CLI-002 |
| `test_generate_index_file_no_bundle_root_exits_2_argparse` | argparse missing-required raises SystemExit(2) | T-CLI-010 |
| `test_generate_index_file_nonexistent_bundle_exits_1` | bundle path doesn't exist → CliError → exit 1 | T-CLI-011, R-CLI-010 |
| `test_generate_index_file_bundle_root_is_file_exits_1` | file path → exit 1 | T-CLI-012 |
| `test_generate_index_file_bundle_root_symlink_to_dir_works` | tmp_path symlink → exit 0 (uses tiny test bundle) | T-CLI-013, R-FS-002 |
| `test_two_patterns_dedup_to_one_row` | two patterns matching same file → 1 row written | T-CLI-020, R-FS-004 |
| `test_empty_pattern_union_exits_1` | patterns match nothing → exit 1; stderr lists all patterns | T-CLI-021, R-DISC-010 |
| `test_absolute_posix_pattern_rejected` | `main([..., '/abs/path/*.lblx'])` on POSIX → exit 1 w/ 'must be relative' | T-CLI-022 (POSIX leg), R-CLI-011 |
| `test_absolute_windows_pattern_rejected` | parametrized; skipif `os.name != 'nt'` | T-CLI-022 (Win leg), R-CLI-011 |
| `test_three_config_files_merged_in_order` | last value wins | T-CLI-030, R-CLI-012, R-CFG-051 |
| `test_label_template_default_packaged_path_used` | use temp bundle; check label generated from packaged template (by sniffing a known string in the output) | T-CLI-050, T-LBL-001, R-CLI-014, R-LBL-001, R-LBL-040 |
| `test_custom_label_template_honored` | `--label-template` pointing at a minimal valid template file containing the sentinel text `CUSTOM-TEMPLATE-SENTINEL`; the generated lblx contains the sentinel | T-LBL-002, R-LBL-002 |
| `test_fail_slow_collects_multiple_filespec_overlength_errors` | monkeypatch the scraper so two of three labels raise the filespec-overlength `LabelError`; `--fail-slow` → `FailSlowAggregateError` with exactly 2 errors | T-AUTO-060, R-FS-010, R-FSLOW-110 |
| `test_default_output_paths_used` | uses `chdir_tmp` + `seeded_cache_overlay`; run main on `simple_pds_only`; assert `(chdir_tmp/'index.csv').is_file()` and `(chdir_tmp/'index.lblx').is_file()` (default names per R-CLI-015). Byte-golden comparison does NOT happen here — the goldens are first generated in Phase 11; `test_default_output_paths_byte_golden` in Phase 11's `test_generate_index_file.py` covers it | T-CLI-060 (paths leg), R-CLI-015 |
| `test_default_output_auto_numbers_when_present` | uses `chdir_tmp`; pre-create `<chdir_tmp>/index.csv` with sentinel bytes `b'OLD'`; invoke main; assert (a) `(chdir_tmp/'index_1.csv').is_file()`, (b) `(chdir_tmp/'index_1.lblx').is_file()`, (c) `(chdir_tmp/'index.csv').read_bytes() == b'OLD'` (original unchanged), (d) one `caplog` record at WARNING level naming the new path | T-CLI-061, R-CLI-015 |
| `test_default_output_auto_numbers_finds_lowest_free_integer` | pre-create both `index.csv` and `index_1.csv` → run writes `index_2.*` | R-CLI-015 |
| `test_default_output_auto_numbers_considers_both_csv_and_lblx` | pre-create only `index.lblx` → run writes `index_1.csv` + `index_1.lblx` | R-CLI-015 |
| `test_specified_output_csv_overwrites_with_warning` | `--output-file foo.csv` exists → overwrite. Assert (a) `caplog.records` contains exactly one record at level `WARNING` whose message contains `"overwriting"` and the path; (b) `result.warnings` (the `GenerateIndexFileResult.warnings` tuple) has length 1 with the same content; (c) no other WARNING/ERROR records emitted | T-CLI-062, R-OUT-013 |
| `test_specified_output_tab_extension_uses_tab_for_data_and_lblx_for_label` | `--output-file foo.tab` → writes foo.tab + foo.lblx | T-CLI-063, R-OUT-012 |
| `test_specified_output_no_extension_appends_csv` | `--output-file foo` → foo.csv + foo.lblx | T-CLI-065, R-OUT-011 |
| `test_specified_output_csv_replaces_only_csv_extension_for_label` | `--output-file foo.csv` → foo.csv + foo.lblx | T-CLI-064, R-OUT-010 |
| `test_top_level_help_epilog_has_example` | `--help` stdout contains 'Example' or 'pds4_create_xml_index' twice | T-CLI-070, R-CLI-040 |
| `test_each_subcommand_help_has_examples` | parametrize 3 subcommands | T-CLI-071, R-CLI-040 |
| `test_xpath_list_rejects_label_template_arg` | `generate_xpath_list --label-template foo.xml` → argparse SystemExit(2) w/ 'unrecognized' (`--mapping-file` no longer exists on ANY subcommand — spec-amendment #11 — so there is nothing to reject) | T-CLI-081, R-CLI-021 |
| `test_generate_index_file_without_columns_exits_1` | config chain lacking any `columns` section → exit 1; caplog ERROR record contains `'no columns defined'` and `'generate_xpath_list'` | owner decision #10 |
| `test_copy_default_config_rejects_bundle_root` | argparse SystemExit(2) | T-CLI-090, R-CLI-032 |
| `test_copy_default_config_without_output_file_exits_2` | argparse missing-required | T-CLI-091, R-CLI-030 |
| `test_copy_default_config_existing_dest_without_force_exits_1` | exit 1; stderr 'destination exists' | T-CLI-092, R-CLI-031 |
| `test_copy_default_config_existing_dest_with_force_overwrites_with_warning` | overwrite + WARNING | T-CLI-093, R-CLI-031 |
| `test_verbosity_none_warning_level` | `setup_logging` called with verbosity=0 | T-CLI-100, R-CLI-017 |
| `test_verbosity_v_info_level` | -v → 1 | T-CLI-100 |
| `test_verbosity_vv_debug_level` | -vv → 2 | T-CLI-100 |
| `test_verbosity_vvv_debug_clamped` | -vvv → 3, mapped to DEBUG | T-CLI-100 |
| `test_keyboard_interrupt_returns_130_and_cleans_temp_files` | monkeypatch scraper to raise KeyboardInterrupt mid-scrape; assert exit 130; no `index.csv` or `index.lblx` on disk; no `*.tmp` left over | T-FSLOW-020, R-ERR-002 |
| `test_pds4indexerror_subclass_caught_and_mapped_to_exit_code` | parametrize `(exc_cls, expected_exit_code)` over `CliError→1, ConfigError→1, LabelError→2, SchemaError→2, OutputError→2, FailSlowAggregateError→2`. For each: monkeypatch the appropriate `run_*` to raise `exc_cls("msg-XYZ", file_path=Path("/tmp/foo"), lineno=42)` (with `errors=[LidError("inner")]` for FailSlowAggregateError); assert (a) `main(...) == expected_exit_code`, (b) `"msg-XYZ"` in any `caplog` record's message at ERROR level, (c) `"/tmp/foo:42"` in any `caplog` record | R-API-004 |
| `test_unhandled_exception_returns_3_and_prints_traceback` | monkeypatch internal to raise `RuntimeError("intentional-test-token")` → `main(...) == 3`; assert `capsys.readouterr().err` contains `'Traceback'` AND `'RuntimeError'` AND `'intentional-test-token'`; AND does NOT contain `'Pds4IndexError'` (proving the type-check branch was reached and rejected the marker) | spec §17.2 |
| `test_main_does_not_mutate_cwd` | record `os.getcwd()` before `main([...])`; assert it is unchanged after the call (production code MUST NOT chdir) | codebase-analysis §6+§17 |
| `test_main_does_not_call_sys_exit` | call `main([...])` inside `monkeypatch.setattr(sys, 'exit', lambda c: pytest.fail(f"main called sys.exit({c})"))`; assert no fail | library-CLI boundary |
| `test_failslow_aggregate_summary_printed_to_stderr` | bundle with 2 bad LIDs + `--fail-slow` → stderr lists both | T-FSLOW-002 (CLI leg), R-FSLOW-120 |
| `test_run_generate_index_file_returns_result_dataclass` | programmatic API on `simple_pds_only` with `frozen_time` and `chdir_tmp`; assert `isinstance(result, GenerateIndexFileResult)`; assert `result.rows_written == 1`, `result.columns_written == 3`, `result.warnings == ()`, `result.csv_path == (chdir_tmp/'index.csv').resolve()`, `result.label_path == (chdir_tmp/'index.lblx').resolve()`; assert `dataclasses.is_dataclass(result)`; assert `{f.name for f in dataclasses.fields(result)} == {'csv_path','label_path','rows_written','columns_written','warnings'}` (exact set) | R-API-003 |
| `test_run_generate_index_file_raises_failslowaggregateerror` | two bad LIDs + fail_slow=True → raises | T-FSLOW-004, R-API-004 |
| `test_run_generate_index_file_result_warnings_contains_overwrite_messages_only` | not fail-slow errors | T-FSLOW-005, R-API-004 |
| `test_run_generate_index_file_temp_files_cleaned_on_failure` | inject scraper failure → no `*.tmp` left in target dir | R-ERR-002 |
| `test_main_returns_int_exit_code_not_calls_sys_exit` | `assert isinstance(main([...]), int)` | API contract |
| `test_output_file_path_resolved_to_absolute_for_index_file_name_substitution` | the index_file_name template variable is absolute | spec §14.2 |

### 10.5 Phase 10 exit criteria

- [ ] All unit tests pass.
- [ ] Coverage ≥ 95% line+branch on the `cli/` package and `__init__.py`.
- [ ] mypy + ruff clean across the whole `src/` tree.
- [ ] `pds4_create_xml_index --version` runs after `pip install -e .` and
      prints the version.

---

## Phase 11 — Integration tests + fixture bundles

### 11.1 Deliverables

Under `tests/data/bundles/`, VERIFY the 11 bundle subdirectories
committed in Phase 0 per Appendix A.7 (every label file suffixed
`.lblx`); this phase adds the `expected/` golden content and the
integration tests.
**Bundle label content is specified verbatim in
[Appendix B](#appendix-b-test-fixture-content).** Feature-variant tests
(fixed-width, CRLF, multi-config, mapping-full-features) do NOT get
bundles of their own — they reuse `simple_pds_only` or
`multi_namespace` with a feature config (owner decision #8),
and their golden outputs live under the feature-named
`tests/data/expected/<feature>/` directories. **Spec impact:** spec
§24.15's bundle table (17 rows, including the copy bundles and
`large_synthetic`) needs a matching update to 11 bundles; the
`large_synthetic` stress bundle is removed outright (owner decision
#9).

Under `tests/data/configs/`: full content in [Appendix B](#appendix-b-test-fixture-content).

Under `tests/data/expected/`: full content in [Appendix B](#appendix-b-test-fixture-content).

Integration test files (under `tests/integration/`):

- `test_generate_index_file.py` — happy paths and most failure paths.
- `test_generate_xpath_list.py` — happy paths and failure paths.
- `test_copy_default_config.py`.
- `test_subprocess_smoke.py` — invokes `subprocess.run([sys.executable,
  '-m', 'pds4indextools', ...])`.
- `test_determinism.py` — runs each bundle twice and asserts byte-identical
  output (R-IDX-001, R-IDX-002).

### 11.2 Integration tests — detailed list

Each integration test marks `@pytest.mark.integration` so developers can
run a fast subset with `pytest -m "not integration"`. The CI matrix runs
both.

All non-`live` integration tests resolve schemas from the pre-seeded
session cache: they request `seeded_cache_overlay` (A.6) and append it
as the LAST `--config-file` / `config_files` entry — zero network, and
byte-deterministic type resolution against the committed seed XSDs
(R-TST-021, R-TST-030 as amended). The `xsd_cache_session` fixture
remains for `@pytest.mark.live` tests only, which exercise real
downloads from pds.nasa.gov.

**Golden-lblx binding rule**: every test that compares `.lblx` output
byte-for-byte against a committed golden invokes
`run_generate_index_file` PROGRAMMATICALLY with
`csv_post_write_hook=lambda p: os.utime(p, (frozen_csv_mtime, frozen_csv_mtime))`
under `frozen_time` — exactly mirroring the generator (Appendix I).
Tests that go through the CLI (`main([...])`) have no hook, so they
compare CSV bytes fully but lblx bytes only modulo the
`creation_date_time` line (see T-CLI-060 in Phase 10 for the exact
masking mechanism; Phase 9 verifies `$FILE_ZULU(...)$` is the
template's only mtime-dependent macro).

Full list with bundle and verifying R-IDs:

#### `test_generate_index_file.py`

| Test | Bundle | Verifies |
|---|---|---|
| `test_simple_pds_only_happy_path` | `simple_pds_only` | R-IDX-001, R-LBL-001, R-CSV-061 |
| `test_simple_pds_only_byte_identical_to_expected` | `simple_pds_only` | golden CSV+lblx comparison |
| `test_default_output_paths_byte_golden` | CLI path: `chdir_tmp` + `frozen_time` + `data_root` + `seeded_cache_overlay`; run `main` on `simple_pds_only`; assert `(chdir_tmp/'index.csv').read_bytes() == (data_root/'expected'/'simple_pds_only'/'index.csv').read_bytes()`; assert the lblx matches the golden after the creation-date mask: split both byte streams on the line terminator, assert each side contains EXACTLY ONE line containing `<creation_date_time>`, drop it from both, compare the rest byte-for-byte (the CLI path has no `csv_post_write_hook`, so only the `$FILE_ZULU$`-derived line is uncontrolled) | T-CLI-060 (bytes leg), R-CLI-015 |
| `test_multi_namespace_three_labels_render_geom_and_rings_prefixes` | `multi_namespace` | R-XP-011, R-SCH-040 |
| `test_nilled_label_substitutes_config_defaults` | `nilled` | T-NIL-001, R-NIL-010, R-NIL-020 |
| `test_nilled_bad_nilreason_aborts_with_exit_2` | `nilled_bad` | T-NIL-010, R-NIL-010 |
| `test_repeated_tags_renumbered_in_canonical_form` | `repeated_tags` | T-XP-020, R-XP-020 |
| (see B.6 — no integration test; R-XP-021 is exercised by `test_renumber_non_monotone_interleave_raises_xpatherror` in `tests/unit/test_xpath_canonicalization_and_renumbering.py`) | n/a | T-XP-021, R-XP-021 |
| `test_multi_lid_two_labels_share_lid_aborts_with_exit_2` | `multi_lid` | T-LID-050, R-LID-020 |
| `test_multi_lid_under_failslow_aborts_before_write` | `multi_lid` + `--fail-slow` | T-LID-051, R-LID-020, R-FSLOW-110, R-FSLOW-120 |
| `test_bom_label_rejected_with_parseerror` | `bom` | T-PARSE-001 implied, R-PARSE-001 |
| `test_non_ascii_value_label_rejected_with_scrapedvalueerror` | `non_ascii_value` | T-CSV-040, R-VAL-030 |
| `test_quote_in_value_variable_width_rejected` | `quote_in_value` + `quote_in_value_var.yaml` | R-VAL-040 |
| `test_quote_in_value_fixed_width_passes_through` | `quote_in_value` + `quote_in_value_fixed.yaml` | R-VAL-040 |
| `test_version_mismatch_two_labels_aborts` | `version_mismatch` | T-SCH-020, R-SCH-040 |
| `test_no_schema_location_label_raises_schemaresolutionerror` | `no_schema_location` | T-SCH-030, R-SCH-050 |
| `test_fixed_width_config_byte_identical_to_expected` | `simple_pds_only` + `fixed_width.yaml`; golden in `expected/fixed_width/` (see B.13: for this single-row bundle the CSV bytes equal the variable-width bytes; multi-row padding is unit-tested at T-CSV-020/021) | R-CSV-070, R-CSV-071 |
| `test_fixed_width_lblx_uses_table_character` | same run; lblx golden contains `<Table_Character>` with correct `record_length`/`field_location`/`field_length` | R-LBL-020, R-LBL-060 |
| `test_crlf_config_writes_crlf_csv_and_label_record_delimiter` | `simple_pds_only` + `crlf.yaml`; golden in `expected/crlf/` | T-CSV-030, R-CSV-003, R-LBL-060 |
| `test_lf_config_writes_lf_record_delimiter` | `simple_pds_only` + `simple.yaml` (LF default; negative case) | T-CSV-031, R-LBL-060 |
| `test_multi_config_three_yamls_merge_in_order` | `simple_pds_only` + the three `multi_config_*.yaml`; golden in `expected/multi_config/` | T-CFG-040, R-CFG-050, R-CFG-051 |
| `test_mapping_full_features_byte_identical_to_expected_csv` | `multi_namespace` + `mapping_full_features.yaml` (every columns-entry shape); golden in `expected/mapping_full_features/` | T-MAP-090, R-MAP-300, R-MAP-320, R-AUTO-010 |
| `test_mapping_xpath_not_in_any_label_produces_empty_column` | `multi_namespace` + chain (`multi_namespace.yaml`, `xpath_not_in_label.yaml`) | T-MAP-080, T-NIL-040, R-MAP-311, R-MISS-010 |
| `test_columns_not_listing_an_observed_xpath_drops_it` | `simple_pds_only` + chain (`simple.yaml`, `columns_only_lid.yaml`); assert CSV header bytes equal `b"LID\n"` exactly; assert exactly 1 data row with no commas; assert `result.columns_written == 1`; assert `title`/`version_id` strings are absent from the output bytes | T-MAP-081, R-MAP-310 |
| `test_missing_columns_exits_1_with_guidance` | `simple_pds_only` + a config chain that defines NO `columns` (e.g. `minimal.yaml` only) → exit 1; ERROR record contains `'no columns defined'` and `'generate_xpath_list'` | owner decision #10 |
| `test_empty_columns_list_aborts` | overlay config with `columns: []` → exit 1 (`ConfigError` at load) | T-MAP-082, R-MAP-312 |
| `test_run_generate_index_file_programmatic_returns_result` | API path | R-API-003 |
| `test_run_generate_index_file_programmatic_raises_failslowaggregateerror` | API path with 2 bad LIDs | T-FSLOW-004, R-API-004 |
| `test_run_generate_index_file_programmatic_success_warnings_overwrite_only` | API path w/ overwrite | T-FSLOW-005, R-API-004 |
| `test_run_generate_index_file_keyboardinterrupt_propagates_with_temp_cleanup` | mock scraper → KeyboardInterrupt | T-FSLOW-020, R-ERR-002 |
| `test_generate_index_file_with_fixed_width_renders_label_table_character` | `simple_pds_only` + `fixed_width.yaml` | R-LBL-* product class booleans |
| `test_progress_bar_disabled_in_non_tty` | `multi_namespace`; run under the `deterministic_env` fixture (stderr non-TTY); assert no tqdm control bytes in captured stderr | R-LOG-020, R-LOG-021 |
| `test_no_xsd_redownload_within_session` | `multi_namespace` run twice with `seeded_cache_overlay`, under an active `responses` mock with NO registered endpoints (any HTTP attempt would error); both runs succeed → proves every lookup was a cache hit, zero downloads | R-SCH-020, R-TST-021 |
| `test_generate_index_file_md5_matches_csv` | bundle with stable content | T-LBL-050, R-LBL-070 |
| `test_generate_index_file_record_delimiter_matches_csv_bytes_lf` | LF bundle | T-LBL-060, R-LBL-060 |
| `test_generate_index_file_record_delimiter_matches_csv_bytes_crlf` | CRLF bundle | T-LBL-060, R-LBL-060 |
| `test_single_bad_lid_fail_fast_exits_2_no_output` | tmp-dir bundle written by the test (one label whose LID is `not-a-urn`) → exit 2 immediately, no CSV/lblx on disk | T-FSLOW-001, R-ERR-001 |
| `test_three_bad_lids_fail_slow_accumulates_three` | tmp-dir bundle: three bad-LID labels + `--fail-slow` → aggregate of 3, exit 2, no output files | T-FSLOW-002, R-FSLOW-110, R-FSLOW-120 |
| `test_bad_lid_and_missing_version_id_accumulated_under_fail_slow` | tmp-dir bundle: one bad-LID label + one missing-`version_id` label + `--fail-slow` → aggregate of 2 | T-LID-040, R-FSLOW-110, R-FSLOW-120 |
| `test_fail_slow_all_good_writes_normally` | `simple_pds_only` + `--fail-slow` → output byte-identical to the non-fail-slow run | T-FSLOW-003, R-FSLOW-130 |
| `test_network_failure_not_masked_by_fail_slow` | no seeded cache; `responses` returns 500 for the XSD URL; `--fail-slow` → immediate exit 2 (`SchemaNetworkError` is NOT collected) | T-FSLOW-010, R-SCH-060, R-FSLOW-100 |
| `test_non_ascii_value_under_fail_slow_accumulates_then_aborts` | `non_ascii_value` + `--fail-slow` → aggregate contains the `ScrapedValueError`; no output files | T-CSV-041, R-FSLOW-110, R-FSLOW-120 |
| `test_sort_by_lid_ascending` | `multi_namespace` + chain (`multi_namespace.yaml`, tmp-path overlay YAML `output: {sort_by: ['LID']}` written by the test) → rows ordered by LID ascending (`LID` is the emitted header, R-SORT-020) | T-CSV-060 |
| `test_sort_by_lid_descending` | same, overlay `sort_by: ['-LID']` → descending | T-CSV-060 |
| `test_sort_by_unknown_column_aborts_with_configerror` | same, overlay `sort_by: ['unknown']` → exit 1 | T-CSV-061, R-SORT-020 |

#### `test_generate_xpath_list.py`

| Test | Bundle | Verifies |
|---|---|---|
| `test_xpath_list_emits_yaml_columns_block` | `simple_pds_only`; byte-identical match against `tests/data/expected/xpath_lists/simple_pds_only.yaml` (LF terminators) | T-XPL-001, R-XPL-020 (as amended) |
| `test_xpath_list_first_occurrence_order_across_alphabetically_sorted_labels` | `multi_namespace`; assert (a) byte-identical match against `tests/data/expected/xpath_lists/multi_namespace.yaml`, (b) exactly 5 `- xpath:` entries, (c) entries 0..2 are the pds-namespace XPaths from `a.lblx`'s `Identification_Area` | T-XPL-002, R-XPL-010 |
| `test_xpath_list_output_is_loadable_as_config` | run on `simple_pds_only`; `yaml.safe_load` the output → mapping with a `columns` list; passing the file through `load_config` (chained after `minimal.yaml`) validates cleanly — the emitted block is usable as-is | spec-amendment #12 round-trip |
| `test_xpath_list_emits_canonical_form_with_predicate_one` | `simple_pds_only` | T-XPL-004, R-XP-002 |
| `test_xpath_list_failslow_behaves_like_index_file` | bundle with 1 good + 1 bad-LID | T-XPL-010, R-FSLOW-100 |
| `test_xpath_list_output_path_defaults_columns_yaml` | default output is `./columns.yaml` | R-CLI-022 (as amended) |
| `test_xpath_list_auto_numbers_when_default_exists` | pre-create `columns.yaml` → writes `columns_1.yaml` | R-CLI-022 |
| `test_xpath_list_specified_path_overwrites_with_warning` | overwrite | R-CLI-022 |
| `test_xpath_list_specified_path_no_extension_appends_yaml` | `--output-file foo` → `foo.yaml` | R-CLI-022 (as amended) |

#### `test_copy_default_config.py`

| Test | Verifies |
|---|---|
| `test_copy_default_config_bytes_byte_identical_to_packaged` | T-CDC-001, R-CFG-201 |
| `test_copy_default_config_refuses_overwrite_without_force` | T-CDC-002, R-CLI-031 |
| `test_copy_default_config_force_overwrites_with_warning` | T-CDC-003, R-CLI-031 |
| `test_copy_default_config_force_is_idempotent` | run with `--force` twice into the same path; assert dest bytes after each call equal `importlib.resources.files('pds4indextools.templates').joinpath('default_config.yaml').read_bytes()`; assert `hashlib.md5(dest.read_bytes()).hexdigest()` is the same after both runs | R-CLI-031 (critique skill §13) |

#### `test_subprocess_smoke.py`

Every test in this file invokes
`subprocess.run(..., timeout=60, check=False, capture_output=True, text=True)`.
The 60-second budget matches the global `--timeout=60` from `addopts`.
All `subprocess.run` calls use the list-of-strings argv form; `shell=True`
is FORBIDDEN. The test invocations use `sys.executable` (not a hard-coded
`'python'`) so the active venv interpreter runs.

| Test | Verifies |
|---|---|
| `test_subprocess_generate_index_file_happy_path` | T-SUB-001 |
| `test_subprocess_generate_index_file_bad_bundle_exit_1` | T-SUB-002 |
| `test_subprocess_generate_xpath_list_happy_path` | T-SUB-003 |
| `test_subprocess_generate_xpath_list_bad_bundle_exit_1` | T-SUB-004 |
| `test_subprocess_copy_default_config_happy_path` | T-SUB-005 |
| `test_subprocess_copy_default_config_overwrite_exit_1` | T-SUB-006 |
| `test_subprocess_version_flag` | R-CLI-003 end-to-end |
| `test_subprocess_no_subcommand_exits_2` | R-CLI-005 end-to-end |

#### `test_determinism.py`

| Test | Verifies |
|---|---|
| `test_two_runs_produce_byte_identical_csv_simple_pds_only` | run pipeline twice in separate tmp dirs under `frozen_time` and `chdir_tmp`; assert `dir1/index.csv` and `dir2/index.csv` are byte-identical via `hashlib.sha256(...).hexdigest()` AND via `read_bytes()` equality AND via `filecmp.cmp(..., shallow=False)`; assert `os.path.getsize` matches | R-IDX-001 |
| `test_two_runs_produce_byte_identical_lblx_simple_pds_only` | as above for `.lblx`; both runs use the same `frozen_time` decorator so MD5 / Zulu macros match | R-IDX-001 |
| `test_two_runs_produce_byte_identical_csv_multi_namespace` | as above for `multi_namespace` bundle | R-IDX-001 |
| `test_two_runs_produce_byte_identical_lblx_multi_namespace` | as above | R-IDX-001 |
| `test_two_runs_byte_identical_with_filesystem_order_randomization` | run once normally; run again with `monkeypatch.setattr(Path, 'glob', <reversed wrapper>)` (use `monkeypatch.setattr`, NOT direct attribute assignment, per `python_testing.mdc` §10); assert `sha256(csv_a) == sha256(csv_b)` AND `sha256(lblx_a) == sha256(lblx_b)`; assert the monkeypatched glob was actually invoked at least once during the second run (sanity-check) | R-IDX-002 |

`test_determinism.py` uses BOTH `frozen_time` (via `freezegun.freeze_time`
for in-Python time) AND `frozen_csv_mtime` (via `os.utime` on the
written CSV before label generation, to fix `$FILE_ZULU(...)$`) per
Appendix I. The lblx golden comparison is exact bytes; no portion of
the label is masked. The module docstring states this contract.

(The former 1,000-label `large_synthetic` stress test file is removed
per owner decision #9. Its still-relevant assertions — progress-bar
suppression and XSD-cache reuse — live in `test_generate_index_file.py`
above against the 3-label `multi_namespace` bundle; determinism under
filesystem perturbation is covered in `test_determinism.py`.)

### 11.3 Phase 11 exit criteria

- [ ] All integration tests pass.
- [ ] Total coverage (unit + integration) ≥ 90% line+branch
      measured over the ENTIRE test suite (`python_testing.mdc` §7).
- [ ] `pytest` (full suite) finishes in under 2 minutes on the dev box.
- [ ] No tests are skipped without an explicit
      `pytest.mark.skipif(..., reason="...")` decorator. Reason strings
      are one short sentence (`python_testing.mdc` §10).
- [ ] No test comments include line numbers, verbose rationale, or
      modification history (`python_testing.mdc` §10).
- [ ] Every `pytest.mark.xfail` (if any exist) uses `strict=True` and
      includes a `reason=` referencing an open issue URL
      (critique skill §19).
- [ ] No `skipif` references a Python version below 3.10 (the project's
      minimum); no `skipif` references an OS the CI does not cover.
- [ ] `pytest --markers` output shows exactly two project-registered
      markers: `live` and `integration`; no unregistered marker fires
      anywhere in the suite (proved by `--strict-markers`).

---

## Phase 12 — Documentation

### 12.1 Deliverables

Template docs files are the basis (§0.0): `docs/conf.py`,
`docs/index.rst`, `docs/module.rst`, `docs/contributing.rst`,
`docs/code_of_conduct.md`, `docs/Makefile`, `docs/make.bat` are already
committed from the template. This phase modifies the first three
minimally and adds NEW documentation pages only:

- `docs/conf.py` — apply the delta in [Appendix C.1](#c1-docsconfpy)
  to the committed template file (intersphinx targets + nitpick
  ignores only).
- `docs/index.rst` — apply the delta in [Appendix C.2](#c2-docsindexrst)
  (extend the template toctree).
- `docs/module.rst` — apply the delta in [Appendix C.9](#c9-docsmodulerst)
  (extend the template automodule skeleton with per-submodule sections).
- `docs/contributing.rst`, `docs/code_of_conduct.md` — template files,
  UNCHANGED.
- New pages: `docs/installation.rst` — per [Appendix C.3](#c3-docsinstallationrst);
  `docs/quickstart.rst` — per [Appendix C.4](#c4-docsquickstartrst);
  `docs/cli.rst` — per [Appendix C.5](#c5-docsclirst);
  `docs/config.rst` — per [Appendix C.6](#c6-docsconfigrst);
  `docs/architecture.rst` — per [Appendix C.8](#c8-docsarchitecturerst);
  `docs/usage_examples.rst` — per [Appendix C.10a](#c10a-docsusage_examplesrst).
- `README.md` — keep the committed template structure (badge block,
  section order, `<!-- start-after-point -->` markers) and fill in the
  TODO sections per [Appendix C.12](#c12-readmemd). No logo.
- `CONTRIBUTING.md` — keep the committed template content; extend only
  as needed per [Appendix C.13](#c13-contributingmd).
- `tests/unit/test_documentation_conventions.py` — the eleven tests below
  (plus three public-API traceability tests added for R-API-001/R-API-002:
  `test_every_public_callable_has_docstring`,
  `test_every_public_function_is_fully_type_annotated`, and
  `test_every_public_class_annotations_resolve`), all parametrized where
  applicable:
  - `test_every_public_name_in_root_all_appears_in_module_rst` —
    parametrize over every name in `pds4indextools.__all__`; for each
    name, assert `name` appears in `docs/module.rst` text (read once
    at module scope).
  - `test_every_submodule_all_subset_of_root_all` — for every
    submodule that defines `__all__`, every name is a subset of
    `pds4indextools.__all__`.
  - `test_module_rst_no_duplicate_automodule_directives` — count
    distinct `.. automodule::` lines; assert each appears at most once.
  - `test_no_args_section_in_any_docstring` — recursively walk every
    public symbol via `inspect.getmembers(pds4indextools)`; assert
    `'Args:'` not in `inspect.getdoc(obj)` (handles both
    `Args:`-spelled docstrings and `Args:` mid-paragraph).
  - `test_every_public_class_has_docstring` — parametrize over every
    class in `__all__`; assert `inspect.getdoc(cls) is not None and
    inspect.getdoc(cls).strip() != ''` (covers R-DOC-010).
  - `test_no_args_heading_in_source_docstrings` — greps every
    `src/**/*.py` file for lines matching `^\s*Args:` and asserts zero
    hits (`documentation.mdc` §4; replaces the shell-script tripwire
    the earlier draft added to `scripts/run-all-checks.sh`).
  - `test_no_british_spellings_in_prose` — greps `src/**/*.py`,
    `docs/**/*.rst`, `docs/**/*.md`, `README.md`, `CONTRIBUTING.md`
    (excluding `docs/_build/`) for the word-boundary pattern
    `\b(colour|behaviour|optimise|organis(e|ing|ation)|licence|analyse|favour|labelled|cancelled|catalogue|programme|whilst)\b`
    and asserts zero hits (`documentation.mdc` §2 American English).
  - `test_single_space_after_period` — greps the same file set for
    `\.  [A-Za-z]` (period + two spaces + letter) and asserts zero
    hits (`documentation.mdc` §2).
  - `test_pragma_no_cover_budget` — counts `# pragma: no cover`
    occurrences across `src/**/*.py` and asserts the count is ≤ 5
    (Phase 14 budget).
  - `test_verify_public_api_script_passes` — imports
    `scripts/verify_public_api.py` (via
    `importlib.util.spec_from_file_location`) and asserts its
    `main() == 0`. This is how the script runs in CI: through the
    template's ordinary pytest step, with no workflow changes.
  - `test_verify_test_coverage_script_passes` — same wrapper for
    `scripts/verify_test_coverage.py`.

### 12.2 Sphinx build invariants

- `sphinx-build -W -b html docs docs/_build/html` exits 0 with ZERO
  warnings emitted (`documentation.mdc` §5).
- `sphinx-build -n -W -b html docs docs/_build/nit-html` exits 0 with
  ZERO warnings emitted (nitpicky AND warnings-as-errors combined per
  `documentation.mdc` §5).
- Every public name in `pds4indextools.__all__` appears in
  `docs/module.rst` via `automodule`. A verification script
  `scripts/verify_public_api.py` is exercised by
  `test_verify_public_api_script_passes` in the ordinary pytest run
  (codebase-analysis §6): import every submodule under
  `pds4indextools.*`; collect names not starting with `_` defined at
  module level; compare against each submodule's `__all__`; compare
  against the `:members:` listing extracted from `docs/module.rst`;
  exit 1 if any set disagrees.
- Every narrative-prose mention of a class, method, function, module,
  attribute, or data constant in the docs tree (README, *.rst, *.md,
  docstrings) uses the appropriate Sphinx cross-reference role from
  `documentation.mdc` §5:
  - `` :class:`~pds4indextools.module.Class` ``
  - `` :meth:`~pds4indextools.module.Class.method` ``
  - `` :func:`~pds4indextools.module.func` ``
  - `` :mod:`pds4indextools.module` ``
  - `` :attr:`~pds4indextools.module.Class.attr` ``
  - `` :data:`~pds4indextools.module.NAME` ``
  - `` :exc:`~pds4indextools.errors.SomeError` `` (Sphinx's
    exception-specific alias of `:class:`). The project picks `:exc:`
    for every exception class and applies it consistently across the
    docs tree.
- Bare CamelCase or `module.symbol` text in narrative prose is forbidden
  EVEN inside inline literals (`` ` ``). Inline literals are reserved
  for YAML/JSON keys, file paths, CLI tokens, and shell snippets.
- Cross-references are omitted inside `.. code-block::` directives,
  `::` literal blocks, Mermaid blocks, YAML examples, and section
  titles (`documentation.mdc` §5).
- Section titles in any `.rst` file are plain text only; cross-reference
  roles are forbidden inside section titles. To cross-link a section,
  give it a `.. _label:` and use `` :ref:`label` `` from prose.
- Every docstring in `src/` follows PEP 257 + Google style with
  `Parameters:` (NOT `Args:`), `Returns:`/`Raises:` blocks only where
  applicable, behavioral notes sufficient to write a black-box test,
  90-char wrap (`documentation.mdc` §4).
- All prose (docstrings, RST, MD) uses American-English spelling;
  British forms (color/colour, behavior/behaviour, optimize/optimise,
  organization/organisation, license/licence, analyze/analyse) are
  flagged by `test_no_british_spellings_in_prose` in
  `tests/unit/test_documentation_conventions.py`. (No project-local
  shell check is added to `scripts/run-all-checks.sh` — §0.0.)
- Exactly one space after every sentence-terminating period; enforced
  by `test_single_space_after_period` in the same test file
  (`documentation.mdc` §2).
- No docstring uses `Args:` instead of `Parameters:`; enforced by
  `test_no_args_heading_in_source_docstrings` in the same test file
  (`documentation.mdc` §4).
- PyMarkdown scan passes per `scripts/run-all-checks.sh --pymarkdown`.

### 12.3 Phase 12 exit criteria

- [ ] `sphinx-build -W -b html docs docs/_build/html` exits 0 with ZERO
      warnings.
- [ ] `sphinx-build -n -W -b html docs docs/_build/nit-html` exits 0
      with ZERO warnings (nitpicky AND warnings-as-errors together).
- [ ] `pymarkdown scan docs/ .cursor/ README.md CONTRIBUTING.md` exits 0.
- [ ] README quickstart matches `docs/quickstart.rst` example exactly.
- [ ] Every name in `__all__` has a Google-style docstring with
      `Parameters:` (NOT `Args:`), `Returns:`/`Raises:` blocks only
      where applicable, behavioral notes sufficient for a black-box
      test, and 90-char wrap (`documentation.mdc` §4).
- [ ] `scripts/verify_public_api.py` exits 0 (proves `__all__` ↔
      `module.rst` are in sync).
- [ ] `pytest tests/unit/test_documentation_conventions.py` GREEN
      (includes the Args:/American-English/single-space/pragma-budget
      convention tests and the two verify-script wrappers).
- [ ] `git diff` on `docs/conf.py`, `docs/index.rst`, `docs/module.rst`,
      `README.md`, and `CONTRIBUTING.md` shows only the deltas
      enumerated in Appendix C (template content otherwise preserved).

---

## Phase 13 — CI verification (template workflows, unchanged)

### 13.1 Deliverables

NONE. The three template workflows are already committed and are kept
byte-identical to the template (with the REPONAME/MODULENAME
substitutions already applied):

- `.github/workflows/run-tests.yml` — lint job (ruff check, ruff
  format, mypy, `sphinx-build -W`, pymarkdown) plus a test matrix
  (Python 3.10/3.11/3.12/3.13 on ubuntu-latest) running
  `pytest --cov=src --cov-report=xml -n auto tests` with a codecov
  upload.
- `.github/workflows/publish_to_pypi.yml` — template publish workflow.
- `.github/workflows/publish_to_test_pypi.yml` — template test-publish
  workflow.

No new workflows are added (§0.0; the previously drafted `ci.yml` and
`pip_audit.yml` are dropped). **Spec impact:** spec §23's
R-CI-001..R-CI-005 (multi-OS matrix, pip-audit job, separate docs job)
describe the dropped design and need updating to match the template
workflows; `scripts/verify_test_coverage.py` exempts the `R-CI-*`
family (Appendix A.13). Everything the dropped workflows checked
is reachable from the template's standard steps:

- `scripts/verify_public_api.py` and `scripts/verify_test_coverage.py`
  run inside pytest via the wrapper tests in
  `tests/unit/test_documentation_conventions.py` (Phase 12).
- Docstring/prose conventions and the pragma budget are unit tests in
  the same file.
- pyroma, vulture, and the nitpicky Sphinx build run locally via
  `scripts/run-all-checks.sh` and the Phase 12/14 exit criteria; they
  are not CI-gated, matching the template's division of labor.

### 13.2 Phase 13 verification tasks

This phase only CONFIRMS the committed workflows run green against the
finished code:

1. Confirm `git diff` between each workflow file and its template
   counterpart shows only the REPONAME/MODULENAME substitutions.
2. Open a pull request to `main` (or run
   `gh workflow run run-tests.yml`) — the workflow triggers only on
   pushes/PRs to `main`, the weekly cron, and manual dispatch, NOT on
   feature-branch pushes — and confirm both jobs (lint + all four
   matrix legs) pass.

### 13.3 Phase 13 exit criteria

- [ ] `gh workflow list` shows exactly the three template workflows.
- [ ] `run-tests.yml`, triggered via a PR to `main` or
      `gh workflow run`, passes: the lint job and all four test-matrix
      legs.
- [ ] `publish_to_pypi.yml` and `publish_to_test_pypi.yml` are
      byte-identical to their template counterparts (modulo the
      pre-existing name substitutions).

---

## Phase 14 — Final verification

### 14.1 Verification commands

Run, in order, from the repo root:

```bash
python -m pip install -e ".[dev,docs]"
scripts/run-all-checks.sh                # full default suite
```

The script default is "all-on" (per the script's `SCOPE_SPECIFIED=false`
branch). The expected end-state is `EXIT_CODE=0`. If any check fails:

1. Re-run with `-s` (sequential) to get clear output for the failing
   check.
2. Diagnose using logic, stack traces, and targeted logging
   (`python_testing.mdc` §10). Do NOT guess at causes; if stuck
   in a fix loop, revert and re-approach from first principles, or ask
   for help.
3. Address the failing check; do not relax thresholds; do not skip
   tests.
4. Re-run the failing check alone via `--<check-name>`.
5. Re-run the full script.

### 14.2 Final exit criteria

- [ ] `scripts/run-all-checks.sh` exits 0.
- [ ] `python -m pip install build && python -m build --sdist --wheel`
      succeeds, then `pip install dist/rms_pds4indextools-*.whl`
      followed by `pds4_create_xml_index --version` works from a fresh
      venv.
- [ ] `python -m pytest` (which applies the configured
      `--cov=src --cov-branch` addopts) exits 0 and
      `coverage report --fail-under=90` reports overall coverage ≥ 90%
      line AND branch, measured over the ENTIRE test suite
      (`python_testing.mdc` §7).
- [ ] Total `# pragma: no cover` count in `src/` is ≤ 5; each occurrence
      has a one-sentence rationale comment immediately preceding it.
- [ ] `python -m pyroma --min=9 .` passes (manual invocation; the
      checker script runs pyroma without `--min`).
- [ ] `git status` clean.
- [ ] Every spec R-ID has at least one corresponding T-ID in the test
      tree (verified by `scripts/verify_test_coverage.py` — Appendix
      A.13). The script additionally confirms that every R-ID appears
      inside a test function body in `tests/unit/` or
      `tests/integration/` (i.e., in files under those directories;
      the script distinguishes directories, not syntactic context).
      The `R-CI-*`,
      `R-PKG-*`, `R-DOC-*`, `R-DEP-*`, and `R-TST-*` families are
      exempt (satisfied by infrastructure/docs/policy, not test bodies;
      see A.13's `_EXEMPT_PREFIXES`).
- [ ] Every public function/class/method docstring matches the
      associated implementation (`python.mdc` §6: docstrings
      updated when code changes).
- [ ] No stub functions, no `TODO`/`FIXME`/`XXX` markers in source or
      tests (`grep -RInE '\b(TODO|FIXME|XXX)\b' src/ tests/ docs/ scripts/`
      empty; word-boundary anchors avoid false hits in URLs or hex
      constants).
- [ ] `git grep -nP '^[^#]*\bprint\s*\(' src/pds4indextools/` returns no
      matches (library-hygiene grep tripwire, codebase-analysis §2).
- [ ] `git grep -nP '^[^#]*\bsys\.exit\s*\(' src/pds4indextools/`
      returns exactly two matches: `cli_entrypoint()` in
      `cli/_dispatch.py` AND the `if __name__ == '__main__'` block
      in `__main__.py`. Any other match is a regression.
- [ ] `legacy/` carries no top-level README, docs, or PyPI metadata that
      contradicts the new `src/pds4indextools/` package; if any legacy
      doc remains in `legacy/`, it is prefixed with a "Historical — see
      `docs/` for the current documentation" banner
      (`documentation.mdc` §6).
- [ ] `pytest -W error tests/` (no other warnings filter) is run once
      manually as the implementer finalizes; every currently-ignored
      DeprecationWarning in `filterwarnings` is paired with a TODO
      comment and a tracking-issue URL (critique skill §16).

---

# Critical files (paths the implementer touches)

Template-owned files not listed here (`.github/`, `.gitignore`,
`.readthedocs.yaml`, `codecov.yml`, `requirements.txt`, `LICENSE`,
`docs/Makefile`, `docs/make.bat`, `docs/contributing.rst`,
`docs/code_of_conduct.md`, `scripts/read-docs.sh`) are NOT touched
(§0.0).

```
CONTRIBUTING.md                                       Phase 12, App C.13 (template + delta)
README.md                                             Phase 12, App C.12 (template + delta)
docs/architecture.rst                                 Phase 12, App C.8
docs/cli.rst                                          Phase 12, App C.5
docs/conf.py                                          Phase 12, App C.1 (template + delta)
docs/config.rst                                       Phase 12, App C.6
docs/index.rst                                        Phase 12, App C.2 (template + delta)
docs/installation.rst                                 Phase 12, App C.3
docs/module.rst                                       Phase 12, App C.9 (template + delta)
docs/quickstart.rst                                   Phase 12, App C.4
docs/usage_examples.rst                               Phase 12, App C.10a
pyproject.toml                                        Phase 0,  App A.1 (template + delta)
scripts/run-all-checks.sh                             Phase 0 (ENABLE_VULTURE=true toggle only)
scripts/generate_expected_outputs.py                  Phase 0 (source), Phase 11 (run), App I.1
scripts/verify_public_api.py                          Phase 0,  App F
scripts/verify_test_coverage.py                       Phase 0,  App A.13
src/pds4indextools/__init__.py                        Phase 10
src/pds4indextools/__main__.py                        Phase 10
src/pds4indextools/_io.py                             Phase 0 (stub) / Phase 7.5 (impl)
src/pds4indextools/_logging.py                        Phase 2
src/pds4indextools/cli/__init__.py                    Phase 10
src/pds4indextools/cli/_args.py                       Phase 10
src/pds4indextools/cli/_dispatch.py                   Phase 10
src/pds4indextools/cli/_parser.py                     Phase 10
src/pds4indextools/cli/_paths.py                      Phase 10
src/pds4indextools/cli/_runners.py                    Phase 10
src/pds4indextools/config.py                          Phase 3
src/pds4indextools/csv_writer.py                      Phase 8
src/pds4indextools/errors.py                          Phase 1
src/pds4indextools/label_writer.py                    Phase 9
src/pds4indextools/py.typed                           Phase 0
src/pds4indextools/schema_types.py                    Phase 6
src/pds4indextools/scraper/__init__.py                Phase 7
src/pds4indextools/scraper/_parse.py                  Phase 7
src/pds4indextools/scraper/_value.py                  Phase 7
src/pds4indextools/scraper/_nil.py                    Phase 7
src/pds4indextools/scraper/_lid.py                    Phase 7
src/pds4indextools/scraper/_orchestrator.py           Phase 7
src/pds4indextools/templates/default_config.yaml      Phase 0,  App A.4
src/pds4indextools/templates/index_label_template.xml Phase 0,  App A.5
src/pds4indextools/xpath_norm.py                      Phase 5
tests/__init__.py                                     Phase 0
tests/conftest.py                                     Phase 0,  App A.6
tests/data/                                           Phase 0/11, App A.7, App B
tests/integration/__init__.py                         Phase 0
tests/integration/test_copy_default_config.py         Phase 11
tests/integration/test_determinism.py                 Phase 11
tests/integration/test_generate_index_file.py         Phase 11
tests/integration/test_generate_xpath_list.py         Phase 11
tests/integration/test_subprocess_smoke.py            Phase 11
tests/unit/__init__.py                                Phase 0
tests/unit/test_atomic_file_writes.py                 Phase 7.5
tests/unit/test_cli_parsing_dispatch_and_exit_codes.py Phase 10
tests/unit/test_config_loading_and_merging.py         Phase 3
tests/unit/test_csv_writing_quoting_and_sorting.py    Phase 8
tests/unit/test_documentation_conventions.py          Phase 12
tests/unit/test_errors_hierarchy_and_formatting.py    Phase 1
tests/unit/test_fixture_integrity.py                  Phase 0
tests/unit/test_label_scraping_and_validation.py      Phase 7
tests/unit/test_label_template_substitution.py        Phase 9
tests/unit/test_logging_configuration_and_progress.py Phase 2
tests/unit/test_package_layout_and_metadata.py        Phase 0
tests/unit/test_schema_cache_and_type_resolution.py   Phase 6
tests/unit/test_xpath_canonicalization_and_renumbering.py Phase 5
```

---

# Reusable utilities to leverage from the existing repo

| Utility | Location | Use it for |
|---|---|---|
| `scripts/run-all-checks.sh` | repo root | every per-phase check + final |
| `legacy/pds4indextools/pds4_create_xml_index.py::renumber_xpaths` lines 427-512 | legacy reference | algorithm spec for `xpath_norm.renumber_xpaths` |
| `legacy/pds4indextools/pds4_create_xml_index.py::find_base_attribute` lines 921-1006 | legacy reference | algorithm spec for `schema_types.SchemaTypeResolver.resolve` |
| `legacy/pds4indextools/default_config.yaml` | legacy reference | byte-equivalent values for `templates/default_config.yaml` |
| `legacy/test_files/labels/*.xml` | legacy reference | inspiration for fixture XML content; **do not copy verbatim** — fixtures are HAND-CURATED per R-TST-040 |

# End-to-end verification scenario

After Phase 14, an unattended agent must be able to do this from a clean
checkout:

```bash
git clean -fdx -e venv
python -m venv venv
source venv/bin/activate    # POSIX
python -m pip install --upgrade pip
python -m pip install -e ".[dev,docs]"
scripts/run-all-checks.sh
pds4_create_xml_index --version
pds4_create_xml_index generate_index_file --bundle-root tests/data/bundles/simple_pds_only --config-file tests/data/configs/simple.yaml --output-file /tmp/out.csv '**/*.lblx'
diff /tmp/out.csv tests/data/expected/simple_pds_only/index.csv
diff <(grep -v '<creation_date_time>' /tmp/out.lblx) \
     <(grep -v '<creation_date_time>' tests/data/expected/simple_pds_only/index.lblx)
```

The CSV diff exits 0 by R-IDX-001 byte-identical determinism; the lblx
diff masks the single `creation_date_time` line (a live CLI run cannot
freeze the CSV mtime that `$FILE_ZULU$` reads) and everything else is
byte-identical.

---

# Appendices

The appendices below contain every byte of file content the implementer
must reproduce. **Each appendix is the source of truth for that file.**
When the plan text above and an appendix conflict, the appendix wins.

The appendices are deliberately bulky; the plan body above stays
scan-readable. The appendices are listed under their A.*/B.*/C.*/D.* IDs.

## Appendix A — Build, configuration, packaging

### A.1 `pyproject.toml`

The complete resulting file. It is the committed template-derived file
plus ONLY the §0.2 delta; sections not mentioned in §0.2 are
byte-identical to the template.

```toml
[build-system]
requires = ["setuptools", "setuptools_scm[toml]"]
build-backend = "setuptools.build_meta"

[project]
name = "rms-pds4indextools"
dynamic = ["version"]
description = "Generate tabular index files and PDS4 labels by scraping PDS4 XML label trees"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
  "lxml",
  "pyyaml",
  "pydantic>=2",
  "rms-pdstemplate>=2.4",
  "requests",
  "requests-file",
  "platformdirs",
  "tqdm",
]
license = {text = "Apache-2.0"}
authors = [
  {name = "Robert S. French", email = "rfrench@seti.org"}
]
maintainers = [
  {name = "Robert S. French", email = "rfrench@seti.org"}
]
keywords = ["pds4", "planetary data system", "index", "metadata", "xml"]
classifiers = [
  "Development Status :: 5 - Production/Stable",
  "Natural Language :: English",
  "Topic :: Scientific/Engineering",
  "Topic :: Scientific/Engineering :: Astronomy",
  "Topic :: Software Development :: Libraries :: Python Modules",
  "Topic :: Utilities",
  "License :: OSI Approved :: Apache Software License",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Operating System :: MacOS :: MacOS X",
  "Operating System :: POSIX :: Linux",
  "Operating System :: Microsoft :: Windows"
]

[project.urls]
Homepage = "https://github.com/SETI/rms-pds4indextools"
Documentation = "https://rms-pds4indextools.readthedocs.io/en/latest"
Repository = "https://github.com/SETI/rms-pds4indextools"
Source = "https://github.com/SETI/rms-pds4indextools"
Issues = "https://github.com/SETI/rms-pds4indextools/issues"

[tool.pytest.ini_options]
pythonpath = [
  "src"
]
testpaths = ["tests"]
addopts = [
  "-n", "auto",
  "--cov=src",
  "--cov-branch",
  "--strict-markers",
  "--strict-config",
  "--timeout=60",
  "--timeout-method=thread",
]
markers = [
  "live: marks tests requiring live network beyond XSD lookup (deselect with -m \"not live\")",
  "integration: marks integration tests (deselect with -m \"not integration\")",
]
# Warnings policy lives entirely in `filterwarnings`. Do NOT add
# `-W error` to addopts — it preempts `filterwarnings` and turns
# pkg_resources/setuptools_scm DeprecationWarnings into collection
# errors before the ignores fire (critique skill §22).
filterwarnings = [
  "error",
  # Each ignore MUST pair with a TODO comment + tracking issue URL when
  # the upstream fix is known (critique skill §16).
  "ignore::DeprecationWarning:_pytest.*",           # pytest internal noise
  "ignore::DeprecationWarning:pkg_resources.*",     # setuptools_scm/pyroma
  "ignore::DeprecationWarning:pdstemplate.*",       # TODO: track upstream pdstemplate
  # google.api_core emits this at import time ONLY on Python 3.10 (EOL notice),
  # reached transitively via pdstemplate -> rms-filecache -> google-cloud-storage;
  # not actionable here and gone once 3.10 is dropped from the matrix.
  "ignore:You are using a Python version:FutureWarning",
  "ignore::PendingDeprecationWarning",              # broad floor; promote specific ones as discovered
]

[tool.setuptools]
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"pds4indextools" = ["py.typed", "templates/*.yaml", "templates/*.xml"]

[tool.setuptools_scm]
local_scheme = "no-local-version"
write_to = "src/pds4indextools/_version.py"

[project.optional-dependencies]
dev = [
  "rms-pds4indextools",
  "coverage",
  "freezegun",
  "lxml-stubs",
  "mypy",
  "pymarkdownlnt",
  "pytest",
  "pytest-cov",
  "pytest-timeout",
  "pytest-xdist",
  "responses",
  "ruff",
  "types-PyYAML",
  "types-requests",
  # "bandit[toml]",
  "pyroma",
  "vulture",
  "rms-pds4indextools[docs]",
]
docs = [
  "myst-parser",
  "sphinx",
  "sphinxcontrib-mermaid",
  "sphinx-rtd-theme",
]

[project.scripts]
pds4_create_xml_index = "pds4indextools.cli:cli_entrypoint"

# Tool configuration

[tool.coverage.run]
branch = true
parallel = true
source = ["pds4indextools"]
omit = ["tests/*", "*/_version.py"]

[tool.coverage.report]
exclude_lines = [
  "pragma: no cover",
  "def __repr__",
  "raise NotImplementedError",
]
fail_under = 90

[tool.mypy]
strict = true
disallow_subclassing_any = false

[[tool.mypy.overrides]]
module = "pds4indextools._version"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["pdstemplate.*", "requests_file.*", "tqdm.*"]
ignore_missing_imports = true

[tool.ruff]
target-version = "py310"
line-length = 100
exclude = [
#  "TODO"
]

[tool.ruff.format]
quote-style = "single"

[tool.ruff.lint]
# Explicit rule set (recommended for library projects). Categories:
# E, W = pycodestyle errors/warnings; F = Pyflakes; I = isort; UP = pyupgrade;
# B = bugbear; SIM = simplify; C4 = comprehensions; A = builtins (no shadowing);
# N = pep8-naming; PT = pytest-style; RUF = Ruff-specific (e.g. unused noqa).
select = ["E", "F", "W", "I", "UP", "B", "SIM", "C4", "A", "N", "PT", "RUF"]
# PT011 - pytest.raises is too broad.
# SIM105 - Use contextlib.suppress for suppressions.
# SIM108 - Use ternary operator for simple if/else.
extend-ignore = ["PT011", "SIM105", "SIM108"]

[tool.ruff.lint.per-file-ignores]
#"TODO" = ["TODO"]

[tool.pymarkdown.plugins.md013]
# Line length (disable so README/CONTRIBUTING can use longer lines).
enabled = false

[tool.pymarkdown.plugins.md033]
# Inline HTML (e.g. <br>) allowed in Markdown.
enabled = false

# Uncomment when enabling bandit in [project.optional-dependencies].dev.
# [tool.bandit]
# exclude_dirs = ["tests", "venv", ".venv"]
# targets = ["src"]

[tool.vulture]
paths = ["src"]
exclude = ["tests/"]
min_confidence = 70
```

### A.2 `requirements.txt` — template file, UNCHANGED

The committed template `requirements.txt` (`-e .` plus its explanatory
comment) is kept as-is.

### A.3 `MANIFEST.in` — intentionally ABSENT

The template has no `MANIFEST.in` and none is created. setuptools-scm's
git file-finder governs sdist contents, exactly as in every other RMS
template repo.

### A.4 `src/pds4indextools/templates/default_config.yaml`

```yaml
# Default configuration for pds4_create_xml_index.
# Users override these via one or more --config-file arguments; user
# settings are deep-merged onto these defaults (scalars/lists replaced,
# dicts merged).

nillable:
  pds:ASCII_Date_YMD:
    inapplicable: '0001-01-01'
    missing:      '0002-01-01'
    unknown:      '0003-01-01'
    anticipated:  '0004-01-01'
  pds:ASCII_Date_Time_YMD:
    inapplicable: '0001-01-01T12:00'
    missing:      '0002-01-01T12:00'
    unknown:      '0003-01-01T12:00'
    anticipated:  '0004-01-01T12:00'
  pds:ASCII_Date_Time_YMD_UTC:
    inapplicable: '0001-01-01T12:00Z'
    missing:      '0002-01-01T12:00Z'
    unknown:      '0003-01-01T12:00Z'
    anticipated:  '0004-01-01T12:00Z'
  pds:ASCII_Integer:
    inapplicable: -999
    missing:      -998
    unknown:      -997
    anticipated:  -996
  pds:ASCII_Real:
    inapplicable: -999.0
    missing:      -998.0
    unknown:      -997.0
    anticipated:  -996.0
  pds:ASCII_Short_String_Collapsed:
    inapplicable: inapplicable
    missing:      missing
    unknown:      unknown
    anticipated:  anticipated

output:
  fixed_width: false
  sort_by: []
  line_ending: LF

xsd_cache_dir: null
```

### A.5 `src/pds4indextools/templates/index_label_template.xml`

Use the content of
`legacy/pds4indextools/index_label_template_pds.xml` verbatim with these
two changes:

1. Add a new substituted MD5/timestamp block. Replace the trailing
   `<File_Area_*>` section with the form:

```xml
$IF(Table_Character)
        <Table_Character>
            <name>$BASENAME(index_file_name)$</name>
            <local_identifier>index</local_identifier>
            <offset unit="byte">$object_length_h$</offset>
            <records>$records$</records>
            <description>Index of metadata scraped from PDS4 labels.</description>
            <record_character>
                <fields>$fields$</fields>
                <groups>0</groups>
                <record_length unit="byte">$maximum_record_length$</record_length>
            $FOR(field, k=Field_Content)
                <Field_Character>
                    <name>$field['name']$</name>
                    <field_number>$field['field_number']$</field_number>
                    <field_location unit="byte">$field['field_location']$</field_location>
                    <data_type>$field['data_type']$</data_type>
                    <field_length unit="byte">$field['field_length']$</field_length>
                    <description>XPath: $field['xpath']$</description>
                </Field_Character>
            $END_FOR
            </record_character>
        </Table_Character>
$END_IF
$IF(Table_Delimited)
        <Table_Delimited>
            <name>$BASENAME(index_file_name)$</name>
            <local_identifier>index</local_identifier>
            <offset unit="byte">$object_length_h$</offset>
            <parsing_standard_id>PDS DSV 1</parsing_standard_id>
            <records>$records$</records>
            <record_delimiter>$RECORD_DELIMITER$</record_delimiter>
            <field_delimiter>Comma</field_delimiter>
            <Record_Delimited>
                <fields>$fields$</fields>
                <groups>0</groups>
                <maximum_record_length unit="byte">$maximum_record_length$</maximum_record_length>
            $FOR(field, k=Field_Content)
                <Field_Delimited>
                    <name>$field['name']$</name>
                    <field_number>$field['field_number']$</field_number>
                    <data_type>$field['data_type']$</data_type>
                    <maximum_field_length unit="byte">$field['maximum_field_length']$</maximum_field_length>
                    <description>XPath: $field['xpath']$</description>
                </Field_Delimited>
            $END_FOR
            </Record_Delimited>
        </Table_Delimited>
$END_IF
```

2. The `<File_Area_*>` wrapper around the Table is generated by the
   legacy template; preserve it. The implementer copies the rest of
   `legacy/pds4indextools/index_label_template_pds.xml` lines 1-223 and
   replaces the two Table sections per item 1 above PLUS one further
   edit: every occurrence of `$DATETIME(calculated_creation_date_time)$`
   (three in the legacy file, at its lines 135/147/156) is replaced
   with `$FILE_ZULU(index_file_name)$` — the tool defines no
   `calculated_creation_date_time` variable, and an undefined name is a
   render error under `raise_exceptions=True`. `md5_checksum` keeps
   `$FILE_MD5(index_file_name)$`. After these edits,
   `$FILE_ZULU(index_file_name)$` is the template's ONLY
   mtime-dependent macro (the Phase 9 exit check relies on this).
3. The `$RECORD_DELIMITER$` variable is supplied by the tool:
   `'Line-Feed'` when `output.line_ending == 'LF'`,
   `'Carriage-Return Line-Feed'` when `'CRLF'` (R-LBL-060). It is added
   to the substitution dict by `label_writer.build_substitution_dict`
   AFTER `label_contents.model_dump()` (overlay-last). It is NOT
   listed in the spec's R-LBL-012 reserved-keys set, so if a user
   accidentally sets `label_contents.RECORD_DELIMITER`, the tool's
   value silently wins. The spec's R-LBL-012 reserved set remains the
   exact 11 names; the plan body Phase 3 and Phase 9 stay aligned with
   the spec.

### A.6 `tests/conftest.py`

```python
"""Shared pytest fixtures for the pds4indextools test suite.

The fixtures here are intentionally minimal. Anything specific to a
single test file should live in that file or in a sibling conftest.
"""

import hashlib
import os
import socket
import sys
from collections.abc import Iterator
from pathlib import Path

import platformdirs
import pytest


HERE = Path(__file__).resolve().parent
DATA_ROOT = HERE / 'data'


@pytest.fixture(scope='session')
def data_root() -> Path:
    """Absolute path to ``tests/data``."""
    return DATA_ROOT


@pytest.fixture(scope='session')
def bundle_root_factory(data_root: Path) -> 'BundleRootFactory':
    """Factory returning the absolute path to ``tests/data/bundles/<name>``."""
    return BundleRootFactory(data_root / 'bundles')


class BundleRootFactory:
    """Helper that resolves a bundle name to an absolute filesystem path."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def __call__(self, name: str) -> Path:
        path = self._root / name
        if not path.is_dir():
            raise FileNotFoundError(f'unknown test bundle: {name} ({path})')
        return path


@pytest.fixture(scope='session')
def xsd_cache_session(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session-scoped XSD cache directory shared across integration tests.

    pytest-xdist gives each worker its own ``tmp_path_factory`` base path
    but the basetemp is a stable per-session directory; we anchor our
    cache one level above so all workers in the same session share the
    download cache (R-TST-021).

    NOTE: ``SchemaCache.fetch`` uses ``write-temp-then-os.replace`` so
    concurrent xdist workers cannot interleave or leave partial files
    (critique skill §6).
    """
    base = tmp_path_factory.getbasetemp().parent / 'xsd_cache_session'
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def isolated_xsd_cache(tmp_path: Path) -> Path:
    """Per-test fresh XSD cache directory (unit tests only)."""
    cache = tmp_path / 'xsd_cache'
    cache.mkdir()
    return cache


# Every xsi:schemaLocation URL that appears in a fixture bundle, mapped
# to the seed XSD (in tests/data/xsd_cache_seed/) that serves it. The
# seeded cache makes schema resolution work with ZERO network in every
# non-live test (R-TST-030 as amended).
_FIXTURE_SCHEMA_URLS: dict[str, str] = {
    'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd': 'pds_v1_basic.xsd',
    'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1K00.xsd': 'pds_v1_basic.xsd',
    'https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1L00_2000.xsd': 'geom_v1.xsd',
    'https://pds.nasa.gov/pds4/rings/v1/PDS4_RINGS_1L00_1G00.xsd': 'rings_v1.xsd',
}


@pytest.fixture(scope='session')
def seeded_xsd_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session cache dir pre-seeded with every fixture schema URL.

    Files are stored under ``sha256(url).xsd`` — exactly the cache-hit
    key ``SchemaCache.fetch`` uses — so no test that requests this
    cache ever touches the network.
    """
    cache = tmp_path_factory.mktemp('seeded_xsd_cache')
    for url, seed in _FIXTURE_SCHEMA_URLS.items():
        digest = hashlib.sha256(url.encode('utf-8')).hexdigest()
        (cache / f'{digest}.xsd').write_bytes(
            (DATA_ROOT / 'xsd_cache_seed' / seed).read_bytes()
        )
    return cache


@pytest.fixture
def seeded_cache_overlay(seeded_xsd_cache: Path, tmp_path: Path) -> Path:
    """Config-overlay YAML pointing ``xsd_cache_dir`` at the seeded cache.

    Tests append this path as the LAST ``--config-file`` (or
    ``config_files`` entry) so the run resolves schemas from the seeded
    cache with zero network.
    """
    overlay = tmp_path / 'xsd_cache_overlay.yaml'
    overlay.write_text(f'xsd_cache_dir: {seeded_xsd_cache}\n', encoding='utf-8')
    return overlay


@pytest.fixture
def chdir_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Chdir into ``tmp_path`` for the duration of the test."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _has_network(host: str = 'pds.nasa.gov', port: int = 443, timeout: float = 1.0) -> bool:
    """Return True iff the given host:port accepts a TCP connection.

    Overridable via the ``PDS4INDEX_TEST_HOST`` env var; timeout is
    bounded to 1s to keep the cost of a session-scoped call small
    (critique skill §15).
    """
    host = os.environ.get('PDS4INDEX_TEST_HOST', host)
    try:
        socket.create_connection((host, port), timeout=timeout).close()
    except OSError:
        return False
    return True


@pytest.fixture(scope='session')
def has_network() -> bool:
    """``True`` iff the configured test host is reachable."""
    return _has_network()


class _NonTtyStream:
    """Delegating wrapper whose ``isatty()`` is always ``False``.

    Setting ``isatty`` directly on a real ``TextIOWrapper`` raises
    ``AttributeError`` (C-level slots), so we swap the whole stream for
    a wrapper instead.
    """

    def __init__(self, wrapped: object) -> None:
        self._wrapped = wrapped

    def __getattr__(self, name: str) -> object:
        return getattr(self._wrapped, name)

    def isatty(self) -> bool:
        return False


@pytest.fixture
def deterministic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Erase non-deterministic environment knobs.

    Forces ``TZ=UTC``, ``PYTHONHASHSEED=0``, clears ``COLUMNS``/``LINES``,
    forces stderr to be considered non-TTY so the progress bar is off
    (R-LOG-021).
    """
    monkeypatch.setenv('TZ', 'UTC')
    monkeypatch.setenv('PYTHONHASHSEED', '0')
    monkeypatch.delenv('COLUMNS', raising=False)
    monkeypatch.delenv('LINES', raising=False)
    monkeypatch.setattr(sys, 'stderr', _NonTtyStream(sys.stderr))


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Auto-mark integration tests under ``tests/integration/``."""
    integration_root = (HERE / 'integration').resolve()
    for item in items:
        if integration_root in item.path.resolve().parents:
            item.add_marker(pytest.mark.integration)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the opt-in flag for live-network tests."""
    parser.addoption(
        '--run-live',
        action='store_true',
        default=False,
        help='Run tests marked @pytest.mark.live (network beyond XSD lookup).',
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip @pytest.mark.live tests unless opted in."""
    if 'live' in item.keywords and not item.config.getoption('--run-live'):
        pytest.skip('live test (use --run-live to enable)')


@pytest.fixture
def guard_user_platform_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Force ``platformdirs.user_cache_dir`` to a per-test scratch path.

    ``schema_types`` is REQUIRED to use ``import platformdirs`` and call
    ``platformdirs.user_cache_dir(...)`` through the module attribute
    (Phase 6), so patching that one attribute is sufficient — the name
    is looked up on the ``platformdirs`` module at call time (critique
    skill §7). Tests that touch the schema cache request this fixture
    explicitly. Returns the scratch path so tests may inspect it.
    """
    scratch = tmp_path / 'platform_cache_guard'
    scratch.mkdir()

    def fake_user_cache_dir(app: str) -> str:
        return str(scratch / app)

    monkeypatch.setattr(platformdirs, 'user_cache_dir', fake_user_cache_dir)
    return scratch


@pytest.fixture
def frozen_time() -> Iterator[None]:
    """Freeze wall clock to ``2026-05-14T00:00:00Z`` for byte-identical output.

    Note: freezegun does NOT freeze OS file mtime (``os.stat(...).st_mtime``).
    Phase 9's `$FILE_ZULU(index_file_name)$` macro reads file mtime, so
    tests that compare lblx bytes also need ``frozen_csv_mtime`` (below)
    or apply ``os.utime`` after writing the CSV. See Appendix I for the
    binding generation procedure.
    """
    from freezegun import freeze_time
    with freeze_time('2026-05-14T00:00:00Z'):
        yield


# POSIX seconds for 2026-05-14T00:00:00Z (UTC). MUST equal the
# frozen_time date; Appendix I's FROZEN_MTIME is the same value.
_FROZEN_MTIME_EPOCH = 1778716800


@pytest.fixture
def frozen_csv_mtime() -> int:
    """Provide the canonical frozen CSV mtime (POSIX seconds).

    Tests that produce byte-identical lblx outputs request this fixture
    in addition to ``frozen_time`` and pass
    ``csv_post_write_hook=lambda p: os.utime(p, (frozen_csv_mtime, frozen_csv_mtime))``
    to ``run_generate_index_file`` (or call ``os.utime`` on the CSV
    directly before label generation). This mirrors exactly what the
    golden-bytes generator does (Appendix I).
    """
    return _FROZEN_MTIME_EPOCH
```

Fixture dependency notes (critique skill §14):

- `guard_user_platform_cache` is NOT autouse. Schema/scraper/CLI tests
  request it explicitly. Test files that do not exercise platformdirs
  do not pay the cost.
- `tmp_path` is shared between any fixture that takes it; `guard_user_platform_cache`
  creates `tmp_path/'platform_cache_guard'` inside the same `tmp_path`
  that the test sees, so tests that need a pristine tmp_path use
  `tmp_path_factory.mktemp('clean')` instead and chdir there.
- `frozen_time` is used by every Phase 9 unit test that invokes
  PdsTemplate AND by every Phase 11 byte-identical integration test.

### A.7 `tests/data/` tree

11 bundles; NO copy bundles, NO empty `non_monotone` directory, and
NO `large_synthetic` (owner decisions
#8 and #9). Feature variants (fixed-width, CRLF, multi-config,
mapping-full-features) exist only as configs plus
`expected/<feature>/` golden directories; their tests point
`--bundle-root` at `simple_pds_only` or `multi_namespace`.

```
tests/data/
├── bundles/
│   ├── simple_pds_only/
│   │   └── row1.lblx
│   ├── multi_namespace/
│   │   ├── a.lblx
│   │   ├── b.lblx
│   │   └── c.lblx
│   ├── nilled/
│   │   └── nilled.lblx
│   ├── nilled_bad/
│   │   └── nilled.lblx
│   ├── repeated_tags/
│   │   └── repeated.lblx
│   ├── multi_lid/
│   │   ├── a.lblx
│   │   ├── b.lblx
│   │   └── c.lblx
│   ├── bom/
│   │   └── bom.lblx
│   ├── non_ascii_value/
│   │   └── nonascii.lblx
│   ├── quote_in_value/
│   │   └── quoted.lblx
│   ├── version_mismatch/
│   │   ├── a.lblx
│   │   └── b.lblx
│   └── no_schema_location/
│       └── no_schema.lblx
├── configs/
│   ├── minimal.yaml
│   ├── simple.yaml
│   ├── multi_namespace.yaml
│   ├── repeated_tags.yaml
│   ├── xpath_not_in_label.yaml
│   ├── columns_only_lid.yaml
│   ├── fixed_width.yaml
│   ├── crlf.yaml
│   ├── multi_config_a.yaml
│   ├── multi_config_b.yaml
│   ├── multi_config_c.yaml
│   ├── mapping_full_features.yaml
│   ├── nilled.yaml
│   ├── quote_in_value_var.yaml
│   ├── quote_in_value_fixed.yaml
│   ├── version_mismatch.yaml
│   ├── test_config_extras.yaml
│   ├── test_config_invalid_top.yaml
│   ├── test_config_invalid_output.yaml
│   ├── test_config_invalid_nillable.yaml
│   ├── test_config_relative_path.yaml
│   ├── test_config_reserved_key.yaml
│   ├── test_config_partial_a.yaml
│   ├── test_config_partial_b.yaml
│   └── test_config_partial_c.yaml
├── xsd_cache_seed/
│   ├── pds_v1_basic.xsd
│   ├── pds_v1_units.xsd
│   ├── geom_v1.xsd
│   ├── rings_v1.xsd
│   └── README.md
└── expected/
    ├── simple_pds_only/
    │   ├── index.csv
    │   └── index.lblx
    ├── multi_namespace/
    │   ├── index.csv
    │   └── index.lblx
    ├── nilled/
    │   ├── index.csv
    │   └── index.lblx
    ├── repeated_tags/
    │   ├── index.csv
    │   └── index.lblx
    ├── quote_in_value/
    │   ├── index.csv
    │   └── index.lblx
    ├── fixed_width/
    │   ├── index.csv
    │   └── index.lblx
    ├── crlf/
    │   ├── index.csv
    │   └── index.lblx
    ├── multi_config/
    │   ├── index.csv
    │   └── index.lblx
    ├── mapping_full_features/
    │   ├── index.csv
    │   └── index.lblx
    └── xpath_lists/
        ├── simple_pds_only.yaml
        └── multi_namespace.yaml
```

(There is no `mapping_files/` directory: column definitions live in
the config YAMLs — owner decision #10. Column-validation error cases
are exercised with inline YAML written to `tmp_path` in
`test_config_loading_and_merging.py`, not committed fixtures.)

`expected/fixed_width/`, `expected/crlf/`, and `expected/multi_config/`
are generated from the `simple_pds_only` bundle under their feature
configs; `expected/mapping_full_features/` is generated from
`multi_namespace` under `mapping_full_features.yaml` (see Appendix I).

Bundles whose runs ABORT (`nilled_bad`, `non_monotone`, `multi_lid`,
`bom`, `non_ascii_value`, `version_mismatch`, `no_schema_location`)
have NO `expected/<bundle>/` directory — the integration test asserts
on the raised exception and on the absence of any output file.

For bundles whose runs always fail (`bom`, `non_ascii_value`,
`nilled_bad`, `non_monotone`, `multi_lid`, `version_mismatch`,
`no_schema_location`), no `expected/<bundle>/` directory is created — the
test asserts on the raised exception and on the absence of any output
file.

### A.8 `.readthedocs.yaml` — template file, UNCHANGED

The committed template `.readthedocs.yaml` is kept as-is (it already
installs the package with the `docs` extra and builds `docs/conf.py`).

### A.9 `.gitignore` — template file, UNCHANGED

The committed template `.gitignore` is kept as-is; it already covers
`**/_version.py`, coverage artifacts, `docs/_build/`, tool caches, and
virtual environments.

### A.10 Small YAML config snippets used by `test_config_loading_and_merging.py`

`tests/data/configs/minimal.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:test:test_index
  product_class: Product_Ancillary
```

`tests/data/configs/test_config_extras.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:test:test_index
  product_class: Product_Ancillary
  custom_var: 'hello world'
```

`tests/data/configs/test_config_invalid_top.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:test:test_index
  product_class: Product_Ancillary
unrecognized_top_level_key: 1
```

`tests/data/configs/test_config_invalid_output.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:test:test_index
  product_class: Product_Ancillary
output:
  fixed_width: false
  bogus: 1
```

`tests/data/configs/test_config_invalid_nillable.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:test:test_index
  product_class: Product_Ancillary
nillable:
  pds:ASCII_Integer:
    inapplicable: -999
    missing:      -998
    unknown:      -997
    anticipated:  -996
    frobnicate:   42
```

`tests/data/configs/test_config_relative_path.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:test:test_index
  product_class: Product_Ancillary
xsd_cache_dir: ./relative/cache
```

`tests/data/configs/test_config_reserved_key.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:test:test_index
  product_class: Product_Ancillary
  index_file_name: /tmp/should_be_rejected.csv
```

`tests/data/configs/test_config_partial_a.yaml`:

```yaml
output:
  fixed_width: false
```

`tests/data/configs/test_config_partial_b.yaml` (LID differs from
`minimal.yaml` so the two files are not byte-identical):

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_bundle:partial:test_index
  product_class: Product_Ancillary
```

`tests/data/configs/test_config_partial_c.yaml`:

```yaml
nillable:
  pds:ASCII_NonNegative_Integer:
    inapplicable: 0
    missing: 0
    unknown: 0
    anticipated: 0
```

`tests/data/configs/simple.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_simple:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Simple index file
columns:
  - auto: lid
    name: LID
  - auto: filename
    name: FILE_NAME
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: TITLE
```

`tests/data/configs/multi_namespace.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_multi_ns:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Multi-namespace index file
columns:
  - auto: lid
    name: LID
  - auto: filename
    name: FILE_NAME
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: TITLE
  - xpath: pds:Product_Observational<1>/pds:Observation_Area<1>/geom:Geometry<1>/geom:method<1>
    name: GEOM_METHOD
  - xpath: pds:Product_Observational<1>/pds:Observation_Area<1>/rings:Ring<1>/rings:ring_name<1>
    name: RING_NAME
```

`tests/data/configs/repeated_tags.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_rep:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Repeated-tags index file
columns:
  - auto: lid
    name: LID
  - xpath: pds:Product_Observational<1>/pds:Observation_Area<1>/pds:Observing_System<1>/pds:name<1>
    name: OS1
  - xpath: pds:Product_Observational<1>/pds:Observation_Area<1>/pds:Observing_System<2>/pds:name<1>
    name: OS2
  - xpath: pds:Product_Observational<1>/pds:Observation_Area<1>/pds:Observing_System<3>/pds:name<1>
    name: OS3
```

`tests/data/configs/xpath_not_in_label.yaml` (overlay — replaces the
chain's `columns` wholesale per R-CFG-050):

```yaml
columns:
  - auto: lid
    name: LID
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:nonexistent<1>
    name: GONE
```

`tests/data/configs/columns_only_lid.yaml` (overlay):

```yaml
columns:
  - auto: lid
    name: LID
```

`tests/data/configs/fixed_width.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_simple:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Fixed-width index file
output:
  fixed_width: true
columns:
  - auto: lid
    name: LID
  - auto: filename
    name: FILE_NAME
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: TITLE
```

`tests/data/configs/crlf.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_simple:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: CRLF index file
output:
  line_ending: CRLF
columns:
  - auto: lid
    name: LID
  - auto: filename
    name: FILE_NAME
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: TITLE
```

`tests/data/configs/multi_config_a.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_simple:index:index
  product_class: Product_Ancillary
output:
  fixed_width: false
  sort_by: ['a']
columns:
  - auto: lid
    name: LID
  - auto: filename
    name: FILE_NAME
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: TITLE
```

`tests/data/configs/multi_config_b.yaml`:

```yaml
output:
  fixed_width: true
  sort_by: ['FILE_NAME']
nillable:
  pds:ASCII_Real:
    inapplicable: -999.0
    missing:      -2.0
    unknown:      -997.0
    anticipated:  -996.0
```

`tests/data/configs/multi_config_c.yaml`:

```yaml
output:
  fixed_width: false
label_contents:
  title: Final title
```

`tests/data/configs/mapping_full_features.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_simple:index:index
  product_class: Product_Metadata_Supplemental
  version_id: '1.0'
  title: Mapping features index
columns:
  - auto: lid
    name: LID
  - auto: filename
  - auto: bundle_name
    name: BUNDLE
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
  - xpath: pds:Product_Observational<1>/pds:Observation_Area<1>/geom:Geometry<1>/geom:method<1>
    name: METHOD
```

`tests/data/configs/nilled.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_nilled:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Nilled index
columns:
  - auto: lid
    name: LID
  - xpath: pds:Product_Observational<1>/pds:Observation_Area<1>/pds:Time_Coordinates<1>/pds:stop_date_time<1>
    name: STOP
```

There is NO `nilled_bad.yaml`: the `nilled_bad` failing-bundle test
reuses `nilled.yaml` directly (the failing run does not depend on
config differences, and a byte-identical copy would violate the Phase 0
no-duplicate-fixtures criterion).

`tests/data/configs/quote_in_value_var.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_quote:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Quote in value (variable-width)
output:
  fixed_width: false
columns:
  - auto: lid
    name: LID
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: TITLE
```

`tests/data/configs/quote_in_value_fixed.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_quote:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Quote in value (fixed-width)
output:
  fixed_width: true
columns:
  - auto: lid
    name: LID
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: TITLE
```

`tests/data/configs/version_mismatch.yaml`:

```yaml
label_contents:
  logical_identifier: urn:nasa:pds:test_vm:index:index
  product_class: Product_Ancillary
  version_id: '1.0'
  title: Version mismatch index
columns:
  - auto: lid
    name: LID
```

### A.11 XSD seed files

Place under `tests/data/xsd_cache_seed/`. These are HAND-CURATED minimal
XSDs that mimic the PDS4 type registry well enough to exercise the
22-query chain in `schema_types.py`.

`pds_v1_basic.xsd` (the seed contains enough to resolve `logical_identifier`,
`version_id`, `title`, `name`, `description`, `editor_list`, `Citation_Information`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns="http://pds.nasa.gov/pds4/pds/v1"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:pds="http://pds.nasa.gov/pds4/pds/v1"
           targetNamespace="http://pds.nasa.gov/pds4/pds/v1"
           elementFormDefault="qualified">
  <xs:simpleType name="ASCII_LID">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_LIDVID_LID">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_File_Name">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_File_Specification_Name">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_Short_String_Collapsed">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_Text_Preserved">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_Integer">
    <xs:restriction base="xs:integer"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_Real">
    <xs:restriction base="xs:double"/>
  </xs:simpleType>
  <xs:simpleType name="ASCII_Date_YMD">
    <xs:restriction base="xs:date"/>
  </xs:simpleType>

  <xs:element name="logical_identifier">
    <xs:simpleType>
      <xs:restriction base="pds:ASCII_LID"/>
    </xs:simpleType>
  </xs:element>
  <xs:element name="version_id">
    <xs:simpleType>
      <xs:restriction base="pds:ASCII_Short_String_Collapsed"/>
    </xs:simpleType>
  </xs:element>
  <xs:element name="title">
    <xs:simpleType>
      <xs:restriction base="pds:ASCII_Short_String_Collapsed"/>
    </xs:simpleType>
  </xs:element>
  <xs:element name="name">
    <xs:simpleType>
      <xs:restriction base="pds:ASCII_Short_String_Collapsed"/>
    </xs:simpleType>
  </xs:element>
  <xs:element name="description">
    <xs:simpleType>
      <xs:restriction base="pds:ASCII_Text_Preserved"/>
    </xs:simpleType>
  </xs:element>
  <xs:element name="editor_list">
    <xs:simpleType>
      <xs:restriction base="pds:ASCII_Short_String_Collapsed"/>
    </xs:simpleType>
  </xs:element>
  <xs:element name="stop_date_time">
    <xs:simpleType>
      <xs:restriction base="pds:ASCII_Date_YMD"/>
    </xs:simpleType>
  </xs:element>
</xs:schema>
```

`pds_v1_units.xsd` (exercises the simpleContent/extension `_WO_Units` fallback chain, queries 13+):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns="http://pds.nasa.gov/pds4/pds/v1"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:pds="http://pds.nasa.gov/pds4/pds/v1"
           targetNamespace="http://pds.nasa.gov/pds4/pds/v1"
           elementFormDefault="qualified">
  <xs:simpleType name="ASCII_NonNegative_Integer">
    <xs:restriction base="xs:integer"/>
  </xs:simpleType>
  <xs:simpleType name="Wavelength_Range_WO_Units">
    <xs:restriction base="xs:double"/>
  </xs:simpleType>
  <xs:complexType name="Wavelength_Range">
    <xs:simpleContent>
      <xs:extension base="pds:Wavelength_Range_WO_Units">
        <xs:attribute name="unit" type="xs:string"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
  <xs:element name="wavelength_range" type="pds:Wavelength_Range"/>
</xs:schema>
```

`geom_v1.xsd` (serves the `geom` namespace URL declared by the
`multi_namespace` bundle):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns="http://pds.nasa.gov/pds4/geom/v1"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:geom="http://pds.nasa.gov/pds4/geom/v1"
           targetNamespace="http://pds.nasa.gov/pds4/geom/v1"
           elementFormDefault="qualified">
  <xs:simpleType name="ASCII_Short_String_Collapsed">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:element name="method">
    <xs:simpleType>
      <xs:restriction base="geom:ASCII_Short_String_Collapsed"/>
    </xs:simpleType>
  </xs:element>
</xs:schema>
```

`rings_v1.xsd` (serves the `rings` namespace URL):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns="http://pds.nasa.gov/pds4/rings/v1"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:rings="http://pds.nasa.gov/pds4/rings/v1"
           targetNamespace="http://pds.nasa.gov/pds4/rings/v1"
           elementFormDefault="qualified">
  <xs:simpleType name="ASCII_Short_String_Collapsed">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
  <xs:element name="ring_name">
    <xs:simpleType>
      <xs:restriction base="rings:ASCII_Short_String_Collapsed"/>
    </xs:simpleType>
  </xs:element>
</xs:schema>
```

`README.md` (in the same directory):

```markdown
# Test XSD seeds

Hand-curated PDS4 XSD snippets sufficient to exercise the query-chain
resolution in `pds4indextools.schema_types.SchemaTypeResolver`. These
intentionally do **not** mirror the real PDS4 schemas; they only
declare the simple types that the test fixtures reference. Every
golden output is generated against THESE seeds, never against the live
schemas.

`pds_v1_basic.xsd` serves both `PDS4_PDS_1L00.xsd` and
`PDS4_PDS_1K00.xsd` fixture URLs; `geom_v1.xsd` / `rings_v1.xsd` serve
the geom and rings URLs; `pds_v1_units.xsd` exercises the `_WO_Units`
fallback. The mapping from fixture URL to seed file is
`_FIXTURE_SCHEMA_URLS` in `tests/conftest.py` (mirrored by
`scripts/generate_expected_outputs.py`).

Only tests marked `@pytest.mark.live` download real schemas from
`https://pds.nasa.gov/` (R-SCH-010, R-TST-030 as amended).
```

### A.12 Inline XML used by `test_label_scraping_and_validation.py`

The scraper tests need fragments small enough to be defined as Python
strings. Tests write each constant to `tmp_path / '<scenario>.lblx'`
(always the `.lblx` suffix) before scraping. Define a module-level
constants block at the top of
`tests/unit/test_label_scraping_and_validation.py`:

```python
NS_PDS = 'http://pds.nasa.gov/pds4/pds/v1'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'

SIMPLE_LABEL = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="{NS_PDS}" xmlns:xsi="{NS_XSI}"
 xsi:schemaLocation="{NS_PDS} https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_simple:index:row1</logical_identifier>
        <version_id>1.0</version_id>
        <title>Row 1</title>
    </Identification_Area>
</Product_Observational>
'''

LABEL_BOM = '﻿' + SIMPLE_LABEL  # serialised to bytes EF BB BF + ...

LABEL_NO_DEFAULT_NS = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<pds:Product_Observational xmlns:pds="{NS_PDS}" xmlns:xsi="{NS_XSI}"
 xsi:schemaLocation="{NS_PDS} https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <pds:Identification_Area>
        <pds:logical_identifier>urn:nasa:pds:t:t:t</pds:logical_identifier>
        <pds:version_id>1.0</pds:version_id>
    </pds:Identification_Area>
</pds:Product_Observational>
'''

LABEL_WITH_NIL = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="{NS_PDS}" xmlns:xsi="{NS_XSI}"
 xsi:schemaLocation="{NS_PDS} https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_simple:index:row1</logical_identifier>
        <version_id>1.0</version_id>
        <title>Row 1</title>
    </Identification_Area>
    <Time_Coordinates>
        <stop_date_time xsi:nil="true" nilReason="missing"/>
    </Time_Coordinates>
</Product_Observational>
'''

# ... and so on for every fixture combination (one per scraper test).
```

Implementer enumerates one string constant per scraper test scenario;
the constant name encodes the scenario. The plan above's test-function
table lists every scenario.

### A.13 `scripts/verify_test_coverage.py`

This script walks the spec and confirms every `R-*` ID is referenced in
at least one test file. It is executed by the Phase 14 exit criteria and
by the `test_verify_test_coverage_script_passes` wrapper test in
`tests/unit/test_documentation_conventions.py` (so it runs in CI through
the template's ordinary pytest step). NOTE: the script uses `git grep`,
which sees only TRACKED files — `git add` new tests/fixtures before
running it (each phase ends with a commit, so this holds naturally).

```python
"""Verify every R-* ID in specs/SPECS-pds4_create_xml_index.md is referenced.

Walks ``specs/SPECS-*.md`` extracting every ``R-[A-Z]+-[0-9]+`` token,
then greps ``tests/`` for each. Writes unreferenced R-IDs to stderr and
exits 1 if any are missing; exits 0 if all R-IDs are covered.

Additional strictness: each R-ID must appear inside a real test file
(``tests/unit/`` or ``tests/integration/``), not only in a top-level
docstring or markdown table elsewhere.

Run:
    python scripts/verify_test_coverage.py
"""

import re
import subprocess
import sys
from pathlib import Path


# Uses [0-9] (not \d): this same pattern string is handed to ``git grep -oE``
# (POSIX ERE), where ``\d`` is a literal 'd' and would match nothing.
R_ID_RE = re.compile(r'R-[A-Z]+-[0-9]{3}')
ROOT = Path(__file__).resolve().parent.parent

# R-ID families satisfied by repository infrastructure, packaging,
# docs, or testing policy itself rather than by individual test bodies:
#   R-CI-*  — template CI workflows
#   R-PKG-* — package layout/packaging
#   R-DOC-* — documentation deliverables
#   R-DEP-* — dependency policy
#   R-TST-* — testing-strategy meta-rules
_EXEMPT_PREFIXES: tuple[str, ...] = (
    'R-CI-', 'R-PKG-', 'R-DOC-', 'R-DEP-', 'R-TST-',
)


def collect_r_ids() -> set[str]:
    """Return the set of non-exempt R-IDs in the spec."""
    spec = ROOT / 'specs' / 'SPECS-pds4_create_xml_index.md'
    text = spec.read_text(encoding='utf-8')
    return {
        rid for rid in R_ID_RE.findall(text)
        if not rid.startswith(_EXEMPT_PREFIXES)
    }


def _grep_in(paths: tuple[str, ...]) -> set[str]:
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ['git', 'grep', '-h', '-oE', R_ID_RE.pattern, '--', *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return set(proc.stdout.split())


def collect_referenced_ids() -> set[str]:
    """Return the set of R-IDs referenced anywhere under tests/."""
    return _grep_in(('tests/',))


def collect_test_function_ids() -> set[str]:
    """Return the set of R-IDs referenced under tests/unit/ or tests/integration/."""
    return _grep_in(('tests/unit/', 'tests/integration/'))


def main() -> int:
    """Emit unreferenced R-IDs to stderr; return non-zero if any are missing."""
    spec_ids = collect_r_ids()
    test_ids = collect_referenced_ids()
    test_dir_ids = collect_test_function_ids()
    missing = sorted(spec_ids - test_ids)
    if missing:
        sys.stderr.write('Spec R-IDs not referenced in tests/:\n')
        for rid in missing:
            sys.stderr.write(f'  {rid}\n')
        return 1
    only_in_docs = sorted((spec_ids & test_ids) - test_dir_ids)
    if only_in_docs:
        sys.stderr.write(
            'Spec R-IDs referenced only outside tests/unit/ or tests/integration/:\n',
        )
        for rid in only_in_docs:
            sys.stderr.write(f'  {rid}\n')
        return 1
    sys.stdout.write(f'All {len(spec_ids)} R-IDs referenced in tests/.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

This script is a convergence check, not a substitute for actual test
content. The Phase 14 exit criterion uses it as a TRIPWIRE only.

---

## Appendix B — Test fixture content

### B.0 Golden-bytes contract for `expected/<bundle>/`

For every bundle with an `expected/<bundle>/` directory, the golden
`index.csv` AND `index.lblx` files are PRODUCED ONCE by the generator
script in [Appendix I.1](#i1-scriptsgenerate_expected_outputspy). The
generator is deterministic (pinned `rms-pdstemplate`, `freezegun`,
`os.utime` fixing CSV mtime). The generator's first-run output IS the
golden — by definition. The byte sequences in subsequent appendix
sections (B.1, B.2, B.3, …) show the EXPECTED CSV bytes verbatim where
small enough to inline (≤ 50 lines). For `index.lblx` outputs the byte
specifications point at the generator (Appendix I) rather than inlining
the long XML; the integration tests compare against the committed
files. Phase 11's "first commit" step (Appendix I, step 4) is the only
moment the bytes are introduced; from that point on, drift causes a
test failure, not a regeneration.

### B.1 `simple_pds_only` bundle

`tests/data/bundles/simple_pds_only/row1.lblx`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_simple:index:row1</logical_identifier>
        <version_id>1.0</version_id>
        <title>Row 1</title>
        <information_model_version>1.21.0.0</information_model_version>
        <product_class>Product_Observational</product_class>
    </Identification_Area>
</Product_Observational>
```

Columns come from the `columns:` block of
`tests/data/configs/simple.yaml` (A.10): `LID` (auto `lid`),
`FILE_NAME` (auto `filename`), `TITLE` (title XPath).

`tests/data/expected/simple_pds_only/index.csv` — exactly the bytes:

```text
LID,FILE_NAME,TITLE
urn:nasa:pds:test_simple:index:row1,row1.lblx,Row 1
```

with LF (`\n`) line terminators and final `\n` after `Row 1`.

`tests/data/expected/simple_pds_only/index.lblx` — produced by the
generator in [Appendix I.1](#i1-scriptsgenerate_expected_outputspy)
under `frozen_time('2026-05-14T00:00:00Z')` and `os.utime(csv,
(_FROZEN_MTIME_EPOCH, _FROZEN_MTIME_EPOCH))`. Run once in Phase 11; the
output bytes are committed to `tests/data/expected/simple_pds_only/index.lblx`
and become the golden. Every golden-comparison integration test runs
under the same `frozen_time` + `frozen_csv_mtime` fixture pair. The
same procedure produces every other bundle's `expected/<bundle>/index.lblx`
in B.2..B.16.

### B.2 `multi_namespace` bundle

Three labels named `a.lblx`, `b.lblx`, `c.lblx`. Each declares the
`pds:`/`geom:`/`rings:` namespaces. The labels differ only in their LID
suffix (`row_a`, `row_b`, `row_c`) and a `<geom:Geometry>` /
`<rings:Ring>` block.

`a.lblx`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:geom="http://pds.nasa.gov/pds4/geom/v1"
 xmlns:rings="http://pds.nasa.gov/pds4/rings/v1"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd
                      http://pds.nasa.gov/pds4/geom/v1 https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1L00_2000.xsd
                      http://pds.nasa.gov/pds4/rings/v1 https://pds.nasa.gov/pds4/rings/v1/PDS4_RINGS_1L00_1G00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_multi_ns:index:row_a</logical_identifier>
        <version_id>1.0</version_id>
        <title>Row A</title>
    </Identification_Area>
    <Observation_Area>
        <geom:Geometry>
            <geom:method>row_a_method</geom:method>
        </geom:Geometry>
        <rings:Ring>
            <rings:ring_name>row_a_ring</rings:ring_name>
        </rings:Ring>
    </Observation_Area>
</Product_Observational>
```

`b.lblx` and `c.lblx` are identical except the LID suffix, the
`<title>` text (`Row B` / `Row C`), and the `_method` / `_ring` values
(`row_b_method`/`row_b_ring`, etc.).

Columns come from `tests/data/configs/multi_namespace.yaml` (A.10):
`LID`, `FILE_NAME`, `TITLE`, `GEOM_METHOD`, `RING_NAME`.

`tests/data/expected/multi_namespace/index.csv`:

```text
LID,FILE_NAME,TITLE,GEOM_METHOD,RING_NAME
urn:nasa:pds:test_multi_ns:index:row_a,a.lblx,Row A,row_a_method,row_a_ring
urn:nasa:pds:test_multi_ns:index:row_b,b.lblx,Row B,row_b_method,row_b_ring
urn:nasa:pds:test_multi_ns:index:row_c,c.lblx,Row C,row_c_method,row_c_ring
```

### B.3 `nilled` bundle

One label `nilled.lblx` whose `<stop_date_time>` element is
`xsi:nil="true" nilReason="missing"`. Expected substitution from
`default_config.yaml` nillable mapping: `0002-01-01`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_nilled:index:row1</logical_identifier>
        <version_id>1.0</version_id>
    </Identification_Area>
    <Observation_Area>
        <Time_Coordinates>
            <stop_date_time xsi:nil="true" nilReason="missing"/>
        </Time_Coordinates>
    </Observation_Area>
</Product_Observational>
```

Columns come from `tests/data/configs/nilled.yaml` (A.10): `LID`,
`STOP`.

`tests/data/expected/nilled/index.csv`:

```text
LID,STOP
urn:nasa:pds:test_nilled:index:row1,0002-01-01
```

### B.4 `nilled_bad` bundle

Identical to `nilled` but `nilReason="bogus"` — run aborts with
`NilError`. No expected output.

### B.5 `repeated_tags` bundle

One label whose `<Observation_Area>` contains three sibling
`<Observing_System>` blocks (R-XP-020 renumber test).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_rep:index:row1</logical_identifier>
        <version_id>1.0</version_id>
    </Identification_Area>
    <Observation_Area>
        <Observing_System><name>OS_1</name></Observing_System>
        <Observing_System><name>OS_2</name></Observing_System>
        <Observing_System><name>OS_3</name></Observing_System>
    </Observation_Area>
</Product_Observational>
```

Columns come from `tests/data/configs/repeated_tags.yaml` (A.10):
`LID`, `OS1`, `OS2`, `OS3`.

`tests/data/expected/repeated_tags/index.csv`:

```text
LID,OS1,OS2,OS3
urn:nasa:pds:test_rep:index:row1,OS_1,OS_2,OS_3
```

### B.6 `non_monotone` bundle

**Binding choice**: NO XML fixture. The R-XP-021 path cannot be
naturally exercised through a PDS4 label because lxml's `getpath()`
groups predicates by tag (so even interleaving sibling tags produces
monotonic per-tag indexes). There is NO `non_monotone` bundle
directory at all (git cannot track an empty directory).

The R-XP-021 path is tested ONLY at the unit level via a synthetic
direct call:

```python
def test_renumber_non_monotone_interleave_raises_xpatherror() -> None:
    with pytest.raises(XPathError) as exc_info:
        renumber_xpaths(['pds:A<2>/pds:B<1>', 'pds:A<1>/pds:B<1>'])
    assert 'non-monotone' in str(exc_info.value).lower()
```

The integration test `test_non_monotone_label_raises_xpatherror`
(referenced in Phase 11) is REMOVED — it cannot be constructed and
its R-ID coverage is satisfied by the unit test above. The Phase 11
test table entry for `non_monotone` is replaced with a one-line note
that the bundle has no integration test (only the unit test). The
spec's R-XP-021 is mapped to the unit test T-ID T-XP-021.

### B.7 `multi_lid` bundle

Three labels `a.lblx`, `b.lblx`, `c.lblx`, each with the SAME LID
`urn:nasa:pds:test_lid:index:dup_row` but different filenames. In
fail-fast mode the run aborts at the SECOND label with a `LidError`
naming the colliding pair (`a.lblx`, `b.lblx`); under `--fail-slow`
both collisions (b-vs-a and c-vs-a) are collected before the aggregate
abort. The three files
differ ONLY in their `<title>` text (`Dup row A` / `Dup row B` /
`Dup row C`) so that no two fixture files are byte-identical (Phase 0
exit criterion) while the LID collision is preserved. `a.lblx`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_lid:index:dup_row</logical_identifier>
        <version_id>1.0</version_id>
        <title>Dup row A</title>
    </Identification_Area>
</Product_Observational>
```

### B.8 `bom` bundle

Single label `bom.lblx` whose bytes start with `0xEF 0xBB 0xBF` followed
by the `simple_pds_only/row1.lblx` bytes. The run aborts with
`ParseError`.

Phase 0 generation procedure (run once; commit the resulting file as a
normal git blob, no LFS):

```bash
python -c "from pathlib import Path; \
  Path('tests/data/bundles/bom/bom.lblx').write_bytes( \
    b'\xef\xbb\xbf' + Path('tests/data/bundles/simple_pds_only/row1.lblx').read_bytes())"
```

The unit test `test_bom_file_starts_with_bom_bytes` (in
`tests/unit/test_fixture_integrity.py`) asserts
`Path('tests/data/bundles/bom/bom.lblx').read_bytes().startswith(b'\xef\xbb\xbf')`.

### B.9 `non_ascii_value` bundle

Single label with `<title>Rôw 1</title>` (one `ô` character). The
run aborts with `ScrapedValueError`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_nonascii:index:row1</logical_identifier>
        <version_id>1.0</version_id>
        <title>Rôw 1</title>
    </Identification_Area>
</Product_Observational>
```

### B.10 `quote_in_value` bundle

Single label `quoted.lblx`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_quote:index:row1</logical_identifier>
        <version_id>1.0</version_id>
        <title>R"ow 1</title>
    </Identification_Area>
</Product_Observational>
```

Columns come from the `columns:` blocks of
`quote_in_value_var.yaml` / `quote_in_value_fixed.yaml` (A.10): `LID`
and `TITLE` only (deliberately no `filename` column — the expected
output below has two columns).

Two integration tests:

- `test_quote_in_value_variable_width_rejected` uses
  `tests/data/configs/quote_in_value_var.yaml` (fixed_width=false) →
  run aborts with `ScrapedValueError`. No `expected/` files.
- `test_quote_in_value_fixed_width_passes_through` uses
  `tests/data/configs/quote_in_value_fixed.yaml` (fixed_width=true) →
  run succeeds; bytes follow.

Fixed-width column-width arithmetic (per §13.4–§13.6):

- Column `LID`: values are
  `'urn:nasa:pds:test_quote:index:row1'` (34 bytes). No comma. So
  `must_quote = False`, `max_byte_length = 34`.
- Column `TITLE`: value `'R"ow 1'` (6 bytes). No comma. So
  `must_quote = False` (R-CSV-040: must_quote is true ONLY for
  comma-bearing values; `"` does NOT trigger it). `max_byte_length = 6`.

Header row (unpadded per R-CSV-071): `LID,TITLE\n` (10 bytes including
the trailing LF).

Data row: each cell padded right with spaces to its column width;
columns separated by comma; no trailing comma; LF terminator:
`urn:nasa:pds:test_quote:index:row1,R"ow 1\n`
(34 bytes + comma + 6 bytes + LF = 42 bytes). The LID cell is already
34 bytes so no padding is added; the TITLE cell is already 6 bytes so
no padding is added either. (R-CSV-070 pads to `max_byte_length`; when
the value's byte length already equals the column max, zero padding
bytes are added.)

Expected `tests/data/expected/quote_in_value/index.csv` literal bytes:

```text
LID,TITLE
urn:nasa:pds:test_quote:index:row1,R"ow 1
```

Both lines end with LF only (`\n`). No trailing whitespace; no padding
beyond the column-width formula. The lblx is generated per Appendix I.

### B.11 `version_mismatch` bundle

Two labels declaring the same default namespace but pointing at
different `xsi:schemaLocation` URLs. The integration test asserts that
the run aborts with `SchemaVersionError` naming both URLs and both file
paths.

`a.lblx`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_vm:index:row_a</logical_identifier>
        <version_id>1.0</version_id>
    </Identification_Area>
</Product_Observational>
```

`b.lblx` (`1L00` → `1K00` in the schema URL):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1K00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_vm:index:row_b</logical_identifier>
        <version_id>1.0</version_id>
    </Identification_Area>
</Product_Observational>
```

### B.12 `no_schema_location` bundle

Single label without the `xsi:schemaLocation` attribute. Run aborts with
`SchemaResolutionError`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_nosch:index:row1</logical_identifier>
        <version_id>1.0</version_id>
    </Identification_Area>
</Product_Observational>
```

### B.13 `fixed_width` feature (no bundle of its own)

There is NO `fixed_width` bundle directory (owner decision #8). The
integration tests and the golden-bytes generator run the
`simple_pds_only` bundle with `tests/data/configs/fixed_width.yaml`
(whose `columns:` block matches `simple.yaml`'s), writing goldens to
`tests/data/expected/fixed_width/`.

Column widths (single data row, so every data cell already equals its
column's max byte length): `LID` = 35
(`urn:nasa:pds:test_simple:index:row1`), `FILE_NAME` = 9 (`row1.lblx`),
`TITLE` = 5 (`Row 1`). Because padding extends cells only up to the
column max (R-CSV-070) and the header row is never padded (R-CSV-071),
the fixed-width CSV bytes for this bundle are IDENTICAL to the
variable-width bytes:

```text
LID,FILE_NAME,TITLE
urn:nasa:pds:test_simple:index:row1,row1.lblx,Row 1
```

Fixed-width mode is therefore verified end-to-end through the lblx
golden (`<Table_Character>` with its `record_length`,
`field_location`, and `field_length` values per R-LBL-020). Visible
multi-row padding is exercised by the Phase 8 unit tests
(T-CSV-020/021) with synthetic rows of differing cell lengths.

### B.14 `crlf` feature (no bundle of its own)

Runs the `simple_pds_only` bundle with `tests/data/configs/crlf.yaml`;
goldens in `tests/data/expected/crlf/`. Expected CSV
(binary view — explicit `\r\n` line terminators):

```text
LID,FILE_NAME,TITLE\r\n
urn:nasa:pds:test_simple:index:row1,row1.lblx,Row 1\r\n
```

(Where `\r\n` is the literal two-byte sequence `0x0D 0x0A`.) The
expected lblx is produced by Appendix I's generator with
`OutputSection.line_ending = 'CRLF'`; the lblx
`<record_delimiter>Carriage-Return Line-Feed</record_delimiter>` is
the binding match for T-CSV-030.

### B.15 `multi_config` feature (no bundle of its own)

Runs the `simple_pds_only` bundle; the integration test passes three
configs in order:
`multi_config_a.yaml` → `multi_config_b.yaml` → `multi_config_c.yaml`.
The merged result has `output.fixed_width = false` (from `c`, which
overrides `b`'s `true`), `output.sort_by = ['FILE_NAME']` (from `b`,
which replaces `a`'s `['a']`), `label_contents.title = 'Final title'`
(from `c`), and `label_contents.logical_identifier` and
`.product_class` inherited from `a`. `FILE_NAME` is the emitted header
for the `filename` auto-column in `multi_config_a.yaml`'s `columns:`
block (R-SORT-020 requires sort keys to name emitted columns), so the
sort succeeds and a CSV is produced. (`a`'s `['a']` never reaches validation — merge happens
first.)

Columns come from `multi_config_a.yaml`'s `columns:` block (the later
configs in the chain define no `columns`, so `a`'s list survives the
merge).

Expected `tests/data/expected/multi_config/index.csv`:

```text
LID,FILE_NAME,TITLE
urn:nasa:pds:test_simple:index:row1,row1.lblx,Row 1
```

The lblx is produced by Appendix I's generator. A.7's tree
includes the `expected/multi_config/` subdirectory.

### B.16 `mapping_full_features` feature (no bundle of its own)

Runs the `multi_namespace` bundle directly (no copies). The
`columns:` block of `tests/data/configs/mapping_full_features.yaml`
(A.10) exercises every entry shape: auto with rename (`lid` → `LID`),
bare auto with `name` omitted (header `filename`), auto with rename
(`bundle_name` → `BUNDLE`), xpath with `name` omitted (header = the
raw canonical XPath), and xpath with rename (`METHOD`).

Expected `tests/data/expected/mapping_full_features/index.csv`:

```text
LID,filename,BUNDLE,pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>,METHOD
urn:nasa:pds:test_multi_ns:index:row_a,a.lblx,test_multi_ns,Row A,row_a_method
urn:nasa:pds:test_multi_ns:index:row_b,b.lblx,test_multi_ns,Row B,row_b_method
urn:nasa:pds:test_multi_ns:index:row_c,c.lblx,test_multi_ns,Row C,row_c_method
```

(The `pds:Product_...` column header is the raw canonical XPath
because the entry's `name` was omitted — R-MAP-012.1 analog.)

### B.17 — removed (`large_synthetic` bundle dropped)

The 1,000-label `large_synthetic` stress bundle, its generator, its
mapping file, and its expected outputs are all removed per owner
decision #9. The R-IDs it exercised are covered elsewhere: R-IDX-002
(filesystem-order perturbation) in `test_determinism.py`, R-LOG-020/021
(progress bar) and R-SCH-020/R-TST-021 (XSD cache reuse) in
`test_generate_index_file.py` against `multi_namespace`.

### B.18 — removed (mapping-file fixtures dropped)

The mapping `.txt` fixture files are removed with the format (owner
decision #10). Column-validation error cases are unit-tested in
`test_config_loading_and_merging.py` with inline YAML written to
`tmp_path`.

### B.19 Expected `xpath_list` outputs (YAML columns blocks)

`tests/data/expected/xpath_lists/simple_pds_only.yaml` — exact bytes
(LF terminators):

```yaml
# Generated by pds4_create_xml_index generate_xpath_list.
# Edit each `name:` (or delete unwanted entries), then merge this
# `columns:` block into one of your --config-file YAMLs.
columns:
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:logical_identifier<1>
    name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:logical_identifier<1>
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:version_id<1>
    name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:version_id<1>
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
    name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:information_model_version<1>
    name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:information_model_version<1>
  - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:product_class<1>
    name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:product_class<1>
```

`tests/data/expected/xpath_lists/multi_namespace.yaml` — same shape,
five entries in first-occurrence order: the three
`pds:Identification_Area` XPaths, then
`.../geom:Geometry<1>/geom:method<1>`, then
`.../rings:Ring<1>/rings:ring_name<1>` (`a.lblx` is alphabetically
first and contributes all distinct XPaths; `b.lblx` and `c.lblx`
contribute none new).

---

## Appendix C — Documentation files

### C.1 `docs/conf.py` — template file + minimal delta

The committed template `docs/conf.py` is the basis. Apply ONLY this
delta; every other line stays byte-identical to the committed file:

1. In `intersphinx_mapping`, replace the unused `numpy` and
   `matplotlib` entries with the projects this library actually
   references:

   ```python
   intersphinx_mapping = {
       'python': ('https://docs.python.org/3', None),
       'lxml': ('https://lxml.de/apidoc/', None),
       'pydantic': ('https://docs.pydantic.dev/latest/', None),
       'requests': ('https://requests.readthedocs.io/en/latest/', None),
   }
   ```

2. Append at the end of the file (needed so the Phase 12
   `sphinx-build -n -W` exit criterion can pass — pdstemplate publishes
   no Sphinx inventory):

   ```python
   nitpick_ignore = [
       # PdsTemplate types are not documented externally; skip in nitpicky mode.
       ('py:class', 'pdstemplate.PdsTemplate'),
   ]
   ```

   If the `-n -W` build surfaces further unresolvable THIRD-PARTY
   references (e.g. `lxml.etree._Element`, `tqdm.tqdm`, pydantic
   internals), appending them to `nitpick_ignore` is part of this
   enumerated delta — never ignore references to PUBLIC `pds4indextools.*`
   symbols; a missing public target is a real docs bug. The one sanctioned
   exception is a PRIVATE symbol that autodoc leaks as a rendering artifact
   of pydantic type-alias expansion — specifically
   `pds4indextools.config._require_absolute`, surfaced when autodoc expands
   the `AbsolutePath = Annotated[Path, AfterValidator(_require_absolute)]`
   alias in `IndexConfig.xsd_cache_dir` (and, without
   `from __future__ import annotations`, the alias is evaluated eagerly so
   `autodoc_type_aliases` cannot suppress it). The public `AbsolutePath`
   alias itself is documented in `module.rst`, so ignoring the leaked
   private ref hides no public API.

No other settings are changed: the template already enables autodoc,
napoleon, viewcode, intersphinx, mermaid (`mermaid_output_format =
'raw'`), myst_parser, `html_theme = 'sphinx_rtd_theme'`,
`add_module_names = False`, and `suppress_warnings = ['myst.header']`.
`nitpicky` is NOT set in `conf.py`; nitpicky builds are exercised via
the `-n` flag in the Phase 12 exit-criteria commands.

### C.2..C.13 Documentation file contents

Each file below is composed by following the BINDING section structure
listed for it. Every bullet listed for a file appears as a section
header (or sub-section header where indented) in the rendered output,
IN THE ORDER SHOWN. The implementer does NOT add prose beyond what is
needed to satisfy each bullet, and does NOT add sections beyond those
listed. Sample/example code in each file is sourced verbatim from the
specified test bundle or appendix. Each file is short (≤300 lines) and
referenced ONCE in the toctree. Cross-references use the spec-mandated
Sphinx roles (`:class:`, `:meth:`, `:func:`, `:mod:`, `:attr:`,
`:data:`, `:exc:`) per `documentation.mdc` §5.

**Note on equivalence**: the C.2-C.13 structural outlines specify
section headers, cross-reference roles, and example sources. The
implementer's prose between section headers IS implementer-authored —
this is acknowledged. The convergence gate is:

1. `sphinx-build -W -n -b html docs` exits 0 with ZERO warnings
   (every cross-reference resolves to a real symbol; no unused doc).
2. `scripts/verify_public_api.py` exits 0 (every public symbol is
   in `module.rst`).
3. `pytest tests/unit/test_documentation_conventions.py` GREEN (every
   name in `__all__` appears in `module.rst`; no `Args:` in any
   docstring; every public class has a non-empty docstring; American
   English; one space after periods; pragma budget).
4. PyMarkdown scan passes.

These four gates pin the document structure and consistency tightly
enough that two implementers' prose differs only in stylistic choices
within each section. The user's bar is satisfied: an implementer with
no context can write the docs cold using the structural outline plus
the gates above.

**C.2 `docs/index.rst`** — template file + minimal delta. The committed
template `index.rst` (title, `.. include:: ../README.md` with
`:start-after: <!-- start-after-point -->`, toctree, Indices section)
is the basis. The ONLY change is extending the toctree entries from
`module` to this ordered list:

```rst
   installation
   quickstart
   cli
   config
   usage_examples
   architecture
   module
   contributing
   code_of_conduct
```

**C.3 `docs/installation.rst`** — Must include (`documentation.mdc` §3
Install-guide row):
- `pip install rms-pds4indextools`
- `pip install "rms-pds4indextools[dev]"` (test/lint stack)
- `pip install "rms-pds4indextools[docs]"` (Sphinx + theme)
- Supported Python versions table (3.10, 3.11, 3.12, 3.13) with OS
  matrix (Linux / macOS / Windows).
- Runtime dependency list (lxml, pyyaml, pydantic, rms-pdstemplate,
  requests, requests-file, platformdirs, tqdm) with version floors;
  cross-reference :mod:`lxml` via intersphinx.
- System dependencies for `lxml` (`libxml2` / `libxslt` on Linux and
  macOS; the lxml wheel is self-contained on Windows).
- Verifying installation: `pds4_create_xml_index --version`.

**C.4 `docs/quickstart.rst`** — Must include:
- End-to-end walkthrough using `tests/data/bundles/simple_pds_only/`
- Code block showing the exact invocation
- Code block showing the exact `index.csv` output
- Code block showing the exact `index.lblx` snippet
- Pointer at `:doc:cli` for full reference

**C.5 `docs/cli.rst`** — Must include:
- Section per subcommand (`generate_index_file`, `generate_xpath_list`,
  `copy_default_config`).
- Each section is composed by hand (we do NOT add `sphinx-argparse`)
  and mirrors the exact `--help` output of each subcommand
  (build by running `pds4_create_xml_index <sub> --help` and pasting
  the output into the .rst file inside a `::` literal block).
- Each section additionally has prose paragraphs covering: exit
  codes (R-API-004), output-file naming rules
  (R-CLI-015 / R-OUT-010..R-OUT-013), and a one-paragraph example.
- The `generate_index_file` section notes that label discovery is
  purely glob-pattern-driven: examples use `'**/*.lblx'`, and a
  sentence states that `.xml` is an equally valid historical label
  suffix — users with `.xml` labels pass `'**/*.xml'` (or both
  patterns) and get identical behavior.

**C.6 `docs/config.rst`** — Must include:
- Section per top-level config key (`columns`, `nillable`, `output`,
  `label_contents`, `xsd_cache_dir`).
- The `columns` section documents every entry shape (one example each:
  `xpath`+`name`, `xpath` with `name` omitted, `auto`+`name`, bare
  `auto`), the validation-rules table (exactly-one selector, valid
  auto tokens, name charset, duplicates, wholesale replacement on
  merge), the required-for-`generate_index_file` rule, and the
  `generate_xpath_list` starter-block workflow.
- Pydantic class reference via `:class:`~pds4indextools.IndexConfig``,
  etc.
- Full example YAML.
- Subsection on the reserved BASE variables (R-LBL-012).

**C.7** — removed (the mapping-file format no longer exists; its
documentation lives in C.6's `columns` section).

**C.8 `docs/architecture.rst`** — Must include (`documentation.mdc` §3
Architecture-overview row):
- Class hierarchy: full Mermaid `classDiagram` of the
  :exc:`~pds4indextools.errors.Pds4IndexError` tree from spec §17.1
  (every exception class with its parent and `FAIL_SLOW_ELIGIBLE` value).
- Public API surface: per-module list of every name in `__all__`, each
  name rendered with the appropriate Sphinx role (`:class:`, `:func:`,
  `:data:`, `:exc:`).
- Interface contracts: for each public `run_*` function, a short
  paragraph stating preconditions, postconditions, and the exception
  types it raises (cross-referenced via `:exc:`).
- Mermaid `flowchart` of data flow:
  ```
  discover → parse → renumber → schema-resolve → filter → sort
            → write CSV → write label
  ```
- Module responsibilities table (10 modules × 1-line description each;
  module name uses `:mod:` role).
- Section on the error model (R-ERR-001, R-API-004).

**C.9 `docs/module.rst`** — template file + delta (`documentation.mdc`
§3 Module-index row). The committed template `module.rst` (the
`.. automodule:: pds4indextools` block with its `:member-order:`,
`:members:`, `:undoc-members:`, `:special-members:`,
`:show-inheritance:`, and `:exclude-members:` options) is the basis.
The root `.. automodule:: pds4indextools` block is REDUCED to render only
the package docstring (its `:members:`/`:special-members:`/
`:exclude-members:` options are dropped): because the root re-exports
every public name, keeping `:members:` there would document each symbol a
SECOND time and the `-n -W` build fails with duplicate-object-description
and ambiguous-cross-reference warnings. The per-symbol documentation lives
in the appended per-submodule subsections instead. The delta APPENDS one
subsection per public submodule, each using explicit `:members:` lists
(plus `.. autodata::`/`.. py:data::` for the module-level constants and
type aliases that `automodule :members:` does not emit) so every
`__all__` name still appears in `module.rst` text:
- Subsections, in this order: errors, config, xpath_norm,
  schema_types, scraper, csv_writer, label_writer, cli. (`_logging`,
  `_io`, and `__main__` are private/entry-point modules — `__main__` is
  documented as the script entry point in a short prose paragraph, not
  an `automodule`.)
- A unit test in `tests/unit/test_documentation_conventions.py` parses
  `module.rst` and asserts that every public name in
  `pds4indextools.__all__` (and each submodule's `__all__`) appears;
  a separate test asserts no `.. automodule::` directive is
  duplicated. New symbol → red test → update both files
  (`documentation.mdc` §3, §6).

**C.10 `docs/contributing.rst`** — template file, UNCHANGED (it already
includes `../CONTRIBUTING.md` via `myst_parser.sphinx_` split around
the code-of-conduct pointer).

**C.10a `docs/usage_examples.rst`** — Must include (`documentation.mdc`
§3 Usage-examples row):
- Workflow 1: generate an index file with a `columns:` config (uses
  `tests/data/bundles/simple_pds_only/`); shows full invocation, full
  rendered `index.csv`, and full rendered `index.lblx` snippet.
- Workflow 2: generate an index file across multiple namespaces (uses
  `tests/data/bundles/multi_namespace/`).
- Workflow 3: fixed-width output (uses
  `tests/data/bundles/simple_pds_only/` with
  `tests/data/configs/fixed_width.yaml`).
- Workflow 4: CRLF line endings (uses
  `tests/data/bundles/simple_pds_only/` with
  `tests/data/configs/crlf.yaml`).
- Workflow 5: fail-slow mode summarizing N errors before exit.
- Workflow 6: generate a starter `columns:` block
  (`generate_xpath_list`) and merge it into a config file.
- Workflow 7: copy and customize the default config
  (`copy_default_config`).
- Workflow 8: programmatic API call to
  :func:`~pds4indextools.run_generate_index_file`.
Each workflow shows the exact invocation, the expected stdout/stderr,
and the expected output file (or excerpt). Cross-references in narrative
prose use the appropriate Sphinx roles (no bare CamelCase even in
inline literals).


**C.11 `docs/code_of_conduct.md`** — template file, UNCHANGED.

**C.12 `README.md`** — template file + delta (`documentation.mdc` §3
README row). The committed template README's structure is kept
EXACTLY: title, the full badge block (already present and correct for
`rms-pds4indextools` — no logo), the `<!-- start-after-point -->`
marker, and the section order `Features` → `Installation` →
`Getting Started` → `Contributing` → `Links` → `Licensing`. The delta
fills the template's TODO placeholders only:
- `Features`: one-paragraph project summary + a short feature bullet
  list (index generation, `.lblx` label generation, column configuration,
  config merging, starter-columns generation via `generate_xpath_list`).
- `Getting Started` / `Usage examples`: the same quickstart invocation
  and output snippet as `docs/quickstart.rst`, using the
  `simple_pds_only` fixture bundle and `'**/*.lblx'` pattern.
No sections are added or removed; the `Installation`, `Contributing`,
`Links`, and `Licensing` sections stay as committed.

**C.13 `CONTRIBUTING.md`** — template file + delta. The committed
template CONTRIBUTING.md is the basis; keep its existing sections and
wording. The delta appends (or fills in, where the template already has
a matching section) ONLY:
- Dev setup line: `pip install -e ".[dev,docs]"`.
- A short `scripts/run-all-checks.sh` walkthrough (default run plus the
  `-c`/`-d` and per-check flags).
- Docstring style note: PEP 257 + Google with `Parameters:` (NOT
  `Args:`), `Returns:`/`Raises:` only where applicable, 90-char wrap,
  Sphinx cross-reference roles per `documentation.mdc` §5.
Nothing else in the template file is altered.

---

## Appendix D — CI workflows (template, unchanged)

The three template workflows are already committed and are kept
byte-identical to the template (with the pre-existing
REPONAME/MODULENAME substitutions). No new CI actions are invented
(§0.0); the previously drafted `ci.yml` and `pip_audit.yml` are
dropped.

### D.1 `.github/workflows/run-tests.yml`

Template file, UNCHANGED. It provides:

- a `lint` job on ubuntu-latest / Python 3.13 running
  `pip install -e ".[dev]"`, `ruff check src tests`,
  `ruff format --check src tests`, `mypy src tests`,
  `sphinx-build -W -b html docs docs/_build`, and
  `pymarkdown scan docs/ .cursor/ README.md CONTRIBUTING.md`;
- a `test` job matrix (Python 3.10 / 3.11 / 3.12 / 3.13 on
  ubuntu-latest) running
  `python -m pytest --cov=src --cov-report=xml -n auto tests`, then
  `coverage report -m`, with a codecov upload on the 3.13 leg.

Because the pytest step runs the full suite, it also executes the
integration tests, the fixture-integrity tests, and the
documentation-convention tests (including the `verify_public_api.py` /
`verify_test_coverage.py` wrapper tests) — no workflow edits are
needed to gate them.

### D.2 `.github/workflows/publish_to_pypi.yml`

Template file, UNCHANGED.

### D.3 `.github/workflows/publish_to_test_pypi.yml`

Template file, UNCHANGED.

---

## Appendix E — removed (no project-local check-script extensions)

The earlier draft extended `scripts/run-all-checks.sh` with four
project-local flags (`--american-english-check`, `--double-space-check`,
`--docstring-conventions`, `--pragma-budget`) plus a
`tests/unit/test_run_all_checks_script.py` verifier. Per the
template-first ground rule (§0.0) those extensions are REMOVED. The
template script is kept as committed; the only permitted change is the
`ENABLE_BANDIT=false` / `ENABLE_VULTURE=true` default toggles (§0.1).
The four checks live on as ordinary unit tests in
`tests/unit/test_documentation_conventions.py` (Phase 12), so they
still gate CI through the template's standard pytest step.

## Appendix F — `scripts/verify_public_api.py`

Phase 12 / 13 / 14 require this script. It compares the public-name
surface of every submodule with the `__all__` of its parent package
and with the `automodule` directives in `docs/module.rst`.

```python
"""Verify __all__ ↔ docs/module.rst correspondence.

For every public submodule of ``pds4indextools``:
  1. Collect names defined at module scope that do NOT start with ``_``.
  2. Compare against the module's ``__all__`` (if present).
  3. Compare against ``:members:`` content rendered from
     ``docs/module.rst``.
Exit 0 if every set is consistent; exit 1 with a list of mismatches
otherwise.

Run:
    python scripts/verify_public_api.py
"""

import importlib
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Modules to audit. Updated when phases add new submodules.
SUBMODULES = (
    'pds4indextools',
    'pds4indextools.config',
    'pds4indextools.csv_writer',
    'pds4indextools.errors',
    'pds4indextools.label_writer',
    'pds4indextools.schema_types',
    'pds4indextools.scraper',
    'pds4indextools.xpath_norm',
    'pds4indextools.cli',
)


def public_names(mod: object) -> set[str]:
    """Return the set of public names DEFINED in mod (not imported ones).

    ``dir()`` also surfaces names imported into the module (e.g. ``Path``,
    ``BaseModel``, or symbols re-exported by the package ``__init__``). Those
    are not part of THIS module's own public surface, so a name is kept only
    when it is defined here: a class/function whose ``__module__`` equals this
    module, or a module-level constant that carries no ``__module__`` (ints,
    frozensets, typing aliases). Imported classes/functions (``__module__``
    set to another module) are excluded.
    """
    modname = mod.__name__
    out: set[str] = set()
    for name in dir(mod):
        if name.startswith('_'):
            continue
        attr = inspect.getattr_static(mod, name)
        if inspect.ismodule(attr):
            # imported submodules are not part of this module's public surface
            continue
        owner = getattr(attr, '__module__', None)
        if owner is not None and owner != modname:
            # imported from another module; not this module's own definition
            continue
        out.add(name)
    return out


def declared_all(mod: object) -> set[str] | None:
    """Return ``set(mod.__all__)`` if defined, else ``None``."""
    all_ = getattr(mod, '__all__', None)
    if all_ is None:
        return None
    return set(all_)


_AUTOMODULE_RE = re.compile(
    r'^\.\.\s*automodule::\s*(?P<mod>[\w\.]+)\s*$', re.MULTILINE,
)


def documented_modules() -> set[str]:
    """Return the set of modules referenced via .. automodule:: in docs/module.rst."""
    text = (ROOT / 'docs' / 'module.rst').read_text(encoding='utf-8')
    return set(_AUTOMODULE_RE.findall(text))


def main() -> int:
    """Run the cross-check; report and return non-zero on mismatches."""
    failures: list[str] = []
    documented = documented_modules()
    for modname in SUBMODULES:
        try:
            mod = importlib.import_module(modname)
        except ImportError as e:
            failures.append(f'{modname}: ImportError {e}')
            continue
        public = public_names(mod)
        all_set = declared_all(mod)
        if all_set is None:
            failures.append(f'{modname}: __all__ is not defined')
        else:
            unexpected = public - all_set
            missing = {name for name in all_set if not hasattr(mod, name)}
            if unexpected:
                failures.append(
                    f'{modname}: public names not in __all__: {sorted(unexpected)}',
                )
            if missing:
                failures.append(
                    f'{modname}: __all__ names not present on module: {sorted(missing)}',
                )
        if modname not in documented:
            failures.append(f'{modname}: missing .. automodule:: in docs/module.rst')
    if failures:
        sys.stderr.write('Public-API drift detected:\n')
        for f in failures:
            sys.stderr.write(f'  {f}\n')
        return 1
    sys.stdout.write(f'OK: {len(SUBMODULES)} modules audited.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

## Appendix G — 22 XSD-resolution XPath queries

The `SchemaTypeResolver.resolve(xpath_leaf_tag)` method runs the
following 22 XPath queries in order against every registered XSD tree
and returns the first non-empty result. The first 11 queries handle
common cases; queries 12-22 cover the `_WO_Units` fallback chain and
deeply nested simpleContent/extension patterns. Query template variables:
`{tag}` is the leaf local-name; `{ns}` is the namespace prefix `pds:`.

```text
01.  .//xs:complexType[@name='{tag}']//xs:extension/@base
02.  .//*[local-name()='element' and @name='{tag}']/descendant::*[local-name()='restriction']/@base
03.  .//*[local-name()='attribute' and @name='{tag}']/descendant::*[local-name()='restriction']/@base
04.  .//*[local-name()='simpleType' and @name='{tag}']/*[local-name()='restriction']/@base
05.  .//*[local-name()='simpleType' and @name='{tag}']/descendant::*[local-name()='restriction']/@base
06.  .//*[local-name()='complexType' and @name='{tag}']/*[local-name()='extension']/@base
07.  .//*[local-name()='complexType' and @name='{tag}']/*/*[local-name()='extension']/@base
08.  .//*[local-name()='complexType' and @name='{tag}']/*/*/*[local-name()='extension']/@base
09.  .//*[local-name()='complexType' and @name='{tag}']/*/*/*/*[local-name()='extension']/@base
10.  .//*[local-name()='complexType' and @name='{tag}']//*[local-name()='extension']/*/@nilReason
11.  .//*[local-name()='complexType' and @name='Science_Facets']//*[local-name()='element' and @name='{tag}']/@type
12.  .//xs:complexType[@name='{tag}']//xs:extension[@base='{ns}{tag}_WO_Units']/xs:attribute[@name='unit']/@type
13.  .//*[local-name()='complexType' and @name='{tag}']/*[local-name()='simpleContent']/*[local-name()='extension']/@base
14.  .//*[local-name()='complexType' and @name='{tag}']/*/*[local-name()='simpleContent']/*[local-name()='extension']/@base
15.  .//*[local-name()='complexType' and @name='{tag}']/*/*/*[local-name()='simpleContent']/*[local-name()='extension']/@base
16.  .//*[local-name()='complexType' and @name='{tag}']/*/*/*/*[local-name()='simpleContent']/*[local-name()='extension']/@base
17.  .//*[local-name()='complexType' and @name='{tag}']/descendant::*[local-name()='simpleContent']/*[local-name()='extension']/@base
18.  .//*[local-name()='element' and @name='{tag}']/*[local-name()='complexType']/*[local-name()='simpleContent']/*[local-name()='extension']/@base
19.  .//*[local-name()='element' and @name='{tag}']/*[local-name()='simpleType']/*[local-name()='restriction']/@base
20.  .//*[local-name()='attribute' and @name='{tag}']/*[local-name()='simpleType']/*[local-name()='restriction']/@base
21.  .//*[local-name()='attribute' and @name='{tag}']/@type
22.  .//*[local-name()='element' and @name='{tag}']/@type
```

Resolution returns the raw XPath result (e.g., `'pds:ASCII_LID'`); the
namespace prefix is stripped only at label-write time per spec §11.3.
If all 22 queries return empty across all registered XSD trees,
`SchemaTypeResolver.resolve` raises
`SchemaResolutionError(f"no PDS4 base type for {tag}")`.

The 22 query strings are DATA (a module-level tuple); the resolver
loop is exercised by the seed-XSD tests in Phase 6 (basic, units, geom,
rings seeds). NO per-query fixture set exists: several slots (e.g. 10,
11) are not independently constructible as "first non-empty" without
contrived schemas, and exhaustive per-slot fixtures would add no
behavioral coverage beyond the loop-plus-seed tests.

## Appendix H — Public-API dataclass definitions (Phase 10 §10.1)

These six dataclasses are part of the public `__all__`. Each is
`@dataclass(frozen=True, slots=True, kw_only=True)`. Field types match
the spec §20.1 sketch but are concretized here.

```python
from dataclasses import dataclass
from pathlib import Path


from collections.abc import Callable


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateIndexFileArgs:
    """Programmatic argument bundle for ``run_generate_index_file``.

    Mirrors the CLI of ``pds4_create_xml_index generate_index_file``.
    """

    bundle_root: Path
    patterns: tuple[str, ...]
    config_files: tuple[Path, ...] = ()
    label_template: Path | None = None
    output_file: Path | None = None
    fail_slow: bool = False
    verbosity: int = 0  # 0=WARNING, 1=INFO, 2=DEBUG, 3=DEBUG (clamped)
    # Hook invoked AFTER the CSV is atomically renamed to its final path
    # AND BEFORE label_writer.build_substitution_dict runs. Used by the
    # golden-bytes generator (Appendix I.1) to freeze the CSV mtime so
    # $FILE_ZULU(...)$ renders a deterministic timestamp. Not part of
    # the CLI surface; CLI users pass None implicitly.
    csv_post_write_hook: Callable[[Path], None] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateIndexFileResult:
    """Result of a successful ``run_generate_index_file`` call."""

    csv_path: Path
    label_path: Path
    rows_written: int
    columns_written: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateXpathListArgs:
    """Programmatic argument bundle for ``run_generate_xpath_list``."""

    bundle_root: Path
    patterns: tuple[str, ...]
    config_files: tuple[Path, ...] = ()
    output_file: Path | None = None
    fail_slow: bool = False
    verbosity: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateXpathListResult:
    """Result of a successful ``run_generate_xpath_list`` call."""

    output_path: Path
    xpath_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class CopyDefaultConfigArgs:
    """Programmatic argument bundle for ``run_copy_default_config``."""

    output_file: Path
    force: bool = False
    verbosity: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class CopyDefaultConfigResult:
    """Result of a successful ``run_copy_default_config`` call."""

    output_path: Path
    warnings: tuple[str, ...] = ()
```

## Appendix I — Golden-bytes generation procedure

Several integration tests assert byte-identical match against
committed `tests/data/expected/<bundle>/index.{csv,lblx}` files. The
following procedure is binding for producing those committed bytes:

1. **Dependency pinning** (Phase 0 `pyproject.toml`):
   `rms-pdstemplate>=2.4` (2.4.0 verified against
   `/seti/all_repos/rms-pdstemplate`) so byte output does not drift
   under a major version bump. Lxml, requests, and pyyaml retain `>=`
   floors.
2. **Generator script**: `scripts/generate_expected_outputs.py`
   (committed to the repo). The script:
   1. Decorates with `@freeze_time('2026-05-14T00:00:00Z')` (uses
      freezegun).
   2. Sets `os.environ['TZ'] = 'UTC'`.
   3. After writing the CSV but BEFORE invoking `write_label`, calls
      `os.utime(csv_path, (1778716800, 1778716800))` (the POSIX
      timestamp for 2026-05-14T00:00:00Z) — this fixes
      `$FILE_ZULU(index_file_name)$` and `$FILE_MD5(...)$` (the MD5
      depends only on byte content, which is also deterministic).
   4. For each bundle with an `expected/` directory, invokes
      `run_generate_index_file(...)` with the same args the integration
      test will use.
   5. Writes the resulting `index.csv` and `index.lblx` into the
      `tests/data/expected/<bundle>/` directory.
3. **Verification at integration-test time**: integration tests apply
   the same `@freeze_time` decorator AND the same `os.utime` patch
   (encapsulated in the `frozen_csv_mtime` fixture in
   `tests/conftest.py`, Appendix A.6). The comparison is bytes via
   `Path.read_bytes()` equality. If the comparison fails, the failure
   is a regression — the implementer does NOT regenerate the expected
   bytes from a failing test; they fix the regression.
4. **First commit**: Phase 11 deliverable. The first run of
   `scripts/generate_expected_outputs.py` is performed once during
   Phase 11; its output is committed verbatim to
   `tests/data/expected/<bundle>/`. The bytes ARE the golden bytes
   from that point on.
5. **Drift check**: every golden-comparison integration test compares
   the pipeline's live output against the committed bytes on every
   pytest run (locally and in the template's CI pytest step). Any
   drift fails a test; the fix is a code fix, never a silent
   regeneration. (No dedicated CI drift step exists — §0.0 forbids new
   workflows, and the byte-comparison tests already cover it.)

The generator script's source code is in [Appendix I.1](#i1-scriptsgenerate_expected_outputspy).

### I.1 `scripts/generate_expected_outputs.py`

```python
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
    ('repeated_tags',         'repeated_tags',   'repeated_tags.yaml'),
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
```

The `csv_post_write_hook` field of
:class:`~pds4indextools.GenerateIndexFileArgs` (Appendix H) is the
binding extension point. The runner contract is: after the CSV is
atomically renamed to its final path AND before
`label_writer.build_substitution_dict` runs, the runner calls
`args.csv_post_write_hook(csv_final_path)` if it is not None. This lets
the generator inject `os.utime` so `$FILE_ZULU(index_file_name)$`
renders the frozen timestamp embedded in `_FROZEN_MTIME_EPOCH`. No
private wiring is duplicated.

> End of plan.

