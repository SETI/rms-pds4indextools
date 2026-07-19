The big picture: from a bundle to an index
==========================================

Before diving into the details, it helps to hold the whole journey in your
head. It is short. This page sketches the flow from start to finish and then
introduces the small example bundle that every later page uses, so that the
detailed steps ahead always have something concrete to point at.

The whole journey in one picture
--------------------------------

Building an index is a straight line with four stops:

1. **You point the index tool at a folder of labels.** This folder is your *bundle
   root*. Every file the index tool reports is named relative to it, so it is the
   anchor for the whole run.

2. **You tell the index tool which labels to read.** You do this with one or more
   *patterns*, like ``**/*.xml``, which pick out label files inside the
   bundle. The index tool opens each matching label and looks inside.

3. **You tell the index tool what you want in the table.** Your *columns* and a few
   layout choices live in a small *settings file* written in YAML. This is the
   one place your decisions are recorded, so you never have to retype them.

4. **The index tool writes the two output files.** It produces the ``index.csv``
   table and a matching ``.lblx`` label that describes it. Both land in the
   same folder, ready to use or archive.

In one sentence: *point it at a folder, choose which labels and which columns,
and it writes the table and the table's label.* Everything else in this guide
is just filling in those four stops with confidence.

Meet the example bundle
-----------------------

Throughout this guide we work with a tiny imaging bundle called
``moon_images``. It holds three PDS4 labels, one per observation, tucked in a
``data`` subfolder:

.. code-block:: text

   moon_images/
   └── data/
       ├── crater_north.xml
       ├── crater_south.xml
       └── mare_plain.xml

Your own bundles will be larger and may have many subfolders, but the ideas
are exactly the same. Three labels are just enough to see everything clearly.

One label, up close
-------------------

Here is the full content of ``crater_north.xml``. If you have seen a PDS4
label before, it will look familiar; if you have not, do not worry, because
the index tool reads it for you and you only ever pick out the pieces you want:

.. code-block:: xml

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

The other two labels are the same shape with different values. ``crater_south.xml``
has the identifier ending in ``crater_south`` and the title
``South Polar Crater Field``; ``mare_plain.xml`` ends in ``mare_plain`` and is
titled ``Mare Basalt Plain``.

Notice that every label carries a handful of useful facts: a logical
identifier (a unique name for the product), a version, a human-readable title,
and so on. An index is simply a table that lifts the facts you choose out of
each label and lines them up side by side. By the end of this guide you will
have turned these three labels into exactly that:

.. code-block:: text

   LID,FILE_NAME,TITLE,VERSION
   urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain,1.0
   urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field,1.0
   urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field,1.0

Do not worry about how to get there yet. The pages that follow build up to
this result one small, comfortable step at a time, starting with how you choose
which labels go in.
