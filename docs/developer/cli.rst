Command-Line Interface
======================

The installed console script ``pds4_create_xml_index`` exposes three
subcommands (``generate_index_file``, ``generate_xpath_list``, and
``copy_default_config``); both underscore and hyphen spellings are accepted
(for example ``generate_index_file`` and ``generate-index-file``).

The complete command-and-option reference — every subcommand and flag, with
plain-language explanations and examples — lives in the User Guide, at
:doc:`/user/command-reference`; the User Guide's :doc:`/user/quick-start`
covers getting going. This page does not repeat that material. It documents
only the developer-facing exit-code contract the CLI guarantees.

.. _cli-exit-codes:

Exit codes
----------

Every subcommand shares the same exit-code contract (R-API-004). A run
returns ``0`` on success. The non-zero codes are the module-level
constants in :mod:`pds4indextools.errors`:

- :data:`~pds4indextools.errors.EXIT_USER_ERROR` (``1``) for a usage or
  configuration problem, raised as :exc:`~pds4indextools.errors.CliError`
  or :exc:`~pds4indextools.errors.ConfigError`.
- :data:`~pds4indextools.errors.EXIT_RUNTIME_ERROR` (``2``) for a data or
  output problem, raised as :exc:`~pds4indextools.errors.LabelError`,
  :exc:`~pds4indextools.errors.SchemaError`,
  :exc:`~pds4indextools.errors.OutputError`, or
  :exc:`~pds4indextools.errors.FailSlowAggregateError`.
- :data:`~pds4indextools.errors.EXIT_INTERNAL_ERROR` (``3``) for any
  unexpected exception that is not a
  :exc:`~pds4indextools.errors.Pds4IndexError`; the traceback is printed.
- :data:`~pds4indextools.errors.EXIT_SIGINT` (``130``) when the run is
  interrupted with SIGINT.
