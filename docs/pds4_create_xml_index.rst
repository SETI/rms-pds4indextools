``pds4_create_xml_index`` Program
=================================

Introduction
------------

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

``pds4_create_xml_index`` generates index file headers that represent the position of each
element in the XML hierarchy in a manner similar to `the standard XPath format
<https://developer.mozilla.org/en-US/docs/Web/XPath>`_. While familiarity with XPath
syntax is beneficial, it is not necessary to use this tool effectively. Note that for
simplicity we call our headers XPaths throughout this document and within the command line
arguments, despite some minor syntax differences. Here we describe the syntax we use for
our headers.

An XPath header is read from left to right, starting with the root element and moving
through each subsequent child element. Elements are separated by a forward slash (``/``).
If an element has multiple instances within a single parent, predicates (numbers within
angle brackets) are used to specify the exact instance, such as
``../pds:Observation_Area<1>/pds:version_id<1>``, which selects the first ``version_id``
element in ``Observation_Area``. The predicate numbers count the instances of the child
element, rather than its structural position in the file. For example, given the XML
fragment::

  <Product_Observational>
      <Identification_Area>
          <logical_identifier>...</logical_identifier>
          <Citation_Information>
              <author_list>...</author_list>
              <publication_year>...</publication_year>
              <keyword>...</keyword>
              <keyword>...</keyword>
              <description>...</description>
          </Citation_Information>
      </Identification_Area>
  </Product_Observational>

the available XPath headers are::

  Product_Observational<1>/Identification_Area<1>/logical_identifier<1>
  Product_Observational<1>/Identification_Area<1>/Citation_Information<1>/author_list<1>
  Product_Observational<1>/Identification_Area<1>/Citation_Information<1>/publication_year<1>
  Product_Observational<1>/Identification_Area<1>/Citation_Information<1>/keyword<1>
  Product_Observational<1>/Identification_Area<1>/Citation_Information<1>/keyword<2>
  Product_Observational<1>/Identification_Area<1>/Citation_Information<1>/description<1>


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

  - ``filename``: The base filename of the label file
  - ``filepath``: The path of the label file relative to the top-level directory
  - ``bundle_lid``: The LID of the bundle containing the label file
  - ``bundle``: The name of the bundle containing the label file

- ``--sort-by COMMA_SEPARATED_HEADER_NAME(s)``: Sort the resulting index file by the
  value(s) in one or more columns. The column names are those that appear in the final
  index file, as modified by ``--simplify-xpaths``, ``--limit-xpaths-file``, or
  ``--clean-header-field-names``, and include any additional columns added with
  ``--add-extra-file-info``. To see a list of available column names, use
  ``--output-headers-file``. More than one sort key can be specified by separating them by
  commas, in which case the sort proceeds hierarchically from left to right. As the XPath
  syntax includes special characters that may be interpreted by the shell, it may be
  necessary to surround the list of sort keys with double quotes.

  Example::

    pds4_create_xml_index <...> --sort-by "pds:Product_Observational/pds:Identification_Area<1>/pds:version_id<1>,pds:logical_identifier"

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
  specific XPaths to extract from the label files. If this argument is not specified, all
  elements found in the label files will be included. This command uses only the whole
  versions of the XPath(s) -- simplified versions are not allowed. The given text file
  can specify XPaths using ``glob``-style syntax, where each XPath level is treated as if
  it were a directory in a filesystem. Available wildcards are:

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

Miscellaneous
"""""""""""""

- ``--verbose``: Display detailed information during the file scraping process that may
  be useful for debugging.

- ``--config-file``: Specify one or more YAML-style configuration files for further
  customization of the extraction process. See the section below for details.


Configuration Files
-------------------

``pds4_create_xml_index`` allows for the use of `YAML <https://yaml.org/spec/1.2.2/>`_
configuration files to alter specific contents of index files and generated label files.
Configuration files can specify information for "nillable elements" and details to be
included in the generated label file. Because you can specify multiple configuration
files, you have the option of separating different types of configuration data into
separate files, or including it all in a single file.

Nillable Elements
^^^^^^^^^^^^^^^^^

