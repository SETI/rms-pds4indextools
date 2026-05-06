``pds4_create_collection_product`` Program
==========================================

Introduction
------------
The RMS Node's PDS4 Collection Product Creation Tool (``pds4_create_collection_product``)
is designed to create bespoke collection product files from existing `Planetary Data
System (PDS) <https://pds.nasa.gov>`_ `PDS4-format
<https://pds.nasa.gov/datastandards/documents/>`_ label files. This tool automates the
creation of collection products by recursively searching for all label files within a
specified directory and extracting their LIDVIDs. This information is then compared
against user-provided details (the bundle and collection names) to determine which label
files are primary members and which are secondary members. The results are compiled into a
CSV file with two columns: the ``Member Status`` (which is either ``P`` for primary or
``S`` for secondary) and the ``LIDVID``. The CSV file is placed in the user's specified
location, or in the collection's top-level directory if no specific destination is
provided. The resulting collection product is sorted by ``Member Status`` and then by
``LIDVID``.

**NOTE**: Due to the specialized contents of each collection product label, this tool does
not generate a collection product label file to accompany the generated CSV file; all data
providers are advised to work with their assigned PDS Node to create an appropriate
collection product label file. However, to avoid any collection product label that may be
present from accidentally being included as a member of the collection itself, label files
with the name ``collection_<collection_name>.xml`` are ignored when producing the
collection product.


Command Line Arguments
----------------------

Required arguments
^^^^^^^^^^^^^^^^^^

One command line argument is required in every run, the path to the collection you wish to
make a collection product for. This path will also be referenced as the output path for
the collection product if it is not otherwise specified.

If not overridden using the arguments described below, the path to the collection will be
used to deduce the names of the bundle and collection by assuming that the collection path
has the form::

    /dir.../dir/<bundle_name>/<collection_name>

The bundle and collection names are used to determine the ``Member Status`` of the labels
within the collection. If a label's ``logical_identifier`` contains both the given bundle
and collection, it is considered a primary member. Labels that contain only one or neither
of these names are classified as secondary members. Data providers are strongly encouraged
to manually check the resulting collection product file to make sure that the proper set
of LIDVIDs have been included and that their primary/secondary determination is correct.

Example::

    pds4_create_collection_product /path/to/my_bundle/my_collection


Optional arguments
^^^^^^^^^^^^^^^^^^

- ``--bundle BUNDLE_NAME``: Provide the name of the bundle the collection belongs to. This
  only needs to be specified if you don't want to use the default of the second-to-last
  directory name when determining primary or secondary members status.

- ``--collection COLLECTION_NAME``: Provide the name of the collection. This only needs to
  be specified if you don't want to use the default of the final directory name when
  determining primary or secondary member status.

- ``--collection-product-file COLLECTION_PRODUCT_FILEPATH``: Specify the location and name
  of the collection product. This allows for the collection product to be generated
  outside of the collection it represents. It is recommended that the file have the suffix
  ``.csv``. If no directory is specified, the collection product will be written to the
  current directory. If this argument is not specified, the collection product will be
  written to the top-level directory of the collection with the name
  ``collection_<collection_name>.csv``
