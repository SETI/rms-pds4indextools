from pathlib import Path
import pytest
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent / Path("pds4indextools")))
import pds4_create_xml_index as tools


# These two variables are the same for all tests, so we can either declare them as  
# global variables, or get the ROOT_DIR at the setup stage before running each test 
ROOT_DIR = Path(__file__).resolve().parent.parent
test_files_dir = ROOT_DIR / 'test_files'
expected_dir = test_files_dir / 'expected'
labels_dir = test_files_dir / 'labels'



# Testing load_config_file()
def test_load_config_object():
    config_object = tools.load_config_file(None)

    assert config_object['pds:ASCII_Date_Time_YMD_UTC']['inapplicable'] == '0001-01-01T12:00Z'
    assert config_object['pds:ASCII_Date_Time_YMD_UTC']['missing'] == '0002-01-01T12:00Z'
    assert config_object['pds:ASCII_Date_Time_YMD_UTC']['unknown'] == '0003-01-01T12:00Z'
    assert config_object['pds:ASCII_Date_Time_YMD_UTC']['anticipated'] == '0004-01-01T12:00Z'

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

    assert config_object['pds:ASCII_Short_String_Collapsed']['inapplicable'] == 'inapplicable'
    assert config_object['pds:ASCII_Short_String_Collapsed']['missing'] == 'missing'
    assert config_object['pds:ASCII_Short_String_Collapsed']['unknown'] == 'unknown'
    assert config_object['pds:ASCII_Short_String_Collapsed']['anticipated'] == 'anticipated'


    # Tests that the config_object is loaded over. 
    config_object = tools.load_config_file(expected_dir / 'tester_config.ini')

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

    assert config_object['pds:ASCII_Short_String_Collapsed']['inapplicable'] == 'inapplicable_alt'
    assert config_object['pds:ASCII_Short_String_Collapsed']['missing'] == 'missing_alt'
    assert config_object['pds:ASCII_Short_String_Collapsed']['unknown'] == 'unknown_alt'
    assert config_object['pds:ASCII_Short_String_Collapsed']['anticipated'] == 'anticipated_alt'


    # now, a bad config file
    with pytest.raises(SystemExit):
        with pytest.raises(OSError):
            tools.load_config_file("non_existent_file.ini")


# Testing default_value_for_nil()
def test_default_value_for_nil():
    config_object = tools.load_config_file(None)
    integer = 'pds:ASCII_Integer'
    double_float = 'pds:ASCII_Real'

    assert config_object['pds:ASCII_Integer']['inapplicable'] == '-999'
    assert tools.default_value_for_nil(config_object, integer, 'inapplicable') == -999
    assert config_object['pds:ASCII_Integer']['missing'] == '-998'
    assert tools.default_value_for_nil(config_object, integer, 'missing') == -998
    assert config_object['pds:ASCII_Integer']['unknown'] == '-997'
    assert tools.default_value_for_nil(config_object, integer, 'unknown') == -997
    assert config_object['pds:ASCII_Integer']['anticipated'] == '-996'
    assert tools.default_value_for_nil(config_object, integer, 'anticipated') == -996


    assert config_object['pds:ASCII_Real']['inapplicable'] == '-999.0'
    assert tools.default_value_for_nil(config_object, double_float, 'inapplicable') == -999.0
    assert config_object['pds:ASCII_Real']['missing'] == '-998.0'
    assert tools.default_value_for_nil(config_object, double_float, 'missing') == -998.0
    assert config_object['pds:ASCII_Real']['unknown'] == '-997.0'
    assert tools.default_value_for_nil(config_object, double_float, 'unknown') == -997.0
    assert config_object['pds:ASCII_Real']['anticipated'] == '-996.0'
    assert tools.default_value_for_nil(config_object, double_float, 'anticipated') == -996.0


# Testing split_into_elements()
def test_split_into_elements():
    xpath = '/pds:Product_Observational/pds:Observation_Area<1>/pds:Observing_System<1>/pds:name<1>'
    pieces = tools.split_into_elements(xpath)
    assert pieces == ['pds:Observation_Area', 'pds:Observing_System', 'pds:name']


# Testing process_schema_location()
def test_process_schema_location():
    label_file = 'tester_label_1.xml'
    schema_files = tools.process_schema_location(labels_dir / label_file)
    assert schema_files[0] == 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1B00.xsd'
    assert schema_files[1] == 'https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1B00.xsd'
    assert schema_files[2] == 'https://pds.nasa.gov/pds4/mission/cassini/v1/PDS4_CASSINI_1B00_1300.xsd'
