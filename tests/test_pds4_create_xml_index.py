import pandas as pd
from pathlib import Path
import pytest
import os
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent / Path("pds4indextools")))
import pds4_create_xml_index as tools
import tempfile


# These two variables are the same for all tests, so we can either declare them as  
# global variables, or get the root_dir at the setup stage before running each test 
root_dir = Path(__file__).resolve().parent.parent
test_files_dir = root_dir / 'test_files'

# Set parameters values that you would like to pass into test_elements_file,
# in this case, I assume we are running the same test with different sets of
# golden_file new_file, and cmd_line.
@pytest.mark.parametrize(
        'golden_file,new_file,cmd_line',
        [
            # simple test cases
            (str(test_files_dir / 'elements_file_success.csv'),
             'elements_file.csv',
             [
                str(test_files_dir),
                'tester_label_1.xml',
                '--elements-file',
                str(root_dir / 'samples/sample_elements.txt'),  
                '--output-file',     
             ]
            ),
            # Okay, basic capture
            (str(test_files_dir / 'elements_file_success_2.csv'),
             'elements_file_2.csv',
             [
                str(test_files_dir),
                'tester_label_2.xml',
                '--elements-file',
                str(root_dir / 'samples/element_2.txt'),  
                '--output-file',     
             ]
            ),
            # Multiple partial captures
            (str(test_files_dir / 'elements_file_success_3.csv'),
             'elements_file_3.csv',
             [
                str(test_files_dir),
                'tester_label_2.xml',
                'tester_label_3.xml',
                '--elements-file',
                str(root_dir / 'samples/element_3.txt'),  
                '--output-file',     
             ]
            ),

            # exclusion test
            (str(test_files_dir / 'elements_file_success_4.csv'),
            'elements_file_4.csv',
             [
                str(test_files_dir),
                'tester_label_*.xml',
                '--elements-file',
                str(root_dir / 'test_files/elements_4.txt'),  
                '--output-file',     
             ]
            )
        ]
                        )
                    
def test_elements_file(golden_file, new_file, cmd_line):
    # Create a temporary directory in the same location as the test_files directory
    with tempfile.TemporaryDirectory(dir=test_files_dir.parent) as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # THE PATH TO THE NEW FILE
        path_to_file = temp_dir_path / new_file
        # Call main() function with the simulated command line arguments
        cmd_line.append(str(path_to_file))
        tools.main(cmd_line)

        # Assert that the file now exists
        assert os.path.isfile(path_to_file)

        # Open and compare the two files
        with open(path_to_file, 'rb') as created:
            formed = created.read()

        with open(golden_file, 'rb') as new:
            expected = new.read()

        assert formed == expected
    

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
    config_object = tools.load_config_file("../test_files/tester_config.ini")

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



def test_split_into_elements():
    xpath = '/pds:Product_Observational/pds:Observation_Area[1]/pds:Observing_System[1]/pds:name[1]'
    pieces = tools.split_into_elements(xpath)
    assert pieces == ('pds:Observation_Area', 'pds:Observing_System', 'pds:name')



def test_process_schema_location():
    test_files_dir = Path(__file__).resolve().parent.parent / 'test_files'
    label_file = 'tester_label_1.xml'
    schema_files = tools.process_schema_location(test_files_dir / label_file)
    assert schema_files[0] == 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1B00.xsd'
    assert schema_files[1] == 'https://pds.nasa.gov/pds4/disp/v1/PDS4_DISP_1B00.xsd'
    assert schema_files[2] == 'https://pds.nasa.gov/pds4/mission/cassini/v1/PDS4_CASSINI_1B00_1300.xsd'





# root_dir = Path(__file__).resolve().parent.parent
# print(root_dir)