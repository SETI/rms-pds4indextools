"""Command-line and programmatic interface for pds4indextools.

Re-exports the top-level entry points (:func:`main`, :func:`cli_entrypoint`),
the three ``run_*`` functions, and the six public argument/result dataclasses.
Everything else in the package is private (underscore-prefixed) and split
across ``_args``, ``_parser``, ``_dispatch``, ``_paths``, and ``_runners`` to
keep each module small and free of import cycles.

Implements spec section 3 (R-CLI-*), section 5, section 6, and section 20
(R-API-*).
"""

from pds4indextools.cli._args import (
    CopyDefaultConfigArgs,
    CopyDefaultConfigResult,
    GenerateIndexFileArgs,
    GenerateIndexFileResult,
    GenerateXpathListArgs,
    GenerateXpathListResult,
)
from pds4indextools.cli._dispatch import cli_entrypoint, main
from pds4indextools.cli._runners import (
    run_copy_default_config,
    run_generate_index_file,
    run_generate_xpath_list,
)

__all__ = [
    'CopyDefaultConfigArgs',
    'CopyDefaultConfigResult',
    'GenerateIndexFileArgs',
    'GenerateIndexFileResult',
    'GenerateXpathListArgs',
    'GenerateXpathListResult',
    'cli_entrypoint',
    'main',
    'run_copy_default_config',
    'run_generate_index_file',
    'run_generate_xpath_list',
]
