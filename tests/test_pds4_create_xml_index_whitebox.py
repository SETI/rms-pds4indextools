import argparse
from datetime import datetime
from lxml import etree
import os
import pandas as pd
from pathlib import Path
import pytest
import pds4indextools.pds4_create_xml_index as tools
import textwrap as _textwrap
from unittest.mock import patch


# These two variables are the same for all tests, so we can either declare them as
# global variables, or get the ROOT_DIR at the setup stage before running each test
ROOT_DIR = Path(__file__).resolve().parent.parent
TEST_FILES_DIR = ROOT_DIR / 'test_files'
SAMPLES_DIR = TEST_FILES_DIR / 'samples'
EXPECTED_DIR = TEST_FILES_DIR / 'expected'
LABELS_DIR = TEST_FILES_DIR / 'labels'


# Testing load_config_file()
def test_load_config_object():
    config_object = tools.load_config_file()

    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['inapplicable'] ==
            '0001-01-01T12:00Z')
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['missing'] ==
            '0002-01-01T12:00Z')
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['unknown'] ==
            '0003-01-01T12:00Z')
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['anticipated'] ==
            '0004-01-01T12:00Z')

    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD']['inapplicable'] ==
            '0001-01-01T12:00')
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD']['missing'] ==
            '0002-01-01T12:00')
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD']['unknown'] ==
            '0003-01-01T12:00')
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD']['anticipated'] ==
            '0004-01-01T12:00')

    assert config_object['nillable']['pds:ASCII_Date_YMD']['inapplicable'] == '0001-01-01'
    assert config_object['nillable']['pds:ASCII_Date_YMD']['missing'] == '0002-01-01'
    assert config_object['nillable']['pds:ASCII_Date_YMD']['unknown'] == '0003-01-01'
    assert config_object['nillable']['pds:ASCII_Date_YMD']['anticipated'] == '0004-01-01'

    assert config_object['nillable']['pds:ASCII_Integer']['inapplicable'] == -999
    assert config_object['nillable']['pds:ASCII_Integer']['missing'] == -998
    assert config_object['nillable']['pds:ASCII_Integer']['unknown'] == -997
    assert config_object['nillable']['pds:ASCII_Integer']['anticipated'] == -996

    assert config_object['nillable']['pds:ASCII_Real']['inapplicable'] == -999.0
    assert config_object['nillable']['pds:ASCII_Real']['missing'] == -998.0
    assert config_object['nillable']['pds:ASCII_Real']['unknown'] == -997.0
    assert config_object['nillable']['pds:ASCII_Real']['anticipated'] == -996.0

    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['inapplicable'] == 'inapplicable')
    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['missing'] == 'missing')
    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['unknown'] == 'unknown')
    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['anticipated'] == 'anticipated')

    # Tests that the config_object is loaded over.
    config_object = tools.load_config_file(
        specified_config_files=[str(SAMPLES_DIR / 'tester_config_nillable.yaml'),])

    assert config_object['nillable']['pds:ASCII_Date_YMD']['inapplicable'] == '0001-01-01'
    assert config_object['nillable']['pds:ASCII_Date_YMD']['missing'] == '0002-01-01'
    assert config_object['nillable']['pds:ASCII_Date_YMD']['unknown'] == '0003-01-01'
    assert config_object['nillable']['pds:ASCII_Date_YMD']['anticipated'] == '0004-01-01'

    assert config_object['nillable']['pds:ASCII_Integer']['inapplicable'] == -9999
    assert config_object['nillable']['pds:ASCII_Integer']['missing'] == -9988
    assert config_object['nillable']['pds:ASCII_Integer']['unknown'] == -9977
    assert config_object['nillable']['pds:ASCII_Integer']['anticipated'] == -9966

    assert config_object['nillable']['pds:ASCII_Real']['inapplicable'] == -9999.0
    assert config_object['nillable']['pds:ASCII_Real']['missing'] == -9988.0
    assert config_object['nillable']['pds:ASCII_Real']['unknown'] == -9977.0
    assert config_object['nillable']['pds:ASCII_Real']['anticipated'] == -9966.0

    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['inapplicable'] == 'inapplicable_alt')
    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['missing'] == 'missing_alt')
    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['unknown'] == 'unknown_alt')
    assert (config_object['nillable']['pds:ASCII_Short_String_Collapsed']
            ['anticipated'] == 'anticipated_alt')

    # Tests specified configuration files wiht one or the other
    config_object = tools.load_config_file(
        specified_config_files=[str(SAMPLES_DIR / 'tester_config_label.yaml'),])

    assert config_object['label-contents']['version_id'] == '1.0'
    assert (config_object['label-contents']['title'] ==
            'Index file for my occultation bundle')

    # A bad default config file
    with pytest.raises(SystemExit):
        tools.load_config_file(default_config_file=EXPECTED_DIR / 'non_existent_file.ini')

    # A bad specified config file
    with pytest.raises(SystemExit):
        tools.load_config_file(specified_config_files=list(
            str(EXPECTED_DIR / 'non_existent_file.ini')))


