Command-Line Interface
======================

The installed console script ``pds4_create_xml_index`` exposes three
subcommands. Each subcommand accepts ``--help`` to print the usage summary
reproduced below. Both underscore and hyphen spellings are accepted (for
example ``generate_index_file`` and ``generate-index-file``).

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

``generate_index_file``
-----------------------

Scrape the discovered labels and write an index CSV plus its paired PDS4
label::

    usage: pds4_create_xml_index generate_index_file [-h] --bundle-root PATH
                                                     [--config-file PATH]
                                                     [--output-file PATH]
                                                     [--fail-slow] [-v]
                                                     [--label-template PATH]
                                                     PATTERN [PATTERN ...]

    Scrape labels and write an index CSV plus its PDS4 label.

    positional arguments:
      PATTERN               One or more globs relative to --bundle-root.

    options:
      -h, --help            show this help message and exit
      --bundle-root PATH    Bundle root directory (or a symlink to one); required.
      --config-file PATH    Config YAML overlaid on the default; may be given many
                            times.
      --output-file PATH    Output file path; defaults are auto-numbered when in
                            use.
      --fail-slow           Accumulate per-label errors instead of stopping at the
                            first.
      -v, --verbose         Increase logging verbosity (-v INFO, -vv/-vvv DEBUG).
      --label-template PATH
                            Custom label template; defaults to the packaged
                            template.

Label discovery is purely glob-pattern-driven. The examples pass
``'**/*.lblx'``, but ``.xml`` is an equally valid historical label suffix:
a bundle whose labels end in ``.xml`` is scraped by passing ``'**/*.xml'``,
and passing both patterns discovers both suffixes with identical behavior.

Output-file naming follows R-CLI-015 and R-OUT-010 through R-OUT-013. When
``--output-file`` is omitted, the tool writes ``./index.csv`` and
``./index.lblx``; if either name is already taken, the basename is
auto-numbered (``index_1.csv``, ``index_2.csv``, and so on) to the lowest
free integer that leaves both names free. When ``--output-file`` is given, a
``.csv`` suffix is used verbatim, a bare stem gains ``.csv``, and any other
suffix (for example ``.tab``) is honored for the data file; the label always
takes the same stem with ``.lblx``. An explicit target that already exists
is overwritten with a WARNING and is never auto-numbered.

For example, the following run scrapes one bundle and writes ``index.csv``
and ``index.lblx`` next to it::

    pds4_create_xml_index generate_index_file \
        --bundle-root ./bundle --config-file cols.yaml \
        --output-file index.csv 'data/*.lblx'

See :ref:`cli-exit-codes` for the return-code contract.

``generate_xpath_list``
-----------------------

Scrape the discovered labels and write a starter ``columns:`` YAML block
that can be edited and merged into a configuration file::

    usage: pds4_create_xml_index generate_xpath_list [-h] --bundle-root PATH
                                                     [--config-file PATH]
                                                     [--output-file PATH]
                                                     [--fail-slow] [-v]
                                                     PATTERN [PATTERN ...]

    Scrape labels and write a starter columns YAML block.

    positional arguments:
      PATTERN             One or more globs relative to --bundle-root.

    options:
      -h, --help          show this help message and exit
      --bundle-root PATH  Bundle root directory (or a symlink to one); required.
      --config-file PATH  Config YAML overlaid on the default; may be given many
                          times.
      --output-file PATH  Output file path; defaults are auto-numbered when in
                          use.
      --fail-slow         Accumulate per-label errors instead of stopping at the
                          first.
      -v, --verbose       Increase logging verbosity (-v INFO, -vv/-vvv DEBUG).

Output-file naming mirrors R-CLI-022: when ``--output-file`` is omitted, the
tool writes ``./columns.yaml`` and auto-numbers it (``columns_1.yaml`` and
so on) if the name is taken. There is no paired label file for this
subcommand. For example::

    pds4_create_xml_index generate_xpath_list \
        --bundle-root ./bundle --output-file columns.yaml 'data/*.lblx'

See :ref:`cli-exit-codes` for the return-code contract.

``copy_default_config``
-----------------------

Write a copy of the packaged default configuration so it can be customized::

    usage: pds4_create_xml_index copy_default_config [-h] --output-file PATH
                                                     [--force] [-v]

    Write a copy of the packaged default configuration.

    options:
      -h, --help          show this help message and exit
      --output-file PATH  Destination path for the copied config; required.
      --force             Overwrite the destination if it already exists.
      -v, --verbose       Increase logging verbosity (-v INFO, -vv/-vvv DEBUG).

The ``--output-file`` path is required and is used verbatim. Writing to an
existing path fails unless ``--force`` is given, in which case the
destination is overwritten. For example::

    pds4_create_xml_index copy_default_config \
        --output-file ./config.yaml --force

See :ref:`cli-exit-codes` for the return-code contract.
