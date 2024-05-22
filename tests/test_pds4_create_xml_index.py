from pathlib import Path
import pytest
import os
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent / Path("pds4indextools")))
import pds4_create_xml_index as tools
import tempfile


# These two variables are the same for all tests, so we can either declare them as  
# global variables, or get the ROOT_DIR at the setup stage before running each test 
ROOT_DIR = Path(__file__).resolve().parent.parent
test_files_dir = ROOT_DIR / 'test_files'
samples_dir = test_files_dir / 'samples'
expected_dir = test_files_dir / 'expected'
labels_dir = test_files_dir / 'labels'


@pytest.mark.parametrize(
        'golden_file,new_file,cmd_line',
        [
            # Testing --elements-file
            (str(expected_dir / 'elements_file_success_1.txt'),
             'elements_file.txt',
             [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                '--dump-available-xpaths',
                '--elements-file',
                str(samples_dir / 'element_1.txt'),
                '--output-file'
             ]
            ),

            (str(expected_dir / 'elements_file_success_2.txt'),
             'elements_file_2.txt',
             [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_2.xml')),
                '--dump-available-xpaths',
                '--elements-file',
                str(samples_dir / 'element_2.txt'),  
                '--output-file',
             ]
            ),

            (str(expected_dir / 'elements_file_success_3.txt'),
             'elements_file_3.txt',
             [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_2.xml')),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--dump-available-xpaths',
                '--elements-file',
                str(samples_dir / 'element_3.txt'),  
                '--output-file',     
             ]
            ),


            (str(expected_dir / 'elements_file_success_4.txt'),
            'elements_file_4.txt',
             [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                str(labels_dir.name / Path('tester_label_2.xml')),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--dump-available-xpaths',
                '--elements-file',
                str(samples_dir / 'element_4.txt'),
                '--output-file',     
             ]
            ),
             
            # Testing --simplify-xpaths
            (str(expected_dir / 'simplify_xpaths_success_1.txt'),
            'simplify_xpaths_1.txt',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                '--dump-available-xpaths',
                '--simplify-xpaths',
                '--output-file',     
            ]
            ),

            (str(expected_dir / 'simplify_xpaths_success_2.txt'),
                'simplify_xpaths_2.txt',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                str(labels_dir.name / Path('tester_label_2.xml')),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--dump-available-xpaths',
                '--simplify-xpaths',
                '--elements-file',
                str(samples_dir / 'elements_xpath_simplify_2.txt'),
                '--output-file',     
            ]
            ),

            (str(expected_dir / 'simplify_xpaths_success_3.txt'),
                'simplify_xpaths_3.txt',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_2.xml')),
                '--dump-available-xpaths',
                '--simplify-xpaths',
                '--elements-file',
                str(samples_dir / 'elements_xpath_simplify_3.txt'),
                '--output-file',     
            ]
            ),

            (str(expected_dir / 'simplify_xpaths_success_4.txt'),
                'simplify_xpaths_4.txt',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--dump-available-xpaths',
                '--simplify-xpaths',
                '--elements-file',
                str(samples_dir / 'elements_xpath_simplify_4.txt'),
                '--output-file',
            ]
            ),
            
            # Testing --extra-file-info
            (str(expected_dir / 'extra_file_info_success_1.csv'),
                'extra_file_info_1.csv',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_2.xml')),
                '--elements-file',
                str(samples_dir / 'element_1.txt'),
                '--extra-file-info',
                'filename',
                'filepath',
                '--output-file',     
            ]
            ),

            (str(expected_dir / 'extra_file_info_success_2.csv'),
                'extra_file_info_2.csv',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                str(labels_dir.name / Path('tester_label_2.xml')),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--elements-file',
                str(samples_dir / 'element_extra_file_info_2.txt'),
                '--extra-file-info',
                'filename',
                '--sort-by',
                'filename',
                '--output-file',     
            ]
            ),

            (str(expected_dir / 'extra_file_info_success_3.csv'),
                'extra_file_info_3.csv',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                str(labels_dir.name / Path('tester_label_2.xml')),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--elements-file',
                str(samples_dir / 'element_extra_file_info_2.txt'),
                '--extra-file-info',
                'filename',
                'filepath',
                'LID',
                'bundle',
                'bundle_lid',
                '--sort-by',
                'filename',
                '--output-file',     
            ]
            ),
            
            # Testing --clean-header-field-names
            (str(expected_dir / 'clean_header_field_names_success_1.txt'),
            'clean_header_field_names_1.txt',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                '--dump-available-xpaths',
                '--clean-header-field-names',
                '--output-file',     
            ]
            ),

            (str(expected_dir / 'clean_header_field_names_success_2.txt'),
                'clean_header_field_names_2.txt',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                str(labels_dir.name / Path('tester_label_2.xml')),
                '--dump-available-xpaths',
                '--elements-file',
                str(samples_dir / 'elements_clean_header_field_names.txt'),
                '--clean-header-field-names',
                '--output-file',     
            ]
            ),
            
            # Testing --sort by
            (str(expected_dir / 'sort_by_success_1.csv'),
            'sort_by_1.csv',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                str(labels_dir.name / Path('tester_label_2.xml')),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--elements-file',
                str(samples_dir / 'elements_clean_header_field_names.txt'),
                '--sort-by',
                'pds:Product_Observational/pds:Identification_Area<1>/pds:logical_identifier<1>',
                '--output-file', 
            ]
            ),
            
            (str(expected_dir / 'sort_by_success_2.csv'),
            'sort_by_2.csv',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('tester_label_1.xml')),
                str(labels_dir.name / Path('tester_label_2.xml')),
                str(labels_dir.name / Path('tester_label_3.xml')),
                '--elements-file',
                str(samples_dir / 'elements_clean_header_field_names.txt'),
                '--extra-file-info',
                'bundle_lid',
                'filepath',
                '--sort-by',
                'bundle_lid',
                '--output-file', 
            ]
            ),

            (str(expected_dir / 'identical_labels_success.csv'),
            'identical_labels.csv',
            [
                str(test_files_dir),
                str(labels_dir.name / Path('identical_label_*.xml')),
                '--elements-file',
                str(samples_dir / 'identical_elements.txt'),
                '--extra-file-info',
                'filename',
                '--sort-by',
                'filename',
                '--output-file'
           ]
           ),       
        ]
                        )
