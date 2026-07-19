Choosing which labels to include
================================

Two things together decide which labels end up in your index: where your
bundle lives, and which files inside it you want to read. You give the first
with ``--bundle-root`` and the second with one or more *patterns*. This page
explains both in depth, with plenty of examples against the ``moon_images``
bundle, so you can select exactly the labels you mean, no more and no less.

The bundle root
---------------

The ``--bundle-root`` option names the top folder your labels live under. It
is required on every run that reads labels. For our example it is the
``moon_images`` folder:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --bundle-root moon_images ...

The bundle root does two jobs. First, it is the starting point for the
patterns you write: a pattern like ``data/*.xml`` is understood as "inside the
bundle root, in the ``data`` folder." Second, and just as important, it sets
how file paths appear in your output. Every path the index tool writes is measured
*relative to the bundle root*. So with a bundle root of ``moon_images``, the
label at ``moon_images/data/crater_north.xml`` is recorded in the index as
``data/crater_north.xml``. Choose your bundle root thoughtfully, then, because
it decides how tidy and portable those recorded paths look.

You may point ``--bundle-root`` at a real folder or at a symbolic link that
leads to one; both work the same way.

Patterns: choosing the files
----------------------------

After the options, you give one or more *patterns*. A pattern is a filename
sketch with wildcards in it, and the index tool includes every label whose path
(relative to the bundle root) matches. The simplest useful pattern reaches
into every subfolder and grabs every ``.xml`` file:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --bundle-root moon_images "**/*.xml"

Here ``**`` means "this folder and any folders below it, to any depth," and
``*.xml`` means "any file name ending in ``.xml``." Together they sweep the
whole bundle. Because our three labels live in ``moon_images/data``, this picks
up all three.

The wildcards you can use
-------------------------

Patterns understand a small, dependable set of wildcards. Here is each one,
with an example matched against ``moon_images``:

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * - Wildcard
     - What it means
     - Example and what it matches
   * - ``*``
     - Any run of characters, except a folder separator.
     - ``data/*.xml`` matches all three labels.
   * - ``?``
     - Exactly one character.
     - ``data/crater_n?rth.xml`` matches ``crater_north.xml``.
   * - ``**``
     - This folder and everything beneath it, to any depth.
     - ``**/*.xml`` matches all three labels, wherever they sit.
   * - ``[seq]``
     - Any single character listed inside the brackets.
     - ``data/[cm]*.xml`` matches names starting with ``c`` or ``m``, so all
       three.
   * - ``[!seq]``
     - Any single character **not** listed inside the brackets.
     - ``data/[!m]*.xml`` matches names not starting with ``m``, so the two
       ``crater`` labels.

A slightly trickier one is worth seeing. Because ``?`` matches exactly one
character, ``data/????_*.xml`` matches only ``mare_plain.xml``: ``mare`` is
four characters followed by an underscore, whereas ``crater`` is six and so
does not fit the four ``?`` marks.

Quote your patterns
-------------------

Always wrap your patterns in quotation marks, as every example here does. The
reason is that your terminal's shell also understands ``*``, ``?``, and
``[...]``, and if you leave a pattern unquoted the shell may try to expand it
*before* the index tool ever sees it. Quoting the pattern hands it to the index tool
untouched, so the index tool matches it against your bundle exactly as you wrote it.
Single quotes (``'**/*.xml'``) and double quotes (``"**/*.xml"``) both work.

Using several patterns at once
------------------------------

You may give more than one pattern, separated by spaces, and the index tool includes
any label that matches *any* of them. This is the easy way to combine
selections. For example, to include labels ending in either ``.xml`` or
``.lblx`` (PDS4 labels come with both extensions), give both patterns:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --bundle-root moon_images "**/*.xml" "**/*.lblx"

You can also list specific files, or mix broad and narrow patterns:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --bundle-root moon_images "data/crater_north.xml" "data/mare_plain.xml"

If a label happens to match more than one of your patterns, it still appears
only once in the index; the index tool never duplicates a label.

Patterns must stay inside the bundle
------------------------------------

Patterns are always relative to the bundle root, never absolute. A pattern
that starts with a leading slash, such as ``/data/*.xml``, is rejected with a
message telling you the pattern must be relative to ``--bundle-root``. This is
a safety feature: it keeps every index describing files that genuinely live
under the bundle you named, which is exactly what an archive index should do.
To include files elsewhere, point ``--bundle-root`` at the right folder
instead.

When nothing matches
--------------------

If none of your patterns match any file, the run stops right away and tells
you so, naming the patterns it tried and the bundle root it searched:

.. code-block:: text

   no files matched any of the patterns ['**/*.fits'] under .../moon_images

Nothing is written; there is simply nothing to index. This is almost always a
small mix-up rather than a real problem. Check that the extension is right
(``.xml`` versus ``.lblx``), that any subfolder in the pattern is spelled the
way it appears on disk, and that ``--bundle-root`` points where you think it
does. Adjust the pattern and run again.