# Testing default_value_for_nil()
def test_default_value_for_nil():
    config_object = tools.load_config_file()
    integer = 'pds:ASCII_Integer'
    double_float = 'pds:ASCII_Real'
    datetime_ymd_utc = 'pds:ASCII_Date_Time_YMD_UTC'

    assert config_object['nillable']['pds:ASCII_Integer']['inapplicable'] == -999
    assert tools.default_value_for_nil(config_object, integer, 'inapplicable') == -999
    assert config_object['nillable']['pds:ASCII_Integer']['missing'] == -998
    assert tools.default_value_for_nil(config_object, integer, 'missing') == -998
    assert config_object['nillable']['pds:ASCII_Integer']['unknown'] == -997
    assert tools.default_value_for_nil(config_object, integer, 'unknown') == -997
    assert config_object['nillable']['pds:ASCII_Integer']['anticipated'] == -996
    assert tools.default_value_for_nil(config_object, integer, 'anticipated') == -996

    assert config_object['nillable']['pds:ASCII_Real']['inapplicable'] == -999.0
    assert tools.default_value_for_nil(config_object, double_float,
                                       'inapplicable') == -999.0
    assert config_object['nillable']['pds:ASCII_Real']['missing'] == -998.0
    assert tools.default_value_for_nil(config_object, double_float,
                                       'missing') == -998.0
    assert config_object['nillable']['pds:ASCII_Real']['unknown'] == -997.0
    assert tools.default_value_for_nil(config_object, double_float,
                                       'unknown') == -997.0
    assert config_object['nillable']['pds:ASCII_Real']['anticipated'] == -996.0
    assert tools.default_value_for_nil(config_object, double_float,
                                       'anticipated') == -996.0

    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['inapplicable'] ==
            '0001-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'inapplicable') == '0001-01-01T12:00Z'
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['missing'] ==
            '0002-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'missing') == '0002-01-01T12:00Z'
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['unknown'] ==
            '0003-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'unknown') == '0003-01-01T12:00Z'
    assert (config_object['nillable']['pds:ASCII_Date_Time_YMD_UTC']['anticipated'] ==
            '0004-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'anticipated') == '0004-01-01T12:00Z'

    # Testing None
    assert tools.default_value_for_nil(config_object, None, 'anticipated') is None


def test_default_value_for_nil_ascii_date_time_ymd_utc():
    datetime_ymd_utc = 'pds:ASCII_Date_Time_YMD_UTC'
    example_config = tools.load_config_file()

    # Test 'inapplicable'
    nil_value = 'inapplicable'
    expected_result = '0001-01-01T12:00Z'
    assert (tools.default_value_for_nil(example_config, datetime_ymd_utc, nil_value) ==
            expected_result)

    # Test 'missing'
    nil_value = 'missing'
    expected_result = '0002-01-01T12:00Z'
    assert (tools.default_value_for_nil(example_config, datetime_ymd_utc, nil_value) ==
            expected_result)

    # Test 'unknown'
    nil_value = 'unknown'
    expected_result = '0003-01-01T12:00Z'
    assert (tools.default_value_for_nil(example_config, datetime_ymd_utc, nil_value) ==
            expected_result)

    # Test 'anticipated'
    nil_value = 'anticipated'
    expected_result = '0004-01-01T12:00Z'
    assert (tools.default_value_for_nil(example_config, datetime_ymd_utc, nil_value) ==
            expected_result)


# Testing split_into_elements()
def test_split_into_elements():
    xpath = ('/pds:Product_Observational/pds:Observation_Area<1>/'
             'pds:Observing_System<1>/pds:name<1>')
    pieces = tools.split_into_elements(xpath)
    assert pieces == ['pds:Observation_Area', 'pds:Observing_System', 'pds:name']


# Testing process_schema_location()
def test_process_schema_location():
    label_file = 'tester_label_1.xml'
    schema_files = tools.process_schema_location(LABELS_DIR / label_file)
    assert (schema_files[0] ==
            'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1B00.xsd')
    assert (schema_files[1] ==
            'https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1B00.xsd')
    assert (schema_files[2] ==
            'https://pds.nasa.gov/pds4/mission/cassini/v1/PDS4_CASSINI_1B00_1300.xsd')


def test_parse_label_file_exception_handling(capsys):
    non_existent_file = 'testing_label_fake.xml'
    with pytest.raises(SystemExit) as excinfo:
        tools.process_schema_location(non_existent_file)
    assert excinfo.value.code == 1
    assert (f'Label file could not be found at {non_existent_file}' in
            capsys.readouterr().out)


def test_extract_logical_identifier():
    label_file = 'tester_label_1.xml'
    tree = etree.parse(str(LABELS_DIR / label_file))
    assert (tools.extract_logical_identifier(tree) ==
            'urn:nasa:pds:cassini_iss_saturn:data_raw:1455200455n')


def test_download_xsd_file():
    with pytest.raises(SystemExit):
        tools.download_xsd_file('https://pds.nasa.gov/pds4/pds/v1/badschema.xsd')


def test_clean_headers():
    data = {
        'pds:Product_Observational/pds:Identification_Area<1>/pds:version_id<1>':
        ['1.0']
        }
    df = pd.DataFrame(data)
    tools.clean_headers(df)
    assert (df.columns[0] ==
            'pds_Product_Observational__pds_Identification_Area_1__pds_version_id_1')


def test_scrape_namespaces():
    tree = tools.download_xsd_file('https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1B00.xsd')
    ns = tools.scrape_namespaces(tree)

    assert ns == {'xs': 'http://www.w3.org/2001/XMLSchema',
                  'pds': 'http://pds.nasa.gov/pds4/pds/v1'}


def test_get_longest_row_length():
    filename = EXPECTED_DIR / 'extra_file_info_success_1.csv'
    result = tools.get_longest_row_length(filename)
    assert result == 254

    # Failure
    with pytest.raises(OSError):
        filename = (
            '0eD8s3JGt9RmE5YnVpLZxkf2A1gNbWqQ7TXHlchyojFzPBrMOIKvaSuUwd4pC6JrXjmtbZVnLQW9'
            'gDKfpq7cHWnPoyT5sBM3YXIzlq06F4GDvw1MRaOJpEZU9kBX2AysnVrH6TQeY3G8oKPw5xfmLzN2'
            'hF7sJ9Qc8LbH4ErWaMKtVUXoPIjzpRy1D0qW4s3N7Km8HGaLFCvxl6eyP7UZjWopX4rBdQ2VME3G'
            '9XtF8h2TsjvQnKwDYLb50O8xFI6gUJwpQmA7nrZ4EYkTXoR9CpMN8QG6fKjW5uVDl3oJ1wzBsPpT'
            '2cFmLRe7Hg1SYkN8qQv9RcHjA0F3I4mU')
        result = tools.get_longest_row_length(filename)


@pytest.fixture
def create_temp_file():
    # Create a temporary file
    with open('temp.txt', 'w') as f:
        f.write("Temporary file for testing")
    yield 'temp.txt'
    # Clean up: Delete the temporary file after the test
    os.remove('temp.txt')


@pytest.mark.parametrize('platform_name', ['Windows', 'Linux', 'Darwin'])
def test_get_creation_date(create_temp_file, platform_name):
    # Mock platform.system() to simulate different platforms
    with patch('platform.system', return_value=platform_name):
        creation_date = tools.get_creation_date(create_temp_file)
        assert isinstance(creation_date, str)
        # Assert that the returned date is in ISO 8601 format
        assert datetime.fromisoformat(creation_date)


def test_update_nillable_elements_from_xsd_file():
    xsd_files = []
    nillable_elements_info = {}
    label_files = ['test_files/labels/tester_label_1.xml',
                   'test_files/labels/tester_label_2.xml']

    for label_file in label_files:
        xml_urls = tools.process_schema_location(label_file)
        for url in xml_urls:
            if url not in xsd_files:
                xsd_files.append(url)
                tools.update_nillable_elements_from_xsd_file(url, nillable_elements_info)

    assert nillable_elements_info == {
        'start_time': 'pds:ASCII_Date_Time',
        'start_date_time': 'pds:ASCII_Date_Time_YMD_UTC',
        'stop_time': 'pds:ASCII_Date_Time',
        'stop_date_time': 'pds:ASCII_Date_Time_YMD_UTC',
        'publication_date': 'pds:ASCII_Date_YMD',
        'stop_date': 'pds:ASCII_Date_YMD',
        'reference_frame_id': 'pds:ASCII_Short_String_Collapsed',
        'gain_mode_id': 'cassini:gain_mode_id_WO_Units',
        'gain_mode_id_ir': 'pds:ASCII_Short_String_Collapsed',
        'gain_mode_id_vis': 'pds:ASCII_Short_String_Collapsed',
        'wavelength_range': 'pds:ASCII_Short_String_Collapsed',
        'dsn_station_number': 'pds:ASCII_Integer'}


def test_update_nillable_elements_from_xsd_file_with_edge_cases():
    # Scenario 1: Testing with a type attribute that is None or already in
    # nillable_elements_info

    # Mock XSD content with an element that doesn't have a 'type' attribute
    xsd_content_missing_type = """
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
        <xs:element name="element_without_type" nillable="true"/>
        <xs:element name="start_time" type="pds:ASCII_Date_Time" nillable="true"/>
    </xs:schema>
    """
    # Mock XSD content where type_attribute is already in nillable_elements_info
    xsd_content_duplicate_type = """
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
        <xs:element name="start_time" type="pds:ASCII_Date_Time" nillable="true"/>
        <xs:element name="duplicate_element" type="pds:ASCII_Date_Time" nillable="true"/>
    </xs:schema>
    """

    # Parse the mock XSD contents into XML trees
    tree_missing_type = etree.fromstring(xsd_content_missing_type)
    tree_duplicate_type = etree.fromstring(xsd_content_duplicate_type)

    # Mock the download_xsd_file function to return these trees based on input
    with patch(
        'pds4indextools.pds4_create_xml_index.download_xsd_file'
                   ) as mock_download:
        # Define the behavior of the mock for each file
        mock_download.side_effect = (
            lambda url: tree_missing_type if 'missing_type' in url
            else tree_duplicate_type
            )

        # Initialize the dictionary that will hold the nillable elements information
        nillable_elements_info = {
            'start_time': 'pds:ASCII_Date_Time'  # Simulate an existing entry
        }

        # Call the function with the first scenario (missing type)
        tools.update_nillable_elements_from_xsd_file(
            'test_files/labels/missing_type.xsd', nillable_elements_info)
        assert 'element_without_type' not in nillable_elements_info


def test_clean_header_field_names():
    data = {
        'column:1': [1, 2, 3],
        'column/2': [4, 5, 6],
        '<column>3': [7, 8, 9],
        'normal_column': [10, 11, 12]
        }
    df = pd.DataFrame(data)

    tools.clean_headers(df)
    new = df.to_dict()

    assert new == {
        'column_1': {0: 1, 1: 2, 2: 3},
        'column__2': {0: 4, 1: 5, 2: 6},
        '_column3': {0: 7, 1: 8, 2: 9},
        'normal_column': {0: 10, 1: 11, 2: 12}
        }


def test_compute_max_field_lengths():

    lengths = tools.compute_max_field_lengths(
        str(EXPECTED_DIR / 'extra_file_info_success_1.csv'))

    assert lengths == {
        'filename': 18,
        'filepath': 25,
        'pds:Product_Observational/pds:Identification_Area<1>/pds:logical_identifier<1>':
        72,
        'pds:Product_Observational/pds:Identification_Area<1>/pds:version_id<1>': 3,
        'pds:Product_Observational/pds:Identification_Area<1>/pds:title<1>': 132
        }

    # failure
    with pytest.raises(SystemExit):
        lengths = tools.compute_max_field_lengths(str(EXPECTED_DIR / 'fake_file.csv'))


def test_sort_dataframe_key_error():
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [30, 25, 35]
    })
    sort_keys = ['height']  # Non-existent column

    with pytest.raises(ValueError, match=f"Unknown sort key '{sort_keys[0]}'. For a list "
                                         f"of available sort keys, use the "
                                         f"--output-headers-file option."):
        tools.sort_dataframe(df, sort_keys)


