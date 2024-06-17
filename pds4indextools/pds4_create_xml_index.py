"""
PDS4 Indexing Tool

This script scrapes label files within specified directories, extracts information from
user-defined XPaths/elements, and generates either an index file or a .txt file containing
the XPaths available to the user. The script provides options for customizing the 
extraction process, such as:
    - Specifying desired content by either limiting the results or requesting additional
      file information.
    - Sorting the resulting file by a user-specified value.
    - Allowing for a user-made configuration file (.ini) for further custom content.

Usage:
    python pds4_create_xml_index.py <directorypath> <pattern>
        [--elements-file ELEMENTS_FILE]
        [--simplify-xpaths]
        [--output-file OUTPUT_FILE]
        [--verbose]
        [--sort-by SORT_BY]
        [--clean-header-field-names]
        [--extra-file-info EXTRA_FILE_INFO]
        [--config-file CONFIG_FILE]
        [--dump-available-xpaths]
        [--fixed-width]

Arguments:
    directorypath        The path to the directory containing the bundle to scrape.
    pattern              The glob pattern(s) (which may include wildcards like *, ?,
                         and **) for the files you wish to index. Multiple patterns
                         may be specified separated by spaces. Surround each pattern
                         with quotes.
    --elements-file ELEMENTS_FILE
                         Optional text file containing elements to scrape.
    --simplify-xpaths    Replace unique XPath segments with shortened versions.
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
    --dump-available-xpaths
                         Create a .txt file containing all available XPath headers for
                         given label file(s). Can be modified and used as a file for
                         --elements-file
    --fixed-width        Create a fixed-width index file. 

Example:
    python3 pds4_create_xml_index.py <toplevel_directory> "glob_path1" "glob_path2"
    --output_file <outputfile> --elements-file sample_elements.txt --verbose
"""

import argparse
from collections import namedtuple
import csv
import configparser
from datetime import datetime
import fnmatch
import functools
from itertools import groupby
from lxml import etree
import os
import pandas as pd
from pathlib import Path
import platform
import requests
import sys
import yaml

import pdstemplate as ps


SplitXPath = namedtuple('SplitXPath',
                        ['xpath', 'parent', 'child', 'prefix', 'num'])


def convert_header_to_xpath(root, xpath_find, namespaces):
    """
    Replace hierarchical components of XPath with attribute names and namespaces.

    While the XPaths are accurate to the hierarchy of the elements referenced, they
    provide no information on their own without the attributed label file for reference.
    This function replaces the asterisks with the respective names of the elements and
    attributes they represent.

    Args:
        root (Element): The root element of the XML document.
        xpath_find (str): Original XML header path.
        namespaces (dict): Dictionary of XML namespace mappings.

    Returns:
        str: Converted XPath expression.
    """
    sections = xpath_find.split('/')
    xpath_final = ''
    portion = ''
    for sec in sections[1:]:
        portion = portion + '/' + sec
        tag = str(root.xpath(portion, namespaces=namespaces)[0].tag)
        if '*' in sec:
            sec = sec[1:]
        if ':' in sec:
            sec = ''
        xpath_final = xpath_final + '/' + tag + sec

    return xpath_final


def correct_duplicates(label_results):
    """
    Correct numbering of XPaths to have correct predicates.

    Some namespaces do not contain predicates, and as a result must be made artificially
    unique via injected substrings. This function aids in the reformatting of these
    strings so they match the syntax of the renumbering function. Note that this function
    does not affect elements or attributes that natively contain the '_num' substring
    (cassini:filter_name_1 and cassini:filter_name_2, for example).

    Args:
        label_results (dict): The dictionary of XML results.
    """
    element_names = []
    for key in list(label_results.keys()):
        tag = key.split('/')[-1].split('<')[0]
        number = tag.split('_')[-1]
        if number.isdigit():
            cropped = tag.replace('_'+number, '')
            if any(cropped == x for x in element_names):
                key_new = key.replace(('_' +number+'<1>'),'<1>')
                parent = key_new.split('/')[-2].split('<')[0]
                key_new = key_new.replace(parent+'<1>', parent+'<'+str(int(number)+1)+'>')
                label_results[key_new] = label_results.pop(key)
        element_names.append(tag)


