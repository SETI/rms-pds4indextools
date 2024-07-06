from pathlib import Path
import pytest
import os
import tempfile
import pds4indextools.pds4_create_xml_index as tools


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
            # Testing --limit-xpaths-file
            (
                str(expected_dir / 'limit_xpaths_file_success_1.txt'),
                'limit_xpaths_file.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_1.txt'),
                    '--output-headers-file'
                ]
            ),

            (
                str(expected_dir / 'limit_xpaths_file_success_2.txt'),
                'limit_xpaths_file_2.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_2.txt'),
                    '--output-headers-file',
                ]
            ),

            (
                str(expected_dir / 'limit_xpaths_file_success_2.txt'),
                'elements_dupe_file_2.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_duplicates.txt'),
                    '--output-headers-file',
                ]
            ),

            (
                str(expected_dir / 'limit_xpaths_file_success_3.txt'),
                'limit_xpaths_file_3.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_3.txt'),
                    '--output-headers-file',
                ]
            ),


            (
                str(expected_dir / 'limit_xpaths_file_success_4.txt'),
                'limit_xpaths_file_4.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_4.txt'),
                    '--output-headers-file',
                ]
            ),

            # Testing --simplify-xpaths
            (
                str(expected_dir / 'simplify_xpaths_success_1.txt'),
                'simplify_xpaths_1.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    '--simplify-xpaths',
                    '--output-headers-file',
                ]
            ),

            (
                str(expected_dir / 'simplify_xpaths_success_2.txt'),
                'simplify_xpaths_2.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--simplify-xpaths',
                    '--limit-xpaths-file',
                    str(samples_dir / 'elements_xpath_simplify_2.txt'),
                    '--output-headers-file',
                ]
            ),

            (
                str(expected_dir / 'simplify_xpaths_success_3.txt'),
                'simplify_xpaths_3.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    '--simplify-xpaths',
                    '--limit-xpaths-file',
                    str(samples_dir / 'elements_xpath_simplify_3.txt'),
                    '--output-headers-file',
                ]
            ),

            (
                str(expected_dir / 'simplify_xpaths_success_4.txt'),
                'simplify_xpaths_4.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--simplify-xpaths',
                    '--limit-xpaths-file',
                    str(samples_dir / 'elements_xpath_simplify_4.txt'),
                    '--output-headers-file',
                ]
            ),

            # Testing --add-extra-file-info
            (
                str(expected_dir / 'extra_file_info_success_1.csv'),
                'extra_file_info_1.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_1.txt'),
                    '--add-extra-file-info',
                    'filename,filepath',
                    '--output-index-file',
                ]
            ),

            (
                str(expected_dir / 'extra_file_info_success_2.csv'),
                'extra_file_info_2.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_5.txt'),
                    '--add-extra-file-info',
                    'filename',
                    '--sort-by',
                    'filename',
                    '--output-index-file',
                ]
            ),

            (
                str(expected_dir / 'extra_file_info_success_3.csv'),
                'extra_file_info_3.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'element_5.txt'),
                    '--add-extra-file-info',
                    'filename,filepath,lid,bundle,bundle_lid',
                    '--sort-by',
                    'filename',
                    '--output-index-file',
                ]
            ),

            # Testing --clean-header-field-names
            (
                str(expected_dir / 'clean_header_field_names_success_1.txt'),
                'clean_header_field_names_1.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    '--clean-header-field-names',
                    '--output-headers-file',
                ]
            ),

            (
                str(expected_dir / 'clean_header_field_names_success_2.txt'),
                'clean_header_field_names_2.txt',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'elements_clean_header_field_names.txt'),
                    '--clean-header-field-names',
                    '--output-headers-file',
                ]
            ),

            # Testing --sort by
            (
                str(expected_dir / 'sort_by_success_1.csv'),
                'sort_by_1.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'elements_clean_header_field_names.txt'),
                    '--sort-by',
                    'pds:Product_Observational/pds:Identification_Area<1>/'
                    'pds:logical_identifier<1>',
                    '--output-index-file',
                ]
            ),

            (
                str(expected_dir / 'sort_by_success_2.csv'),
                'sort_by_2.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    str(labels_dir.name / Path('tester_label_2.xml')),
                    str(labels_dir.name / Path('tester_label_3.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'elements_clean_header_field_names.txt'),
                    '--add-extra-file-info',
                    'bundle_lid,filepath',
                    '--sort-by',
                    'bundle_lid',
                    '--output-index-file',
                ]
            ),

            (
                str(expected_dir / 'identical_labels_success.csv'),
                'identical_labels.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('identical_label_*.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'identical_elements.txt'),
                    '--add-extra-file-info',
                    'filename',
                    '--sort-by',
                    'filename',
                    '--output-index-file'
                ]
            ),
            (
                str(expected_dir / 'nilled_element_success.csv'),
                'nilled_element.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('nilled_label.xml')),
                    '--limit-xpaths-file',
                    str(samples_dir / 'elements_nilled.txt'),
                    '--output-index-file'
                ]
            ),
            (
                str(expected_dir / 'fixed_width_success.csv'),
                'fixed_width.csv',
                [
                    str(test_files_dir),
                    str(labels_dir.name / Path('tester_label_1.xml')),
                    '--fixed-width',
                    '--output-index-file'
                ]
            )
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