def test_success(golden_file, new_file, cmd_line):
    # Create a temporary directory
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




# Testing --extra-file-info (failure case)
@pytest.mark.parametrize(
    'cmd_line',
    [
        (
            str(test_files_dir),
            str(labels_dir.name / Path('tester_label_1.xml')),
            str(labels_dir.name / Path('tester_label_2.xml')),
            str(labels_dir.name / Path('tester_label_3.xml')),
            '--elements-file',
            str(samples_dir / 'element_1.txt'),
            '--extra-file-info',
            'bad_element',
            '--output-file',     
        ),
        (
            str(test_files_dir),  # directory path
            ' bad_directory/labels/tester_label_*.xml',  # non-existent directory
            '--elements-file',
            str(samples_dir / 'element_1.txt'),  # elements file
            '--extra-file-info',  # extra file info
            'filename',
            '--output-file',     
        ),
        (
            str(test_files_dir),  # directory path
            str(labels_dir.name / Path('tester_label_1.xml')),
            str(labels_dir.name / Path('tester_label_2.xml')),
            str(labels_dir.name / Path('tester_label_3.xml')),
            '--elements-file',
            str(samples_dir / 'element_empty.txt'),  # empty elements file
            '--output-file',     
        ),
    ]
)
def test_failures(cmd_line):
    # Call main() function with the simulated command line arguments
    with pytest.raises(SystemExit) as e:
        tools.main(cmd_line)
    assert e.type == SystemExit
    assert e.value.code != 0  # Check that the exit code indicates failure