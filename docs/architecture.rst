Architecture
============

This page describes the exception hierarchy, the public API surface, the
programmatic interface contracts, the data-flow pipeline, and the error
model.

Exception hierarchy
-------------------

Every error the tool raises derives from a single root,
:exc:`~pds4indextools.errors.Pds4IndexError`. The class-level
``FAIL_SLOW_ELIGIBLE`` flag records whether an error may be accumulated
under ``--fail-slow`` (R-ERR-001).

.. mermaid::

    classDiagram
        Exception <|-- Pds4IndexError
        Pds4IndexError <|-- CliError
        Pds4IndexError <|-- ConfigError
        Pds4IndexError <|-- LabelError
        Pds4IndexError <|-- SchemaError
        Pds4IndexError <|-- OutputError
        Pds4IndexError <|-- FailSlowAggregateError
        LabelError <|-- ParseError
        LabelError <|-- LidError
        LabelError <|-- XPathError
        LabelError <|-- NilError
        LabelError <|-- ScrapedValueError
        SchemaError <|-- SchemaResolutionError
        SchemaError <|-- SchemaVersionError
        SchemaError <|-- SchemaNetworkError
        SchemaError <|-- SchemaCacheError
        class Pds4IndexError {
            FAIL_SLOW_ELIGIBLE = false
        }
        class CliError {
            FAIL_SLOW_ELIGIBLE = false
        }
        class ConfigError {
            FAIL_SLOW_ELIGIBLE = false
        }
        class LabelError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class ParseError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class LidError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class XPathError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class NilError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class ScrapedValueError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class SchemaError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class SchemaResolutionError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class SchemaVersionError {
            FAIL_SLOW_ELIGIBLE = true
        }
        class SchemaNetworkError {
            FAIL_SLOW_ELIGIBLE = false
        }
        class SchemaCacheError {
            FAIL_SLOW_ELIGIBLE = false
        }
        class OutputError {
            FAIL_SLOW_ELIGIBLE = false
        }
        class FailSlowAggregateError {
            FAIL_SLOW_ELIGIBLE = false
        }

Public API surface
------------------

The public API is the union of each submodule's exported names, re-exported
at the package root.

The :mod:`pds4indextools.errors` submodule exports the exception classes
:exc:`~pds4indextools.errors.Pds4IndexError`,
:exc:`~pds4indextools.errors.CliError`,
:exc:`~pds4indextools.errors.ConfigError`,
:exc:`~pds4indextools.errors.LabelError`,
:exc:`~pds4indextools.errors.ParseError`,
:exc:`~pds4indextools.errors.LidError`,
:exc:`~pds4indextools.errors.XPathError`,
:exc:`~pds4indextools.errors.NilError`,
:exc:`~pds4indextools.errors.ScrapedValueError`,
:exc:`~pds4indextools.errors.SchemaError`,
:exc:`~pds4indextools.errors.SchemaResolutionError`,
:exc:`~pds4indextools.errors.SchemaVersionError`,
:exc:`~pds4indextools.errors.SchemaNetworkError`,
:exc:`~pds4indextools.errors.SchemaCacheError`,
:exc:`~pds4indextools.errors.OutputError`, and
:exc:`~pds4indextools.errors.FailSlowAggregateError`, plus the exit-code
constants :data:`~pds4indextools.errors.EXIT_USER_ERROR`,
:data:`~pds4indextools.errors.EXIT_RUNTIME_ERROR`,
:data:`~pds4indextools.errors.EXIT_INTERNAL_ERROR`, and
:data:`~pds4indextools.errors.EXIT_SIGINT`.

The :mod:`pds4indextools.config` submodule exports the models
:class:`~pds4indextools.config.IndexConfig`,
:class:`~pds4indextools.config.ColumnSpec`,
:class:`~pds4indextools.config.NillableEntry`,
:class:`~pds4indextools.config.OutputSection`,
:class:`~pds4indextools.config.LabelContents`,
:class:`~pds4indextools.config.CitationInformation`, and
:class:`~pds4indextools.config.ModificationDetail`, the validated path alias
:data:`~pds4indextools.config.AbsolutePath`, the token set
:data:`~pds4indextools.config.AUTO_COLUMN_TOKENS`, and the functions
:func:`~pds4indextools.config.load_config` and
:func:`~pds4indextools.config.parse_sort_key`.

The :mod:`pds4indextools.xpath_norm` submodule exports
:func:`~pds4indextools.xpath_norm.canonicalize_xpath` and
:func:`~pds4indextools.xpath_norm.renumber_xpaths`.

The :mod:`pds4indextools.schema_types` submodule exports
:class:`~pds4indextools.schema_types.SchemaCache`,
:class:`~pds4indextools.schema_types.SchemaTypeResolver`, and
:data:`~pds4indextools.schema_types.AUTO_COLUMN_TYPES`.

The :mod:`pds4indextools.scraper` submodule exports
:class:`~pds4indextools.scraper.ScrapeResult` and
:func:`~pds4indextools.scraper.scrape_label`.

The :mod:`pds4indextools.csv_writer` submodule exports
:class:`~pds4indextools.csv_writer.ColumnStat`,
:class:`~pds4indextools.csv_writer.CsvWritePlan`,
:func:`~pds4indextools.csv_writer.build_plan`,
:func:`~pds4indextools.csv_writer.sort_rows`, and
:func:`~pds4indextools.csv_writer.write_csv`.

The :mod:`pds4indextools.label_writer` submodule exports
:func:`~pds4indextools.label_writer.build_substitution_dict`,
:func:`~pds4indextools.label_writer.load_packaged_template`,
:func:`~pds4indextools.label_writer.normalize_modification_detail`, and
:func:`~pds4indextools.label_writer.write_label`.

