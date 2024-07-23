``pds4_create_collection_product`` Program
=================================

Introduction
------------
The RMS Node's PDS4 Collection Product Creation Tool (``pds4_create_collection_product``)
is designed to create bespoke collection product files from
`Planetary Data System (PDS) <https://pds.nasa.gov>`_ `PDS4-format
<https://pds.nasa.gov/datastandards/documents/>`_label files. This tool automates the
creation of collection products by recursively searching for all label files within a
specified directory and extracting their identifying information. This information is then
compared against user-provided details (the bundle and collection names) to determine
which label files are primary members and which are secondary members. The results are
compiled into a CSV file and placed in the user's specified location, or in the
collection's location if no specific destination is provided. This allows for a quick and
efficient way to check the contents of collections.

Command Line Arguments
----------------------

Required arguments
^^^^^^^^^^^^^^^^^^

Three command line arguments are required in every run.

The first is the path to the collection you wish to make a collection product for. This
path will also be referenced as the output path for the collection product if it is not
otherwise specified.

The second is the name of the bundle.

The third is the name of the collection.

The given bundle and collection names are used to determine the ``Member Status`` of the
labels within the collection. If a label's ``logical_identifier`` contains both the given
bundle and collection, it is considered a primary member. Labels that contain only one or
neither of these names are classified as secondary members.

Example::

    pds4_create_collection_product /path/to/collection cassini_vims_cruise data_raw


Optional arguments
^^^^^^^^^^^^^^^^^^

``--collection-product-file COLLECTION_PRODUCT_FILEPATH``: Specify the location and name
of the collection product. This allows for the collection product to be generated outside
of the collection it represents. It is recommended that the file have the suffix ``.csv``.
If no directory is specified, the collection product will be written to the current
directory. If this command is not used, the collection product will be written to the path
to the collection.