def default_value_for_nil(config, data_type, nil_value):
    """
    Find the default value for a nilled element.

    Args:
        config (dict): The configuration data.
        data_type (str): The attribute describing the data type of the element.
        nil_value (str): The associated value for nilReason.

    Returns:
        Any: Default replacement value of correct data type.
    """
    if data_type == 'pds:ASCII_Integer':
        default = config[data_type].getint(nil_value)
    elif data_type == 'pds:ASCII_Real':
        default = config[data_type].getfloat(nil_value)
    else:
        default = config[data_type][nil_value]

    return default


def extract_logical_identifier(tree):
    """
    Extract the logical_identifier element from an XML tree.

    Args:
        tree (ElementTree.Element): The XML tree.

    Returns:
        str or None: The text content of the logical_identifier element,
                     or None if not found.
    """
    # Define namespace mapping
    namespaces = {'pds': 'http://pds.nasa.gov/pds4/pds/v1'}

    # Find logical_identifier element within Identification_Area
    logical_identifier = tree.find(
        './/pds:Identification_Area/pds:logical_identifier', namespaces=namespaces)

    if logical_identifier is not None:
        return logical_identifier.text.strip()
    else:
        return None


def filter_dict_by_glob_patterns(input_dict, glob_patterns, verboseprint):
    """
    Filter a dictionary based on a list of glob patterns matching for keys.

    Args:
        input_dict (dict): The dictionary to filter.
        glob_patterns (list): A list of glob patterns to match against dictionary keys.

    Returns:
        dict: Filtered dictionary with desired contents.
    """
    filtered_dict = {}

    if glob_patterns is None:
        return input_dict

    if glob_patterns == []:
        print('Given elements file is empty.')
        sys.exit(1)
    else:
        for pattern in glob_patterns:
            if not pattern.startswith('!'):
                verboseprint(f'Adding elements according to: {pattern}')
                for key, value in input_dict.items():
                    if fnmatch.fnmatch(key, pattern):
                        filtered_dict[key] = value
            else:
                verboseprint(f'Removing elements according to: {pattern}')
                pattern = pattern.replace('!', '')
                for key, value in list(filtered_dict.items()):
                    if fnmatch.fnmatch(key, pattern):
                        del filtered_dict[key]

        return filtered_dict


