"""Output-path resolution for the index and xpath-list subcommands.

Implements the binding extension table plus default auto-numbering of
R-CLI-015, R-CLI-022, and R-OUT-010..R-OUT-013. Each resolver returns
absolute paths and any warning strings the caller must both log and record
on the result dataclass.

Implements R-CLI-015, R-CLI-022, and R-OUT-010..R-OUT-013.
"""

from pathlib import Path

__all__ = [
    '_resolve_output_paths',
    '_resolve_xpath_list_output_path',
]

_INDEX_DEFAULT_STEM = 'index'
_XPATH_DEFAULT_STEM = 'columns'


def _explicit_index_paths(output_file: Path) -> tuple[Path, Path]:
    """Apply the R-OUT-010..R-OUT-012 extension table to an explicit output.

    Parameters:
        output_file: The user-supplied ``--output-file`` value.

    Returns:
        The ``(data_path, label_path)`` pair. The label always ends in
        ``.lblx`` on the data-file stem; the data file keeps ``.csv``, keeps
        any non-``.lblx`` extension verbatim, or gains ``.csv`` when the stem
        has no extension (R-OUT-010, R-OUT-011, R-OUT-012).
    """
    suffix = output_file.suffix
    if suffix == '.csv':
        return output_file, output_file.with_suffix('.lblx')
    if suffix == '.lblx':
        return output_file.with_suffix('.csv'), output_file
    if suffix == '':
        return output_file.with_suffix('.csv'), output_file.with_suffix('.lblx')
    return output_file, output_file.with_suffix('.lblx')


def _lowest_free_paired_stem(directory: Path, base: str) -> tuple[Path, Path, str | None]:
    """Return the base or lowest-numbered free ``(csv, lblx)`` pair.

    Parameters:
        directory: The directory the default output is written to.
        base: The base stem (``index``).

    Returns:
        A ``(csv_path, label_path, warning)`` triple. ``warning`` is ``None``
        when the base stem is free and a message naming the numbered paths
        otherwise (R-CLI-015).
    """
    csv_path = directory / f'{base}.csv'
    label_path = directory / f'{base}.lblx'
    if not csv_path.exists() and not label_path.exists():
        return csv_path, label_path, None
    number = 1
    while True:
        csv_candidate = directory / f'{base}_{number}.csv'
        label_candidate = directory / f'{base}_{number}.lblx'
        if not csv_candidate.exists() and not label_candidate.exists():
            warning = (
                f'default output name in use; writing to {csv_candidate.resolve()} '
                f'and {label_candidate.resolve()} instead'
            )
            return csv_candidate, label_candidate, warning
        number += 1


def _resolve_output_paths(output_file: Path | None) -> tuple[Path, Path, tuple[str, ...]]:
    """Resolve the CSV and label output paths for ``generate_index_file``.

    Parameters:
        output_file: The user-supplied ``--output-file`` value, or ``None``
            for the auto-numbered ``./index.csv`` default (R-CLI-015).

    Returns:
        An ``(csv_path, label_path, warnings)`` triple with absolute paths.
        ``warnings`` carries one message when the default name was
        auto-numbered or when an explicit target is being overwritten
        (R-OUT-013), else it is empty.

    Implements R-CLI-015 and R-OUT-010..R-OUT-013.
    """
    warnings: tuple[str, ...] = ()
    if output_file is None:
        csv_path, label_path, warning = _lowest_free_paired_stem(Path.cwd(), _INDEX_DEFAULT_STEM)
        if warning is not None:
            warnings = (warning,)
        return csv_path.resolve(), label_path.resolve(), warnings

    csv_path, label_path = _explicit_index_paths(output_file)
    csv_path = csv_path.resolve()
    label_path = label_path.resolve()
    if csv_path.exists() or label_path.exists():
        warnings = (f'overwriting existing output: {csv_path} and {label_path}',)
    return csv_path, label_path, warnings


def _resolve_xpath_list_output_path(output_file: Path | None) -> tuple[Path, tuple[str, ...]]:
    """Resolve the YAML output path for ``generate_xpath_list``.

    Parameters:
        output_file: The user-supplied ``--output-file`` value, or ``None``
            for the auto-numbered ``./columns.yaml`` default (R-CLI-022).

    Returns:
        An ``(output_path, warnings)`` pair with an absolute path. ``warnings``
        carries one message when the default name was auto-numbered or when an
        explicit target is being overwritten, else it is empty.

    Implements R-CLI-022.
    """
    if output_file is None:
        directory = Path.cwd()
        default_path = directory / f'{_XPATH_DEFAULT_STEM}.yaml'
        if not default_path.exists():
            return default_path.resolve(), ()
        number = 1
        while True:
            candidate = directory / f'{_XPATH_DEFAULT_STEM}_{number}.yaml'
            if not candidate.exists():
                candidate = candidate.resolve()
                warning = f'default output name in use; writing to {candidate} instead'
                return candidate, (warning,)
            number += 1

    path = output_file.with_suffix('.yaml') if output_file.suffix == '' else output_file
    path = path.resolve()
    warnings: tuple[str, ...] = ()
    if path.exists():
        warnings = (f'overwriting existing output: {path}',)
    return path, warnings
