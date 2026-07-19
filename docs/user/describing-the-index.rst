Describing your index product
=============================

Your index table is itself an archive product, so it needs its own PDS4 label.
The tool writes that label for you, but a few things about the index only you
can decide: what to call it, what kind of product it is, and how to title it.
You provide those in the ``label_contents:`` section of your settings file.
This page walks through each piece of information you can give, which pieces
are required, and what the tool fills in on its own.

Keep in mind throughout that this section describes the *index you are
creating*, not the data labels you are reading. The identifier and title here
belong to your new index table.

The two required pieces
-----------------------

Two settings must always be present. The tool needs them for every run, even
when you are only listing columns.

**A logical identifier for your index.** This is the unique name you are
assigning to the index product, in the same ``urn:nasa:pds:...`` style your
other products use. Give your index its own identifier, distinct from any data
product:

.. code-block:: yaml

   logical_identifier: urn:nasa:pds:moon_images:index

**The kind of product it is.** PDS4 has a specific category for tables like
this, and you choose one of exactly two values:

- ``Product_Ancillary`` marks the index as an ancillary product that
  accompanies and supports the data in your bundle.
- ``Product_Metadata_Supplemental`` marks it as a supplemental metadata table
  that summarizes the products in your bundle.

Pick whichever your archive expects for an index of this sort; if you are
unsure, follow the convention already used in your project.

.. code-block:: yaml

   product_class: Product_Ancillary

With just those two lines the tool will run, but a good label deserves a couple
more details.

The recommended extras
----------------------

**A title.** A short, human-readable name for the index. This is what a person
sees when they look at your product, so make it descriptive:

.. code-block:: yaml

   title: Moon Images Index

**A version.** The version of the index product itself. Quote it so it is kept
as text rather than read as a number:

.. code-block:: yaml

   version_id: '1.0'

Putting the required and recommended pieces together gives the
``label_contents:`` block this guide uses:

.. code-block:: yaml

   label_contents:
     logical_identifier: urn:nasa:pds:moon_images:index
     product_class: Product_Ancillary
     version_id: '1.0'
     title: Moon Images Index

Optional descriptive information
--------------------------------

If your archive likes fuller labels, you can add two more optional blocks.

**Citation information** records who made the index and when, so others can
cite it. You provide the parts you have, such as an author list, a year, and a
short description:

.. code-block:: yaml

   label_contents:
     logical_identifier: urn:nasa:pds:moon_images:index
     product_class: Product_Ancillary
     version_id: '1.0'
     title: Moon Images Index
     Citation_Information:
       author_list: Lunar Team
       publication_year: '2026'
       description: An index of the Moon Images bundle.

**A modification note** records the history of the product. Each entry is a
date, a version, and a short note of what changed. Because it is a list, start
each entry with a dash:

.. code-block:: yaml

   label_contents:
     logical_identifier: urn:nasa:pds:moon_images:index
     product_class: Product_Ancillary
     version_id: '1.0'
     title: Moon Images Index
     Modification_Detail:
       - modification_date: '2026-07-01'
         version_id: '1.0'
         description: First public release of the index.

If you leave the modification note out entirely, the tool writes a sensible
default for you: a single entry dated the day you run it, carrying your version
and the note ``Initial version.`` So a first release needs no modification
block at all unless you want to word it yourself.

What the tool fills in for you
------------------------------

You only supply the information above. Everything else in the label, the tool
works out and writes automatically, so you never hand-edit the finished label:

- the current date and a creation timestamp,
- the number of records and columns in your table,
- a checksum and the byte sizes of the file,
- a full description of every column, including its header and where its
  values came from,
- and the standard boilerplate a valid PDS4 label requires.

The result is a complete, archive-ready label that matches your table exactly.
You will get a plain-language tour of that finished label on the page
:doc:`running-it`.