def test_validate_label_type():
    arg = 'ancillary'
    valid_choices = {'ancillary': 'Product_Ancillary',
                     'metadata': 'Product_Metadata_Supplemental'}
    assert tools.validate_label_type(arg, valid_choices) == 'Product_Ancillary'

    # failure
    with pytest.raises(argparse.ArgumentTypeError):
        arg = 'bad_label_type'
        assert tools.validate_label_type(arg, valid_choices) == 'Product_Ancillary'


@patch('os.path.exists')
def test_generate_unique_filename(mock_exists):
    # Setup the mock to return True for the first two checks and False thereafter
    mock_exists.side_effect = [True, True, False]

    # Run the function with a base filename
    base_name = "file.txt"
    result = tools.generate_unique_filename(base_name)

    # Assert that the result is what we expect given the mocked behavior
    # Since the first two checks return True, the counter reaches 2
    assert result == "file2.txt"

    # Ensure os.path.exists was called the expected number of times
    assert mock_exists.call_count == 3


def test_fill_text():
    # Create an instance of MultilineFormatter
    formatter = tools.MultilineFormatter(prog="test_prog")

    # Example input text with multiline separator
    input_text = "This is a long text that should be wrapped.|nThis is a new paragraph."

    # Expected formatted output (with appropriate indentation and line wrapping)
    width = 40
    indent = "    "  # 4 spaces

    expected_output = (
        _textwrap.fill("This is a long text that should be wrapped.",
                       width, initial_indent=indent, subsequent_indent=indent) + '\n' +
        _textwrap.fill("This is a new paragraph.", width, initial_indent=indent,
                       subsequent_indent=indent) + '\n'
    )

    # Run the _fill_text method
    result = formatter._fill_text(input_text, width, indent)

    # Assert the result matches the expected output
    assert result == expected_output


