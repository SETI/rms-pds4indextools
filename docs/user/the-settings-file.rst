Writing your settings file
==========================

Your settings file is one short text file that records every choice you make:
which columns you want, how the table should look, and how to describe the
finished index. Writing it down once means you never retype those choices, and
you can rerun the exact same index whenever your data changes. The file is
written in a format called YAML. If you have never met YAML, this page teaches
you just enough of it, gently, and then builds our example settings file up one
section at a time.

A five-minute introduction to YAML
----------------------------------

YAML is a plain-text way of writing down settings so that both you and the
tool can read them. You write it in any text editor and save it with a
``.yaml`` ending. There are only a few rules to learn.

**Settings are written as** ``key: value`` **pairs.** A name, a colon, a
space, then the value:

.. code-block:: yaml

   title: Moon Images Index

**Indentation shows what belongs to what.** When one setting contains others,
the inner settings are indented underneath it. Here ``fixed_width`` and
``line_ending`` belong to ``output``:

.. code-block:: yaml

   output:
     fixed_width: false
     line_ending: LF

**Indent with spaces, never tabs.** This is the single most common thing to
trip over. Use two spaces per level (any consistent number of spaces works,
but be consistent). If your editor inserts a tab when you press the Tab key,
turn that setting off or type the spaces by hand; a stray tab makes the whole
file unreadable to the tool.

**Lists use a dash.** When a setting holds several items, write each on its own
line, indented, starting with a dash and a space:

.. code-block:: yaml

   sort_by:
     - TITLE
     - VERSION

**A list can hold whole groups, not just single values.** Each dash can
introduce a small block of ``key: value`` pairs. This is exactly how a column
is written: the dash starts a new column, and the lines indented under it
describe that column:

.. code-block:: yaml

   columns:
     - auto: lid
       name: LID
     - auto: filename
       name: FILE_NAME

**Quote a value when it might be mistaken for something else.** Most text needs
no quotes, but wrap a value in single quotes when it is all digits, or looks
like a number or a date, but you want it kept as text. A version like ``1.0``
would otherwise be read as the number one, so write it quoted:

.. code-block:: yaml

   version_id: '1.0'

**Comments start with a hash.** Anything after a ``#`` on a line is a note for
humans and is ignored by the tool. Use comments freely to remind yourself what
a setting is for:

.. code-block:: yaml

   # Sort the table alphabetically by title.
   sort_by:
     - TITLE

That is genuinely all the YAML you need. Now let us build the real file.

A friendly starting point
-------------------------

You can start from a blank file, or you can ask the tool to hand you a copy of
its built-in defaults to build on:

.. code-block:: console

   $ pds4_create_xml_index copy_default_config --output-file moon_index.yaml

This writes a file of sensible default settings, with comments, that you can
open and edit. It is a comfortable place to begin, though you will still add
your own columns and a description of your index, which the next sections walk
through. (If the file you name already exists, the tool declines to overwrite
it unless you add ``--force``, so you cannot clobber your work by accident.)

Building the file, section by section
-------------------------------------

A settings file for building an index has three main sections: ``columns:``,
``output:``, and ``label_contents:``. We will add them one at a time and end up
with the complete ``moon_index.yaml`` used throughout this guide.

**1. The columns.** This is the block you prepared on the previous page: the
list of columns, in the order you want them, each with a friendly header.

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

**2. The output settings.** This block controls how the table is written. Here
we ask for comma-separated (not fixed-width) output, plain line endings, and
rows sorted by title. The next page, :doc:`sorting-and-layout`, explains each
of these choices in full; for now, add the block as shown.

.. code-block:: yaml

   output:
     fixed_width: false
     line_ending: LF
     sort_by:
       - TITLE

**3. The description of the index.** This block, ``label_contents:``, tells the
tool how to describe the index product it is about to create: the name you are
giving your index, the kind of product it is, its title, and its version. The
next page, :doc:`describing-the-index`, covers every field; here is the block
for our example.

.. code-block:: yaml

   label_contents:
     logical_identifier: urn:nasa:pds:moon_images:index
     product_class: Product_Ancillary
     version_id: '1.0'
     title: Moon Images Index

Put the three blocks together, one after another, and you have the finished
settings file:

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

Save that as ``moon_index.yaml``. It is everything the tool needs to build the
index, and on the page :doc:`running-it` you will use it to do exactly that.

Layering more than one settings file
-------------------------------------

You can hand the tool more than one settings file, and it combines them in the
order you list them, with later files winning where they overlap. You do this
by giving ``--config-file`` more than once:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --bundle-root moon_images \
       --config-file moon_index.yaml --config-file overrides.yaml "**/*.xml"

This is handy when you want a shared base of settings plus a small tweak for
one run. Suppose ``moon_index.yaml`` sorts by title, but for a single report
you want the rows sorted by version instead. Rather than editing your main
file, put just the change in a tiny second file, ``overrides.yaml``:

.. code-block:: yaml

   output:
     sort_by:
       - VERSION

Because it is listed last, its ``sort_by`` replaces the one in the base file,
while every other setting in ``moon_index.yaml`` is left untouched. Layering
lets you keep one dependable base file and reach for small overlays only when
you need them.
