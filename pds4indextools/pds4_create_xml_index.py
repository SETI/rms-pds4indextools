"""
PDS4 Indexing Tool

This script scrapes label files within specified directories, extracts information from
user-defined XPaths/elements, and generates either an index file or a .txt file containing
the XPaths available to the user. The script provides options for customizing the
extraction process. For a full list of options, use:

python pds4_create_xml_index.py --help
"""

import argparse
from collections import namedtuple
import csv
import configparser
from datetime import datetime
import fnmatch
import functools
import itertools
from itertools import groupby
from lxml import etree
import os
import pandas as pd
from pathlib import Path
import platform
import requests
import sys
import textwrap as _textwrap
import yaml

import pdstemplate as ps

try:
    from ._version import __version__
except ImportError:  # pragma: nocover
    try:
        from _version import __version__
    except ImportError:  # pragma: nocover
        __version__ = 'Version unspecified'


SplitXPath = namedtuple('SplitXPath',
                        ['xpath', 'parent', 'child', 'prefix', 'num'])


def convert_header_to_xpath(root, xml_header_path, namespaces):
    """
    Replace hierarchical components of XPath with attribute names and namespaces.

    While the XPaths are accurate to the hierarchy of the elements referenced, they
    provide no information on their own without the attributed label file for reference.
    This function replaces the asterisks with the respective names of the elements and
    attributes they represent.

    Parameters:
        root (Element): The root element of the XML document.
        xml_header_path (str): Original XML header path.
        namespaces (dict): Dictionary of XML namespace mappings.

    Returns:
        str: Converted XPath expression.

    Example:
        >>> tree = etree.parse(str(path_to_label_file))
        >>> root = tree.getroot()
        >>> xml_header_path = '/*/*[1]/*[2]'
        >>> namespaces = root.nsmap
        >>> convert_header_to_xpath(root, xml_header_path, namespaces)
        'pds:Product_Observational/pds:Identification_Area[1]/pds:version_id[2]'
    """
    sections = xml_header_path.split('/')
    xpath_final = ''
    portion = ''
    for sec in sections[1:]:
        portion = f'{portion}/{sec}'
        tag = str(root.xpath(portion, namespaces=namespaces)[0].tag)
        if sec.startswith('*'):
            sec = sec[1:]
        if ':' in sec:
            sec = ''
        xpath_final = f'{xpath_final}/{tag}{sec}'

    return xpath_final


def correct_duplicates(label_results):
    """
    Correct numbering of XPaths to have correct predicates.

    Some namespaces do not contain predicates, and as a result, must be made artificially
    unique via injected substrings. This function aids in the reformatting of these
    strings so they match the syntax of the renumbering function. Note that this function
    does not affect elements or attributes that natively contain the '_num' substring
    (e.g., cassini:filter_name_1 and cassini:filter_name_2).

    Parameters:
        label_results (dict): The dictionary of XML results. This argument will be
            mutated by the function.

    Example:
            # XPaths in label_results shortened for readability
        >>> keys = list(label_result.keys())
        >>> keys = [
                ../geom:SPICE_Kernel_Identification<1>/geom:kernel_type<1>,
                ../geom:SPICE_Kernel_Identification<1>/geom:kernel_type_1<1>,
                ../geom:SPICE_Kernel_Identification<1>/geom:kernel_type_2<1>,
                ../geom:SPICE_Kernel_Identification<1>/geom:kernel_type_3<1>,
                ../geom:SPICE_Kernel_Identification<1>/geom:kernel_type_4<1>
                ]
        >>> correct_duplicate(label_results)
        >>> keys = list(label_result.keys())
        >>> keys = [
                ../geom:SPICE_Kernel_Identification<1>/geom:kernel_type<1>,
                ../geom:SPICE_Kernel_Identification<2>/geom:kernel_type<1>,
                ../geom:SPICE_Kernel_Identification<3>/geom:kernel_type<1>,
                ../geom:SPICE_Kernel_Identification<4>/geom:kernel_type<1>,
                ../geom:SPICE_Kernel_Identification<5>/geom:kernel_type<1>
                ]
    """
    element_names = set()
    for key in list(label_results.keys()):
        tag = key.split('/')[-1].split('<')[0]
        number = tag.split('_')[-1]
        if number.isdigit():
            cropped = tag.replace('_'+number, '')
            if cropped in element_names:
                key_new = key.replace(('_' + number + '<1>'), '<1>')
                parent = key_new.split('/')[-2].split('<')[0]
                key_new = key_new.replace(parent+'<1>', parent+'<'+str(int(number)+1)+'>')
                label_results[key_new] = label_results.pop(key)
        element_names.add(tag)


def clean_headers(df):
    """
    Clean the headers of a DataFrame by replacing certain characters with safer
    alternatives.

    Parameters:
        df (pandas.DataFrame): The DataFrame whose headers need to be cleaned.
    """
    return df.rename(columns=lambda x: x.replace(
            ':', '_').replace('/', '__').replace('<', '_').replace('>', ''), inplace=True)