The :mod:`pds4indextools.cli` submodule exports the argument and result
dataclasses :class:`~pds4indextools.cli.GenerateIndexFileArgs`,
:class:`~pds4indextools.cli.GenerateIndexFileResult`,
:class:`~pds4indextools.cli.GenerateXpathListArgs`,
:class:`~pds4indextools.cli.GenerateXpathListResult`,
:class:`~pds4indextools.cli.CopyDefaultConfigArgs`, and
:class:`~pds4indextools.cli.CopyDefaultConfigResult`, the three runner
functions :func:`~pds4indextools.cli.run_generate_index_file`,
:func:`~pds4indextools.cli.run_generate_xpath_list`, and
:func:`~pds4indextools.cli.run_copy_default_config`, and the entry points
:func:`~pds4indextools.cli.main` and
:func:`~pds4indextools.cli.cli_entrypoint`.

The package root additionally exports the logger accessor
:func:`~pds4indextools.module_logger`.

Interface contracts
-------------------

The three ``run_*`` functions are the programmatic entry points. Each takes
a single frozen argument dataclass and returns a single result dataclass;
each raises a subclass of :exc:`~pds4indextools.errors.Pds4IndexError` on
failure (R-API-004).

:func:`~pds4indextools.cli.run_generate_index_file` takes a
:class:`~pds4indextools.cli.GenerateIndexFileArgs`. Precondition: the bundle
root exists and the configuration supplies a non-empty ``columns`` block.
Postcondition: an index CSV and its paired ``.lblx`` label are written, and
a :class:`~pds4indextools.cli.GenerateIndexFileResult` naming the written
paths is returned. It raises :exc:`~pds4indextools.errors.ConfigError` for
an invalid configuration, :exc:`~pds4indextools.errors.LabelError` or
:exc:`~pds4indextools.errors.SchemaError` for label or schema problems,
:exc:`~pds4indextools.errors.FailSlowAggregateError` when accumulated
fail-slow errors occur, and :exc:`~pds4indextools.errors.OutputError` for a
write failure.

:func:`~pds4indextools.cli.run_generate_xpath_list` takes a
:class:`~pds4indextools.cli.GenerateXpathListArgs`. Precondition: the bundle
root exists. Postcondition: a starter ``columns:`` YAML block is written and
a :class:`~pds4indextools.cli.GenerateXpathListResult` is returned. It
raises the same label and schema errors as above, plus
:exc:`~pds4indextools.errors.OutputError` for a write failure.

:func:`~pds4indextools.cli.run_copy_default_config` takes a
:class:`~pds4indextools.cli.CopyDefaultConfigArgs`. Precondition: the
destination is writable and either absent or ``force`` is set.
Postcondition: the packaged default configuration is copied to the
destination and a :class:`~pds4indextools.cli.CopyDefaultConfigResult` is
returned. It raises :exc:`~pds4indextools.errors.OutputError` when the
destination exists and ``force`` is not set, or on a write failure.

Data flow
---------

A ``generate_index_file`` run moves each label through a fixed pipeline:

.. mermaid::

    flowchart LR
        discover --> parse
        parse --> renumber
        renumber --> schema_resolve
        schema_resolve --> filter
        filter --> sort
        sort --> write_csv
        write_csv --> write_label

Labels are discovered by glob, parsed into element trees, their XPaths are
renumbered into canonical form, scraped values are resolved against the XSD
schema types, the configured columns filter the results, rows are sorted,
the CSV is written, and finally the PDS4 label is written.

Module responsibilities
-----------------------

============================================  ===================================
Module                                        Responsibility
============================================  ===================================
:mod:`pds4indextools.errors`                  Single-rooted exception tree and
                                              exit-code constants.
:mod:`pds4indextools.config`                  Pydantic configuration schema,
                                              loading, and merging.
:mod:`pds4indextools.xpath_norm`              Canonicalizing and renumbering
                                              XPaths.
:mod:`pds4indextools.schema_types`            Fetching and caching XSDs and
                                              resolving PDS4 data types.
:mod:`pds4indextools.scraper`                 Scraping values and identifiers
                                              from one label.
:mod:`pds4indextools.csv_writer`              Planning, sorting, and writing the
                                              index CSV.
:mod:`pds4indextools.label_writer`            Building substitutions and writing
                                              the PDS4 label.
:mod:`pds4indextools.cli`                     Argument parsing, dispatch, and the
                                              three runner functions.
``_logging``                                  Internal logging setup and the
                                              logger accessor.
``_io``                                       Internal atomic-write helpers.
============================================  ===================================

Error model
-----------

Fail-slow-eligible errors are the label-content errors
(:exc:`~pds4indextools.errors.LabelError` and its subclasses) and most
schema errors, but not
:exc:`~pds4indextools.errors.SchemaNetworkError` or
:exc:`~pds4indextools.errors.SchemaCacheError`, which always halt the run
(R-ERR-001). Under ``--fail-slow`` the eligible errors are accumulated and
reported together as a
:exc:`~pds4indextools.errors.FailSlowAggregateError` before output is
written; all other errors halt immediately. The command-line layer maps each
error to its exit code (R-API-004): user and configuration errors return
:data:`~pds4indextools.errors.EXIT_USER_ERROR`, data and output errors
return :data:`~pds4indextools.errors.EXIT_RUNTIME_ERROR`, an unexpected
exception returns :data:`~pds4indextools.errors.EXIT_INTERNAL_ERROR`, and
SIGINT returns :data:`~pds4indextools.errors.EXIT_SIGINT`.
