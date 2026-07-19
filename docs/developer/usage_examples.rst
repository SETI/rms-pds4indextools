Usage Examples
==============

Each example below builds on the same self-contained ``moon_images`` bundle
used throughout the :doc:`User Guide </user/index>`: three
``Product_Observational`` labels,
``crater_north.xml``, ``crater_south.xml``, and ``mare_plain.xml``, under a
``data/`` directory, with the titles ``North Polar Crater Field``,
``South Polar Crater Field``, and ``Mare Basalt Plain``. Every example shows
the exact invocation together with the resulting output. Successful runs are
quiet on stderr unless a warning applies. Runs that resolve XSD schemas use a
local schema cache; point ``xsd_cache_dir`` at a writable directory (see
:doc:`config`) to avoid repeated downloads.

Building a basic index file
---------------------------

Start from a ``moon_images.yaml`` configuration naming three columns, the
logical identifier, the file name, and the product title:

.. code-block:: yaml

    columns:
      - auto: lid
        name: LID
      - auto: filename
        name: FILE_NAME
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
        name: TITLE
    label_contents:
      logical_identifier: urn:nasa:pds:moon_images:index
      product_class: Product_Ancillary

Generate the index file::

    pds4_create_xml_index generate_index_file \
        --bundle-root moon_images \
        --config-file moon_images.yaml \
        --output-file index.csv \
        '**/*.xml'

The command writes ``index.csv`` with one row per label, in glob-discovery
order::

    LID,FILE_NAME,TITLE
    urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field
    urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field
    urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain

It also writes ``index.lblx``. The field definition for the first column is::

    <Field_Delimited>
        <name>LID</name>
        <field_number>1</field_number>
        <data_type>ASCII_LID</data_type>
        <maximum_field_length unit="byte">42</maximum_field_length>
        <description>XPath: lid</description>
    </Field_Delimited>

Sorting the rows by title
-------------------------

Add an ``output`` section with a ``sort_by`` key to order the rows. Sorting
by ``TITLE`` reorders the rows alphabetically by product title:

.. code-block:: yaml

    output:
      sort_by:
        - TITLE

Rerun the command with that key added to the configuration; the rows are now
sorted by title rather than by discovery order::

    LID,FILE_NAME,TITLE
    urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain
    urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field
    urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field

Prefix a sort key with ``-`` to sort that key in descending order.

Picking just the columns you want
---------------------------------

The ``columns`` list controls exactly which values appear and in what order.
Adding a fourth column that selects ``version_id`` adds a ``VERSION`` column:

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

The resulting ``index.csv`` gains the extra column::

    LID,FILE_NAME,TITLE,VERSION
    urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field,1.0
    urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field,1.0
    urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain,1.0

Lining the columns up
---------------------

Setting ``output.fixed_width: true`` pads every column to its widest value so
the columns align:

.. code-block:: yaml

    output:
      fixed_width: true

With the three-column configuration, each value is padded to its column's
maximum width::

    LID,FILE_NAME,TITLE
    urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field
    urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field
    urn:nasa:pds:moon_images:data:mare_plain  ,mare_plain.xml  ,Mare Basalt Plain

The final column is padded to its own width as well; the trailing spaces after
the two shorter titles simply cannot be shown in this rendered block.

Ending lines with CRLF
----------------------

Setting ``output.line_ending: CRLF`` terminates every record with a
carriage-return and line-feed pair instead of a bare line-feed:

.. code-block:: yaml

    output:
      line_ending: CRLF

The bytes of ``index.csv`` match the basic run except that each line ends with
``\r\n``::

    LID,FILE_NAME,TITLE\r\n
    urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field\r\n
    urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field\r\n
    urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain\r\n

Discovering the available columns
---------------------------------

Run ``generate_xpath_list`` to emit every discovered leaf XPath as a
``columns:`` block. A configuration supplying the required ``label_contents``
is still needed::

    pds4_create_xml_index generate_xpath_list \
        --bundle-root moon_images \
        --config-file moon_images.yaml \
        --output-file columns.yaml \
        '**/*.xml'

The written ``columns.yaml`` lists one entry per leaf element::

    # Generated by pds4_create_xml_index generate_xpath_list.
    # Edit each `name:` (or delete unwanted entries), then merge this
    # `columns:` block into one of your --config-file YAMLs.
    columns:
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:logical_identifier<1>
        name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:logical_identifier<1>
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:version_id<1>
        name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:version_id<1>
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
        name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:title<1>
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:information_model_version<1>
        name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:information_model_version<1>
      - xpath: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:product_class<1>
        name: pds:Product_Observational<1>/pds:Identification_Area<1>/pds:product_class<1>

Edit each ``name:`` to a friendly header, delete the entries you do not want,
and merge the block into one of your ``--config-file`` YAMLs.

Copying the default configuration
---------------------------------

Write a copy of the packaged default configuration so it can be customized::

    pds4_create_xml_index copy_default_config --output-file config.yaml

The command writes ``config.yaml`` beginning with::

    # Default configuration for pds4_create_xml_index.
    # Users override these via one or more --config-file arguments; user
    # settings are deep-merged onto these defaults (scalars/lists replaced,
    # dicts merged).

Pass ``--force`` to overwrite an existing destination.

Using the index tool from Python
--------------------------------

The same pipeline is available in Python through
:func:`~pds4indextools.cli.run_generate_index_file`, which takes a
:class:`~pds4indextools.cli.GenerateIndexFileArgs` and returns a
:class:`~pds4indextools.cli.GenerateIndexFileResult`:

.. code-block:: python

    from pathlib import Path

    from pds4indextools import (
        GenerateIndexFileArgs,
        run_generate_index_file,
    )

    result = run_generate_index_file(
        GenerateIndexFileArgs(
            bundle_root=Path('moon_images'),
            patterns=('**/*.xml',),
            config_files=(Path('moon_images.yaml'),),
            output_file=Path('index.csv'),
        )
    )
    print(result.csv_path, result.rows_written)

The call writes the same ``index.csv`` and ``index.lblx`` as the basic run and
returns the written paths and row and column counts. On failure it raises a
subclass of :exc:`~pds4indextools.errors.Pds4IndexError`.
