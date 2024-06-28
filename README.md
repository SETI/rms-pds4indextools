# rms-pds4indextools

Supported versions: Python >= 3.8

# PDS Ring-Moon Systems Node, SETI Institute

# `pds4indextools` MODULE OVERVIEW

The PDS4 Indexing Tool (`pds4indextools`) is a Python module designed to 
facilitate the extraction and indexing of information from Planetary Data System
(PDS) label files. This tool automates the process of parsing specified 
directories for label files, extracting user-defined elements using XPath 
expressions, and generating organized output files. Users can customize the 
extraction process through various options, such as filtering content, 
sorting output, and integrating additional file metadata. The tool supports 
flexibility with configuration files and provides a straightforward interface 
for creating both CSV-based index files and text files listing available XPath 
headers. Whether for scientific research, data management, or archival purposes, 
the PDS4 Indexing Tool offers a robust solution for efficiently managing and 
accessing structured data within PDS-compliant datasets.

`pds4indextools` may be installed by running `pip install pds4indextools`.

Python versions 3.9 thru 3.12 are currently supported, with pre-built wheels
available for Linux, MacOS, and Windows.

# `XPath` SYNTAX AND STRUCTURE

Before using the tool, it is imperative that the user becomes comfortable with 
the XPath language, and how it is parsed with `lxml`.

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

- Square brackets are replaced by angled brackets. This module utilizes `glob`
  syntax for finding label files and filtering out elements/attributes. Because
  square brackets have meaning within `glob` statements, they needed to be
  replaced with angled brackets. 

- The values within the predicates have been renumbered. In XPath syntax,
  predicates are used to determine the location of an element in relation to its
  parent. While this is useful in other applications, this logic fails if
  multiples of the element and its parent appear within the document. Even if
  the elements all have different values, all of their XPaths would be the same.
  Instead, the predicates are renumbered to reflect which instance of the
  element the value is represented by.

# SETUP

After using `pip install pds4indextools`, you can start planning where you would
like to run the module from. While the module can run from anywhere, it is
important to know where you plan to scrape the labels. This way you can avoid
either producing an empty output file, or a file containing incorrect contents.


# COMMAND-LINE ARGUMENTS

This module uses command-line arguments to create and tailor the contents and
format of your output file.

`REQUIRED COMMAND-LINE ARGUMENTS -- LABEL LOCATION AND NOMENCLATURE`
- directorypath: The topmost level directory you want to navigate. This is the 
  starting point where the code will look for matching labels.

- patterns: The glob pattern(s) that will be used to find label files under the
  given directorypath. The directorypath combined with these patterns should
  form a complete filepath. `glob` wildcard symbols, such as `*`, `?`, and `**`,
  are allowed. Surround each pattern with quotes. If the user wants to specify
  multiple patterns, separate with spaces.

`REQUIRED COMMAND-LINE ARGUMENTS -- OUTPUT FILE FORMAT`
- output-csv-file: Specify the location and filename of the index file. This
  file will contain the extracted information organized in CSV format.

- output-txt-file: Specify the location and filename of the XPath headers file.
  This file will contain a list of available XPaths extracted from the label
  files.

`OPTIONAL COMMAND-LINE ARGUMENTS -- CUSTOMIZATION`
- elements-file: Optional. Specify a text file containing a list of specific
  elements or XPaths to extract from the label files. If not specified, all
  elements found in the label files will be included.

- simplify-xpaths: Optional. If specified, the output will only include unique
  XPaths with simplified tags. Duplicate values will still use their full XPath.

- verbose: Optional. Activate verbose mode to display detailed information
  during the file scraping process.

- sort-by: Optional. Specify one or more columns to sort the index file.
  Columns can be identified by either the full XPath header or the simplified
  version if `--simplify-xpaths` is used. Use `--dump-available-xpaths` to see
  all available sorting options.

- clean-header-field-names: Optional. If specified, column headers will be
  renamed to use only characters permissible in variable names, making them
  more compatible with certain systems.

- add-extra-file-info: Optional. Add additional columns to the final index file.
  Choose from "LID", "filename", "filepath", "bundle_lid", and "bundle". Specify
  multiple values as separate arguments separated by spaces.

- config-file: Optional. Specify a `.ini` configuration file for further
  customization of the extraction process.

- dump-available-xpaths: Optional. Generates a `.txt` file containing all
  available XPaths within the given label files. This file can serve as a base
  file for `--elements-file` if modified.

- fixed-width: Optional. If specified, the index file will be formatted with
  fixed-width columns.

- generate-label: Optional. Specify the type of PDS4 label to generate for the
  index file. Choose either "Product_Ancillary" or
  "Product_Metadata_Supplemental".

- label-user-input: Optional. Provide an optional `.yaml` file containing
  additional information for the generated PDS4 label.
