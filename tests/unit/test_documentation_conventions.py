"""Documentation-convention tests (Phase 12, spec section 12.1).

These tests enforce the documentation contract: the public API surface is
mirrored in ``docs/module.rst``; docstrings use ``Parameters:`` rather than
``Args:``; every public class is documented; prose is American English with a
single space after each sentence; the coverage-pragma budget holds; and the
two verification scripts pass through the ordinary pytest run.

Implements R-DOC-010 and the section 12.1/12.2 documentation invariants.
"""

import importlib
import importlib.util
import inspect
import re
from collections.abc import Callable
from pathlib import Path
from typing import cast, get_type_hints

import pytest

import pds4indextools

_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _ROOT / 'src' / 'pds4indextools'
_DOCS = _ROOT / 'docs'
_MODULE_RST_TEXT = (_DOCS / 'module.rst').read_text(encoding='utf-8')

# The public submodules re-exported through the package root.
_PUBLIC_SUBMODULES = (
    'pds4indextools.config',
    'pds4indextools.csv_writer',
    'pds4indextools.errors',
    'pds4indextools.label_writer',
    'pds4indextools.schema_types',
    'pds4indextools.scraper',
    'pds4indextools.xpath_norm',
    'pds4indextools.cli',
)

_BRITISH_RE = re.compile(
    r'\b(colour|behaviour|optimise|organis(e|ing|ation)|licence|analyse|'
    r'favour|labelled|cancelled|catalogue|programme|whilst)\b'
)
_DOUBLE_SPACE_RE = re.compile(r'\.  [A-Za-z]')
_ARGS_HEADING_RE = re.compile(r'^\s*Args:')
_AUTOMODULE_RE = re.compile(r'^\.\.\s*automodule::\s*(\S+)\s*$', re.MULTILINE)


def _src_py_files() -> list[Path]:
    """Return every Python source file under the package."""
    return sorted(_SRC.rglob('*.py'))


def _prose_files() -> list[Path]:
    """Return the source, docs, and top-level Markdown files carrying prose."""
    files: list[Path] = list(_src_py_files())
    files += sorted(p for p in _DOCS.rglob('*.rst') if '_build' not in p.parts)
    files += sorted(p for p in _DOCS.rglob('*.md') if '_build' not in p.parts)
    files += [_ROOT / 'README.md', _ROOT / 'CONTRIBUTING.md']
    return files


def _public_classes() -> list[type]:
    """Return every class named in the package ``__all__``."""
    classes: list[type] = []
    for name in pds4indextools.__all__:
        obj = getattr(pds4indextools, name)
        if inspect.isclass(obj):
            classes.append(obj)
    return classes


def _public_callables() -> list[str]:
    """Return the ``__all__`` names bound to a public function or class."""
    names: list[str] = []
    for name in pds4indextools.__all__:
        obj = getattr(pds4indextools, name)
        if inspect.isclass(obj) or inspect.isfunction(obj):
            names.append(name)
    return sorted(names)


def _public_functions() -> list[str]:
    """Return the ``__all__`` names bound to a module-level public function."""
    return sorted(
        name for name in pds4indextools.__all__ if inspect.isfunction(getattr(pds4indextools, name))
    )


def _documented_objects() -> list[object]:
    """Return the package, its public symbols, and their in-package members."""
    objects: list[object] = [pds4indextools]
    seen: set[int] = {id(pds4indextools)}
    for name in pds4indextools.__all__:
        obj = getattr(pds4indextools, name)
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        objects.append(obj)
        if inspect.isclass(obj):
            for _, member in inspect.getmembers(obj):
                origin = getattr(member, '__module__', None)
                if (
                    isinstance(origin, str)
                    and origin.startswith('pds4indextools')
                    and id(member) not in seen
                ):
                    seen.add(id(member))
                    objects.append(member)
    return objects


@pytest.mark.parametrize('name', sorted(pds4indextools.__all__))
def test_every_public_name_in_root_all_appears_in_module_rst(name: str) -> None:
    """Every ``__all__`` name is documented in ``docs/module.rst`` (R-DOC-010)."""
    assert name in _MODULE_RST_TEXT, f'{name!r} is missing from docs/module.rst'


@pytest.mark.parametrize('modname', _PUBLIC_SUBMODULES)
def test_every_submodule_all_subset_of_root_all(modname: str) -> None:
    """Each public submodule's ``__all__`` is a subset of the root ``__all__``."""
    module = importlib.import_module(modname)
    submodule_all = set(getattr(module, '__all__', ()))
    root_all = set(pds4indextools.__all__)
    extra = submodule_all - root_all
    assert extra == set(), f'{modname}: names not re-exported at the root: {sorted(extra)}'


