What this tool does for you
===========================

Welcome. If you look after a bundle of PDS4 data, you have almost certainly
faced a familiar chore: you need a single, tidy summary of everything in the
bundle. Which products are in there? What are their titles, their
identifiers, their versions, the dates they were observed? The answers all
live inside the individual PDS4 labels, but they are scattered across dozens,
hundreds, or thousands of separate files. Opening each one by hand to copy a
value into a spreadsheet is slow, tedious, and easy to get wrong.

This tool does that chore for you. You point it at your folder of labels, you
tell it once which pieces of information you care about, and it reads every
label and gathers those pieces into a single table. That is what an *index*
is: one table, one row per product, one column per piece of information, so
that the whole bundle can be seen at a glance, searched, sorted, and handed to
someone else.

This guide is written for you, the archivist or data producer. It assumes you
are comfortable with your data and with typing commands into a terminal, but
it assumes nothing about programming, and it never asks you to read or
understand any source code. Everything is explained in terms of what you type
and what you see.

The two files you get
---------------------

Every successful run produces two files that belong together:

- **The table** itself, saved as a comma-separated values file (a ``.csv``
  file, which opens in any spreadsheet program or text editor). This is the
  index: a header row naming your columns, then one row for each label.

- **A PDS4 label for that table**, saved with a ``.lblx`` extension. Just as
  each of your data products has a label describing it, your new index table
  is itself a small archive product, so it needs its own label. The tool
  writes that label for you, describing every column in the table and filling
  in the housekeeping details (dates, record counts, a checksum) automatically.
  The result is ready to place in an archive alongside your data.

You provide the interesting choices; the tool handles the bookkeeping.

What you need before you start
------------------------------

To follow along you need three things:

1. **A folder of PDS4 labels.** These are the XML label files that come with
   your data, usually ending in ``.xml`` or ``.lblx``. This guide calls that
   folder your *bundle*, and it can be organized into subfolders however you
   like.

2. **Python and its installer, pip.** The tool is a small Python program. If
   you can already run ``python`` and ``pip`` from a terminal, you are set;
   the next page walks through installing the tool itself. You do not need to
   write any Python.

3. **An internet connection the first time you run it.** PDS4 labels refer to
   official schema files that describe the PDS4 standard, and the tool fetches
   those the first time it needs them. After that it remembers them, so later
   runs are faster and can even work offline. There is nothing you need to set
   up for this; it just happens.

How this guide is organized
---------------------------

This is a walkthrough, not a dry reference, so it is meant to be read roughly
in order the first time. You will install the tool, meet a small example
bundle that reappears on every page, learn how to choose which labels and
which columns go into your index, write a short settings file that records
your choices, run the tool, and read the results. A reference page near the
end lists every command and option for later lookup, and a final page helps
you out when something does not go as planned.

Take your time and try the examples as you go. By the end you will be able to
turn any folder of PDS4 labels into a finished, archive-ready index.