# Assume the get_true_type function is imported from the relevant module.
# from pds4indextools.pds4_create_xml_index import get_true_type
@patch('pds4indextools.pds4_create_xml_index.download_xsd_file')
@patch('pds4indextools.pds4_create_xml_index.scrape_namespaces')
@patch('pds4indextools.pds4_create_xml_index.find_base_attribute')
def test_true_type_found_in_first_file(mock_find_base_attribute, mock_scrape_namespaces,
                                       mock_download_xsd_file):
    # Setup mocks
    mock_download_xsd_file.return_value = "mock_xsd_tree"
    mock_scrape_namespaces.return_value = {"mock_namespace": "mock_value"}
    mock_find_base_attribute.side_effect = ["mock_true_type", None]

    xsd_files = ["file1.xsd", "file2.xsd"]
    tag = "mock_tag"
    namespaces = {"existing_namespace": "value"}

    result = tools.get_true_type(xsd_files, tag, namespaces)

    assert result == "mock_true_type"
    mock_download_xsd_file.assert_called_once_with("file1.xsd")
    mock_find_base_attribute.assert_called_once_with("mock_xsd_tree", tag,
                                                     {"mock_namespace": "mock_value"})


@patch('pds4indextools.pds4_create_xml_index.download_xsd_file')
@patch('pds4indextools.pds4_create_xml_index.scrape_namespaces')
@patch('pds4indextools.pds4_create_xml_index.find_base_attribute')
def test_true_type_found_in_second_file(mock_find_base_attribute, mock_scrape_namespaces,
                                        mock_download_xsd_file):
    # Setup mocks
    mock_download_xsd_file.return_value = "mock_xsd_tree"
    mock_scrape_namespaces.return_value = {"mock_namespace": "mock_value"}

    # First file returns None for both original and modified tags
    # Second file returns the true_type for the original tag
    mock_find_base_attribute.side_effect = [None, None, "mock_true_type"]

    xsd_files = ["file1.xsd", "file2.xsd"]
    tag = "mock_tag"
    namespaces = {"existing_namespace": "value"}

    result = tools.get_true_type(xsd_files, tag, namespaces)

    print(f"Download called: {mock_download_xsd_file.call_count} times")
    print(f"Find base attribute called: {mock_find_base_attribute.call_count} times")

    # Check if the loop iterates over both files and correctly identifies the type in
    # the second file
    assert result == "mock_true_type"
    assert mock_download_xsd_file.call_count == 2
    assert mock_find_base_attribute.call_count == 3


