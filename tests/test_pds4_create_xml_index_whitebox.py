from datetime import datetime
from lxml import etree
import os
import pandas as pd
from pathlib import Path
import pytest
import pds4indextools.pds4_create_xml_index as tools
from unittest import mock


# These two variables are the same for all tests, so we can either declare them as
# global variables, or get the ROOT_DIR at the setup stage before running each test
ROOT_DIR = Path(__file__).resolve().parent.parent
test_files_dir = ROOT_DIR / 'test_files'
expected_dir = test_files_dir / 'expected'
labels_dir = test_files_dir / 'labels'


# Testing load_config_file()
def test_load_config_object():
    config_object = tools.load_config_file()

    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['inapplicable'] ==
            '0001-01-01T12:00Z')
    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['missing'] ==
            '0002-01-01T12:00Z')
    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['unknown'] ==
            '0003-01-01T12:00Z')
    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['anticipated'] ==
            '0004-01-01T12:00Z')

    assert config_object['pds:ASCII_Date_Time_YMD']['inapplicable'] == '0001-01-01T12:00'
    assert config_object['pds:ASCII_Date_Time_YMD']['missing'] == '0002-01-01T12:00'
    assert config_object['pds:ASCII_Date_Time_YMD']['unknown'] == '0003-01-01T12:00'
    assert config_object['pds:ASCII_Date_Time_YMD']['anticipated'] == '0004-01-01T12:00'

    assert config_object['pds:ASCII_Date_YMD']['inapplicable'] == '0001-01-01'
    assert config_object['pds:ASCII_Date_YMD']['missing'] == '0002-01-01'
    assert config_object['pds:ASCII_Date_YMD']['unknown'] == '0003-01-01'
    assert config_object['pds:ASCII_Date_YMD']['anticipated'] == '0004-01-01'

    assert config_object['pds:ASCII_Integer']['inapplicable'] == '-999'
    assert config_object['pds:ASCII_Integer']['missing'] == '-998'
    assert config_object['pds:ASCII_Integer']['unknown'] == '-997'
    assert config_object['pds:ASCII_Integer']['anticipated'] == '-996'

    assert config_object['pds:ASCII_Real']['inapplicable'] == '-999.0'
    assert config_object['pds:ASCII_Real']['missing'] == '-998.0'
    assert config_object['pds:ASCII_Real']['unknown'] == '-997.0'
    assert config_object['pds:ASCII_Real']['anticipated'] == '-996.0'

    assert (config_object['pds:ASCII_Short_String_Collapsed']['inapplicable'] ==
            'inapplicable')
    assert (config_object['pds:ASCII_Short_String_Collapsed']['missing'] ==
            'missing')
    assert (config_object['pds:ASCII_Short_String_Collapsed']['unknown'] ==
            'unknown')
    assert (config_object['pds:ASCII_Short_String_Collapsed']['anticipated'] ==
            'anticipated')

    # Tests that the config_object is loaded over.
    config_object = tools.load_config_file(
        specified_config_file=expected_dir/'tester_config.ini')

    assert config_object['pds:ASCII_Date_YMD']['inapplicable'] == '0001-01-01'
    assert config_object['pds:ASCII_Date_YMD']['missing'] == '0002-01-01'
    assert config_object['pds:ASCII_Date_YMD']['unknown'] == '0003-01-01'
    assert config_object['pds:ASCII_Date_YMD']['anticipated'] == '0004-01-01'

    assert config_object['pds:ASCII_Integer']['inapplicable'] == '-9999'
    assert config_object['pds:ASCII_Integer']['missing'] == '-9988'
    assert config_object['pds:ASCII_Integer']['unknown'] == '-9977'
    assert config_object['pds:ASCII_Integer']['anticipated'] == '-9966'

    assert config_object['pds:ASCII_Real']['inapplicable'] == '-9999.0'
    assert config_object['pds:ASCII_Real']['missing'] == '-9988.0'
    assert config_object['pds:ASCII_Real']['unknown'] == '-9977.0'
    assert config_object['pds:ASCII_Real']['anticipated'] == '-9966.0'

    assert (config_object['pds:ASCII_Short_String_Collapsed']['inapplicable'] ==
            'inapplicable_alt')
    assert (config_object['pds:ASCII_Short_String_Collapsed']['missing'] ==
            'missing_alt')
    assert (config_object['pds:ASCII_Short_String_Collapsed']['unknown'] ==
            'unknown_alt')
    assert (config_object['pds:ASCII_Short_String_Collapsed']['anticipated'] ==
            'anticipated_alt')

    # A bad default config file
    with pytest.raises(SystemExit):
        tools.load_config_file(default_config_file=expected_dir/'non_existent_file.ini')

    # A bad specified config file
    with pytest.raises(SystemExit):
        tools.load_config_file(specified_config_file=expected_dir/'non_existent_file.ini')


# Testing default_value_for_nil()
def test_default_value_for_nil():
    config_object = tools.load_config_file()
    integer = 'pds:ASCII_Integer'
    double_float = 'pds:ASCII_Real'
    datetime_ymd_utc = 'pds:ASCII_Date_Time_YMD_UTC'

    assert config_object['pds:ASCII_Integer']['inapplicable'] == '-999'
    assert tools.default_value_for_nil(config_object, integer, 'inapplicable') == -999
    assert config_object['pds:ASCII_Integer']['missing'] == '-998'
    assert tools.default_value_for_nil(config_object, integer, 'missing') == -998
    assert config_object['pds:ASCII_Integer']['unknown'] == '-997'
    assert tools.default_value_for_nil(config_object, integer, 'unknown') == -997
    assert config_object['pds:ASCII_Integer']['anticipated'] == '-996'
    assert tools.default_value_for_nil(config_object, integer, 'anticipated') == -996

    assert config_object['pds:ASCII_Real']['inapplicable'] == '-999.0'
    assert tools.default_value_for_nil(config_object, double_float,
                                       'inapplicable') == -999.0
    assert config_object['pds:ASCII_Real']['missing'] == '-998.0'
    assert tools.default_value_for_nil(config_object, double_float,
                                       'missing') == -998.0
    assert config_object['pds:ASCII_Real']['unknown'] == '-997.0'
    assert tools.default_value_for_nil(config_object, double_float,
                                       'unknown') == -997.0
    assert config_object['pds:ASCII_Real']['anticipated'] == '-996.0'
    assert tools.default_value_for_nil(config_object, double_float,
                                       'anticipated') == -996.0

    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['inapplicable'] ==
            '0001-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'inapplicable') == '0001-01-01T12:00Z'
    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['missing'] ==
            '0002-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'missing') == '0002-01-01T12:00Z'
    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['unknown'] ==
            '0003-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'unknown') == '0003-01-01T12:00Z'
    assert (config_object['pds:ASCII_Date_Time_YMD_UTC']['anticipated'] ==
            '0004-01-01T12:00Z')
    assert tools.default_value_for_nil(config_object, datetime_ymd_utc,
                                       'anticipated') == '0004-01-01T12:00Z'


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
    schema_files = tools.process_schema_location(labels_dir / label_file)
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
    tree = etree.parse(str(labels_dir / label_file))
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
    filename = expected_dir / 'extra_file_info_success_1.csv'
    result = tools.get_longest_row_length(filename)
    assert result == 254


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
    with mock.patch('platform.system', return_value=platform_name):
        creation_date = tools.get_creation_date(create_temp_file)
        assert isinstance(creation_date, str)
        # Assert that the returned date is in ISO 8601 format
        assert datetime.fromisoformat(creation_date)
