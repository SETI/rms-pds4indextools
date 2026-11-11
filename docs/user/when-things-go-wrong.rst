When things go wrong
====================

Every so often a run ends with a message instead of an index. Almost always it
is a small, fixable mix-up, and the index tool tries to tell you exactly what it
found. This page is organized by *symptom*: find the one that matches what you
are seeing, read what it means, and follow the fix. Nothing here requires you
to understand the index tool's inner workings.

"It says no files matched"
--------------------------

*What you see:* a message that no files matched your patterns under the bundle
root, and no output written.

*What it means:* the index tool looked where you told it and found nothing to index.
The patterns and the folder simply did not line up.

*How to fix it:* check three things. Is the extension right, ``.xml`` versus
``.lblx``? Is every subfolder named in the pattern spelled exactly as it is on
disk? Does ``--bundle-root`` point at the folder you think it does? A broad
pattern like ``"**/*.xml"`` is a good way to confirm the index tool can see your
labels at all; narrow it down once that works. See :doc:`choosing-labels`.

"It stopped on one label and wrote nothing"
-------------------------------------------

*What you see:* the run halts naming a single label and describing what was
wrong with it, such as a parsing problem or a missing required piece, and no
files appear.

*What it means:* one of your labels could not be read, so the index tool stopped
rather than build an index that silently left a product out.

*How to fix it:* open the named label and correct the problem it described,
then run again. If you would rather see *all* the troubled labels at once
instead of fixing them one at a time, add ``--fail-slow``: the index tool then works
through every label, gathers all the problems, and lists them together at the
end. Note that even with ``--fail-slow``, if any label failed, no index is
written; fix them all and rerun. See :doc:`running-it`.

"Some non-string columns are absent from some labels and set no missing_value"
------------------------------------------------------------------------------

*What you see:* the run stops before writing anything, with a message that
lists one or more columns with their data types, how many labels lack each
one, and a few example label files.

*What it means:* each listed column is a number, date, or other non-text
column that points to an element some labels do not contain, and the column
does not say what to write in its place. (A text column in the same situation
is simply filled with ``missing``.) Either the element really is absent from
those labels, or the column address points at a slightly different place than
you intended.

*How to fix it:* open one of the example labels and check whether it really
lacks that piece of information. If it does, add a ``missing_value:`` to that
column's entry; the message suggests one, such as ``'-998.0'`` for a real
number. See :doc:`configuration-reference`. If the label *does* have it,
re-check the column address against that label.

"It says missing_value '' is only allowed for string columns"
-------------------------------------------------------------

*What you see:* the run stops before writing anything and lists columns that
set ``missing_value: ''``.

*What it means:* a blank cell is allowed only in a text column. The listed
columns hold numbers, dates, or other formatted values.

*How to fix it:* give each listed column a non-blank ``missing_value:``, such
as ``'-999'``.

"A value looks wrong"
---------------------

*What you see:* the index builds fine, but a column holds a value you did not
expect, such as ``missing``.

*What it means:* usually the column address points at a slightly different
place than you intended, or the label lacks the element and the cell holds
the placeholder: your ``missing_value:``, or ``missing`` for a text column
that sets none.

*How to fix it:* re-check the column address against a label that has the
value. The surest way to get an address right is to let the index tool write it for
you with ``generate_xpath_list`` and copy the exact line, rather than typing an
address by hand. See :doc:`choosing-columns`.

"It can't reach the schemas, or I'm offline"
--------------------------------------------

*What you see:* on a first run, a message about being unable to fetch or reach
the PDS4 schemas.

*What it means:* PDS4 labels refer to official schema files, and the index tool needs
to read them. The very first time, it downloads the ones your labels use, so it
needs the internet for that one run.

*How to fix it:* connect to the internet and run it once. After that first
successful run the index tool keeps a local copy of the schemas it fetched, so
later runs that need only those schemas are faster and work with no connection
at all. Priming only covers the schemas already in that copy, so a bundle that
uses a schema version you have not fetched before will need a connection once
more for that one. If you are behind a restrictive network, running it once
somewhere with normal internet access is enough to prime it for the schemas it
sees there. See :doc:`installing`.

"My settings file was rejected"
-------------------------------

*What you see:* a message that the settings file could not be read or is not
valid, sometimes pointing at a line number.

*What it means:* the YAML in your settings file has a formatting slip. YAML is
picky about layout, and a few small mistakes account for most rejections:

- **A tab where spaces belong.** YAML must be indented with spaces, never
  tabs. If your editor inserted a tab, replace it with spaces. This is by far
  the most common cause.
- **Uneven indentation.** Every item at the same level must be indented by the
  same amount. A line that is one space off can spoil the block it belongs to.
  Line up your indentation carefully, using the same number of spaces per
  level throughout.
- **A value that needed quotes.** A value that is all digits or looks like a
  number or date can be misread. Wrap such values in single quotes, for
  example ``version_id: '1.0'``.

*How to fix it:* open the file, look near the line the message mentions, and
check those three things first. The page :doc:`the-settings-file` walks through
the YAML rules from the start if you would like a refresher.

"It says the index is missing its name or kind"
-----------------------------------------------

*What you see:* a message that the logical identifier or the product class is
required.

*What it means:* every run, even one that only lists columns, must know a
little about the index it is preparing to build: the identifier you are giving
it and what kind of product it is. Those two are required and were not found in
your settings.

*How to fix it:* add a ``label_contents:`` section to your settings file with
at least a ``logical_identifier`` and a ``product_class``:

.. code-block:: yaml

   label_contents:
     logical_identifier: urn:nasa:pds:moon_images:index
     product_class: Product_Ancillary

See :doc:`describing-the-index` for what each field means and which values
``product_class`` accepts.

"It refused to overwrite my file"
---------------------------------

*What you see:* when copying the default settings with ``copy_default_config``,
a message that the destination already exists.

*What it means:* the index tool will not silently overwrite an existing settings file,
so you cannot lose your work by accident.

*How to fix it:* either choose a different name with ``--output-file``, or, if
you really do want to replace the existing file, add ``--force`` to allow it.

.. note::

   When *building an index*, the default output names behave differently: if
   ``index.csv`` already exists, the index tool quietly writes ``index_1.csv``
   instead of refusing, so it never overwrites an earlier index. This is
   covered on the :doc:`running-it` page.
