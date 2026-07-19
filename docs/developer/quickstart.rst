Quickstart
==========

This walkthrough builds an index CSV and its PDS4 label from a small,
self-contained example bundle you can re-create anywhere. The bundle holds
three observational labels under a ``data/`` directory.

The example bundle
------------------

Create a directory named ``moon_images`` with the following layout::

    moon_images/
    └── data/
        ├── crater_north.xml
        ├── crater_south.xml
        └── mare_plain.xml

Each label is a minimal PDS4 ``Product_Observational``. ``crater_north.xml``
is::

    <?xml version="1.0" encoding="UTF-8"?>
    <Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://pds.nasa.gov/pds4/pds/v1 https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
        <Identification_Area>
            <logical_identifier>urn:nasa:pds:moon_images:data:crater_north</logical_identifier>
            <version_id>1.0</version_id>
            <title>North Polar Crater Field</title>
            <information_model_version>1.21.0.0</information_model_version>
            <product_class>Product_Observational</product_class>
        </Identification_Area>
    </Product_Observational>

``crater_south.xml`` and ``mare_plain.xml`` are identical except for their
``logical_identifier`` and ``title``:
``urn:nasa:pds:moon_images:data:crater_south`` with the title
``South Polar Crater Field``, and
``urn:nasa:pds:moon_images:data:mare_plain`` with the title
``Mare Basalt Plain``.

The configuration
-----------------

Write a ``moon_images.yaml`` configuration naming three columns: the logical
identifier, the file name, and the product title:

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
      version_id: '1.0'
      title: Moon Images Index

Resolving the ``title`` column against its XSD data type fetches the schema
named in each label's ``xsi:schemaLocation``. The first run downloads the
schema and caches it; set ``xsd_cache_dir`` to an absolute directory (see
:doc:`config`) to reuse the cache across runs.

Running the tool
----------------

Scrape every ``.xml`` label under the bundle and write an index named
``index.csv``::

    pds4_create_xml_index generate_index_file \
        --bundle-root moon_images \
        --config-file moon_images.yaml \
        --output-file index.csv \
        '**/*.xml'

Label discovery is glob-driven, so the ``'**/*.xml'`` pattern selects the
labels; quote the pattern so the shell does not expand it.

The index CSV
-------------

The command writes ``index.csv`` with one header row and one row per label,
in glob-discovery order::

    LID,FILE_NAME,TITLE
    urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field
    urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field
    urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain

The label
---------

Alongside the CSV, the tool writes ``index.lblx``, a PDS4 label that
describes the CSV as a delimited table. The excerpt below shows the field
definition generated for the third column::

    <Field_Delimited>
        <name>TITLE</name>
        <field_number>3</field_number>
        <data_type>ASCII_Short_String_Collapsed</data_type>
        <maximum_field_length unit="byte">24</maximum_field_length>
        <description>XPath: pds:Product_Observational&lt;1&gt;/pds:Identification_Area&lt;1&gt;/pds:title&lt;1&gt;</description>
    </Field_Delimited>

Next steps
----------

See :doc:`cli` for the full command reference, :doc:`config` for the
configuration-file format, and :doc:`usage_examples` for more examples.