@patch('pds4indextools.pds4_create_xml_index.download_xsd_file')
@patch('pds4indextools.pds4_create_xml_index.scrape_namespaces')
@patch('pds4indextools.pds4_create_xml_index.find_base_attribute')
def test_true_type_found_with_modified_tag(mock_find_base_attribute,
                                           mock_scrape_namespaces,
                                           mock_download_xsd_file):
    # Setup mocks
    mock_download_xsd_file.return_value = "mock_xsd_tree"
    mock_scrape_namespaces.return_value = {"mock_namespace": "mock_value"}
    # Found after modifying the tag
    mock_find_base_attribute.side_effect = [None, "mock_true_type"]

    xsd_files = ["file1.xsd"]
    tag = "mock_tag"
    namespaces = {"existing_namespace": "value"}

    result = tools.get_true_type(xsd_files, tag, namespaces)

    assert result == "mock_true_type"
    mock_find_base_attribute.assert_any_call("mock_xsd_tree", "mock_tag_WO_Units",
                                             {"mock_namespace": "mock_value"})


@patch('pds4indextools.pds4_create_xml_index.download_xsd_file')
@patch('pds4indextools.pds4_create_xml_index.scrape_namespaces')
@patch('pds4indextools.pds4_create_xml_index.find_base_attribute')
def test_true_type_not_found(mock_find_base_attribute, mock_scrape_namespaces,
                             mock_download_xsd_file):
    # Setup mocks
    mock_download_xsd_file.return_value = "mock_xsd_tree"
    mock_scrape_namespaces.return_value = {"mock_namespace": "mock_value"}
    mock_find_base_attribute.return_value = None  # Never found

    xsd_files = ["file1.xsd", "file2.xsd"]
    tag = "mock_tag"
    namespaces = {"existing_namespace": "value"}

    result = tools.get_true_type(xsd_files, tag, namespaces)

    assert result is None
    assert mock_download_xsd_file.call_count == 2
    assert mock_find_base_attribute.call_count == 4