def default_value_for_nil(config, data_type, nil_value):
    """
    Find the default value for a nilled element.

    Parameters:
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
    elif data_type is None:
        default = None
    else:
        default = config[data_type][nil_value]

    return default


def extract_logical_identifier(tree):
    """
    Extract the logical_identifier element from an XML tree.

    Parameters:
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

    return logical_identifier.text.strip()


def filter_dict_by_glob_patterns(input_dict, glob_patterns, valid_add_extra_file_info,
                                 verboseprint):
    """
    Filter a dictionary based on a list of glob patterns matching for keys.

    This function filters the input dictionary by including or excluding keys based on
    the provided glob patterns. The glob patterns follow Unix shell-style wildcards.
    Patterns can start with '!' to indicate exclusion.

    Parameters:
        input_dict (dict): The dictionary to filter. Keys are expected to be strings.
        glob_patterns (list): A list of glob patterns to match against dictionary keys.
            Patterns starting with '!' indicate keys that should be excluded from the
            result.
        valid_extra_file_info (list): A list of allowed values that cannot be excluded
            from the result.
        verboseprint (function): A function for printing verbose messages.

    Returns:
        dict: A filtered dictionary containing only the keys that match the inclusion
        patterns and do not match the exclusion patterns.

    Notes:
        1. If `glob_patterns` is `None`, the function returns the original `input_dict`
           unchanged.
        2. If `glob_patterns` is an empty list, the function prints a message and exits
           the program.
        3. For each pattern in `glob_patterns`:
            - If the pattern does not start with '!', the function adds to `filtered_dict`
              all key-value pairs from `input_dict` that match the pattern.
            - If the pattern starts with '!', the function removes from `filtered_dict`
              all key-value pairs that match the pattern (after removing the '!'
              character).

    Example:
        >>> input_dict = {
        ...     'file1.txt': 'content1',
        ...     'file2.log': 'content2',
        ...     'file3.txt': 'content3',
        ...     'file4.log': 'content4'
        ... }
        >>> glob_patterns = ['*.txt', '!file3.txt']
        >>> verboseprint = print
        >>> valid_add_extra_file_info = ['lid', 'filename', 'filepath', 'bundle_lid',
                                         'bundle']
        >>> filter_dict_by_glob_patterns(input_dict, glob_patterns,
                                         valid_add_extra_file_info, verboseprint)
        {'file1.txt': 'content1'}
    """
    filtered_dict = {}

    if glob_patterns is None:
        return input_dict

    for pattern in glob_patterns:
        if not pattern.startswith('!'):
            verboseprint(f'Adding elements according to: {pattern}')
            for key, value in input_dict.items():
                if fnmatch.fnmatch(key, pattern):
                    filtered_dict[key] = value
        else:
            verboseprint(f'Removing elements according to: {pattern}')
            pattern = pattern[1:]
            for key, value in list(filtered_dict.items()):
                if fnmatch.fnmatch(key, pattern) and key not in valid_add_extra_file_info:
                    del filtered_dict[key]

    return filtered_dict


def load_config_file(
        default_config_file=Path(__file__).resolve().parent/'pds4indextools.ini',
        specified_config_file=None):
    """
    Create a config object from a given configuration file.

    This will always load in the default configuration file 'pds4indextools.ini'. In the
    event a specified configuration file is given, the contents of that file will
    override what is in the default configuration file.

    Parameters:
        default_config_file (str, optional): Name of or path to the default configuration
            file.
        specified_config_file (str, optional): Name of or path to a specified
            configuration file.

    Returns:
        configparser.ConfigParser: A ConfigParser object.
    """
    config = configparser.ConfigParser()

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

    Parameters:
        file_path (str): Path to the XML file.

    Returns:
        list: List of XSD URLs extracted from the schema location.
    """
    # Load and parse the XML file
    try:
        tree = etree.parse(file_path)
    except OSError:
        print(f'Label file could not be found at {file_path}')
        sys.exit(1)

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

    Parameters:
        label_results (dict): A dictionary containing XML data to be processed.
        key (str): The key representing the XML tag to be processed.
        root (Element): The root element of the XML tree.
        namespaces (dict): A dictionary containing XML namespace mappings.
        prefixes (dict): A dictionary containing XML namespace prefixes.
    """
    key_new = convert_header_to_xpath(root, key, namespaces)

    # Replace namespaces with prefixes
    for namespace in prefixes.keys():
        if namespace in key_new:
            key_new = key_new.replace('{' + namespace + '}', prefixes[namespace] + ':')

    # Check if key_new already exists in label_results, append suffix if necessary
    if key_new in label_results:
        suffix_gen = itertools.count(start=1, step=1)
        while True:
            trial_key = f"{key_new}_{next(suffix_gen)}"
            if trial_key not in label_results:
                key_new = trial_key
                break

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

    Parameters:
        xpaths (list): The list of XPaths or XPath fragments.

    Returns:
        dict: A dictionary containing a mapping from the original XPaths to the
            renumbered XPaths.
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

        Parameters:
            xpath (str): The XPath string to convert.

        Returns:
            SplitXPath: A namedtuple containing the parent, child, and num
                elements of the XPath.
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
        unique_nums = sorted({x.num for x in prefix_group_list if x.num is not None})
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
                    {
                        f'{x.parent}/{x.child}': (
                            f'{x.prefix}{renumber_map[x.num]}/{child_map[x.child]}'
                        )
                        for x in children
                    }
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

    Parameters:
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


