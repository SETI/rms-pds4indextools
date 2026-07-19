Configuration
=============

The tool is configured with YAML files layered on top of a packaged
default. Each ``--config-file`` is deep-merged onto the default in the order
given (nested mappings merge recursively; lists and scalars replace
wholesale), and the result is validated into an
:class:`~pds4indextools.config.IndexConfig` model. The sections below
describe each top-level key.

The ``columns`` key
-------------------

The ``columns`` key is an ordered list of output-column selectors, each
validated into a :class:`~pds4indextools.config.ColumnSpec`. Exactly one of
``xpath`` or ``auto`` is set per entry, and an optional ``name`` sets the
CSV header. The four entry shapes are:

.. code-block:: yaml

    columns:
      # 1. An XPath selector with an explicit header.
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
        name: TITLE
      # 2. An XPath selector with no name; the selector text becomes the header.
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:version_id<1>
      # 3. An auto token with an explicit header.
      - auto: lid
        name: LID
      # 4. A bare auto token; the token text becomes the header.
      - auto: filename

The five auto tokens are the members of
:data:`~pds4indextools.config.AUTO_COLUMN_TOKENS`: ``lid``, ``lidvid``,
``filespec``, ``filename``, and ``bundle_name``.

The entries are validated by these rules:

===================================  ========================================
Rule                                 Behavior
===================================  ========================================
Exactly one selector                 Each entry sets ``xpath`` or ``auto``,
                                     never both and never neither.
Valid auto tokens                    An ``auto`` value must be one of the
                                     five tokens above.
Name charset                         A non-blank ``name`` holds only
                                     printable ASCII with no comma and no
                                     double-quote.
No whitespace in ``xpath``           An ``xpath`` selector contains no
                                     internal whitespace.
No duplicate selectors               Two entries never share the same
                                     ``xpath`` or ``auto`` selector.
No duplicate headers                 Two entries never resolve to the same
                                     header.
Wholesale replacement on merge       A ``columns`` list in a higher-priority
                                     file replaces the lower-priority list
                                     entirely; entries are not merged.
===================================  ========================================

A ``columns`` block is required for ``generate_index_file`` (the check is
enforced by the command-line layer, not the model). To build a starter
block, run ``generate_xpath_list`` to emit every discovered leaf XPath as a
``columns:`` list, edit each ``name:`` or delete unwanted entries, and merge
the result into one of your ``--config-file`` YAMLs.

The ``nillable`` key
--------------------

The ``nillable`` key maps a PDS4 data-type name to a
:class:`~pds4indextools.config.NillableEntry` giving the four replacement
values written when a scraped value carries a ``nilReason`` attribute:
``inapplicable``, ``missing``, ``unknown``, and ``anticipated``.

The ``output`` key
------------------

The ``output`` key is an :class:`~pds4indextools.config.OutputSection`
controlling the CSV format: ``fixed_width`` (a Boolean selecting a
fixed-width character table instead of a comma-delimited one), ``line_ending``
(either ``LF`` or ``CRLF``), and ``sort_by`` (an ordered list of sort keys,
each parsed by :func:`~pds4indextools.config.parse_sort_key`; a ``-`` prefix
sorts descending).

The ``label_contents`` key
--------------------------

The ``label_contents`` key is a
:class:`~pds4indextools.config.LabelContents` holding substitution variables
for the generated index label. Its two required fields are
``logical_identifier`` (the LID of the generated product) and
``product_class`` (``Product_Ancillary`` or
``Product_Metadata_Supplemental``). Optional fields include ``version_id``,
``title``, ``Citation_Information`` (a
:class:`~pds4indextools.config.CitationInformation`), and
``Modification_Detail`` (one or more
:class:`~pds4indextools.config.ModificationDetail` entries). Unknown keys are
passed through to the label template, except the reserved names below.

The ``xsd_cache_dir`` key
-------------------------

The ``xsd_cache_dir`` key is an optional absolute directory used to cache
downloaded XSD schemas. A relative path is rejected during validation.

Full example
------------

A complete configuration for the quickstart bundle looks like:

.. code-block:: yaml

    label_contents:
      logical_identifier: urn:nasa:pds:test_simple:index:index
      product_class: Product_Ancillary
      version_id: '1.0'
      title: Simple index file
    output:
      fixed_width: false
      line_ending: LF
    columns:
      - auto: lid
        name: LID
      - auto: filename
        name: FILE_NAME
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
        name: TITLE

Reserved BASE variables
-----------------------

The tool computes several label variables itself and rejects any
``label_contents`` key that would shadow one of them (R-LBL-012). The
reserved names are ``index_file_name``, ``Field_Content``, ``fields``,
``records``, ``Table_Character``, ``Table_Delimited``, ``Product_Ancillary``,
``Product_Metadata_Supplemental``, ``object_length_h``, ``object_length_t``,
and ``maximum_record_length``.