def load_config_file(specified_config_file):
    """
    Create a config object from a given configuration file.

    This will always load in the default configuration file 'pds4indextools.ini'. In the
    event a specified configuration file is given, the contents of that file will
    override what is in the default configuration file.

    Args:
        specified_config_file (str, optional): Name of or path to a specified
                                               configuration file.

    Returns:
        configparser.ConfigParser: A ConfigParser object.
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


def process_schema_location(file_path):
    """
    Process schema location from an XML file.

    Args:
        file_path (str): Path to the XML file.

    Returns:
        list: List of XSD URLs extracted from the schema location.
    """
    # Load and parse the XML file
    try:
        tree = etree.parse(file_path)
    except OSError:
        print('Given file does not exist')

    # Extract the xsi:schemaLocation attribute value
    root = tree.getroot()
    schema_location_values = root.get(
        '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
    ).split()

    # Filter XSD URLs
    xsd_urls = [url for url in schema_location_values if url.endswith('.xsd')]

    return xsd_urls


def process_headers(label_results, key, root, namespaces, prefixes):
    """
    Process headers to have more readable contents.

    Processes XPath headers by converting parts of the XPath into element tags,
    replacing namespaces with prefixes, and updating the label_results dictionary.
    If a duplicate XPath is encountered, it appends an underscore and a number
    to make the XPath unique.

    Args:
        label_results (dict): A dictionary containing XML data to be processed.
        key (str): The key representing the XML tag to be processed.
        root (Element): The root element of the XML tree.
        namespaces (dict): A dictionary containing XML namespace mappings.
        prefixes (dict): A dictionary containing XML namespace prefixes.
    """
    key_new = convert_header_to_xpath(root, key, namespaces)
    for namespace in prefixes.keys():
        if namespace in key_new:
            key_new = key_new.replace(
                '{'+namespace+'}', prefixes[namespace]+':')
    if key_new in label_results:
        # If the XPath already exists, append an underscore and a number
        i = 1
        while True:
            new_key = f"{key_new}_{i}"
            if new_key not in label_results:
                key_new = new_key
                break
            i += 1
    label_results[key_new] = label_results.pop(key)


def renumber_xpaths(xpaths):
    """
    Renumber a list of XPaths to be sequential at each level.

    lxml appends a unique ID in [] after each tag based on its physical position
    in the XML hierarchy. For example:

        /pds:Product_Observational/pds:Observation_Area[2]/
        pds:Observing_System[4]/pds:name[1]

    For ease of use, we would rather have these numbers based on the occurrence
    number rather than the physical position.

    This function takes in a list of XPaths (or XPath fragments) and renumbers
    them at each level of the hierarchy such that each unique tag name is
    numbered sequentially starting at 1. The list of XPaths must already be
    sorted such that the numbers at each level are in ascending order.
    Further, if there are multiple occurrences of a tag at a level, those
    occurrences must be next to each other with no other tags in between.
    For example, these are not permitted:

        /a[2]/b[1]
        /a[1]/b[1]

    or:

        /a[1]/b[1]
        /c[1]
        /a[3]/b[1]

    Renumbering example:

        Original:
            a
            /b[5]/c[5]
            /b[5]/c[7]
            /b[5]/c[9]
            /b[7]/c[5]
            /b[7]/c[7]
            /b[9]/c[9]

        Renumbered:
            a
            /b[1]/c[1]
            /b[1]/c[2]
            /b[1]/c[3]
            /b[2]/c[1]
            /b[2]/c[2]
            /b[3]/c[1]

    Args:
        xpaths (list): The list of XPaths or XPath fragments.

    Returns:
        dict: A dictionary containing a mapping from the original XPaths to the renumbered XPaths.
    """

    def split_xpath_prefix_and_num(s):
        """
        Convert an XPath into a SplitXPath namedtuple.

        Each XPath is of the form:
            <parent> or
            <parent>/<child>    where <child> includes all further levels of the
                                hierarchy
                <parent> is of the form:
                    <prefix> or
                    <prefix>[<num>]     where [<num>] is an optional unique ID

        If there is no <child>, None is used. If there is no [<num>], None is
        used.

        Args:
            xpath (str): The XPath string to convert.

        Returns:
            SplitXPath: A namedtuple containing the parent, child, and num elements of the XPath.
        """
        parent, child, *_ = s.split('/', 1) + [None]
        try:
            idx = parent.index('<')
        except ValueError:
            return SplitXPath(s, parent, child, parent, None)
        return SplitXPath(s, parent, child, parent[:idx], int(parent[idx+1:-1]))

    xpath_map = {}

    # split_xpaths is a list containing tuples of
    #   (full_xpath, parent, child, prefix_of_parent, num_of_parent)
    # If there is no child, child is None
    # If there is no number in [n], num_of_parent is None
    split_xpaths = [split_xpath_prefix_and_num(x) for x in xpaths]

    # Group split_xpaths by prefix
    for prefix, prefix_group in groupby(split_xpaths, lambda x: x.prefix):
        prefix_group_list = list(prefix_group)

        # The parents in the resulting group may have unique IDs.
        # We collect those IDs and create a mapping from the original numbers
        # to a new set of suffixes of the form "[<n>]" where <n> is sequentially
        # increasing starting at 1. We also add a special entry for the empty
        # suffix when there is no number.
        unique_nums = sorted(list(set(x.num for x in prefix_group_list
                                      if x.num is not None)))
        renumber_map = {x: f'<{i+1}>' for i, x in enumerate(unique_nums)}
        renumber_map[None] = ''

        # We further group these by unique parent (including the number)
        # and recursively process all children for each unique parent.
        # When the child map is returned, we update our map using the number
        # remapping for the current parent combined with the child map.
        for parent, parent_group in groupby(prefix_group_list,
                                            lambda x: x.parent):
            parent_group_list = list(parent_group)

            # Find all the entries that have children, package them up,
            # and call renumber_xpaths recursively to renumber the next level
            # down.
            children = [x for x in parent_group_list if x.child is not None]
            if children:
                child_map = renumber_xpaths([x.child for x in children])
                xpath_map.update(
                    {f'{x.parent}/{x.child}':
                        f'{x.prefix}{renumber_map[x.num]}/{child_map[x.child]}'
                            for x in children}
                )

            # Find all the entries that have no children. These are leaf
            # nodes. Renumber them.
            no_children = [x for x in parent_group_list if x.child is None]
            xpath_map.update(
                    {f'{x.parent}': f'{x.prefix}{renumber_map[x.num]}'
                        for x in no_children}
            )

    return xpath_map


def split_into_elements(xpath):
    """
    Extract elements from an XPath in the order they appear.

    Args:
        xpath (str): The XPath of a scraped element.

    Returns:
        tuple: The tuple of elements the XPath is composed of.
    """
    elements = []
    parts = xpath.split('/')

    for part in parts:
        if '<' in part:
            part = part.split('<')
            elements.append(part[0])

    return elements


def store_element_text(element, tree, results_dict, nillable_elements_info, config, label):
    """
    Store text content of an XML element in a results dictionary.

    Args:
        element (Element): The XML element.
        tree (ElementTree): The XML tree.
        results_dict (dict): Dictionary to store results.
        nillable_elements_info (dict): A dictionary containing nillable element information.
        config (dict): The configuration data.
        label (str): The name of the label file.
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