def store_element_text(element, tree, results_dict, xsd_files, nillable_elements_info,
                       config, label_filename):
    """
    Store text content of an XML element in a results dictionary.

    Parameters:
        element (Element): The XML element.
        tree (ElementTree): The XML tree.
        results_dict (dict): Dictionary in which to store results.
        nillable_elements_info (dict): A dictionary containing nillable element
            information.
        config (dict): The configuration data.
        label_filename (str): The name of the label file.
    """
    if element.text and element.text.strip():
        xpath = tree.getpath(element)
        text = ' '.join(element.text.strip().split())
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
                print(f'Non-nillable element in {label_filename} '
                      f'has no associated text: {tag}')
                true_type = None
                for xsd_file in xsd_files:
                    xsd_tree = download_xsd_file(xsd_file)
                    namespaces = scrape_namespaces(xsd_tree)
                    true_type = find_base_attribute(xsd_tree, tag, namespaces)
                    if true_type:
                        break  # Exit the loop once true_type is found

                if not true_type:
                    modified_tag = tag + "_WO_Units"
                    for xsd_file in xsd_files:
                        namespaces = scrape_namespaces(xsd_tree)
                        true_type = find_base_attribute(xsd_tree, modified_tag,
                                                        namespaces)
                        if true_type:
                            break

                default = default_value_for_nil(config, true_type, nil_value)
                results_dict[xpath] = default


def traverse_and_store(element, tree, results_dict, xsd_files,
                       nillable_elements_info, config, label_filename):
    """
    Traverse an XML tree and store text content of specified elements in a dictionary.

    Parameters:
        element (Element): The current XML element.
        tree (ElementTree): The XML tree.
        results_dict (dict): Dictionary to store results.
        nillable_elements_info (dict): A dictionary containing nillable element
            information.
        config (dict): The configuration data.
        label_filename (str): The name of the label file.
    """
    store_element_text(element, tree, results_dict, xsd_files,
                       nillable_elements_info, config, label_filename)
    for child in element:
        traverse_and_store(child, tree, results_dict, xsd_files,
                           nillable_elements_info, config, label_filename)


@functools.lru_cache(maxsize=None)
def download_xsd_file(xsd_file_url):
    """
    Download and parse an XSD file from a given URL using requests.

    Parameters:
        xsd_file_url (str): The URL of the XSD file to download.

    Returns:
        lxml.etree._Element: The root element of the parsed XML tree representing
            the XSD file.
    """
    try:
        return etree.fromstring(requests.get(xsd_file_url).content)
    except etree.XMLSyntaxError:
        print(f'The dictionary file {xsd_file_url} could not be loaded.')
        sys.exit(1)


def update_nillable_elements_from_xsd_file(xsd_file, nillable_elements_info):
    """
    Store all nillable elements and their data types in a dictionary.

    Parameters:
        xsd_file (str): An XML Schema Definition file.
        nillable_elements_info (dict): A dictionary containing nillable element
            information.
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

    Parameters:
        results_list (list): List of dictionaries containing results.
        args (argparse.Namespace): Arguments parsed from command line using argparse.
        output_csv_path (str): The output directory and filename.
    """

    def pad_column_values_and_headers(df):
        """
        Pad the values and headers of a DataFrame to align column widths.

        Parameters:
            df (pandas.DataFrame): The DataFrame whose column values and headers need to
            be padded.

        Returns:
        pandas.DataFrame: A new DataFrame with padded column values and headers, where
            each column's width is equal to the maximum width of its header or its longest
            value.
        """
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
        sort_values = str(args.sort_by).split(',')
        try:
            df.sort_values(by=sort_values, inplace=True)
        except KeyError as bad_sort:
            print(f'Unknown sort key {bad_sort}. For a list of available sort keys, use '
                  f'the --output-headers-file option.')
            sys.exit(1)

    if args.clean_header_field_names:
        clean_headers(df)

    if args.fixed_width:
        padded_df = pad_column_values_and_headers(df)
        print(f'Fixed-width index file generated at {output_csv_path}')
        padded_df.to_csv(output_csv_path, index=False, na_rep='')

    else:
        print(f'Index file generated at {output_csv_path}')
        df.to_csv(output_csv_path, index=False, na_rep='')


