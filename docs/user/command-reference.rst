Every command and option, explained
===================================

This page is the one to keep open in a second tab. It lists all three commands
and every option, each with a plain explanation and a tiny example, so you can
look up a flag you have seen or discover one you have not. For the full
tutorial treatment of any topic, follow the links back into the earlier pages.

The three commands
------------------

The tool does three things, and you pick one by naming it right after
``pds4_create_xml_index``. Each command can be spelled with underscores or with
hyphens, whichever you prefer; both are identical.

``generate_index_file`` (or ``generate-index-file``)
   Reads your labels and writes the index table and its label. This is the main
   command. See :doc:`running-it`.

``generate_xpath_list`` (or ``generate-xpath-list``)
   Reads your labels and writes a ready-to-edit list of every available custom
   column, so you do not have to compose column addresses by hand. See
   :doc:`choosing-columns`.

``copy_default_config`` (or ``copy-default-config``)
   Writes out a copy of the tool's built-in default settings for you to build
   on. See :doc:`the-settings-file`.

Getting help and the version
----------------------------

``--version``
   Prints the tool's version and exits. Example:

   .. code-block:: console

      $ pds4_create_xml_index --version

``--help`` (or ``-h``)
   Prints a usage summary and exits. It works on the tool as a whole and on
   each command, so you can always ask a specific command what it accepts:

   .. code-block:: console

      $ pds4_create_xml_index --help
      $ pds4_create_xml_index generate_index_file --help

Options for reading a bundle
----------------------------

These apply to ``generate_index_file`` and ``generate_xpath_list``, the two
commands that read your labels.

``--bundle-root PATH`` (required)
   The top folder your labels live under. Every path in the output is written
   relative to it, and your patterns are understood relative to it. A symbolic
   link to a folder works too. See :doc:`choosing-labels`.

   .. code-block:: console

      $ pds4_create_xml_index generate_index_file --bundle-root moon_images "**/*.xml"

``PATTERN ...`` (one or more, required)
   Come after the options. One or more glob patterns, relative to the bundle
   root, choosing which labels to include; a label matching any pattern is
   included, and matching several times still includes it once. Absolute
   patterns are rejected. Quote each pattern so your shell does not expand it.
   See :doc:`choosing-labels`.

   .. code-block:: console

      $ pds4_create_xml_index generate_index_file --bundle-root moon_images "**/*.xml" "**/*.lblx"

``--config-file PATH`` (may be repeated)
   Your settings file. Give it more than once to layer several files in order,
   with later files winning where they overlap. See :doc:`the-settings-file`.

   .. code-block:: console

      $ pds4_create_xml_index generate_index_file --bundle-root moon_images \
          --config-file base.yaml --config-file overrides.yaml "**/*.xml"

``--fail-slow``
   Instead of stopping at the first troubled label, work through them all,
   collect every problem, and report them together. Nothing is written if any
   label failed. See :doc:`running-it`.

   .. code-block:: console

      $ pds4_create_xml_index generate_index_file --bundle-root moon_images \
          --config-file moon_index.yaml --fail-slow "**/*.xml"

Options that control the output
-------------------------------

``--output-file PATH``
   Where to write the result. If you leave it off, the index command defaults
   to ``index.csv`` (with a matching ``index.lblx``), and the column-list
   command defaults to ``columns.yaml``. The extension you choose is honored
   for the table; the label is always written next to it with a ``.lblx``
   extension. When a *default* name is already in use, the tool writes to the
   next free numbered name (``index_1.csv``, ``index_2.csv``, and so on) rather
   than overwriting. See :doc:`running-it`.

   .. code-block:: console

      $ pds4_create_xml_index generate_index_file --bundle-root moon_images \
          --config-file moon_index.yaml --output-file index.csv "**/*.xml"

``--label-template PATH`` (``generate_index_file`` only)
   Supply your own label template in place of the built-in one. Most users
   never need this; the built-in template produces a complete, valid label on
   its own. It is here for the rare case where your archive requires a custom
   label layout.

Watching what it does
---------------------

``-v``, ``-vv``, ``-vvv`` (or ``--verbose``)
   Increase how much detail the tool prints as it works. A plain run is quiet;
   ``-v`` prints progress, and ``-vv`` or ``-vvv`` print successively more.
   This affects only what is shown, never the result. Available on every
   command.

   .. code-block:: console

      $ pds4_create_xml_index generate_index_file --bundle-root moon_images \
          --config-file moon_index.yaml -v "**/*.xml"

Options for copying the defaults
--------------------------------

These belong to ``copy_default_config``.

``--output-file PATH`` (required here)
   Where to write the copied settings. Unlike the other commands, this one has
   no default name, so you always name the destination.

   .. code-block:: console

      $ pds4_create_xml_index copy_default_config --output-file moon_index.yaml

``--force``
   Overwrite the destination if it already exists. Without it, the tool
   declines to overwrite an existing file so you cannot lose your work by
   accident.

   .. code-block:: console

      $ pds4_create_xml_index copy_default_config --output-file moon_index.yaml --force