def traverse_and_store(element, tree, results_dict,
                       nillable_elements_info, config, label):
    """
    Traverse an XML tree and store text content of specified elements in a dictionary.

    Args:
        element (Element): The current XML element.
        tree (ElementTree): The XML tree.
        results_dict (dict): Dictionary to store results.
        nillable_elements_info (dict): A dictionary containing nillable element information.
        config (dict): The configuration data.
        label (str): The name of the label file.
    """
    store_element_text(element, tree, results_dict,
                       nillable_elements_info, config, label)
    for child in element:
        traverse_and_store(child, tree, results_dict,
                           nillable_elements_info, config, label)


@functools.lru_cache(maxsize=None)
def download_xsd_file(xsd_file):
    try:
        return etree.fromstring(requests.get(xsd_file).content)
    except etree.XMLSyntaxError:
        print(f'The dictionary file {xsd_file} could not be loaded.')
        sys.exit(1)


def update_nillable_elements_from_xsd_file(xsd_file, nillable_elements_info):
    """
    Store all nillable elements and their data types in a dictionary.

    Args:
        xsd_file (str): An XML Schema Definition file.
        nillable_elements_info (dict): A dictionary containing nillable element information.
    """
    tree = download_xsd_file(xsd_file)
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


def write_results_to_csv(results_list, args, output_csv_path):
    """
    Write results from a list of dictionaries to a CSV file.

    Args:
        results_list (list): List of dictionaries containing results.
        output_csv_path (str): The output directory and filename.
    """

    def pad_column_values_and_headers(df):
        col_widths = {}

        # Calculate max width for each column based on header and values
        for col in df.columns:
            max_width = max(df[col].astype(str).apply(len).max(), len(col))
            col_widths[col] = max_width

        # Create a new DataFrame with padded values
        padded_df = df.copy()
        for col in df.columns:
            padded_df[col] = df[col].astype(str).apply(lambda x: x.ljust(col_widths[col]))

        # Pad headers
        padded_headers = {col: col.ljust(col_widths[col]) for col in df.columns}
        padded_df = padded_df.rename(columns=padded_headers)

        return padded_df

    rows = []
    for result_dict in results_list:
        rows.append(result_dict['Results'])

    df = pd.DataFrame(rows)

    if args.sort_by:
        df.sort_values(by=args.sort_by, inplace=True)

    if args.clean_header_field_names:
        df.rename(columns=lambda x: x.replace(
            ':', '_').replace('/', '__').replace('<', '_').replace('>', ''), inplace=True)
        
    if args.fixed_width:
        padded_df = pad_column_values_and_headers(df)
        padded_df.to_csv(output_csv_path, index=False, na_rep='NaN')

    else:
        df.to_csv(output_csv_path, index=False, na_rep='NaN')


##############LABEL GENERATION FUNCTIONS ####################
@functools.cache
def download_xsd_file(xsd_file):
    return etree.fromstring(requests.get(xsd_file).content)

