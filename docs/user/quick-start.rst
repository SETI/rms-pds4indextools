Quick start
===========

This page is the shortest path from a bundle of PDS4 labels to a finished
index. It assumes you already understand the flow; if any step is unfamiliar,
each one links to the tutorial page that explains it in full. In four small
steps you will produce two files: an index table, ``index.csv``, and its
PDS4 label, ``index.lblx``.

1. Get a starter settings file
------------------------------

Ask the index tool for a copy of its built-in defaults to build on:

.. code-block:: console

   $ pds4_create_xml_index copy_default_config --output-file moon_index.yaml

That writes a commented ``moon_index.yaml`` you can open and edit. (You can
also start from a blank file and type the few settings by hand.) See
:doc:`the-settings-file`.

2. See the columns you can choose from (optional)
-------------------------------------------------

If you are not sure what to put in your columns, let the index tool read your labels
and hand you a ready-to-edit list of every available custom column:

.. code-block:: console

   $ pds4_create_xml_index generate_xpath_list --bundle-root moon_images \
       --output-file columns.yaml "**/*.xml"

Open ``columns.yaml``, keep the rows you want, and give each a friendly
``name:``. See :doc:`choosing-columns`.

3. Fill in the columns and the description
------------------------------------------

Edit ``moon_index.yaml`` so it lists the columns you want and describes the
index you are creating. The columns are a list, each with either a ready-made
``auto:`` token or a custom ``xpath:``, plus an optional header ``name:``. The
description needs at least a ``logical_identifier:`` and a ``product_class:``:

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

Every setting is spelled out on the :doc:`configuration-reference` page.

4. Build the index
------------------

Point the index tool at your bundle, hand it the settings file, and give it a glob
pattern for the labels to include:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --bundle-root moon_images \
       --config-file moon_index.yaml --output-file index.csv "**/*.xml"

It writes ``index.csv`` and, beside it, ``index.lblx``. With the settings
above, the table looks like this, one row per label and sorted by title:

.. code-block:: text

   LID,FILE_NAME,TITLE,VERSION
   urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,Crater North,1.0
   urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,Crater South,1.0
   urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Plain,1.0

That is the whole loop. For a guided walkthrough of any step, start at
:doc:`the-big-picture`; for every command and flag, see
:doc:`command-reference`; and for the complete settings-file specification,
see :doc:`configuration-reference`.
