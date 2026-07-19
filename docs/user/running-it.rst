Running the tool and understanding the results
==============================================

Everything comes together here. You have a bundle, you have picked your labels
and columns, and you have a settings file. One command now turns all of that
into a finished index. This page runs that command, reads what the tool prints,
opens the two files it produces, tours the generated label in plain language,
and covers what happens when you run it again.

The full command
----------------

Here is the complete command this guide has been building toward. It names the
bundle root, points at your settings file, chooses the output file name, and
gives the pattern that selects the labels:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --bundle-root moon_images \
       --config-file moon_index.yaml --output-file index.csv "**/*.xml"

Read it as a sentence: *build an index file from the bundle at* ``moon_images``,
*using the settings in* ``moon_index.yaml``, *writing to* ``index.csv``, *from
every* ``.xml`` *label anywhere in the bundle.*

What a successful run looks like
--------------------------------

When the run succeeds, the tool is quiet: it simply returns you to your prompt
with no message. That silence is good news; it means the index was built
without anything worth flagging. (If it is the very first run on your machine,
you may notice a short pause while the tool fetches the PDS4 schemas it needs,
as described on the :doc:`installing` page. That happens once.)

If you would like to watch it work, add ``-v`` to the command. The tool then
prints progress as it generates the label. Add ``-vv`` or ``-vvv`` for
successively more detail. This is purely for your reassurance or curiosity; it
does not change the result.

The two files it produced
-------------------------

Look in the folder where you ran the command and you will find two new files:

.. code-block:: text

   index.csv
   index.lblx

You asked for ``index.csv``, and you got it, together with ``index.lblx``, its
label. The label is always written right next to the table, with the same base
name and a ``.lblx`` extension, so the pair travels together.

Reading the table
-----------------

Open ``index.csv`` in a spreadsheet program or a text editor. You will see the
header row you designed, then one row per label:

.. code-block:: text

   LID,FILE_NAME,TITLE,VERSION
   urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain,1.0
   urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field,1.0
   urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field,1.0

Each column is one of your choices, each row is one of the three labels, and
the rows are sorted by title because that is what your settings file asked for.
This is your index. You can search it, sort it further in a spreadsheet, or
hand it to a colleague, and it stands on its own.

A plain-language tour of the label
----------------------------------

Now open ``index.lblx``. It is an XML label, longer than the table, and you
never need to edit it by hand, but it is worth understanding what it says about
your index. It falls into two parts.

The first part identifies the index product, using the details you gave in
``label_contents:``: its logical identifier, version, title, and product kind,
followed by a short modification history and standard license information the
tool supplies for you:

.. code-block:: xml

   <Identification_Area>
       <logical_identifier>urn:nasa:pds:moon_images:index</logical_identifier>
       <version_id>1.0</version_id>
       <title>Moon Images Index</title>
       ...
   </Identification_Area>

The second part describes the table file itself. It records the file's name, a
creation timestamp, and a checksum, the number of records, and, one by one, a
description of every column, giving each column's header, its position, its
data type, and a note of where its values came from:

.. code-block:: xml

   <Field_Delimited>
       <name>TITLE</name>
       <field_number>3</field_number>
       <data_type>ASCII_Short_String_Collapsed</data_type>
       ...
   </Field_Delimited>

You do not have to produce any of that; the tool measures your table and writes
this description to match it exactly. The upshot is that ``index.lblx`` is a
complete, valid PDS4 label ready to archive alongside ``index.csv``. Together,
the two files are a finished index product.

Running it again: the auto-numbered names
------------------------------------------

Suppose you run the tool again, letting it use its default output name of
``index.csv`` and its matching ``index.lblx``, but those files already exist
from a previous run. Rather than overwrite your earlier work, the tool leaves
it in place and writes to the next free numbered name, telling you so:

.. code-block:: text

   default output name in use; writing to .../index_1.csv and .../index_1.lblx instead

Run it a third time and you get ``index_2.csv``, and so on. This safety net
applies to the default names. If you name the output yourself with
``--output-file`` and that file already exists, the tool assumes you meant it
and overwrites, printing a brief note that it is doing so. So the rule of thumb
is: rely on the default names and old results are preserved automatically;
name the file yourself and you are in charge of it.

When one label has a problem
----------------------------

If one of your labels cannot be read, perhaps it is not well-formed XML or is
missing a required piece, the tool stops at that first problem, tells you which
file and what was wrong, and writes nothing:

.. code-block:: text

   .../data/broken.xml: failed to parse label: Premature end of data ...

Stopping early is helpful when you want to fix problems one at a time. But when
you would rather see *every* troubled label in one pass, add ``--fail-slow``.
The tool then works through all the labels, collects every problem, and reports
them together at the end:

.. code-block:: text

   .../data/broken.xml: failed to parse label: Premature end of data ...
   .../data/no_lid.xml: label must contain exactly one <logical_identifier>; found 0
   2 errors

Either way, if any label failed, no index is written; the tool never produces a
half-built index that quietly omits products. Fix the labels it named and run
again, and once every label is clean you will get your two files.
