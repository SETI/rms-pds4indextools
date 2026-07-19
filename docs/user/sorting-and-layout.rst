Sorting and layout of the table
===============================

With your columns chosen, you can also decide how the table looks: the order
of the rows, whether the columns are packed tight or padded to line up, and the
invisible character that ends each line. All three live in the ``output:``
section of your settings file. None of them changes *what* is in the table,
only how it is arranged. This page explains each one and shows the effect on
the finished ``index.csv``.

Sorting the rows
----------------

By default, the rows come out in the order the tool reads the labels, which is
alphabetical by each label's path within the bundle. For ``moon_images`` that
means ``crater_north``, then ``crater_south``, then ``mare_plain``:

.. code-block:: text

   LID,FILE_NAME,TITLE,VERSION
   urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field,1.0
   urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field,1.0
   urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain,1.0

To choose the order yourself, list one or more columns under ``sort_by``, using
the friendly header names you gave your columns. Sorting by ``TITLE`` puts the
rows in alphabetical order of title:

.. code-block:: yaml

   output:
     sort_by:
       - TITLE

which reorders the rows so ``Mare Basalt Plain`` comes first:

.. code-block:: text

   LID,FILE_NAME,TITLE,VERSION
   urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain,1.0
   urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field,1.0
   urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field,1.0

**Ascending by default; a leading dash reverses it.** Sorting runs A to Z (and
low to high) unless you put a ``-`` in front of the column name, which sorts
that column Z to A (and high to low). To list titles in reverse:

.. code-block:: yaml

   output:
     sort_by:
       - -TITLE

**Sort by more than one column.** List several columns and the tool sorts by
the first, breaking ties with the second, and so on. This sorts by version,
and within each version by title:

.. code-block:: yaml

   output:
     sort_by:
       - VERSION
       - TITLE

Each entry can carry its own leading dash, so you can, for example, sort by one
column ascending and another descending. To leave the rows in the natural
reading order, simply give no ``sort_by`` at all, or an empty list.

Comma-separated or fixed-width
------------------------------

The ``fixed_width`` setting chooses between two shapes of table.

With ``fixed_width: false`` (the usual choice), each value is written just as
wide as it needs to be, with commas between them. This is the familiar
comma-separated table that spreadsheets expect:

.. code-block:: text

   LID,FILE_NAME,TITLE,VERSION
   urn:nasa:pds:moon_images:data:mare_plain,mare_plain.xml,Mare Basalt Plain,1.0
   urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field,1.0
   urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field,1.0

With ``fixed_width: true``, the tool pads each value with trailing spaces so
that every column is the same width all the way down. The commas are still
there, but now the columns line up into neat vertical stripes when you open the
file in a plain text editor:

.. code-block:: text

   LID,FILE_NAME,TITLE,VERSION
   urn:nasa:pds:moon_images:data:mare_plain  ,mare_plain.xml  ,Mare Basalt Plain       ,1.0
   urn:nasa:pds:moon_images:data:crater_north,crater_north.xml,North Polar Crater Field,1.0
   urn:nasa:pds:moon_images:data:crater_south,crater_south.xml,South Polar Crater Field,1.0

Both hold exactly the same values. Fixed-width is easier for a human to read
straight from a text editor; the plain comma-separated form is more compact.
Either way the accompanying label describes the layout correctly, so both are
valid to archive. When in doubt, leave ``fixed_width: false``.

Line endings: LF or CRLF
------------------------

Every line in the file ends with an invisible character that marks where one
record stops and the next begins. The ``line_ending`` setting picks which one:

- ``LF`` is the line ending used by macOS and Linux, and is a good, portable
  default.
- ``CRLF`` is the line ending traditionally used by Windows.

.. code-block:: yaml

   output:
     line_ending: CRLF

You cannot see the difference by looking at the table, and most programs
happily read either. Choose ``CRLF`` only if you know your files will be used
by Windows tools that specifically expect it; otherwise ``LF`` is the safe
choice. Whichever you pick, the tool records it in the accompanying label so
the description always matches the file.
