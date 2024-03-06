"""
XML Bundle Scraper

This script scrapes XML files within specified directories, extracts information from
user-defined XML elements, and generates a CSV index file. The script provides options
for customizing the extraction process, such as specifying XPath headers, limiting
search levels, and selecting elements to scrape.

Usage:
    python xml_bundle_scraper.py <directorypath> <pattern>
        [--elements-file ELEMENTS_FILE]
        [--xpaths]
        [--output-file OUTPUT_FILE]
        [--verbose]
        [--sort-by SORT_BY] 
        [--clean-header-field-names]
        [--extra-file-info EXTRA_FILE_INFO]
        [--config-file CONFIG_FILE]

Arguments:
    directorypath        The path to the directory containing the bundle to scrape.
    pattern              The glob pattern(s) (which may include wildcards like *, ?,
                         and **) for the files you wish to index. Multiple patterns
                         may be specified separated by spaces. Surround each pattern
                         with quotes.
    --elements-file ELEMENTS_FILE
                         Optional text file containing elements to scrape.
    --xpaths             Activate XPath headers in the final index file.
    --output-file OUTPUT_FILE
                         The output path and filename for the resulting index file.
    --verbose            Activate verbose printed statements during runtime.
    --sort-by SORT_BY    Sort the index file by a chosen set of columns.
    --clean-header-field-names
                         Replace the ":" and "/" with Windows-friendly characters.
    --extra-file-info EXTRA_FILE_INFO  
                         Add additional column(s) to the index file containing file or
                         bundle information. Possible values are: "LID", "filename",
                         "filepath", "bundle", and "bundle_lid". Multiple values may be
                         specified separated by spaces.
    --config-file CONFIG_FILE
                         An optional .ini configuration file for further customization.

Example:
python3 pds4_create_xml_index.py <toplevel_directory> "glob_path1" "glob_path2" 
--output_file <outputfile> --elements-file sample_elements.txt --verbose
"""

import argparse
import configparser
from lxml import etree
import pandas as pd
from pathlib import Path
import requests
import sys


def default_value_for_nil(config, data_type, nil_value):
    """Find the default value for a nilled element.

    Inputs:
        config       The configuration data.
        data_type    The attribute describing the data type of the element.
        nil_value    The associated value for nilReason.

    Returns:
        Default replacement value of correct data type.
    """
    if data_type == 'pds:ASCII_Integer':
        default = config[data_type].getint(nil_value)
    elif data_type == 'pds:ASCII_Real':
        default = config[data_type].getfloat(nil_value)
    else:
        default = config[data_type][nil_value]

    return default


def convert_header_to_tag(path, root, namespaces):
    """Convert an XPath expression to an XML tag.

    Inputs:
        path          XPath expression.
        root          The root element of the XML document.
        namespaces    Dictionary of XML namespace mappings.

    Returns:
        Converted XML tag.
    """
    tag = str(root.xpath(path, namespaces=namespaces)[0].tag)

    return tag


def convert_header_to_xpath(root, xpath_find, namespaces):
    """Convert an XML header path to an XPath expression.

    Inputs:
        root           The root element of the XML document.
        xpath_find     Original XML header path.
        namespaces     Dictionary of XML namespace mappings.

    Returns:
        Converted XPath expression.
    """
    sections = xpath_find.split('/')
    xpath_final = ''
    portion = ''
    for sec in sections[1:]:
        portion = portion + '/' + sec
        tag = str(root.xpath(portion, namespaces=namespaces)[0].tag)
        xpath_final = xpath_final + '/' + tag

    return xpath_final


def load_config_file(specified_config_file):
    """Create a config object from a given configuration file.

    This will always load in the default configuration file 'pds4indextools.ini'. In the
    event a specified configuration file is given, the contents of that file will
    override what is in the default configuration file.

    Inputs:
        specified_config_file     Name of or path to a specified configuration file.

    Returns:
        A ConfigParser object.
    """
    config = configparser.ConfigParser()
    module_dir = Path(__file__).resolve().parent

    default_config_file = module_dir / 'pds4indextools.ini'

    try:
        config.read_file(open(default_config_file))
    except OSError:
        print(f'Unable to read the default configuration file: {default_config_file}')
        sys.exit(1)

    if specified_config_file:
        try:
            config.read_file(open(specified_config_file))
        except OSError:
            print(f'Unable to read configuration file: {specified_config_file}')
            sys.exit(1)
    
    return config

