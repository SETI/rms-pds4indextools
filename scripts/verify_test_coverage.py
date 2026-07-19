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


R_ID_RE = re.compile(r'R-[A-Z]+-\d{3}')
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
