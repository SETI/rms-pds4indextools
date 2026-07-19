"""Public argument and result dataclasses for the ``run_*`` entry points.

These six frozen, keyword-only, slotted dataclasses form the programmatic
surface of the tool (spec section 20.1, Appendix H). Each ``run_*`` function
in :mod:`pds4indextools.cli._runners` consumes an ``*Args`` bundle and
returns the matching ``*Result``. They are re-exported from
:mod:`pds4indextools.cli` and, in turn, from :mod:`pds4indextools`.

Implements R-API-001, R-API-002, and R-API-003.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    'CopyDefaultConfigArgs',
    'CopyDefaultConfigResult',
    'GenerateIndexFileArgs',
    'GenerateIndexFileResult',
    'GenerateXpathListArgs',
    'GenerateXpathListResult',
]


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateIndexFileArgs:
    """Programmatic argument bundle for ``run_generate_index_file``.

    Mirrors the CLI of ``pds4_create_xml_index generate_index_file``.

    Parameters:
        bundle_root: The bundle root :class:`~pathlib.Path` to scrape.
        patterns: The relative glob patterns to discover labels with.
        config_files: The user config :class:`~pathlib.Path` chain, in
            increasing priority order.
        label_template: A custom label template :class:`~pathlib.Path`, or
            ``None`` to use the packaged default (R-LBL-001).
        output_file: The requested output :class:`~pathlib.Path`, or ``None``
            for the auto-numbered ``./index.csv`` default (R-CLI-015).
        fail_slow: ``True`` accumulates per-label errors instead of raising on
            the first (R-FSLOW-110).
        verbosity: The logging verbosity count in ``{0, 1, 2, 3}``.
        csv_post_write_hook: A callable invoked with the final CSV path after
            it is atomically renamed and before label generation, or ``None``.
            Used by the golden-bytes generator (Appendix I.1) to freeze the
            CSV mtime; CLI users pass ``None`` implicitly.

    Implements R-API-001 and R-API-002.
    """

    bundle_root: Path
    patterns: tuple[str, ...]
    config_files: tuple[Path, ...] = ()
    label_template: Path | None = None
    output_file: Path | None = None
    fail_slow: bool = False
    verbosity: int = 0
    csv_post_write_hook: Callable[[Path], None] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateIndexFileResult:
    """Result of a successful ``run_generate_index_file`` call.

    Parameters:
        csv_path: The absolute :class:`~pathlib.Path` of the written CSV.
        label_path: The absolute :class:`~pathlib.Path` of the written label.
        rows_written: The number of data rows written to the CSV.
        columns_written: The number of columns written to the CSV.
        warnings: The overwrite/auto-number warning messages emitted, if any.

    Implements R-API-003.
    """

    csv_path: Path
    label_path: Path
    rows_written: int
    columns_written: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateXpathListArgs:
    """Programmatic argument bundle for ``run_generate_xpath_list``.

    Parameters:
        bundle_root: The bundle root :class:`~pathlib.Path` to scrape.
        patterns: The relative glob patterns to discover labels with.
        config_files: The user config :class:`~pathlib.Path` chain, in
            increasing priority order.
        output_file: The requested output :class:`~pathlib.Path`, or ``None``
            for the auto-numbered ``./columns.yaml`` default (R-CLI-022).
        fail_slow: ``True`` accumulates per-label errors instead of raising on
            the first (R-FSLOW-110).
        verbosity: The logging verbosity count in ``{0, 1, 2, 3}``.

    Implements R-API-001 and R-API-002.
    """

    bundle_root: Path
    patterns: tuple[str, ...]
    config_files: tuple[Path, ...] = ()
    output_file: Path | None = None
    fail_slow: bool = False
    verbosity: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateXpathListResult:
    """Result of a successful ``run_generate_xpath_list`` call.

    Parameters:
        output_path: The absolute :class:`~pathlib.Path` of the written YAML.
        xpath_count: The number of distinct canonical XPaths emitted.
        warnings: The overwrite/auto-number warning messages emitted, if any.

    Implements R-API-003.
    """

    output_path: Path
    xpath_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class CopyDefaultConfigArgs:
    """Programmatic argument bundle for ``run_copy_default_config``.

    Parameters:
        output_file: The destination :class:`~pathlib.Path` for the config.
        force: ``True`` overwrites an existing destination (R-CLI-031).
        verbosity: The logging verbosity count in ``{0, 1, 2, 3}``.

    Implements R-API-001 and R-API-002.
    """

    output_file: Path
    force: bool = False
    verbosity: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class CopyDefaultConfigResult:
    """Result of a successful ``run_copy_default_config`` call.

    Parameters:
        output_path: The absolute :class:`~pathlib.Path` of the written file.
        warnings: The overwrite warning messages emitted, if any.

    Implements R-API-003.
    """

    output_path: Path
    warnings: tuple[str, ...] = ()