def find_base_attribute(xsd_tree, target_name):
    # Initialize target attribute value
    target_attribute_value = None

    # Define the XPath query to find the target element by name
    xpath_query = (
    f".//*[local-name()='element' and @name='{target_name}']/descendant::*[local-name()='restriction']/@base | "
    f".//*[local-name()='attribute' and @name='{target_name}']/descendant::*[local-name()='restriction']/@base | "
    f".//*[local-name()='simpleType' and @name='{target_name}']/*[local-name()='restriction']/@base | "
    f".//*[local-name()='simpleType' and @name='{target_name}']/descendant::*[local-name()='restriction']/@base | "
    f".//*[local-name()='complexType' and @name='{target_name}']//*[local-name()='extension']/@base | "
    f".//*[local-name()='complexType' and @name='{target_name}']//*[local-name()='extension']/*/*/@base | "
    f".//*[local-name()='complexType' and @name='{target_name}']//*[local-name()='extension']/*/*/*/@base | "
    f".//*[local-name()='complexType' and @name='{target_name}']//*[local-name()='extension']/*/*/*/*/@base | "
    f".//*[local-name()='complexType' and @name='{target_name}']//*[local-name()='extension']/*/@nilReason | "
    f".//*[local-name()='complexType' and @name='Science_Facets']"
    f"//*[local-name()='element' and @name='{target_name}']/@type"
)


    # Execute the XPath query
    target_attribute_values = xsd_tree.xpath(xpath_query)

    # Check if any attribute values are found
    if target_attribute_values:
        # Extract the first attribute value found
        target_attribute_value = target_attribute_values[0]

    # Return the target attribute value
    return target_attribute_value
    

def scrape_namespaces(xsd_url):
    # Fetch XSD content from the URL
    response = requests.get(xsd_url)
    if response.status_code != 200:
        # Handle error if XSD file cannot be retrieved
        raise ValueError(f"Failed to fetch XSD file from URL: {xsd_url}")

    # Parse the XSD content
    tree = etree.fromstring(response.content)

    # Extract namespace declarations
    namespaces = tree.nsmap

    # Handle default namespace
    default_namespace = namespaces.get(None)
    if default_namespace:
        # Add the default namespace with a prefix, e.g., 'ns'
        namespaces['ns'] = default_namespace
        # Remove the default namespace
        del namespaces[None]

    return namespaces


def get_creation_date(file_path):
    """
    Returns the creation date of a file in ISO 8601 format.
    
    :param file_path: Path to the file.
    :return: Creation date of the file in ISO 8601 format.
    """
    if platform.system() == 'Windows':
        # On Windows, use os.path.getctime() to get the creation time
        creation_time = os.path.getctime(file_path)
    else:
        # On Unix-based systems, try to get the birth time
        stat = os.stat(file_path)
        try:
            creation_time = stat.st_birthtime
        except AttributeError:
            # Fallback to the last modification time if birth time is not available
            creation_time = stat.st_mtime
    
    # Convert the creation time to a datetime object
    dt_object = datetime.fromtimestamp(creation_time)
    
    # Return the creation date in ISO 8601 format
    return dt_object.isoformat()


def load_yaml_file(yaml_file):
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)
        

def get_longest_row_length(filename):
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')  # Adjust the delimiter as needed
        longest_row_length = 0
        
        for row in reader:
            current_row_length = sum(len(field.strip()) for field in row) + len(row) - 1
            longest_row_length = max(longest_row_length, current_row_length)
            
    return longest_row_length
#############################################################


