Settings file reference
=======================

This page is the complete specification of the settings file. It is organized
by top-level section, and for every setting it gives the name, whether it is
required or optional, its type or allowed values, its default, and what it
does. For the tutorial treatment of any section, follow the links back into the
earlier pages. The settings file is written in YAML; if that format is new to
you, :doc:`the-settings-file` teaches the little you need.

The file has these top-level sections: ``columns:``, ``output:``,
``label_contents:``, ``nillable:``, and ``xsd_cache_dir:``. A run may also
draw on the index tool's built-in defaults and on more than one settings file layered
together, which the final section explains.

``columns:``
------------

A list of the columns that make up your table, in the order they will appear.
This section is **required** for ``generate_index_file``; an empty list is
rejected. Each entry names exactly one column and has **exactly one** of these
two keys:

``xpath:``
   A custom column address, such as
   ``pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>``.
   It contains no spaces. The command ``generate_xpath_list`` writes these
   addresses out for you so you need not compose them by hand. See
   :doc:`choosing-columns`.

``auto:``
   One of exactly five ready-made column tokens:

   - ``lid`` — the label's logical identifier.
   - ``lidvid`` — its versioned identifier (logical identifier plus version).
   - ``filespec`` — its path within the bundle.
   - ``filename`` — its file name alone.
   - ``bundle_name`` — the name of the bundle.

Each entry may also carry one optional key:

``name:``
   The column header written into the table. If it is omitted or left blank,
   the header is the selector text itself (the ``xpath:`` address or the
   ``auto:`` token). A header may contain only printable ASCII, and may not
   contain a comma or a double-quote.

A few rules keep a column list well formed:

- Two entries may not share the same selector.
- Two entries may not resolve to the same header.
- The order of entries is the order of the columns in the table.

A short, valid example:

.. code-block:: yaml

   columns:
     - auto: lid
       name: LID
     - auto: filename
       name: FILE_NAME
     - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
       name: TITLE

Note that ``columns:`` behaves differently from every other section when you
layer settings files: a later file's ``columns:`` **replaces** the earlier one
wholesale rather than merging entry by entry. See `Layering settings files`_.

``output:``
-----------

Controls how the table is written. Every setting here is optional and has a
default, so the whole section may be omitted. See :doc:`sorting-and-layout`.

``fixed_width:``
   ``true`` or ``false``. Default ``false``. When ``false``, columns are
   comma-separated and each is only as wide as it needs to be. When ``true``,
   every column is padded with spaces to the width of its widest value, giving
   a table that lines up when read as plain text.

``sort_by:``
   A list of column header names. Default empty. Rows are sorted by the first
   name, ties broken by the second, and so on. Each name may carry a leading
   ``+`` for ascending (the default) or ``-`` for descending. When the list is
   empty or absent, rows stay in natural discovery order, which is already
   ordered by file path. A name that is not one of your column headers is an
   error.

   .. code-block:: yaml

      output:
        sort_by:
          - TITLE
          - -VERSION

``line_ending:``
   ``LF`` or ``CRLF``. Default ``LF``. ``CRLF`` ends each row with a
   carriage-return plus a line-feed, which some Windows tools prefer; ``LF``
   ends each row with a single line-feed.

``label_contents:``
-------------------

Describes the label of the index product you are creating. This section is
**required** for ``generate_index_file``. Remember throughout that it describes
the *new index you are making*, not the data labels you are reading. See
:doc:`describing-the-index`.

``logical_identifier:`` (required)
   The identifier you assign to your index product, in the usual
   ``urn:nasa:pds:...`` style.

``product_class:`` (required)
   Either ``Product_Ancillary`` or ``Product_Metadata_Supplemental``.

``version_id:`` (optional)
   Your index product's version. Quote it so a value like ``'1.0'`` is kept as
   text rather than read as a number.

``title:`` (optional)
   A short, human-readable name for the index.

``Citation_Information:`` (optional)
   A block recording who made the index and how to cite it. It may contain any
   of: ``author_list`` (a name or a list of names), ``editor_list`` (a name),
   ``publication_year`` (a year), ``doi``, ``keyword`` (one or a list),
   ``description``, and ``Funding_Acknowledgement`` (a block). You may add
   other citation fields too, and they are carried through into the label.

   .. code-block:: yaml

      label_contents:
        Citation_Information:
          author_list: Lunar Team
          publication_year: '2026'
          description: An index of the Moon Images bundle.

``Modification_Detail:`` (optional)
   One entry, or a list of entries, each with ``modification_date``,
   ``version_id``, and ``description``. If you leave this out, the index tool writes
   a sensible default history entry for you.

   .. code-block:: yaml

      label_contents:
        Modification_Detail:
          - modification_date: '2026-07-01'
            version_id: '1.0'
            description: First public release of the index.

``Internal_Reference:``, ``External_Reference:``, ``Source_Product_Internal:``, ``Source_Product_External:`` (optional)
   Lists of reference entries, carried through into the label.

``File_Area_Ancillary:``, ``File_Area_Metadata:`` (optional)
   Blocks describing a file area, carried through into the label.

Any other keys you add under ``label_contents:`` are carried straight through
into the finished label, **except** a set of reserved names that the index tool fills
in itself, such as the file's own name, its size, its checksum, its record and
field counts, and its creation date. Using one of those reserved names is
rejected, so leave those details to the index tool.

``nillable:``
-------------

Tells the index tool how to fill a cell when a label marks that field as having no
value. It maps a PDS4 data-type name to a set of replacement values, one for
each reason a value can be absent: ``inapplicable``, ``missing``, ``unknown``,
and ``anticipated``. The index tool ships with sensible defaults for common date,
number, and text types; you may add more types or override the shipped ones.

.. code-block:: yaml

   nillable:
     pds:ASCII_Integer:
       inapplicable: -999
       missing: -998
       unknown: -997
       anticipated: -996

To see the full set of shipped defaults, write them out with
``copy_default_config`` and read the ``nillable:`` section it prints.

``xsd_cache_dir:``
------------------

A folder, given as an absolute path, or ``null``. Default ``null``. This is
where the index tool keeps the PDS4 schema files it downloads. ``null`` means a
standard per-user cache location chosen for you. The first run downloads the
schemas your labels refer to; later runs reuse the cache and can work with no
network connection.

.. code-block:: yaml

   xsd_cache_dir: null

Layering settings files
-----------------------

You may give ``--config-file`` more than once. The files are applied in order
onto the index tool's built-in defaults, and a later file wins wherever they overlap.
The rules for how they combine are:

- Individual values and lists are **replaced** by the later file.
- Nested blocks are **merged** key by key, so a later file can change one field
  of a block without disturbing the rest.
- ``columns:`` is the one list that is replaced **wholesale**: a later file's
  ``columns:`` takes over completely rather than merging item by item.

See :doc:`the-settings-file` for a worked example of layering.

A complete settings file
------------------------

Here is one realistic settings file that uses the main sections together:

.. code-block:: yaml

   columns:
     - auto: lid
       name: LID
     - auto: filename
       name: FILE_NAME
     - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
       name: TITLE
     - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:version_id<1>
       name: VERSION
   output:
     fixed_width: false
     line_ending: LF
     sort_by:
       - TITLE
   label_contents:
     logical_identifier: urn:nasa:pds:moon_images:index
     product_class: Product_Ancillary
     version_id: '1.0'
     title: Moon Images Index
