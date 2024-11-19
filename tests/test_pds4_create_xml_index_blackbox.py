from pathlib import Path
import pytest
import os
import tempfile
import pds4indextools.pds4_create_xml_index as tools


# These two variables are the same for all tests, so we can either declare them as
# global variables, or get the ROOT_DIR at the setup stage before running each test
ROOT_DIR = Path(__file__).resolve().parent.parent
TEST_FILES_DIR = ROOT_DIR / 'test_files'
SAMPLES_DIR = TEST_FILES_DIR / 'samples'
EXPECTED_DIR = TEST_FILES_DIR / 'expected'
LABELS_DIR = TEST_FILES_DIR / 'labels'
LABEL_NAME = LABELS_DIR.name


def compare_files(path_to_file, golden_file):
    # Assert that the file now exists
    assert os.path.isfile(path_to_file)

    # Open and compare the two files
    with open(path_to_file, 'r') as created:
        formed = created.read()

    with open(golden_file, 'r') as new:
        expected = new.read()

    assert formed == expected


@pytest.mark.parametrize(
    'golden_file,new_file_index,new_file_headers,cmd_line',
    [
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml"
        (
            str(EXPECTED_DIR / 'index_file_success.csv'),
            None, None,
            []
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --generate-label ancillary
        (
            str(EXPECTED_DIR / 'index_file_success.csv'),
            None, None,
            [
                '--generate-label',
                'ancillary'
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --generate-label ancillary --config-file ../test_files/samples/tester_config_reference.yaml --output-index-file label_references_success.csv --simplify-xpaths
        (
            str(EXPECTED_DIR / 'label_references_success.csv'),
            'label_references.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--generate-label',
                'ancillary',
                '--config-file',
                str(SAMPLES_DIR / 'tester_config_reference.yaml'),
                '--simplify-xpaths'
            ]
        ),

        # Testing --limit-xpaths-file with two outputs
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --limit-xpaths-file ../test_files/samples/element_1.txt --output-headers-file limit_xpaths_file.txt --output-index-file limit_xpaths_file.csv
        # Compare result to golden copy:
        # test_files/expected/limit_xpaths_file_success_1.txt
        (
            str(EXPECTED_DIR / 'limit_xpaths_file_success_1.csv'),
            'limit_xpaths_file.csv', 'limit_xpaths_file.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_1.txt')
            ]
        ),

        # Testing --limit-xpaths-file
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --limit-xpaths-file ../test_files/samples/element_1.txt --output-headers-file limit_xpaths_file.txt
        # Compare result to golden copy:
        # test_files/expected/limit_xpaths_file_success_1.txt
        (
            str(EXPECTED_DIR / 'limit_xpaths_file_success_1.txt'),
            None, 'limit_xpaths_file.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_1.txt')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --limit-xpaths-file ../test_files/samples/element_1.txt --output-headers-file limit_xpaths_file.txt
        # Compare result to golden copy:
        # test_files/expected/limit_xpaths_file_success_1.txt
        (
            str(EXPECTED_DIR / 'limit_xpaths_file_success_1.txt'),
            None, 'limit_xpaths_file_wack.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/nonexistent.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_1.txt')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_2.xml" --limit-xpaths-file ../test_files/samples/element_2.txt --output-headers-file limit_xpaths_file_2.txt
        # Compare result to golden copy:
        # test_files/expected/limit_xpaths_file_success_2.txt
        (
            str(EXPECTED_DIR / 'limit_xpaths_file_success_2.txt'),
            None, 'limit_xpaths_file_2.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_2.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_2.txt')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_2.xml" --limit-xpaths-file ../test_files/samples/element_duplicates.txt --output-headers-file elements_dupe_file_2.txt
        # Compare result to golden copy:
        # test_files/expected/limit_xpaths_file_success_2.txt
        (
            str(EXPECTED_DIR / 'limit_xpaths_file_success_2.txt'),
            None, 'elements_dupe_file_2.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_2.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_duplicates.txt')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_2.xml" tester_label_3.xml" --limit-xpaths-file ../test_files/samples/element_3.txt --output-headers-file limit_xpaths_file_3.txt
        # Compare result to golden copy:
        # test_files/expected/limit_xpaths_file_success_3.txt
        (
            str(EXPECTED_DIR / 'limit_xpaths_file_success_3.txt'),
            None, 'limit_xpaths_file_3.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_3.txt')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/element_4.txt --output-headers-file limit_xpaths_file_4.txt
        # Compare result to golden copy:
        # test_files/expected/limit_xpaths_file_success_4.txt
        (
            str(EXPECTED_DIR / 'limit_xpaths_file_success_4.txt'),
            None, 'limit_xpaths_file_4.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_4.txt')
            ]
        ),

        # Testing --simplify-xpaths
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --simplify-xpaths --output-headers-file simplify_xpaths_1.txt
        # Compare result to golden copy:
        # test_files/expected/simplify_xpaths_success_1.txt
        (
            str(EXPECTED_DIR / 'simplify_xpaths_success_1.txt'),
            None, 'simplify_xpaths_1.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--simplify-xpaths'
            ]
        ),

        # Testing --simplify-xpaths
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --simplify-xpaths --limit-xpaths-file ../test_files/samples/elements_xpath_simplify_2.txt --output-headers-file simplify_xpaths_2.txt
        # Compare result to golden copy:
        # test_files/expected/simplify_xpaths_success_2.txt
        (
            str(EXPECTED_DIR / 'simplify_xpaths_success_2.txt'),
            None, 'simplify_xpaths_2.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--simplify-xpaths',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_xpath_simplify_2.txt')
            ]
        ),

        # Testing --simplify-xpaths
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_2.xml" --simplify-xpaths --limit-xpaths-file ../test_files/samples/elements_xpath_simplify_3.txt --output-headers-file simplify_xpaths_3.txt
        # Compare result to golden copy:
        # test_files/expected/simplify_xpaths_success_3.txt
        (
            str(EXPECTED_DIR / 'simplify_xpaths_success_3.txt'),
            None, 'simplify_xpaths_3.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_2.xml',
                '--simplify-xpaths',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_xpath_simplify_3.txt')
            ]
        ),

        # Testing --simplify-xpaths
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_3.xml" --simplify-xpaths --limit-xpaths-file ../test_files/samples/elements_xpath_simplify_4.txt --output-headers-file simplify_xpaths_4.txt
        # Compare result to golden copy:
        # test_files/expected/simplify_xpaths_success_4.txt
        (
            str(EXPECTED_DIR / 'simplify_xpaths_success_4.txt'),
            None, 'simplify_xpaths_4.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_3.xml',
                '--simplify-xpaths',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_xpath_simplify_4.txt')
            ]
        ),

        # Testing --add-extra-file-info
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_2.xml" --limit-xpaths-file ../test_files/samples/element_extra_file_info.txt --add-extra-file-info filename,filepath --output-index-file extra_file_info_1.csv
        # Compare result to golden copy:
        # test_files/expected/extra_file_info_success_1.csv
        (
            str(EXPECTED_DIR / 'extra_file_info_success_1.csv'),
            'extra_file_info_1.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_2.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_extra_file_info.txt'),
                '--add-extra-file-info',
                'filename,filepath',
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/element_5.txt --add-extra-file-info filename --sort-by filename
        # --output-index-file extra_file_info_2.csv
        # Compare result to golden copy:
        # test_files/expected/extra_file_info_success_2.csv
        (
            str(EXPECTED_DIR / 'extra_file_info_success_2.csv'),
            'extra_file_info_2.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_5.txt'),
                '--add-extra-file-info',
                'filename',
                '--sort-by',
                'filename'
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/element_5.txt --add-extra-file-info filename,filepath,lid,bundle,bundle_lid --sort-by filename --output-index-file extra_file_info_3.csv
        # Compare result to golden copy:
        # test_files/expected/extra_file_info_success_3.csv
        (
            str(EXPECTED_DIR / 'extra_file_info_success_3.csv'),
            'extra_file_info_3.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_5.txt'),
                '--add-extra-file-info',
                'filename,filepath,lid,bundle,bundle_lid',
                '--sort-by',
                'filename'
            ]
        ),

        # Testing --clean-header-field-names
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --clean-header-field-names --output-headers-file clean_header_field_names_1.txt
        # Compare result to golden copy:
        # test_files/expected/clean_header_field_names_success_1.txt
        (
            str(EXPECTED_DIR / 'clean_header_field_names_success_1.txt'),
            None, 'clean_header_field_names_1.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--clean-header-field-names'
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_1.xml" --limit-xpaths-file ../test_files/samples/elements_clean_header_field_names.txt --clean-header-field-names --output-headers-file clean_header_field_names_2.txt
        # Compare result to golden copy:
        # test_files/expected/clean_header_field_names_success_2.txt
        (
            str(EXPECTED_DIR / 'clean_header_field_names_success_2.csv'),
            'clean_header_field_names_2.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--clean-header-field-names'
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_1.xml" --limit-xpaths-file ../test_files/samples/elements_clean_header_field_names.txt --clean-header-field-names --output-headers-file clean_header_field_names_2.txt
        # Compare result to golden copy:
        # test_files/expected/clean_header_field_names_success_2.txt
        (
            str(EXPECTED_DIR / 'clean_header_field_names_success_2.txt'),
            None, 'clean_header_field_names_2.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_clean_header_field_names.txt'),
                '--clean-header-field-names'
            ]
        ),

        # Testing --sort by
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/elements_clean_header_field_names.txt --sort-by 'pds:Product_Observational/pds:Identification_Area<1>/pds:logical_identifier<1>' --output-index-file sort_by_1.csv
        # Compare result to golden copy:
        # test_files/expected/sort_by_success_1.csv
        (
            str(EXPECTED_DIR / 'sort_by_success_1.csv'),
            'sort_by_1.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_clean_header_field_names.txt'),
                '--sort-by',
                'pds:Product_Observational/pds:Identification_Area<1>/'
                'pds:logical_identifier<1>'
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/elements_clean_header_field_names.txt --add-extra-file-info bundle_lid,filepath --sort-by bundle_lid --output-index-file sort_by_2.csv
        # Compare result to golden copy:
        # test_files/expected/sort_by_success_2.csv
        (
            str(EXPECTED_DIR / 'sort_by_success_2.csv'),
            'sort_by_2.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_clean_header_field_names.txt'),
                '--add-extra-file-info',
                'bundle_lid,filepath',
                '--sort-by',
                'bundle_lid'
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "identical_label_*.xml" --limit-xpaths-file ../test_files/samples/identical_elements.txt --add-extra-file-info filename --sort-by filename --output-index-file identical_labels.csv
        # Compare result to golden copy:
        # test_files/expected/identical_labels_success.csv
        (
            str(EXPECTED_DIR / 'identical_labels_success.csv'),
            'identical_labels.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/identical_label_*.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'identical_elements.txt'),
                '--add-extra-file-info',
                'filename',
                '--sort-by',
                'filename'
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "nilled_label.xml" --limit-xpaths-file ../test_files/samples/elements_nilled.txt --output-index-file nilled_elements.csv
        # Compare result to golden copy:
        # test_files/expected/nilled_element_success.csv
        (
            str(EXPECTED_DIR / 'nilled_element_success.csv'),
            'nilled_element.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/nilled_label.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_nilled.txt')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --fixed-width --output-index-file fixed_width.csv
        # Compare result to golden copy:
        # test_files/expected/fixed_width_success.csv
        (
            str(EXPECTED_DIR / 'fixed_width_success.csv'),
            'fixed_width.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--fixed-width'
            ]
        ),

        # Executable command: python pds4indextools/pds4_create_xml_index.py ../test_files/labels "nested_label.xml" --output-headers-file headers_nested.txt --simplify-xpaths
        # Compare result to golden copy:
        # test_files/expected/nested_label_success.txt
        (
            str(EXPECTED_DIR / 'nested_label_success.txt'),
            None, 'nested_label.txt',
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/nested_label.xml',
                '--simplify-xpaths',
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --generate-label ancillary --config-file ../test_files/samples/tester_config.yaml --output-index-file generated_label_1.csv
        # Compare result to golden copy:
        # test_files/expected/label_success_1.csv
        # test_files/expected/label_success_1.xml
        (
            str(EXPECTED_DIR / 'label_success_1.csv'),
            'generated_label_1.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--generate-label',
                'ancillary',
                '--config-file',
                str(SAMPLES_DIR / 'tester_config.yaml')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --generate-label metadata --fixed-width --output-index-file generated_label_2.csv --config-file ../test_files/samples/tester_config.yaml --output-index-file generated_label_2.csv
        # Compare result to golden copy:
        # test_files/expected/label_success_2.csv
        # test_files/expected/label_success_2.xml
        (
            str(EXPECTED_DIR / 'label_success_2.csv'),
            'generated_label_2.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                '--generate-label',
                'metadata',
                '--fixed-width',
                '--config-file',
                str(SAMPLES_DIR / 'tester_config.yaml')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/element_5.txt --add-extra-file-info filename,filepath,lid,bundle,bundle_lid --generate-label ancillary --config-file ../test_files/samples/tester_config.yaml --output-index-file generated_label_3.csv
        # Compare result to golden copy:
        # test_files/expected/label_success_3.csv
        # test_files/expected/label_success_3.xml
        (
            str(EXPECTED_DIR / 'label_success_3.csv'),
            'generated_label_3.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/tester_label_1.xml',
                LABEL_NAME + '/tester_label_2.xml',
                LABEL_NAME + '/tester_label_3.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'element_5.txt'),
                '--add-extra-file-info',
                'filename,filepath,lid,bundle,bundle_lid',
                '--sort-by',
                'filename',
                '--generate-label',
                'ancillary',
                '--config-file',
                str(SAMPLES_DIR / 'tester_config.yaml')
            ]
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "rf-tester-label_*.xml" --generate-label metadata --config-file ../test_files/samples/tester_config.yaml --output-index-file cleaned_headers_label.csv --clean-header-field-names
        # Compare result to golden copy:
        # test_files/expected/cleaned_headers_label_success.csv
        # test_files/expected/cleaned_headers_label_success.xml
        (
            str(EXPECTED_DIR / 'cleaned_headers_label_success.csv'),
            'cleaned_headers_label.csv', None,
            [
                str(TEST_FILES_DIR),
                LABEL_NAME + '/rf_tester_label_*.xml',
                '--generate-label',
                'metadata',
                '--config-file',
                str(SAMPLES_DIR / 'tester_config.yaml'),
                '--clean-header-field-names',
                '--simplify-xpaths'
            ]
        ),
    ]
)
def test_success(golden_file, new_file_index, new_file_headers, cmd_line):
    # Create a temporary directory
    with tempfile.TemporaryDirectory(dir=TEST_FILES_DIR.parent) as temp_dir:
        temp_dir_path = Path(temp_dir)

        if new_file_index is None and new_file_headers is None:
            cmd_line.append(str(LABELS_DIR))
            cmd_line.append('tester_label_1.xml')
            # Call main() function with the simulated command line arguments
            tools.main(cmd_line)

            path_to_index_file = ROOT_DIR / 'index.csv'

            compare_files(path_to_index_file, golden_file)
            os.remove(path_to_index_file)

        else:
            # THE PATH TO THE NEW FILE
            if new_file_index:
                path_to_file = temp_dir_path / new_file_index
                path_to_label_file = ROOT_DIR / 'index.xml'
                cmd_line.append('--output-index-file')
                cmd_line.append(str(path_to_file))
                # Call main() function with the simulated command line arguments
                tools.main(cmd_line)

                compare_files(path_to_file, golden_file)

                if '--generate-label' in cmd_line:
                    label_path = str(path_to_file).replace('.csv', '.xml')
                    golden_label = str(golden_file).replace('.csv', '.xml')
                    assert os.path.isfile(label_path)

                    compare_files(label_path, golden_label)
                    if os.path.isfile(path_to_label_file):
                        os.remove(path_to_label_file)

            if new_file_headers:
                path_to_file = temp_dir_path / new_file_headers
                golden_file = str(golden_file).replace('.csv', '.txt')
                cmd_line.append('--output-headers-file')
                cmd_line.append(str(path_to_file))
                # Call main() function with the simulated command line arguments
                tools.main(cmd_line)

                compare_files(path_to_file, golden_file)


@pytest.mark.parametrize(
    'cmd_line',
    [
        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/element_1.txt --add-extra-file-info bad_element --output-headers-file hdout.txt
        (
            str(TEST_FILES_DIR),
            LABEL_NAME + '/tester_label_1.xml',
            LABEL_NAME + '/tester_label_2.xml',
            LABEL_NAME + '/tester_label_3.xml',
            '--limit-xpaths-file',
            str(SAMPLES_DIR / 'element_1.txt'),
            '--add-extra-file-info',
            'bad_element',
            '--output-headers-file',
            'hdout.txt'
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "bad_directory/labels/tester_label_*.xml" --limit-xpaths-file ../test_files/samples/element_1.txt --add-extra-file-info filename --output-headers-file hdout.txt
        (
            str(TEST_FILES_DIR),  # directory path
            'bad_directory/labels/tester_label_*.xml',  # non-existent directory
            '--limit-xpaths-file',
            str(SAMPLES_DIR / 'element_1.txt'),  # elements file
            '--add-extra-file-info',  # extra file info
            'filename',
            '--output-headers-file',
            'hdout.txt'
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" "tester_label_2.xml" "tester_label_3.xml" --limit-xpaths-file ../test_files/samples/element_empty.txt --output-headers-file hdout.txt
        (
            str(TEST_FILES_DIR),  # directory path
            LABEL_NAME + '/tester_label_1.xml',
            LABEL_NAME + '/tester_label_2.xml',
            LABEL_NAME + '/tester_label_3.xml',
            '--limit-xpaths-file',
            str(SAMPLES_DIR / 'element_empty.txt'),  # empty elements file
            '--output-headers-file',
            'hdout.txt'
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --simplify-xpaths --sort-by bad_sort --output-headers-file hdout.csv
        (
            str(TEST_FILES_DIR),
            LABEL_NAME + '/tester_label_1.xml',
            '--simplify-xpaths',
            '--sort-by',
            'bad_sort',
            '--output-index-file',
            'hdout.csv'
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "nonexistent.xml" --output-headers-file hdout.txt
        (
            str(TEST_FILES_DIR),
            LABEL_NAME + '/nonexistent.xml',
            '--output-headers-file',
            'hdout.txt',
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_1.xml" --limit-xpaths-file ../test_files/samples/elements_xpath_simplify_3.txt --output-headers-file hdout.txt
        (
            str(TEST_FILES_DIR),
            LABEL_NAME + '/tester_label_1.xml',
            '--limit-xpaths-file',
            str(SAMPLES_DIR / 'elements_xpath_simplify_3.txt'),
            '--output-headers-file',
            'hdout.txt',
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "tester_label_*.xml" --generate-label ancillary --output-headers-file hdout.txt
        (
            str(TEST_FILES_DIR),
            LABEL_NAME + '/tester_label_*.xml',
            '--generate-label',
            'ancillary',
            '--output-headers-file',
            'hdout.txt',
        ),

        # Executable command: pds4_create_xml_index ../test_files/labels "bad_lid_label.xml" --output-headers-file hdout.txt
        (
            str(TEST_FILES_DIR),
            LABEL_NAME + '/bad_lid_label.xml',
            '--output-headers-file',
            'hdout.txt',
        )

    ]
)
def test_failures(cmd_line):
    try:
        # Call main() function with the simulated command line arguments
        with pytest.raises(SystemExit) as e:
            tools.main(cmd_line)
        assert e.type == SystemExit
        assert e.value.code != 0  # Check that the exit code indicates failure
    finally:
        # Ensure hdout.txt is deleted regardless of test outcome
        if os.path.isfile('hdout.txt'):
            os.remove('hdout.txt')


@pytest.mark.parametrize(
    'NEW_FILE,cmd_line',
    [
        # Executable command: pds4_create_xml_index ../test_files/labels "nilled_label_bad.xml" --limit-xpaths-file ../test_files/samples/elements_nilled_bad.txt --output-index-file indexout.csv
        (
            'nillable.csv',
            [
                str(TEST_FILES_DIR),  # directory path
                LABEL_NAME + '/nilled_label_bad.xml',
                '--limit-xpaths-file',
                str(SAMPLES_DIR / 'elements_nilled_bad.txt'),
                '--output-index-file'
            ]
        )
    ]
)
def test_failure_message(capfd, NEW_FILE, cmd_line):
    with tempfile.TemporaryDirectory(dir=TEST_FILES_DIR.parent) as temp_dir:
        temp_dir_path = Path(temp_dir)

        # THE PATH TO THE NEW FILE
        path_to_file = temp_dir_path / NEW_FILE
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


def test_invalid_arguments():
    with pytest.raises(SystemExit):  # Assuming argparse will call sys.exit on failure
        tools.main(["--invalid-option"])
