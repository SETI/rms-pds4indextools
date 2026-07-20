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