def update_nillable_elements_from_xsd_file(xsd_file, nillable_elements_info):
    """Store all nillable elements and their data types in a dictionary.

    Inputs:
        xsd file                  An XML Schema Definition file.
        nillable_elements_info    A dictionary containing nillable element information.
    """
    tree = etree.fromstring(requests.get(xsd_file).content)
    namespace = {'xs': 'http://www.w3.org/2001/XMLSchema'}

    elements_with_nillable = tree.xpath('//xs:element[@nillable="true"]',
                                        namespaces=namespace)

    for element in elements_with_nillable:
        name = element.get('name')
        type_attribute = element.get('type')
        if type_attribute not in nillable_elements_info.keys():
            if type_attribute:
                # Split the type attribute to handle namespace:typename format
                type_parts = type_attribute.split(':')
                # Take the last part as the type name
                type_name = type_parts[-1]

                # Attempt to find the type definition in the document
                type_definition_xpath = (f'//xs:simpleType[@name="{type_name}"] | '
                                         f'//xs:complexType[@name="{type_name}"]')
                type_definition = tree.xpath(
                    type_definition_xpath, namespaces=namespace)

                if type_definition:
                    # Take the first match
                    type_definition = type_definition[0]
                    base_type = None
                    # For complexType with simpleContent or simpleType, find base attr
                    if type_definition.tag.endswith('simpleType'):
                        restriction = type_definition.find('.//xs:restriction',
                                                           namespaces=namespace)
                        if restriction is not None:
                            base_type = restriction.get('base')
                    elif type_definition.tag.endswith('complexType'):
                        extension = type_definition.find('.//xs:extension',
                                                         namespaces=namespace)
                        if extension is not None:
                            base_type = extension.get('base')

                    nillable_elements_info[name] = (
                        base_type or 'External or built-in type')
                else:
                    # Type definition not found, might be external or built-in type
                    nillable_elements_info[name] = 'External or built-in type'


def process_schema_location(file_path):
    """Process schema location from an XML file.

    Args:
        file_path    Path to the XML file.

    Returns:
        List of XSD URLs extracted from the schema location.
    """
    # Load and parse the XML file
    tree = etree.parse(file_path)
    root = tree.getroot()

    # Extract the xsi:schemaLocation attribute value
    schema_location_values = root.get(
        '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
    ).split()

    # Filter XSD URLs
    xsd_urls = [url for url in schema_location_values if url.endswith('.xsd')]

    return xsd_urls


def process_tags(xml_results, key, root, namespaces, prefixes, args):
    """Process XML tags based on the provided options.

    If the --xpaths command is used, the XPath is converted into a format that
    contains the names and namespaces of all the parent elements of that element.
    If the --xpaths command is not used, the XPath is converted into the
    associated element tag of that element, and given its associated namespace. These
    values then replace their old versions in the xml_results dictionary.


    Inputs:
        xml_results    A dictionary containing XML data to be processed.
        key            The key representing the XML tag to be processed.
        root           The root element of the XML tree.
        namespaces     A dictionary containing XML namespace mappings.
        prefixes       A dictionary containing XML namespace prefixes.
        args           Command-line arguments.
    """
    if args.xpaths:
        key_new = convert_header_to_xpath(root, key, namespaces)
        for namespace in prefixes.keys():
            if namespace in key_new:
                key_new = key_new.replace(
                    '{'+namespace+'}', prefixes[namespace]+':')
        xml_results[key_new] = xml_results[key]
        del xml_results[key]
    else:
        key_new = convert_header_to_tag(key, root, namespaces)
        for namespace in prefixes.keys():
            if namespace in key_new:
                key_new = key_new.replace(
                    '{'+namespace+'}', prefixes[namespace]+':')
        xml_results[key_new] = xml_results[key]
        del xml_results[key]


def store_element_text(element, tree, results_dict, nillable_elements_info, config, label):
    """Store text content of an XML element in a results dictionary.

    Inputs:
        element                   The XML element.
        tree                      The XML tree.
        results_dict              Dictionary to store results.
        nillable_elements_info    A dictionary containing nillable element information.
        config                    The configuration data.
        label                     The name of the label file.
    """
    if element.text and element.text.strip():
        xpath = tree.getpath(element)
        text = ' '.join(element.text.strip().split())

        # Check if the tag already exists in the results dictionary
        if xpath in results_dict:
            # If the tag already exists, create a list to store multiple values
            if not isinstance(results_dict[xpath], list):
                results_dict[xpath] = [results_dict[xpath]]
            results_dict[xpath].append(text)
        else:
            results_dict[xpath] = text
    else:
        xpath = tree.getpath(element)
        tag = element.xpath('local-name()')
        nil_value = element.get('nilReason')
        if tag in nillable_elements_info.keys():
            data_type = nillable_elements_info[tag]
            default = default_value_for_nil(config, data_type, nil_value)
            results_dict[xpath] = default
        else:
            parent_check = len(element)
            if not parent_check:
                print(f'Non-nillable element in {label} has no associated text: {tag}')
                

def traverse_and_store(element, tree, results_dict, elements_to_scrape,
                       nillable_elements_info, config, label):
    """Traverse an XML tree and store text content of specified elements in a dictionary.

    Inputs:
        element                   The current XML element.
        tree                      The XML tree.
        results_dict              Dictionary to store results.
        prefixes                  Dictionary of XML namespace prefixes.
        elements_to_scrape        Optional list of elements to scrape.
        nillable_elements_info    A dictionary containing nillable element information.
        config                    The configuration data.
        label                     The name of the label file.
    """
    tag = str(element.tag)
    if elements_to_scrape is None or any(tag.endswith("}" + elem)
                                         for elem in elements_to_scrape):
        store_element_text(element, tree, results_dict,
                           nillable_elements_info, config, label)
    for child in element:
        traverse_and_store(child, tree, results_dict, elements_to_scrape,
                           nillable_elements_info, config, label)