def find_base_attribute(xsd_tree, target_name, new_namespaces):
    """
    Finds the base attribute of a target element in an XML schema.

    This function searches for the base type of a given target element in the provided
    XML schema tree. It follows nested type definitions to return the final meaningful
    base type, such as `pds:ASCII_NonNegative_Integer`.

    Parameters:
        xsd_tree (etree._Element): The XML schema tree.
        target_name (str): The name of the target element to search for.

    Returns:
        str: The base type of the target element if found, otherwise None.

    Raises:
        etree.XPathEvalError: If there is an error during XPath evaluation.
    """

    # Register namespaces
    namespaces = {
        'xs': 'http://www.w3.org/2001/XMLSchema',
        'pds': 'http://pds.nasa.gov/pds4/pds/v1'
    }
    namespaces.update(new_namespaces)

    def follow_base_type(base_type):
        """
        Recursively follows the base type definitions to find the final base type.

        Parameters:
            base_type (str): The initial base type to follow.

        Returns:
            str: The final base type.
        """
        while True:
            if 'ASCII' in base_type or 'UTF8' in base_type:
                return base_type

            next_query = (
                f".//xs:simpleType[@name='{base_type.split(':')[-1]}']"
                f"//xs:restriction/@base"
            )
            try:
                next_result = xsd_tree.xpath(next_query, namespaces=namespaces)
            except etree.XPathEvalError:
                break
            if not next_result:
                break
            base_type = next_result[0]
        return base_type

    def get_base_type(query):
        """
        Executes an XPath query to find the base type.

        Parameters:
            query (str): The XPath query to execute.

        Returns:
            list: The result of the XPath query.
        """
        try:
            result = xsd_tree.xpath(query, namespaces=namespaces)
            return result
        except etree.XPathEvalError:
            return None

    queries = [
        f".//xs:complexType[@name='{target_name}']//xs:extension/@base",
        f".//*[local-name()='element' and @name='{target_name}']"
        f"/descendant::*[local-name()='restriction']/@base",
        f".//*[local-name()='attribute' and @name='{target_name}']"
        f"/descendant::*[local-name()='restriction']/@base",
        f".//*[local-name()='simpleType' and @name='{target_name}']"
        f"/*[local-name()='restriction']/@base",
        f".//*[local-name()='simpleType' and @name='{target_name}']"
        f"/descendant::*[local-name()='restriction']/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='extension']/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='extension']/*/*/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='extension']/*/*/*/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='extension']/*/*/*/*/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='extension']/*/@nilReason",
        f".//*[local-name()='complexType' and @name='Science_Facets']"
        f"//*[local-name()='element' and @name='{target_name}']/@type",
        f".//xs:complexType[@name='{target_name}']"
        f"//xs:extension[@base='pds:{target_name}_WO_Units']"
        f"/xs:attribute[@name='unit']/@type",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"/descendant::*[local-name()='simpleContent']"
        f"/*[local-name()='extension']/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"/descendant::*[local-name()='simpleContent']"
        f"/*[local-name()='extension']/*/*/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"/descendant::*[local-name()='simpleContent']"
        f"/*[local-name()='extension']/*/*/*/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"/descendant::*[local-name()='simpleContent']"
        f"/*[local-name()='extension']/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='simpleContent']"
        f"/*[local-name()='extension']/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='simpleContent']"
        f"/*[local-name()='extension']/*/*/@base",
        f".//*[local-name()='complexType' and @name='{target_name}']"
        f"//*[local-name()='simpleContent']"
        f"/*[local-name()='extension']/*/*/*/@base"
    ]

    for query in queries:
        result = get_base_type(query)
        if result:
            base_type = result[0]
            return follow_base_type(base_type)

    return None


def scrape_namespaces(tree):
    """
    Fetch and parse an XSD file from a given URL to extract namespace declarations.

    Parameters:
        xsd_tree (etree._Element): The XML schema tree.

    Returns:
        dict: A dictionary containing the namespace declarations found in the XSD file.
    """

    # Extract namespace declarations
    namespaces = tree.nsmap

    return namespaces


