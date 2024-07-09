``pds4_create_xml_index`` Program
=================================

The RMS Node's PDS4 Index Creation Tool (``pds4_create_xml_index``) is designed to
facilitate the extraction and indexing of information from `Planetary Data System (PDS)
<https://pds.nasa.gov>`_ `PDS4-format <https://pds.nasa.gov/datastandards/documents/>`_
label files. This tool automates the process of parsing specified directories for label
files, extracting user-defined elements using XPath expressions, and generating organized
output files. Users can customize the extraction process through various options, such as
filtering content, sorting output, and integrating additional file metadata. The tool
supports flexibility with configuration files and provides a straightforward interface for
creating both CSV-based (variable or fixed-width) index files and text files listing
available XPath headers. Whether for scientific research, data management, or archival
purposes, the PDS4 Index Creation Tool offers a robust solution for efficiently managing
and accessing structured data within PDS4-compliant datasets.


XPath Syntax and Structure
--------------------------

Before using the tool, it is imperative that the user becomes comfortable with
the XPath language and how it is parsed with ``lxml``.

When elements are scraped from a label, they are returned in a format akin to a
filepath. The absolute XPath contains all parent elements up to the root element
of the label. Each element after a certain depth can also contain predicates:
numbers surrounded by square brackets. These predicates give information on the
location of the element in the label file, in relation to surrounding elements.

However, this module returns XPath headers that have been reformatted from XPath
syntax.

- Namespaces are replaced by their prefixes. Namespaces are URIs that identify
  which schema an element belongs to. For readability, the full URI's are
  replaced by their prefixes.

- Square brackets are replaced by angled brackets. This module utilizes ``glob``
  syntax for finding label files and filtering out elements/attributes. Because
  square brackets have meaning within ``glob`` statements, they needed to be
  replaced with angled brackets.

- The values within the predicates have been renumbered. In XPath syntax,
  predicates are used to determine the location of an element in relation to its
  parent. While this is useful in other applications, this logic fails if
  multiples of the element and its parent appear within the document. Even if
  the elements all have different values, all of their XPaths would be the same.
  Instead, the predicates are renumbered to reflect which instance of the
  element the value is represented by.


Command Line Arguments
----------------------

Required arguments
^^^^^^^^^^^^^^^^^^

Two command line arguments are required in every run.

The first is the top-level directory of the collection, bundle, or other directory
structure where the label files are location. All file path strings included in the index
file and/or label will be given relative to this directory.

The second is one or more ``glob``-style patterns that specify the filenames of the labels
to be scraped. The patterns should be given relative to the top-level directory.
``glob``-style patterns allow wildcard symbols similar to those used by most
Unix shells:

- ``?`` matches any single character within a directory or file name
- ``*`` matches any series of characters within a directory or file name
- ``**`` matches any filename or zero or more nested directories
- ``[seq]`` matches any character in ``seq``
- ``[!seq]`` matches any character not in ``seq``

To avoid interpretation by the shell, all patterns must be surrounded by double quotes.
If more than one pattern is specified, they should each be surrounded by double quotes
and separated by spaces.

Example::

    pds4_create_xml_index /top/level/directory "data/planet/*.xml" "**/rings/*.xml"

Optional arguments
^^^^^^^^^^^^^^^^^^