def write_results_to_csv(results_list, args, output_csv_path):
    """Write results from a list of dictionaries to a CSV file.

    Inputs:
        results_list          List of dictionaries containing results.
        output_csv_path       The output directory and filename.
    """
    rows = []
    for result_dict in results_list:
        rows.append(result_dict['Results'])

    df = pd.DataFrame(rows)

    if args.sort_by:
        df.sort_values(by=args.sort_by, inplace=True)

    if args.clean_header_field_names:
        df.rename(columns=lambda x: x.replace(
            ':', '_').replace('/', '__'), inplace=True)

    df.to_csv(output_csv_path, index=False, na_rep='NaN')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directorypath', type=str,
                        help='The path to the directory containing the bundleset, bundle, '
                             'or collection you wish to scrape')

    parser.add_argument('pattern', type=str, nargs='+',
                        help='The glob pattern(s) for the files you wish to index. They '
                             'may include wildcards like  *, ?, and **. If using '
                             'multiple, separate with spaces. Surround each pattern '
                             'with quotes.')

    parser.add_argument('--elements-file', type=str,
                        help='Optional text file containing elements to scrape. If not '
                             'specified, all elements found in the XML files are '
                             'included.')

    parser.add_argument('--xpaths', action='store_true',
                        help='If specified, use full XPaths in the column '
                             'headers. If not specified, use only elements tags.')

    parser.add_argument('--output-file', type=str,
                        help='The output filepath ending with your chosen filename for '
                             'the resulting index file')

    parser.add_argument('--verbose', action='store_true',
                        help='Turn on verbose mode and show the details of file scraping')

    parser.add_argument('--sort-by', type=str, nargs='+',
                        help='Sort resulting index file by one or more columns')

    parser.add_argument('--clean-header-field-names', action='store_true',
                        help='Replace the ":" and "/" in the column headers with '
                             'alternative (legal friendly) characters')
    parser.add_argument('--extra-file-info', type=str, nargs='+',
                        choices=['LID', 'filename', 'filepath',
                                 'bundle_lid', 'bundle'],
                        help='Add additional columns to the final index file. Choose '
                             'from the following: "LID", "filename", "filepath", '
                             '"bundle_lid", and "bundle". If using multiple, separate '
                             'with spaces.')
    parser.add_argument('--config-file', type=str,
                        help='Read a user-specified configuration file.. File must be a '
                             '.ini file.')

    args = parser.parse_args()

    verboseprint = print if args.verbose else lambda *a, **k: None

    config = load_config_file(args.config_file)

    directory_path = Path(args.directorypath)
    patterns = args.pattern

    nillable_elements_info = {}
    label_files = []
    all_results = []
    for pattern in patterns:
        files = directory_path.glob(f"{pattern}")
        label_files.extend(files)

    verboseprint(f'{len(label_files)} matching files found')

    if label_files == []:
        print(f'No files matching {pattern} found in directory: {directory_path}')
        sys.exit(1)

    if args.elements_file:
        verboseprint(
            f'Element file {args.elements_file} chosen for input.')
        with open(args.elements_file, 'r') as elements_file:
            elements_to_scrape = [line.strip() for line in elements_file]
            verboseprint(
                f'Chosen elements to scrape: {elements_to_scrape}')
    else:
        elements_to_scrape = None

    for file in label_files:
        verboseprint(f'Now scraping {file}')
        tree = etree.parse(str(file))
        root = tree.getroot()

        xml_urls = process_schema_location(file)
        for url in xml_urls:
            update_nillable_elements_from_xsd_file(url, nillable_elements_info)

        filepath = file.relative_to(args.directorypath)

        namespaces = root.nsmap
        namespaces['pds'] = namespaces.pop(None)
        prefixes = {v: k for k, v in namespaces.items()}

        xml_results = {}
        traverse_and_store(root, tree, xml_results, elements_to_scrape,
                           nillable_elements_info, config, file)

        for key in list(xml_results.keys()):
            process_tags(xml_results, key, root,
                         namespaces, prefixes, args)

        lid = xml_results.get('pds:logical_identifier', 'Missing_LID')

        # Attach extra columns if asked for.
        bundle_lid = ':'.join(lid.split(':')[:4])
        bundle = bundle_lid.split(':')[-1]
        extras = {'LID': lid, 'filepath': filepath, 'filename': file.name,
                  'bundle': bundle, 'bundle_lid': bundle_lid}
        if args.extra_file_info:
            xml_results = {**{ele: extras[ele] for ele in args.extra_file_info},
                           **xml_results}

        result_dict = {'Results': xml_results}
        all_results.append(result_dict)

    if args.output_file:
        output_path = args.output_file
    else:
        output_path = args.directorypath / Path('index_file.csv')

    verboseprint(f'Output file generated at {output_path}')
    write_results_to_csv(all_results, args, output_path)


if __name__ == '__main__':
    main()