@pytest.mark.parametrize(
    'cmd_line',
    [
        (
            str(test_files_dir),
            str(labels_dir.name / Path('tester_label_1.xml')),
            str(labels_dir.name / Path('tester_label_2.xml')),
            str(labels_dir.name / Path('tester_label_3.xml')),
            '--limit-xpaths-file',
            str(samples_dir / 'element_1.txt'),
            '--add-extra-file-info',
            'bad_element',
            '--output-headers-file',
        ),
        (
            str(test_files_dir),  # directory path
            ' bad_directory/labels/tester_label_*.xml',  # non-existent directory
            '--limit-xpaths-file',
            str(samples_dir / 'element_1.txt'),  # elements file
            '--add-extra-file-info',  # extra file info
            'filename',
            '--output-headers-file',
        ),
        (
            str(test_files_dir),  # directory path
            str(labels_dir.name / Path('tester_label_1.xml')),
            str(labels_dir.name / Path('tester_label_2.xml')),
            str(labels_dir.name / Path('tester_label_3.xml')),
            '--limit-xpaths-file',
            str(samples_dir / 'element_empty.txt'),  # empty elements file
            '--output-headers-file',
        )
    ]
)
def test_failures(cmd_line):
    # Call main() function with the simulated command line arguments
    with pytest.raises(SystemExit) as e:
        tools.main(cmd_line)
    assert e.type == SystemExit
    assert e.value.code != 0  # Check that the exit code indicates failure


@pytest.mark.parametrize(
    'new_file,cmd_line',
    [
        (
            'nillable.csv',
            [
                str(test_files_dir),  # directory path
                str(labels_dir.name / Path('nilled_label_bad.xml')),
                '--limit-xpaths-file',
                str(samples_dir / 'elements_nilled_bad.txt'),
                '--output-index-file'
            ]
        )
    ]
)
def test_failure_message(capfd, new_file, cmd_line):
    with tempfile.TemporaryDirectory(dir=test_files_dir.parent) as temp_dir:
        temp_dir_path = Path(temp_dir)

        # THE PATH TO THE NEW FILE
        path_to_file = temp_dir_path / new_file
        # Call main() function with the simulated command line arguments
        cmd_line.append(str(path_to_file))

        # Capture the output
        tools.main(cmd_line)
        captured = capfd.readouterr()

        # Check if the expected statement is printed in stdout or stderr
        expected_message = ("Non-nillable element in")
        assert expected_message in captured.out or expected_message in captured.err

        expected_message = ("Non-nillable element in")
        assert expected_message in captured.out or expected_message in captured.err
