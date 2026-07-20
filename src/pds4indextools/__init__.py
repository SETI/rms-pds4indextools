"""Tools for generating index files and PDS4 labels from PDS4 XML labels.

This package scrapes PDS4 XML labels into deterministic index CSV files and
their PDS4 labels, and exposes both a command-line interface
(``pds4_create_xml_index``) and a programmatic API. The public surface is the
union of every submodule's ``__all__`` plus :func:`module_logger`; only names
listed in ``__all__`` are supported (``python.mdc`` section 3).
"""

from pds4indextools._logging import library_setup, module_logger

# Attach the library NullHandler to the ``pds4indextools`` logger BEFORE any
# submodule is imported. ``label_writer`` calls PdsTemplate's ``set_logger``
# at import time, and PdsTemplate falls back to printing on stdout unless the
# target logger already has a handler; running ``library_setup`` first keeps
# that fallback from breaking the library/CLI output boundary (R-LBL-040).
library_setup()

from pds4indextools._version import __version__ as __version__  # noqa: E402
from pds4indextools.cli import (  # noqa: E402
    CopyDefaultConfigArgs,
    CopyDefaultConfigResult,
    GenerateIndexFileArgs,
    GenerateIndexFileResult,
    GenerateXpathListArgs,
    GenerateXpathListResult,
    cli_entrypoint,
    main,
    run_copy_default_config,
    run_generate_index_file,
    run_generate_xpath_list,
)
from pds4indextools.config import (  # noqa: E402
    AUTO_COLUMN_TOKENS,
    AbsolutePath,
    CitationInformation,
    ColumnSpec,
    IndexConfig,
    LabelContents,
    ModificationDetail,
    NillableEntry,
    OutputSection,
    load_config,
    parse_sort_key,
)
from pds4indextools.csv_writer import (  # noqa: E402
    ColumnStat,
    CsvWritePlan,
    build_plan,
    sort_rows,
    write_csv,
)
from pds4indextools.errors import (  # noqa: E402
    EXIT_INTERNAL_ERROR,
    EXIT_RUNTIME_ERROR,
    EXIT_SIGINT,
    EXIT_USER_ERROR,
    CliError,
    ConfigError,
    FailSlowAggregateError,
    LabelError,
    LidError,
    NilError,
    OutputError,
    ParseError,
    Pds4IndexError,
    SchemaCacheError,
    SchemaError,
    SchemaNetworkError,
    SchemaResolutionError,
    SchemaVersionError,
    ScrapedValueError,
    XPathError,
)
from pds4indextools.label_writer import (  # noqa: E402
    build_substitution_dict,
    load_packaged_template,
    normalize_modification_detail,
    write_label,
)
from pds4indextools.schema_types import (  # noqa: E402
    AUTO_COLUMN_TYPES,
    SchemaCache,
    SchemaTypeResolver,
)
from pds4indextools.scraper import ScrapeResult, scrape_label  # noqa: E402
from pds4indextools.xpath_norm import canonicalize_xpath, renumber_xpaths  # noqa: E402

__all__ = [
    'AUTO_COLUMN_TOKENS',
    'AUTO_COLUMN_TYPES',
    'EXIT_INTERNAL_ERROR',
    'EXIT_RUNTIME_ERROR',
    'EXIT_SIGINT',
    'EXIT_USER_ERROR',
    'AbsolutePath',
    'CitationInformation',
    'CliError',
    'ColumnSpec',
    'ColumnStat',
    'ConfigError',
    'CopyDefaultConfigArgs',
    'CopyDefaultConfigResult',
    'CsvWritePlan',
    'FailSlowAggregateError',
    'GenerateIndexFileArgs',
    'GenerateIndexFileResult',
    'GenerateXpathListArgs',
    'GenerateXpathListResult',
    'IndexConfig',
    'LabelContents',
    'LabelError',
    'LidError',
    'ModificationDetail',
    'NilError',
    'NillableEntry',
    'OutputError',
    'OutputSection',
    'ParseError',
    'Pds4IndexError',
    'SchemaCache',
    'SchemaCacheError',
    'SchemaError',
    'SchemaNetworkError',
    'SchemaResolutionError',
    'SchemaTypeResolver',
    'SchemaVersionError',
    'ScrapeResult',
    'ScrapedValueError',
    'XPathError',
    'build_plan',
    'build_substitution_dict',
    'canonicalize_xpath',
    'cli_entrypoint',
    'load_config',
    'load_packaged_template',
    'main',
    'module_logger',
    'normalize_modification_detail',
    'parse_sort_key',
    'renumber_xpaths',
    'run_copy_default_config',
    'run_generate_index_file',
    'run_generate_xpath_list',
    'scrape_label',
    'sort_rows',
    'write_csv',
    'write_label',
]