Index file generation
"""""""""""""""""""""

- ``--output-index-file INDEX_FILEPATH``: Specify the location and filename of the index
  file. This file will contain the extracted information organized in CSV format. It is
  recommended that the file have the suffix ``.csv``. If no directory is specified, the
  index file will be written into the current directory. If this option is omitted
  entirely, the default filename ``index.csv`` will be used. However, to prevent
  accidentally overwriting an existing index file, if ``index.csv`` already exists in the
  current directory, the index will be written into ``index1.csv``, ``index2.csv``, etc.
  as necessary.

- ``--add-extra-file-info COMMA_SEPARATED_COLUMN_NAMES``: Generate additional information
  columns in the index file. One or more column names can be specified separated by
  commas. The available column names are:

  - ``filename``: The base filename of the label file.
  - ``filepath``: The path of the label file relative to the top-level directory.
  - ``bundle_lid``: The LID of the bundle containing the label file.
  - ``bundle``: The name of the bundle containing the label file.

- ``--sort-by COMMA_SEPARATED_HEADER_NAME(s)``: Sort the resulting index file by the value
  in one or more columns. The column names are those that appear in the final index file,
  as modified by ``--simplify-xpaths``, ``--limit-xpaths-file``, or
  ``--clean-header-field-names``, and include any additional columns added with
  ``--add-extra-file-info``. To see a list of available column names, use
  ``--output-headers-file``. More than one sort key can be specified by separating them by
  commas, in which case the sort proceeds hierarchically from left to right. As the XPath
  syntax includes special characters that may be interpreted by the shell, it may be
  necessary to surround the list of sort keys with double quotes.

  Example::

    pds4_create_xml_index <...> --sort-by "pds:Product_Observational/pds:Identification_Area<1>/pds:version_id<1>,pds:logical_identifier,"

- ``--fixed-width``: Format the index file using fixed-width columns.

- ``--clean-header-field-names``: Rename column headers to use only characters permissible
  in variable names, making them more compatible with certain file readers.

- ``--simplify-xpaths``: Where possible, rename column headers to use only the tag instead
  of the full XPath. If this would cause ambiguity, leave the name using the full XPath
  instead. This will usually produce an index file with simpler column names, potentially
  making the file easier to display or use.

Limiting results
""""""""""""""""

- ``--limit-xpaths-file XPATHS_FILEPATH``: Specify a text file containing a list of
  specific XPaths to extract from the label files. If not specified, all elements found in
  the label files will be included. The given text file can specify XPaths using
  ``glob``-style syntax, where each XPath level is treated as if it were a directory in a
  filesystem. Available wildcards are:

  - ``?`` matches any single character within an XPath level
  - ``*`` matches any series of characters within an XPath level
  - ``**`` matches any tags and zero or more nested XPath levels
  - ``[seq]`` matches any character in ``seq``
  - ``[!seq]`` matches any character not in ``seq``

  For example, the XPath ``pds:Product_Observational/pds:Identification_Area<1>/pds:version_id<1>``
  could be matched using:

  - ``pds:Product_Observational/pds:Identification_Area<1>/pds:version_id<1>``
  - ``pds:Product_Observational/pds:Identification_Area<1>/*``
  - ``pds:Product_Observational/**/*version*``
  - ``pds:Product_Observational/**``

  In addition, XPaths can be removed from the selected set by prefacing the pattern with ``!``.
  For example, the following set of patterns would select all XPaths except for any
  containing the string ``version`` somewhere in the name::

    **
    !**/*version*

- ``--output-headers-file HEADERS_FILEPATH``: Write a list of all column names included in
  the index file. The column names will precisely agree with those given in the first line
  of the index file, as modified by ``--simplify-xpaths``, ``--limit-xpaths-file``, or
  ``--clean-header-field-names``, and include any additional columns added with
  ``--add-extra-file-info``. This file is useful to easily verify the contents of the
  index file and also to serve as a starting point for a file to be supplied to
  ``--limit-xpaths-file``.

Label generation
""""""""""""""""

- ``--generate-label {ancillary,supplemental}``: Generate a label file describing the
  index file. The label file will be placed in the same directory as the index file and
  will have the same name except that the suffix will be ``.xml``. The required argument
  specifies the type of metadata class to use in the label file, ``Product_Ancillary`` for
  ``ancillary`` or ``Product_Metadata_Supplemental`` for ``supplemental``. Additional
  customization of the label can be provided with ``--label-user-input``.

- ``--label-user-info``: Provide a file containing customization of the generated label.
  The file must be in YAML format.

Miscellaneous
"""""""""""""

- ``--verbose``: Display detailed information during the file scraping process that may
  be useful for debugging.

- ``--config-file``: Specify a ``.ini``-style configuration file for further customization
  of the extraction process.
