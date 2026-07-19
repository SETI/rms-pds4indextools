Quickstart
==========

This walkthrough generates an index CSV and its PDS4 label from the
``simple_pds_only`` example bundle that ships in the test suite. The bundle
holds a single observational label, ``row1.lblx``.

Running the tool
----------------

From the repository root, scrape every ``.lblx`` label under the bundle and
write an index file named ``index.csv``::

    pds4_create_xml_index generate_index_file \
        --bundle-root tests/data/bundles/simple_pds_only \
        --config-file tests/data/configs/simple.yaml \
        --output-file index.csv \
        '**/*.lblx'

The ``--config-file`` YAML names three columns: the logical identifier, the
file name, and the product title. Label discovery is glob-driven, so the
``'**/*.lblx'`` pattern selects the labels; quote the pattern so the shell
does not expand it.

The index CSV
-------------

The command writes ``index.csv`` with one header row and one data row::

    LID,FILE_NAME,TITLE
    urn:nasa:pds:test_simple:index:row1,row1.lblx,Row 1

The label
---------

Alongside the CSV, the tool writes ``index.lblx``, a PDS4 label that
describes the CSV as a delimited table. The excerpt below shows the field
definition generated for the first column::

    <Field_Delimited>
        <name>LID</name>
        <field_number>1</field_number>
        <data_type>ASCII_LID</data_type>
        <maximum_field_length unit="byte">35</maximum_field_length>
        <description>XPath: lid</description>
    </Field_Delimited>

Next steps
----------

See :doc:`cli` for the full command reference, :doc:`config` for the
configuration-file format, and :doc:`usage_examples` for more workflows.