def get_creation_date(file_path):
    """
    Returns the creation date of a file in ISO 8601 format.

    Parameters:
        file_path (str): The path to the file.

    Returns:
        str: The creation date of the file in ISO 8601 format.
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
    """
    Load and parse a YAML file.

    Parameters:
        yaml_file (str): The path to the YAML file to be loaded.

    Returns:
        dict: The contents of the YAML file as a dictionary.
    """
    with open(yaml_file, 'r') as yaml_fp:
        return yaml.safe_load(yaml_fp)


def get_longest_row_length(filename):
    """
    Calculate the length of the longest row in a CSV file.

    Parameters:
        filename (str): The path to the CSV file to be read.

    Returns:
        int: The length of the longest row in the CSV file, measured by the sum of the
        lengths of the fields plus the number of delimiters in the row.
    """
    longest_line = ''
    with open(filename, 'r', newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            line = ','.join(row)
            if len(line) > len(longest_line):
                longest_line = line
    return len(longest_line)


def compute_max_field_lengths(file_path):
    """
    Calculate the maximum length of each column in an index file.

    Parameters:
        file_path (str): The path to the index file.

    Returns:
        dict: A dictionary of headers and the maximum lengths in their columns.

    Raises:
        FileNotFoundError: If the index file was not generated and therefore cannot be
            found.
    """
    max_lengths = {}

    try:
        with open(file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)

            # Initialize the dictionary with headers and set their max length to 0
            for header in reader.fieldnames:
                max_lengths[header] = 0

            # Iterate through each row to calculate maximum field lengths
            for row in reader:
                for header in reader.fieldnames:
                    field_length = len(row[header])
                    if field_length > max_lengths[header]:
                        max_lengths[header] = field_length

    except FileNotFoundError:
        print(f"Index file {file_path} not found")
        sys.exit(1)

    return max_lengths


def validate_comma_separated_list(arg_value, valid_choices):
    """
    Validate and parse a comma-separated list of values.

    Parameters:
        arg_value (str): A string containing comma-separated values to be validated.
        valid_choices (list): A list of valid choices that each value in the
            comma-separated list must be part of.

    Returns:
        list: A list of values parsed from the input string.

    Raises:
        argparse.ArgumentTypeError: If any value in the comma-separated list is not in the
        valid choices.
    """
    values = arg_value.split(',')
    for value in values:
        if value not in valid_choices:
            raise argparse.ArgumentTypeError(f"Invalid choice: '{value}' "
                                             f"(choose from {valid_choices})")
    return values


def validate_label_type(arg_value, valid_choices):
    """
    Validate and parse a single value.

    Parameters:
        arg_value (str): A string value to be validated.
        valid_choices (dict): A dictionary of valid choices for arg_value, with their
        associated full values.

    Returns:
        str: the full version of the aliased string.

    Raises:
        argparse.ArgumentTypeError: If the value is not in the valid choices.
    """
    value = arg_value.lower()
    if value not in valid_choices:
        raise argparse.ArgumentTypeError(f'Invalid choice: "{arg_value}" (choose '
                                         f'from {list(valid_choices.keys())})')
    return valid_choices[value]


def generate_unique_filename(base_name):
    """
    Generate a unique filename by appending a number to the base_name if it already
    exists.

    Parameters:
        base_name (str): The base name of the file including the extension.

    Returns:
        str: A unique filename that does not already exist in the current directory. The
            filename is generated by appending a number to the base name before the file
            extension.
    """
    counter = 1
    new_filename = base_name
    base, extension = os.path.splitext(base_name)

    while os.path.exists(new_filename):
        new_filename = f"{base}{counter}{extension}"
        counter += 1

    return new_filename


class MultilineFormatter(argparse.HelpFormatter):
    """Class to allow multi-line help messages with argparse.

    See details here:
    https://stackoverflow.com/questions/3853722/how-to-insert-newlines-on-argparse-help-text
    """
    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        paragraphs = text.split('|n')
        multiline_text = ''
        for paragraph in paragraphs:
            formatted_paragraph = _textwrap.fill(paragraph, width, initial_indent=indent,
                                                 subsequent_indent=indent) + '\n'
            multiline_text = multiline_text + formatted_paragraph
        return multiline_text


def main(cmd_line=None):
    epilog_sfx = ''
    if __version__ != 'Version unspecified':
        epilog_sfx = f'|nVersion: {__version__}'
    parser = argparse.ArgumentParser(
        formatter_class=MultilineFormatter,
        description='Scrape a set of PDS4 XML labels, usually from a single collection, '
                    'and produce a summary index file.',
        epilog='For more details, please visit the online documentation at: '
               'https://rms-pds4indextools.readthedocs.io/en/latest' + epilog_sfx
        )

    valid_add_extra_file_info = ['lid', 'filename', 'filepath', 'bundle_lid', 'bundle']
    valid_label_types = {'ancillary': 'Product_Ancillary',
                         'metadata': 'Product_Metadata_Supplemental'}

    index_file_generation = parser.add_argument_group('Index File Generation')
    index_file_generation.add_argument('directorypath', type=str,
                                       help='The path to the directory containing the '
                                            'bundleset, bundle, or collection you wish '
                                            'to scrape')

    index_file_generation.add_argument('patterns', type=str, nargs='+',
                                       help='The glob pattern(s) for the files you wish '
                                            'to index. They may include wildcards '
                                            'like *, ?, and **. If supplying multiple '
                                            'patterns, separate with spaces. Surround '
                                            'each pattern with quotes.')

    index_file_generation.add_argument('--output-index-file', type=str,
                                       metavar='INDEX_FILEPATH',
                                       help='Specify the location and filename of the '
                                            'index file.')

    index_file_generation.add_argument(
        '--add-extra-file-info',
        type=lambda x: validate_comma_separated_list(x, valid_add_extra_file_info),
        metavar='COMMA_SEPARATED_COLUMN_NAME(s)',
        help='Add additional columns to the final index file. If specifying multiple '
             'column names, supply them as one argument separated by commas. Possible '
             'values include "lid", "filename", "filepath", "bundle_lid", and "bundle"')

    index_file_generation.add_argument(
        '--sort-by',
        type=str,
        metavar='COMMA_SEPARATED_HEADER_NAME(s)',
        help='Sort resulting index file by one or more columns. Must be specified by '
             'either the full XPath header or the simplified version if using '
             '--simplify-xpaths. To see all available options, use '
             '--output-headers-file.')

    index_file_generation.add_argument('--fixed-width', action='store_true',
                                       help='Create an index file with fixed-width '
                                            'columns.')

    index_file_generation.add_argument('--clean-header-field-names', action='store_true',
                                       help='Rename column headers such that they only '
                                            'contain characters permissible in variable '
                                            'names.')

    index_file_generation.add_argument(
        '--simplify-xpaths',
        action='store_true',
        help='If specified, only writes the tags of unique XPaths to output files. Any '
             'values with duplicate values will still use their full XPath.')

    limiting_results = parser.add_argument_group('Limiting Results')
    limiting_results.add_argument('--limit-xpaths-file', type=str,
                                  metavar='XPATHS_FILEPATH',
                                  help='Optional text file specifying which XPaths to '
                                       'scrape. If not specified, all XPaths found in '
                                       'the label files are included.')

    limiting_results.add_argument('--output-headers-file', type=str,
                                  metavar='HEADERS_FILEPATH',
                                  help='Generate a file containing all possible headers '
                                       'after they have been optionally filtered and/or '
                                       'simplified.')

    label_generation = parser.add_argument_group('Label Generation')
    label_generation.add_argument('--generate-label',
                                  type=lambda x: validate_label_type(x,
                                                                     valid_label_types),
                                  nargs=1,
                                  metavar='{ancillary, metadata}',
                                  help='Generate a PDS4 label for the generated index '
                                       'file called "<output_index_file>.xml". '
                                       'Can generate either a Product_Ancillary or '
                                       'Product_Metadata_Supplemental label.')

    label_generation.add_argument('--label-user-input', type=str,
                                  metavar='USER_INPUT_FILEPATH',
                                  help='Provide an optional file containing additional '
                                       'information for the generated label. File must '
                                       'be in YAML format.')

    misc = parser.add_argument_group('Miscellaneous')
    misc.add_argument('--verbose', action='store_true',
                      help='Turn on verbose mode and show the details of file '
                           'scraping.')

    misc.add_argument('--config-file', type=str,
                      metavar='CONFIG_FILEPATH',
                      help='Read a user-specified configuration file. The file must be '
                           'in .ini file format.')

    args = parser.parse_args(cmd_line)

    verboseprint = print if args.verbose else lambda *a, **k: None

    config = load_config_file(specified_config_file=args.config_file)

    directory_path = Path(args.directorypath)
    verboseprint(f'Top level directory to scrape: {directory_path}')
    patterns = args.patterns
    verboseprint(f'Patterns to scrape: {patterns}')

    # Initializing the required arguments: directorypath and patterns. These
    # will determine which files will be scraped for.

    nillable_elements_info = {}
    label_files = []
    all_results = []
    tags = []
    xsd_files = []

    output_csv_path = None
    output_txt_path = None

    if args.output_index_file:
        output_csv_path = args.output_index_file

    if args.output_headers_file:
        output_txt_path = args.output_headers_file

    if not args.output_index_file and not args.output_headers_file:
        output_csv_path = generate_unique_filename('index.csv')

    for pattern in patterns:
        files = directory_path.glob(pattern)
        if not files:
            verboseprint(f'No files matching {pattern} found in '
                         f'directory: {directory_path}')
        label_files.extend(files)

    verboseprint(f'{len(label_files)} matching file(s) found')

    if label_files == []:
        print(f'No files matching any patterns found in directory: {directory_path}')
        sys.exit(1)

    # Loading in additional patterns from --limit-xpaths-file, if applicable,
    if args.limit_xpaths_file:
        verboseprint(
            f'Element file {args.limit_xpaths_file} used for additional patterns.')
        with open(args.limit_xpaths_file, 'r') as limit_xpaths_file:
            elements_to_scrape = [line.strip() for line in limit_xpaths_file]
            verboseprint('Elements to scrape:')
            for element in elements_to_scrape:
                verboseprint(f'    {element}')

        if elements_to_scrape == []:
            print('Given elements file is empty.')
            sys.exit(1)

    else:
        elements_to_scrape = None

    # For each file in label_files, load in schema files and namespaces for reference.
    # Traverse the label file and scrape the desired contents. Place these contents
    # into a dictionary to later parse into a csv file.
    for label_file in label_files:
        verboseprint(f'Now scraping {label_file}')
        tree = etree.parse(str(label_file))
        root = tree.getroot()

        # Each label file will be scraped for all referenced schema files.
        # This process will also store information on nillable elements for later
        # reference in the event a nilled element exists in a label file.
        xml_urls = process_schema_location(label_file)
        for url in xml_urls:
            if url not in xsd_files:
                xsd_files.append(url)
            update_nillable_elements_from_xsd_file(url, nillable_elements_info)

        filepath = str(label_file.relative_to(args.directorypath)).replace('\\', '/')

        # Creates two dictionaries: one for the namespaces, and one for their
        # associated prefixes.
        namespaces = root.nsmap
        namespaces['pds'] = namespaces.pop(None)
        prefixes = {v: k for k, v in namespaces.items()}

        # Each label file is now traversed and scraped for the requested content.
        label_results = {}
        traverse_and_store(root, tree, label_results, xsd_files,
                           nillable_elements_info, config, label_file)

        # The XPath headers in the label_results dictionary are reformatted to
        # improve readability. Each XPath's namespace is replaced with its prefix for
        # faster reference. Duplicate XPaths are made unique to ensure all results are
        # present in the final product.
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

        # The XPath headers must be renumbered to reflect which instance of the element
        # the column refers to. At this stage, duplicate XPaths may exist again due to
        # the reformatting. These duplicates are corrected to preserve the contents of
        # each element's value.
        xpath_map = renumber_xpaths(label_results.keys())
        for old_xpath, new_xpath in xpath_map.items():
            label_results[new_xpath] = label_results.pop(old_xpath)

        correct_duplicates(label_results)

        # Collect metadata about the label file. The label file's lid is scraped and
        # broken into multiple parts. This metadata can then be requested as additional
        # columns within the index file.
        lid = extract_logical_identifier(tree)
        if lid is None:
            lid = label_results.get('pds:logical_identifier', 'Missing_LID')

        # Attach extra columns if asked for.
        bundle_lid = ':'.join(lid.split(':')[:4])
        bundle = bundle_lid.split(':')[-1]
        extras = {'lid': lid, 'filepath': filepath, 'filename': label_file.name,
                  'bundle': bundle, 'bundle_lid': bundle_lid}
        if args.add_extra_file_info:
            verboseprint('--add-extra-file-info requested '
                         f'for the following: {args.add_extra_file_info}')
            label_results = {**{ele: extras[ele] for ele in
                                args.add_extra_file_info}, **label_results}

        result_dict = {'Results': label_results}
        all_results.append(result_dict)

    if args.add_extra_file_info and elements_to_scrape is not None:
        elements_to_scrape = args.add_extra_file_info + elements_to_scrape

    # The label_results dictionary will now be filtered according to the contents
    # of the --limit-xpaths-file input file. If this command is not used, the original
    # dictionary will be returned. Glob patterns are processed sequentially, with the
    # first pattern having the highest priority.
    for i in range(len(all_results)):
        label_results = all_results[i]['Results']
        label_results = filter_dict_by_glob_patterns(
            label_results, elements_to_scrape, valid_add_extra_file_info, verboseprint)
        all_results[i]['Results'] = label_results

    if all(len(set(r['Results'])) == 0 for r in all_results):
        print('No results found: glob pattern(s) excluded all matches.')
        sys.exit(1)

    # If --simplify-xpaths is used, the XPath headers will be shortened to the
    # element's tag and namespace prefix. This is contingent on the uniqueness of
    # the XPath header; if more than one XPath header shares a tag, a namespace and a
    # predicate value, the XPath header will remain whole.
    if args.simplify_xpaths:
        for i in range(len(all_results)):
            label_results = all_results[i]['Results']
            tags = []
            names = []

            # Step 1: Gather all tags from keys
            for key in label_results.keys():
                elements = key.split('/')
                tag = elements[-1]
                name = tag.split('<')[0]
                tags.append(tag)
                names.append(name)

            # Step 2: Find unique tags
            unique_tags = []
            for tag in tags:
                name = tag.split('<')[0]
                if tags.count(tag) == 1 and names.count(name) == 1:
                    unique_tags.append(tag)

            # Step 3: Create a new dictionary to hold modified results
            new_label_results = {}

            # Step 4: Iterate over original dictionary to modify and copy to new
            # dictionary
            for key, value in list(label_results.items()):
                elements = key.split('/')
                tag = elements[-1]
                if tag in unique_tags:
                    new_tag = tag.split('<')[0]
                    verboseprint(f'XPath header {key} changed to {new_tag}')
                    new_label_results[new_tag] = value
                else:
                    new_label_results[key] = value

            all_results[i]['Results'] = new_label_results

    if output_csv_path:
        verboseprint(f'Index file generated at {output_csv_path}')
        write_results_to_csv(all_results, args, output_csv_path)

    # To instead receive a list of available information available within a label or set
    # of labels, you may use --output-headers-file. This will take all of the keys of
    # the label_results dictionary and place them in the output file, instead of the
    # index file.
    if output_txt_path:
        xpaths = []
        for label in all_results:
            for values in label.values():
                for xpath in values.keys():
                    if xpath not in xpaths:
                        xpaths.append(xpath)

        # The file is now written and placed in a given location. If cleaned header
        # field names are requested, they are processed here before being written in.
        with open(output_txt_path, 'w') as output_fp:
            for item in xpaths:
                if args.clean_header_field_names:
                    verboseprint(
                        '--clean-header-field-names active. Headers reformatted.')
                    item = item.replace(
                        ':', '_').replace('/', '__').replace('<', '_').replace('>', '')
                output_fp.write("%s\n" % item)
        print(f'XPath headers file generated at {output_txt_path}.')
        if not args.output_index_file:
            print('No index file generated because --output-headers-file was '
                  'provided without --output-index-file.')

    # Generates the label for this index file, if --generate-label is used.

    if args.generate_label:
        index_file = output_csv_path

        # The template label file and the default_values.yaml file are initialized.
        module_dir = Path(__file__).resolve().parent
        yaml_file = module_dir / 'default_values.yaml'
        tempfile = str(module_dir / 'index_label_template_pds.xml')
        template = ps.PdsTemplate(tempfile)

        # In this case, this filename is the filename of the index file previously
        # generated.
        try:
            filename = str(Path(index_file).stem)
        except TypeError:
            print('Label not generated. The "--output-index-file" argument is '
                  'required to generate the label file.')
            sys.exit(1)

        header_info = []

        # The index file is opened and read for the contents of the headers. The delimiter
        # is also found for later reference.
        with open(index_file, 'r', encoding='utf-8') as index_fp:
            full_header = index_fp.readline()
            full_header_length = len(full_header)
            index_fp.seek(0)  # Reset file pointer to the beginning

            reader = csv.reader(index_fp, delimiter=',')
            headers = next(reader)

            offset = 0
            field_number = 0
            jump = 1
            field_location = 1
            maximum_field_lengths = compute_max_field_lengths(index_file)

            # Each header is processed for its information, which is then put into
            # header_info to be referenced later. Not all information will be put into
            # the generated label, since some information depends on whether the index
            # file is fixed-width or delimited.
            for header in headers:
                whole_header = header
                if args.fixed_width:
                    header = header.strip()
                if (header in valid_add_extra_file_info and 'lid' in header):
                    true_type = 'pds:ASCII_LID'
                elif (header in valid_add_extra_file_info
                      and 'file' in header):
                    true_type = 'pds:ASCII_File_Specification_Name'
                elif header == 'bundle':
                    true_type = 'pds:ASCII_Text_Preserved'
                else:
                    parts = header.split('/')
                    name = parts[-1].split('<')[0].split(':')[-1]

                    true_type = None

                    for xsd_file in xsd_files:
                        xsd_tree = download_xsd_file(xsd_file)
                        true_type = find_base_attribute(xsd_tree, name, namespaces)
                        if true_type:
                            break

                    if not true_type:
                        modified_name = name + "_WO_Units"
                        for xsd_file in xsd_files:
                            xsd_tree = download_xsd_file(xsd_file)
                            true_type = find_base_attribute(xsd_tree, modified_name,
                                                            namespaces)
                            if true_type:
                                break

                if true_type is None:
                    true_type = ':inapplicable'
                true_type = true_type.split(':')[-1]
                field_number += 1
                header_length = len(header.encode('utf-8'))
                header_name = header

                maximum_field_length = maximum_field_lengths[whole_header]
                header_info.append({'name': header_name,
                                    'field_number': field_number,
                                    'field_location': field_location,
                                    'data_type': true_type,
                                    'field_length': maximum_field_length,
                                    'maximum_field_length': maximum_field_length,
                                    'offset': offset})
                offset += header_length + jump
                field_location = offset

        # The creation date of the index file is stored for later reference.
        creation_date = get_creation_date(index_file)

        # The pre-determined contents of the generated label file. Any additional
        # information is derived from either the default_values.yaml or the specified
        # .yaml file from --label-user-input
        label_content = {
            'logical_identifier': 'urn:nasa:pds:rms_metadata:document_opus:' + filename,
            'creation_date_time': str(creation_date),
            'TEMPFILE': index_file,
            'Field_Content': header_info,
            'fields': len(header_info),
            'maximum_record_length': get_longest_row_length(index_file),
            'object_length_h': full_header_length,
            'object_length_t': os.path.getsize(index_file),
            'Product_Ancillary': False,
            'Product_Metadata_Supplemental': False,
            'Table_Character': False,
            'Table_Delimited': False
            }

        label_content[args.generate_label[0]] = True

        if args.fixed_width:
            label_content['Table_Character'] = True
        else:
            label_content['Table_Delimited'] = True

        additional_data = load_yaml_file(yaml_file)
        unnested_data = {k: v for d in additional_data for k, v in d.items()}
        label_content.update(unnested_data)

        output_subdir = Path(output_csv_path).parent

        print(f'{args.generate_label[0]} label generated at '
              f'{str(output_subdir / filename)}.xml')
        if not args.output_index_file:
            print('Warning: Because --output-index-file was not specified, the '
                  'generated label will only contain generic information. When creating '
                  'index and label files for production use, please specify '
                  '--output-index-file.')
        template.write(label_content, str(output_subdir / filename) + '.xml')


if __name__ == '__main__':
    main()
