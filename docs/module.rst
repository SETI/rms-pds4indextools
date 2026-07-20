``pds4indextools`` Module
=========================

.. automodule:: pds4indextools

The package re-exports the union of every public submodule's ``__all__``
plus one logging helper. The following sections document each submodule.

The package-level logger accessor is:

.. autofunction:: pds4indextools.module_logger

``errors`` Submodule
--------------------

.. automodule:: pds4indextools.errors
    :member-order: bysource
    :members: Pds4IndexError, CliError, ConfigError, LabelError, ParseError,
        LidError, XPathError, NilError, ScrapedValueError, SchemaError,
        SchemaResolutionError, SchemaVersionError, SchemaNetworkError,
        SchemaCacheError, OutputError, FailSlowAggregateError
    :undoc-members:
    :show-inheritance:

.. autodata:: pds4indextools.errors.EXIT_USER_ERROR
.. autodata:: pds4indextools.errors.EXIT_RUNTIME_ERROR
.. autodata:: pds4indextools.errors.EXIT_INTERNAL_ERROR
.. autodata:: pds4indextools.errors.EXIT_SIGINT

``config`` Submodule
--------------------

.. automodule:: pds4indextools.config
    :member-order: bysource
    :members: IndexConfig, ColumnSpec, NillableEntry, OutputSection,
        LabelContents, CitationInformation, ModificationDetail,
        load_config, parse_sort_key
    :undoc-members:
    :show-inheritance:

.. autodata:: pds4indextools.config.AUTO_COLUMN_TOKENS

.. py:data:: AbsolutePath
    :module: pds4indextools.config

    A pydantic-validated absolute :class:`~pathlib.Path` alias. A relative
    path is rejected during configuration validation (R-CFG-024, R-CFG-040).

``xpath_norm`` Submodule
------------------------

.. automodule:: pds4indextools.xpath_norm
    :member-order: bysource
    :members: canonicalize_xpath, renumber_xpaths
    :undoc-members:
    :show-inheritance:

``schema_types`` Submodule
--------------------------

.. automodule:: pds4indextools.schema_types
    :member-order: bysource
    :members: SchemaCache, SchemaTypeResolver
    :undoc-members:
    :show-inheritance:

.. autodata:: pds4indextools.schema_types.AUTO_COLUMN_TYPES

``scraper`` Submodule
---------------------

.. automodule:: pds4indextools.scraper
    :member-order: bysource
    :members: ScrapeResult, scrape_label
    :undoc-members:
    :show-inheritance:

``csv_writer`` Submodule
------------------------

.. automodule:: pds4indextools.csv_writer
    :member-order: bysource
    :members: ColumnStat, CsvWritePlan, build_plan, sort_rows, write_csv
    :undoc-members:
    :show-inheritance:

``label_writer`` Submodule
--------------------------

.. automodule:: pds4indextools.label_writer
    :member-order: bysource
    :members: build_substitution_dict, load_packaged_template,
        normalize_modification_detail, write_label
    :undoc-members:
    :show-inheritance:

``cli`` Submodule
-----------------

.. automodule:: pds4indextools.cli
    :member-order: bysource
    :members: GenerateIndexFileArgs, GenerateIndexFileResult,
        GenerateXpathListArgs, GenerateXpathListResult, CopyDefaultConfigArgs,
        CopyDefaultConfigResult, run_generate_index_file,
        run_generate_xpath_list, run_copy_default_config, main, cli_entrypoint
    :undoc-members:
    :show-inheritance:

Script Entry Point
------------------

The ``__main__`` module wires the console-script entry point
``pds4_create_xml_index`` to :func:`~pds4indextools.cli.cli_entrypoint`, so
``python -m pds4indextools`` and the installed command behave identically.
The private ``_logging`` and ``_io`` modules are internal helpers and are not
part of the public API.