The first application of configuration files is to cover instances of nilled elements.
Nilled elements are those intentionally omitted due to being inapplicable, missing,
unknown, or anticipated. ``pds4_create_xml_index`` has a default configuration file that
contains values for a common set of nilled elements. Below is the ``nillable`` section of
the default configuration file that covers these values::

  nillable:
    pds:ASCII_Date_YMD:
      inapplicable: '0001-01-01'
      missing: '0002-01-01'
      unknown: '0003-01-01'
      anticipated: '0004-01-01'

    pds:ASCII_Date_Time_YMD:
      inapplicable: '0001-01-01T12:00'
      missing: '0002-01-01T12:00'
      unknown: '0003-01-01T12:00'
      anticipated: '0004-01-01T12:00'

    pds:ASCII_Date_Time_YMD_UTC:
      inapplicable: '0001-01-01T12:00Z'
      missing: '0002-01-01T12:00Z'
      unknown: '0003-01-01T12:00Z'
      anticipated: '0004-01-01T12:00Z'

    pds:ASCII_Integer:
      inapplicable: -999
      missing: -998
      unknown: -997
      anticipated: -996

    pds:ASCII_Real:
      inapplicable: -999.0
      missing: -998.0
      unknown: -997.0
      anticipated: -996.0

    pds:ASCII_Short_String_Collapsed:
      inapplicable: inapplicable
      missing: missing
      unknown: unknown
      anticipated: anticipated

**NOTE**: YAML considers the ``000X-0X-0X`` format as a datetime object. As such,
assigned values for ``ASCII_Date_YMD`` and other data types that use this format need to
be surrounded by quotes.

You can support any additional nillable data types, or override the default values, by
supplying additional configuration files with the ``--config-file`` option. Below is an
example of a configuration file that overrides the default values for three of the six
common data types::

  nillable:
    pds:ASCII_Integer:
      inapplicable: -9999
      missing: -9988
      unknown: -9977
      anticipated: -9966

    pds:ASCII_Real:
      inapplicable: -9999.0
      missing: -9988.0
      unknown: -9977.0
      anticipated: -9966.0

    pds:ASCII_Short_String_Collapsed:
      inapplicable: inapplicable_alt
      missing: missing_alt
      unknown: unknown_alt
      anticipated: anticipated_alt


Label Contents
^^^^^^^^^^^^^^

Moreover, the configuration files can include content for label generation. This feature
allows you to add optional classes to the generated label file, such as
``Citation_Information``, and ``Modification_History``. Additionally, you can override
existing values within the generated label file.

Below is the ``label-contents`` section of the default configuration file::

  label-contents:
    version_id: 1.0
    title: Index File
    Citation_Information:
    Modification_Detail:
    Internal_Reference:
    External_Reference:
    Source_Product_Internal:
    Source_Product_External:
    File_Area_Ancillary:
    File_Area_Metadata:

Each listed value with an empty dictionary is an optional field the user can include in
their generated label. If the user does decide to include one of these fields, **they must
also include all elements within that field in their configuration file, even if the
element will remain empty**.

For reference, provided below are the full contents of the optional label classes::

  Citation_Information:
    author_list:
    editor_list:
    publication_year:
    doi:
    keyword:
    description:
    Funding_Acknowledgement:
      funding_source:
      funding_year:
      funding_award:
      funding_acknowledgement_text:
  Modification_Detail:
    modification_date:
    version_id:
    description:
  Internal_Reference:
    lid_reference:
    reference_type:
    comment:
  External_Reference:
    doi:
    reference_text:
    description:
  Source_Product_Internal:
    lidvid_reference:
    reference_type:
    comment:
  Source_Product_External:
    external_source_product_identifier:
    reference_type:
    doi:
    curating_facility:
    description:
  File_Area_Ancillary / File_Area_Metadata:
    creation_date_time:


If no new contents are specified for label generation, the label will contain the
following classes::

  <Identification_Area>
    <logical_identifier>...</logical_identifier>
    <version_id>...</version_id>
    <title>...</title>
    <information_model_version>...</information_model_version>
    <product_class>...</product_class>
    <License_Information>
      <name>Creative Common Public License CC0 1.0 (2024)</name>
      <description>Creative Commons Zero (CC0) license information.</description>
      <Internal_Reference>
        <lid_reference>urn:nasa:pds:system_bundle:document_pds4_standards:creative_commons_1.0.0::1.0</lid_reference>
        <reference_type>product_to_license</reference_type>
      </Internal_Reference>
    </License_Information>
  </Identification_Area>
  <Reference_List>
  </Reference_List>

Depending on the chosen argument for ``--generate-label`` (``ancillary`` or ``metadata``),
the label will be given either the ``File_Area_Ancillary`` or ``File_Area_Metadata``
class, which will then contain either ``Table_Character`` for fixed-width index files or
``Table_Delimited`` for variable-length files. These classes are populated by the label
generation code and cannot be altered with configuration files (except in the case of
nilled elements).

Here is an example of a configuration file that overrides the default title and adds
modification history::

  label-contents:
    title: Index file for my occultation bundle
    Modification_Detail:
      - modification_date: '2024-01-01'
        version_id: 1.1
        description: |
          This is a lengthy description of what this modification
          changed in the bundle.
          There were lots of changes.
      - modification_date: '2023-01-01'
        version_id: 1.0
        description: Initial release.
