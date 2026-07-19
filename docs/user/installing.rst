Installing the tool
===================

The tool ships as a small Python package. Installing it puts a single new
command on your system, ``pds4_create_xml_index``, which you run from a
terminal. This page walks you through the install, shows you how to confirm it
worked, and explains the one thing it needs from the internet.

Before you begin
----------------

You need Python and its package installer, ``pip``, available in your
terminal. Most modern systems already have them. You can check with these two
commands, which simply print version numbers:

.. code-block:: console

   $ python --version
   $ pip --version

If both print a version, you are ready. (On some systems the commands are
spelled ``python3`` and ``pip3``; use whichever works for you, and use the
same spelling throughout.) If neither is found, install Python from
`python.org <https://www.python.org/downloads/>`_ first; ``pip`` comes with it.

Installing with pip
-------------------

Install the tool with a single command:

.. code-block:: console

   $ pip install pds4-create-xml-index

That downloads the tool and everything it depends on, then installs the
``pds4_create_xml_index`` command. When it finishes you will see a line such
as ``Successfully installed pds4-create-xml-index`` near the end of the
output.

.. tip::

   If you like to keep each tool in its own tidy corner, you can create a
   Python *virtual environment* first and install into that. This is optional
   and entirely up to your habits; the plain ``pip install`` above works fine
   on its own.

Confirming it worked
--------------------

Two quick checks tell you the install succeeded. First, ask the tool for its
version:

.. code-block:: console

   $ pds4_create_xml_index --version

This prints the tool's name followed by a version number. If you see that,
the command is installed and on your path.

Second, ask it for help:

.. code-block:: console

   $ pds4_create_xml_index --help

This prints a short usage summary listing the three things the tool can do,
which the rest of this guide explains. You can also ask any individual command
for its own help, for example:

.. code-block:: console

   $ pds4_create_xml_index generate_index_file --help

If both ``--version`` and ``--help`` respond, your install is healthy and you
are ready to build an index.

A note about the internet and schemas
-------------------------------------

PDS4 labels point at official schema files that spell out the rules of the
PDS4 standard, and the tool reads those schemas so it can describe your
columns correctly. The first time you run it, it downloads the handful of
schemas your labels refer to. This happens automatically; you do not configure
anything, and you will not usually notice it beyond a brief pause on that first
run.

After that first download the tool keeps a local copy, so later runs reuse it,
start faster, and can even work with no network connection at all. In short:
be online the first time, and after that it takes care of itself.