def main(cmd_line=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('directorypath', type=str,
                        help='The path to the directory containing the bundleset, '
                             'bundle, or collection you wish to scrape')

    parser.add_argument('pattern', type=str, nargs='+',
                        help='The glob pattern(s) for the files you wish to index. They '
                             'may include wildcards like  *, ?, and **. If using '
                             'multiple, separate with spaces. Surround each pattern '
                             'with quotes.')

    parser.add_argument('--elements-file', type=str,
                        help='Optional text file containing elements to scrape. If not '
                             'specified, all elements found in the XML files are '
                             'included.')

    parser.add_argument('--simplify-xpaths', action='store_true',
                        help='If specified, uses tags of unique XPaths. Any values with '
                             'duplicate values will still use their full XPath.')

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
                        help='Read a user-specified configuration file. File must be a '
                             '.ini file.')
    parser.add_argument('--dump-available-xpaths', action='store_true',
                        help='Give a .txt file of all xpaths within given label '
                             'file(s). This file can be used as a base file for '
                             '--elements-file.')
    parser.add_argument('--fixed-width', action='store_true',
                        help='Create an index file that is fixed-width.')
    parser.add_argument('--generate-label', type=str, nargs=1,
                        choices=['Product_Ancillary', 'Product_Metadata_Supplemental'],
                        help='Generate a PDS4 label for the generated index file. Can '
                             'generate either a Product_Ancillary or '
                             'Product_Metadata_Supplemental label.')
    parser.add_argument('--label-user-input', type=str,
                        help='Provide an optional .yaml file containing additional '
                             'information for the generated label. ')

    if cmd_line is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(cmd_line)

    verboseprint = print if args.verbose else lambda *a, **k: None

    config = load_config_file(args.config_file)

    directory_path = Path(args.directorypath)
    verboseprint(f'Chosen directory path: {directory_path}')
    patterns = args.pattern
    verboseprint(f'Chosen pattern(s): {patterns}')

    nillable_elements_info = {}
    label_files = []
    all_results = []
    tags = []
    xsd_files = []
    for pattern in patterns:
        files = directory_path.glob(f"{pattern}")
        label_files.extend(files)

    verboseprint(f'{len(label_files)} matching file(s) found')

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
            if url not in xsd_files:
                xsd_files.append(url)
            update_nillable_elements_from_xsd_file(url, nillable_elements_info)

        filepath = str(file.relative_to(args.directorypath)).replace('\\', '/')

        namespaces = root.nsmap
        namespaces['pds'] = namespaces.pop(None)
        prefixes = {v: k for k, v in namespaces.items()}

        label_results = {}
        traverse_and_store(root, tree, label_results,
                           nillable_elements_info, config, file)

        for key in list(label_results.keys()):
            process_headers(label_results, key, root, namespaces, prefixes)

        for key in list(label_results.keys()):
            key_new = key.replace('[', '<')
            key_new = key_new.replace(']', '>')
            label_results[key_new] = label_results.pop(key)

        for key in list(label_results.keys()):
            parts = key.split('/')
            new_parts = []
            for part in parts:
                if not part.endswith('>') and parts.index(part) != 1:
                    part = part+'<1>'
                    new_parts.append(part)
                else:
                    new_parts.append(part)
            key_new = '/'.join(new_parts[1:])
            label_results[key_new] = label_results.pop(key)

        for key in list(label_results.keys()):
            if 'cyfunction' in key:
                del label_results[key]

        xpath_map = renumber_xpaths(label_results.keys())
        for old_xpath, new_xpath in xpath_map.items():
            label_results[new_xpath] = label_results.pop(old_xpath)

        correct_duplicates(label_results)

        verboseprint(
            'Now filtering label results according to given element file.')
        label_results = filter_dict_by_glob_patterns(
            label_results, elements_to_scrape, verboseprint)

        if args.simplify_xpaths:
            verboseprint('Simplifying XPath headers.')
            elements = ()
            xpath_elements = []
            names = []
            for key in label_results.keys():
                stuff = split_into_elements(key)
                xpath_elements.append(stuff)
                names.append(stuff[-1])

            duplicates = [tuple(t) for t in set(map(tuple, xpath_elements))
                          if xpath_elements.count(t) > 1]

            duplicate_names = {tag for tag in names if names.count(tag) > 1}

            if duplicate_names:
                verboseprint(f'Duplicate tags found: {duplicate_names}')

            for key in list(label_results.keys()):
                elements = split_into_elements(key)
                tag = elements[-1]
                tags.append(tag)
                if elements not in duplicates and elements[-1] not in duplicate_names:
                    value = tag
                else:
                    value = key
                label_results[value] = label_results.pop(key)

            correct_duplicates(label_results)

        lid = extract_logical_identifier(tree)
        if lid is None:
            lid = label_results.get('pds:logical_identifier', 'Missing_LID')

        # Attach extra columns if asked for.
        bundle_lid = ':'.join(lid.split(':')[:4])
        bundle = bundle_lid.split(':')[-1]
        extras = {'LID': lid, 'filepath': filepath, 'filename': file.name,
                  'bundle': bundle, 'bundle_lid': bundle_lid}
        if args.extra_file_info:
            verboseprint('--extra-file-info requested '
                         f'for the following: {args.extra_file_info}')
            label_results = {**{ele: extras[ele] for ele in args.extra_file_info},
                             **label_results}

        result_dict = {'Results': label_results}
        all_results.append(result_dict)

    if args.output_file:
        output_path = args.output_file
    else:
        output_path = args.directorypath / Path('index_file.csv')

    if args.dump_available_xpaths:
        verboseprint(f'XPaths file generated at {output_path}')
        xpaths = []
        for label in all_results:
            for values in label.values():
                for x in values.keys():
                    if x not in xpaths:
                        xpaths.append(x)

        for x in xpaths:
            tag = x.split('/')[-1].split('<')[0]
            number = x.split('/')[-1].split('<')[0].split('_')[-1]
            if number.isdigit() and tag not in tags:
                y = x.replace('_'+number, '')
                xpaths[xpaths.index(x)] = y

        with open(output_path, 'w') as file:
            for item in xpaths:
                if args.clean_header_field_names:
                    verboseprint(
                        '--clean-header-field-names chosen. Headers reformatted.')
                    item = item.replace(
                        ':', '_').replace('/', '__').replace('<', '_').replace('>', '')
                file.write("%s\n" % item)

    else:
        verboseprint(f'Index file generated at {output_path}')
        write_results_to_csv(all_results, args, output_path)

    if args.generate_label:
        index_file = output_path

        module_dir = Path(__file__).resolve().parent
        yaml_file = module_dir / 'default_values.yaml'
        tempfile = str(module_dir / 'template_pds.xml')
        template = ps.PdsTemplate(tempfile)

        filename = str(Path(index_file).stem)

        header_info = []
        sniffer = csv.Sniffer()

        with open(index_file, 'r', encoding='utf-8') as file:
            full_header = file.readline()
            full_header_length = len(full_header)
            try:
                sample_data = file.read(5000)
                delimiter = sniffer.sniff(sample_data).delimiter
                file.seek(0)  # Reset file pointer to the beginning
            except csv.Error:
                print('Unsupported file format. Please provide a CSV or tab-separated file.')
                sys.exit()
            reader = csv.reader(file, delimiter=delimiter)
            headers = next(reader)

            offset = 0
            field_number = 0
            jump = len(delimiter)
            field_location = 1
            # Example debugging approach
            for header in headers:
                header = header.strip()
                parts = header.split('/')
                name = parts[-1].split('<')[0].split(':')[-1]
                
                true_type = None
                
                for xsd_file in xsd_files:
                    xsd_tree = download_xsd_file(xsd_file)
                    true_type = find_base_attribute(xsd_tree, name)
                    if true_type:
                        break
                
                if not true_type:
                    modified_name = name + "_WO_Units"
                    for xsd_file in xsd_files:
                        xsd_tree = download_xsd_file(xsd_file)
                        true_type = find_base_attribute(xsd_tree, modified_name)
                        if true_type:
                            break


                true_type = true_type.split(':')[-1]
                field_number += 1
                header_length = len(header.encode('utf-8'))
                header_info.append({'name': header,
                                    'field_number': field_number,
                                    'field_location': field_location,
                                    'data_type': true_type,
                                    'field_length': header_length,
                                    'maximum_field_length': header_length,
                                    'offset': offset})
                offset += header_length + jump
                field_location = offset

        creation_date = get_creation_date(index_file)

        label_content = {
            'logical_identifier': 'urn:nasa:pds:rms_metadata:document_opus:' + filename,
            'creation_date_time': str(creation_date),
            'TEMPFILE': index_file,
            'Field_Content': header_info,
            'fields': len(header_info),
            'maximum_record_length': get_longest_row_length(index_file),
            'object_length_h': full_header_length,
            'object_length_t': os.path.getsize(index_file),
            'Table_Delimited': False,
            'Table_Character': False,
            'Product_Ancillary': False,
            'Product_Metadata_Supplemental': False
            }
        
        if args.generate_label[0] == 'Product_Ancillary':
            label_content['Product_Ancillary'] = True
        else:
            label_content['Product_Metadata_Supplemental'] = True

        if args.fixed_width:
            label_content['Table_Character'] = True
        else:
            label_content['Table_Delimited'] = True


        additional_data = load_yaml_file(yaml_file)
        label_content.update(additional_data)

        output_subdir = Path(output_path).parent

        template.write(label_content, str(output_subdir / filename)+'_label.xml')


if __name__ == '__main__':
    main()
