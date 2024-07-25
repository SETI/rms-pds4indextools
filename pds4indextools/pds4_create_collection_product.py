"""
PDS4 Collection Product Creation Tool

This script scrapes label files within a collection for their identifying information,
and creates a collection product file containing the LIDVIDs and the Member Status of the
label files. This tool can also generate the collection product elsewhere within the
user's directory, for use during the creation of collections. For the full instructions
on how to use the tool, see:

python pds4_create_collection_product.py --help
"""

import argparse
import csv
from lxml import etree
from pathlib import Path
import sys


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('collectionpath', type=str, metavar='COLLECTION_PATH',
                        help='The path to the collection product')
    parser.add_argument('--bundle', type=str, metavar='BUNDLE_NAME',
                        help='The name of the bundle')
    parser.add_argument('--collection', type=str, metavar='COLLECTION_NAME',
                        help='The name of the collection')
    parser.add_argument('--collection-product-file', type=str,
                        metavar='COLLECTION_PRODUCT_FILEPATH',
                        help='The output location of the collection product.')

    args = parser.parse_args()

    collection_path = Path(args.collectionpath).absolute()
    print(f"Creating collection product for: {collection_path}")
    label_files = []

    if args.bundle:
        bundle = args.bundle
    else:
        bundle = collection_path.parent.name

    if args.collection:
        collection = args.collection
    else:
        collection = collection_path.name

    print(f"Bundle name: {bundle}")
    print(f"Collection name: {collection}")

    primary = f"{bundle}:{collection}"

    # Gather all XML files in the collection path, sort by directory structure
    label_files = collection_path.glob('**/*.xml')
    if not label_files:
        print(f'No label files found in directory: {collection_path}')
        sys.exit(1)

    # Initialize list to hold rows of data
    data = []

    # Process each XML file
    for label_file in label_files:
        if label_file.name == f'collection_{collection}.xml':
            continue
        tree = etree.parse(str(label_file))
        root = tree.getroot()

        # Handle namespaces
        namespaces = root.nsmap
        namespaces['pds'] = namespaces.pop(None)

        # Extract LID and VID
        try:
            lid = tree.find('.//pds:logical_identifier', namespaces=namespaces).text
        except AttributeError:
            print(f'{label_file} does not contain logical_identifier attribute.')
            sys.exit(1)

        try:
            vid = tree.find('.//pds:version_id', namespaces=namespaces).text
        except AttributeError:
            print(f'{label_file} does not contain version_id attribute.')
            sys.exit(1)

        lidvid = f'{lid}::{vid}'

        # Determine member status
        member_status = 'P' if primary in lid else 'S'

        # Append the data to the list
        data.append([member_status, lidvid])

    # Sorting the list of results
    data.sort()
    # Determine the output file path
    collprod_filepath = (
        args.collection_product_file if args.collection_product_file else
        collection_path / f'collection_{args.collection}.csv')

    # Write data to CSV file
    print(f"Writing out to: {collprod_filepath}")
    with open(collprod_filepath, mode='w', newline='') as collprod_file:
        writer = csv.writer(collprod_file)
        writer.writerows(data)


if __name__ == '__main__':
    main()
