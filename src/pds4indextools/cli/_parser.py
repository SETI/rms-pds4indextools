"""Argparse parser construction for the ``pds4_create_xml_index`` CLI.

Builds the top-level parser and the three subcommand parsers with their
underscored/hyphenated aliases (R-CLI-002), the shared discovery options,
and the multi-paragraph example epilogs (R-CLI-040). Parsing itself,
dispatch, and exit-code mapping live in :mod:`pds4indextools.cli._dispatch`.

Implements spec section 3 (R-CLI-001..R-CLI-041).
"""

import argparse
from pathlib import Path

from pds4indextools._version import __version__

__all__ = [
    '_build_parser',
    '_normalize_subcommand',
]

_PROG = 'pds4_create_xml_index'

_TOP_EPILOG = (
    'Examples:\n'
    '  pds4_create_xml_index generate_index_file --bundle-root ./bundle '
    "'**/*.lblx'\n"
    '  pds4_create_xml_index generate_xpath_list --bundle-root ./bundle '
    "'**/*.lblx'\n"
    '  pds4_create_xml_index copy_default_config --output-file ./config.yaml\n'
)

_INDEX_EPILOG = (
    'Examples:\n'
    '  pds4_create_xml_index generate_index_file --bundle-root ./bundle '
    "'**/*.lblx'\n"
    '  pds4_create_xml_index generate_index_file --bundle-root ./bundle '
    "--config-file cols.yaml --output-file index.csv 'data/*.lblx'\n"
)

_XPATH_EPILOG = (
    'Examples:\n'
    '  pds4_create_xml_index generate_xpath_list --bundle-root ./bundle '
    "'**/*.lblx'\n"
    '  pds4_create_xml_index generate_xpath_list --bundle-root ./bundle '
    "--output-file columns.yaml 'data/*.lblx'\n"
)

_COPY_EPILOG = (
    'Examples:\n'
    '  pds4_create_xml_index copy_default_config --output-file ./config.yaml\n'
    '  pds4_create_xml_index copy_default_config --output-file ./config.yaml '
    '--force\n'
)


def _normalize_subcommand(name: str) -> str:
    """Map a hyphenated subcommand alias to its underscored canonical form.

    Parameters:
        name: The subcommand name as parsed from the command line, in either
            hyphenated (``generate-index-file``) or underscored form.

    Returns:
        The underscored canonical name (``generate_index_file``).

    Implements R-CLI-002.
    """
    return name.replace('-', '_')


def _add_discovery_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the bundle/pattern/config/fail-slow/verbosity options shared by
    the two scraping subcommands (R-CLI-010..R-CLI-017).

    Parameters:
        parser: The subparser to populate.
    """
    parser.add_argument(
        '--bundle-root',
        dest='bundle_root',
        required=True,
        type=Path,
        metavar='PATH',
        help='Bundle root directory (or a symlink to one); required.',
    )
    parser.add_argument(
        '--config-file',
        dest='config_file',
        action='append',
        default=None,
        type=Path,
        metavar='PATH',
        help='Config YAML overlaid on the default; may be given many times.',
    )
    parser.add_argument(
        '--output-file',
        dest='output_file',
        default=None,
        type=Path,
        metavar='PATH',
        help='Output file path; defaults are auto-numbered when in use.',
    )
    parser.add_argument(
        '--fail-slow',
        dest='fail_slow',
        action='store_true',
        help='Accumulate per-label errors instead of stopping at the first.',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        dest='verbose',
        action='count',
        default=0,
        help='Increase logging verbosity (-v INFO, -vv/-vvv DEBUG).',
    )
    parser.add_argument(
        'patterns',
        nargs='+',
        metavar='PATTERN',
        help='One or more globs relative to --bundle-root.',
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with its three subcommand parsers.

    The parser is constructed with an explicit ``prog`` so in-process tests do
    not inherit pytest's ``argv[0]`` in help and usage text. Each scraping
    subcommand accepts underscored and hyphenated aliases (R-CLI-002), a
    required ``--bundle-root``, one or more positional patterns, repeatable
    ``--config-file`` options (``action='append'`` with ``default=None`` to
    avoid a shared mutable default across re-entrant calls), and example
    epilogs (R-CLI-040).

    Returns:
        The configured :class:`argparse.ArgumentParser`.

    Implements R-CLI-002, R-CLI-003, R-CLI-010..R-CLI-032, and R-CLI-040.
    """
    parser = argparse.ArgumentParser(
        prog=_PROG,
        description='Generate PDS4 index files and labels from PDS4 XML labels.',
        epilog=_TOP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'{_PROG} {__version__}',
        help='Print the version and exit.',
    )
    subparsers = parser.add_subparsers(dest='subcommand', metavar='SUBCOMMAND')

    index_parser = subparsers.add_parser(
        'generate_index_file',
        aliases=['generate-index-file'],
        help='Scrape labels and write an index CSV plus its PDS4 label.',
        description='Scrape labels and write an index CSV plus its PDS4 label.',
        epilog=_INDEX_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_discovery_arguments(index_parser)
    index_parser.add_argument(
        '--label-template',
        dest='label_template',
        default=None,
        type=Path,
        metavar='PATH',
        help='Custom label template; defaults to the packaged template.',
    )

    xpath_parser = subparsers.add_parser(
        'generate_xpath_list',
        aliases=['generate-xpath-list'],
        help='Scrape labels and write a starter columns YAML block.',
        description='Scrape labels and write a starter columns YAML block.',
        epilog=_XPATH_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_discovery_arguments(xpath_parser)

    copy_parser = subparsers.add_parser(
        'copy_default_config',
        aliases=['copy-default-config'],
        help='Write a copy of the packaged default configuration.',
        description='Write a copy of the packaged default configuration.',
        epilog=_COPY_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    copy_parser.add_argument(
        '--output-file',
        dest='output_file',
        required=True,
        type=Path,
        metavar='PATH',
        help='Destination path for the copied config; required.',
    )
    copy_parser.add_argument(
        '--force',
        dest='force',
        action='store_true',
        help='Overwrite the destination if it already exists.',
    )
    copy_parser.add_argument(
        '-v',
        '--verbose',
        dest='verbose',
        action='count',
        default=0,
        help='Increase logging verbosity (-v INFO, -vv/-vvv DEBUG).',
    )

    return parser