def test_module_rst_no_duplicate_automodule_directives() -> None:
    """No ``.. automodule::`` target appears more than once in ``module.rst``."""
    targets = _AUTOMODULE_RE.findall(_MODULE_RST_TEXT)
    duplicates = sorted({t for t in targets if targets.count(t) > 1})
    assert duplicates == [], f'duplicate automodule directives: {duplicates}'


def test_no_args_section_in_any_docstring() -> None:
    """No public docstring uses an ``Args:`` heading instead of ``Parameters:``."""
    offenders: list[str] = []
    for obj in _documented_objects():
        doc = inspect.getdoc(obj)
        if doc is not None and 'Args:' in doc:
            offenders.append(getattr(obj, '__name__', repr(obj)))
    assert offenders == [], f'docstrings using Args: {offenders}'


@pytest.mark.parametrize('cls', _public_classes(), ids=lambda c: c.__name__)
def test_every_public_class_has_docstring(cls: type) -> None:
    """Every public class carries a non-empty docstring (R-DOC-010)."""
    doc = inspect.getdoc(cls)
    assert doc is not None, f'{cls.__name__} has no docstring'
    assert doc.strip() != '', f'{cls.__name__} has an empty docstring'


def test_no_args_heading_in_source_docstrings() -> None:
    """No source file contains an ``Args:`` docstring heading (documentation.mdc)."""
    offenders: list[str] = []
    for path in _src_py_files():
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if _ARGS_HEADING_RE.match(line):
                offenders.append(f'{path.relative_to(_ROOT)}:{lineno}')
    assert offenders == [], f'Args: headings found: {offenders}'


def test_no_british_spellings_in_prose() -> None:
    """No prose file uses a British spelling (documentation.mdc section 2)."""
    offenders: list[str] = []
    for path in _prose_files():
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if _BRITISH_RE.search(line):
                offenders.append(f'{path.relative_to(_ROOT)}:{lineno}: {line.strip()}')
    assert offenders == [], f'British spellings found: {offenders}'


def test_single_space_after_period() -> None:
    """No prose file puts two spaces after a sentence period (documentation.mdc)."""
    offenders: list[str] = []
    for path in _prose_files():
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if _DOUBLE_SPACE_RE.search(line):
                offenders.append(f'{path.relative_to(_ROOT)}:{lineno}: {line.strip()}')
    assert offenders == [], f'double spaces after period found: {offenders}'


def test_pragma_no_cover_budget() -> None:
    """The total ``# pragma: no cover`` count stays within the Phase 14 budget."""
    count = 0
    for path in _src_py_files():
        count += path.read_text(encoding='utf-8').count('# pragma: no cover')
    assert count <= 5, f'pragma: no cover budget exceeded: {count} > 5'


@pytest.mark.parametrize('name', _public_callables())
def test_every_public_callable_has_docstring(name: str) -> None:
    """R-API-001: every public function or class in ``__all__`` has a docstring."""
    obj = getattr(pds4indextools, name)
    doc = inspect.getdoc(obj)
    assert doc is not None, f'{name} has no docstring'
    assert doc.strip() != '', f'{name} has an empty docstring'


@pytest.mark.parametrize('name', _public_functions())
def test_every_public_function_is_fully_type_annotated(name: str) -> None:
    """R-API-002: every public function in ``__all__`` is fully type-annotated."""
    func = getattr(pds4indextools, name)
    signature = inspect.signature(func)
    for parameter in signature.parameters.values():
        if parameter.name in ('self', 'cls'):
            continue
        assert parameter.annotation is not inspect.Parameter.empty, (
            f'{name}: parameter {parameter.name!r} is not annotated'
        )
    assert signature.return_annotation is not inspect.Signature.empty, (
        f'{name}: return value is not annotated'
    )


@pytest.mark.parametrize('cls', _public_classes(), ids=lambda c: c.__name__)
def test_every_public_class_annotations_resolve(cls: type) -> None:
    """R-API-002: a public class's field annotations are complete and resolvable."""
    # ``get_type_hints`` raises if any annotation is a broken or unresolvable
    # forward reference, so a clean return proves the class's annotations are
    # well-formed (error classes simply carry no fields and return ``{}``).
    get_type_hints(cls)


def _load_script_main(script_name: str) -> Callable[[], int]:
    """Import a ``scripts/`` module by path and return its ``main`` callable."""
    script_path = _ROOT / 'scripts' / script_name
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast('Callable[[], int]', module.main)


def test_verify_public_api_script_passes() -> None:
    """``scripts/verify_public_api.py`` exits 0 (public API is in sync)."""
    main = _load_script_main('verify_public_api.py')
    assert main() == 0


def test_verify_test_coverage_script_passes() -> None:
    """``scripts/verify_test_coverage.py`` exits 0 (every R-ID is covered)."""
    main = _load_script_main('verify_test_coverage.py')
    assert main() == 0
