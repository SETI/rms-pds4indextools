"""Top-level CLI entry, dispatch, and exception-to-exit-code mapping.

:func:`main` parses argv, configures logging, dispatches to a ``run_*``
function, and maps any error to an exit code without ever calling
``sys.exit`` (the library/CLI boundary). Only :func:`cli_entrypoint` and the
``__main__`` guard call ``sys.exit``.

Implements spec section 3 (R-CLI-003/005), section 17 (R-ERR-002,
R-FSLOW-120), and R-LOG-010.
"""

import argparse
import sys
from typing import NoReturn

from pds4indextools._logging import module_logger, setup_logging
from pds4indextools.cli._args import (
    CopyDefaultConfigArgs,
    GenerateIndexFileArgs,
    GenerateXpathListArgs,
)
from pds4indextools.cli._parser import _build_parser, _normalize_subcommand
from pds4indextools.cli._runners import (
    run_copy_default_config,
    run_generate_index_file,
    run_generate_xpath_list,
)
from pds4indextools.errors import (
    EXIT_INTERNAL_ERROR,
    EXIT_RUNTIME_ERROR,
    EXIT_SIGINT,
    EXIT_USER_ERROR,
    CliError,
    ConfigError,
    FailSlowAggregateError,
    LabelError,
    OutputError,
    Pds4IndexError,
    SchemaError,
)

__all__ = [
    'cli_entrypoint',
    'main',
]

_logger = module_logger('cli')

# Single source of truth mapping exception type to exit code. Order is
# significant: ``FailSlowAggregateError`` is matched before its ``LabelError``
# sub-errors, and the ``Pds4IndexError`` catch-all is matched last so more
# specific subclasses win. Tests parametrize over this tuple.
_EXCEPTION_TO_EXIT_CODE: tuple[tuple[type[BaseException], int], ...] = (
    (CliError, EXIT_USER_ERROR),
    (ConfigError, EXIT_USER_ERROR),
    (FailSlowAggregateError, EXIT_RUNTIME_ERROR),
    (SchemaError, EXIT_RUNTIME_ERROR),
    (LabelError, EXIT_RUNTIME_ERROR),
    (OutputError, EXIT_RUNTIME_ERROR),
    (Pds4IndexError, EXIT_INTERNAL_ERROR),
    (KeyboardInterrupt, EXIT_SIGINT),
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace | int:
    """Parse ``argv`` into a namespace, or return an int on an argparse exit.

    Argparse actions such as ``--version``, ``--help``, and parse errors raise
    ``SystemExit``; those are caught and returned as an integer so :func:`main`
    never calls ``sys.exit`` (R-CLI-003, R-CLI-005). A missing subcommand
    prints the top-level help to stderr and returns 2 (R-CLI-005).

    Parameters:
        argv: The argument vector, or ``None`` to use ``sys.argv[1:]``.

    Returns:
        The parsed :class:`argparse.Namespace`, or an integer exit code when
        argparse handled the invocation itself.
    """
    parser = _build_parser()
    try:
        namespace = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if namespace.subcommand is None:
        parser.print_help(sys.stderr)
        return 2
    return namespace


def _dispatch(namespace: argparse.Namespace) -> int:
    """Dispatch a parsed namespace to the matching ``run_*`` function.

    Parameters:
        namespace: The parsed argparse namespace with a resolved subcommand.

    Returns:
        ``0`` on success; the ``run_*`` function raises on failure.
    """
    subcommand = _normalize_subcommand(namespace.subcommand)
    if subcommand == 'generate_index_file':
        run_generate_index_file(
            GenerateIndexFileArgs(
                bundle_root=namespace.bundle_root,
                patterns=tuple(namespace.patterns),
                config_files=tuple(namespace.config_file or ()),
                label_template=namespace.label_template,
                output_file=namespace.output_file,
                fail_slow=namespace.fail_slow,
                verbosity=min(namespace.verbose, 3),
            )
        )
    elif subcommand == 'generate_xpath_list':
        run_generate_xpath_list(
            GenerateXpathListArgs(
                bundle_root=namespace.bundle_root,
                patterns=tuple(namespace.patterns),
                config_files=tuple(namespace.config_file or ()),
                output_file=namespace.output_file,
                fail_slow=namespace.fail_slow,
                verbosity=min(namespace.verbose, 3),
            )
        )
    else:
        run_copy_default_config(
            CopyDefaultConfigArgs(
                output_file=namespace.output_file,
                force=namespace.force,
                verbosity=min(namespace.verbose, 3),
            )
        )
    return 0


def _exit_code_for(exc: BaseException) -> int:
    """Return the pinned exit code for ``exc`` (R-API-004).

    Parameters:
        exc: The exception to classify.

    Returns:
        The first matching code in :data:`_EXCEPTION_TO_EXIT_CODE`, or
        ``EXIT_INTERNAL_ERROR`` when nothing matches.
    """
    for exc_type, code in _EXCEPTION_TO_EXIT_CODE:
        if isinstance(exc, exc_type):
            return code
    return EXIT_INTERNAL_ERROR


def _handle_exception(exc: BaseException) -> int:
    """Log ``exc`` appropriately and return its exit code.

    A :class:`KeyboardInterrupt` logs ``aborted by user``; a
    :class:`~pds4indextools.errors.Pds4IndexError` (including a
    ``FailSlowAggregateError`` whose ``__str__`` lists every sub-error, per
    R-FSLOW-120) logs its formatted message; anything else logs an
    ``unexpected error`` with a traceback so spec section 17.2's exit-3 path
    surfaces the cause on stderr.

    Parameters:
        exc: The exception raised during dispatch.

    Returns:
        The exit code from :func:`_exit_code_for`.
    """
    code = _exit_code_for(exc)
    if isinstance(exc, KeyboardInterrupt):
        _logger.error('aborted by user')
    elif isinstance(exc, Pds4IndexError):
        _logger.error('%s', exc)
    else:
        _logger.error('unexpected error: %s', exc, exc_info=True)
    return code


def main(argv: list[str] | None = None) -> int:
    """Parse argv, configure logging, dispatch, and return an exit code.

    Never calls ``sys.exit``: argparse-initiated exits are returned by
    the internal ``_parse_args`` helper, and dispatch errors are mapped to
    codes by the internal ``_handle_exception`` helper (the library/CLI
    boundary).

    Parameters:
        argv: The argument vector, or ``None`` to use ``sys.argv[1:]``.

    Returns:
        The process exit code in ``0..130``.

    Implements R-CLI-003, R-CLI-005, R-LOG-010, R-ERR-002, and R-FSLOW-120.
    """
    parsed = _parse_args(argv)
    if isinstance(parsed, int):
        return parsed
    setup_logging(min(parsed.verbose, 3))
    try:
        return _dispatch(parsed)
    except (KeyboardInterrupt, Exception) as exc:
        return _handle_exception(exc)


def cli_entrypoint() -> NoReturn:
    """Console-script wrapper: call :func:`main` and exit with its return code.

    This and the ``__main__`` guard are the only places in ``src`` that call
    ``sys.exit`` (R-CLI-001).
    """
    sys.exit(main())
