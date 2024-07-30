import csv
import io
import pytest
import string

from rest_framework.exceptions import NotFound

from osf_tests.factories import SubjectFactory
from osf.models import RegistrationSchema, RegistrationProvider, NodeLicense
from osf.registrations.utils import (
    BulkRegistrationUpload,
    CategoryField,
    ContributorField,
    DuplicateHeadersError,
    FileUploadNotSupportedError,
    InvalidHeadersError,
    LicenseField,
    MAX_EXCEL_COLUMN_NUMBER,
    METADATA_FIELDS,
    Store,
    get_excel_column_name,
)


def write_csv(header_row, *rows):
    csv_buffer = io.StringIO()
    csv_writer = csv.DictWriter(csv_buffer, fieldnames=header_row)
    csv_writer.writeheader()
    for row in rows:
        csv_writer.writerow(row)
    csv_buffer.seek(0)
    return csv_buffer


def make_row(field_values={}):
    return {**{
        'Title': 'Test title',
        'Description': 'Test description',
        'Admin Contributors': 'jane doe<jane.doe@email.com>; joan doe<joan.doe@email.com>',
        'Read-Write Contributors': '',
        'Read-Only Contributors': '',
        'Bibliographic Contributors': 'jane doe<jane.doe@email.com>; joan doe<joan.doe@email.com>',
        'Category': 'Project',
        'Affiliated Institutions': '',
        'License': 'No license; 2030; jane doe, john doe, joan doe',
        'Subjects': 'Law',
        'Tags': '',
        'Project GUID': '',
        'External ID': '',
        'summary': 'Test study',
    }, **field_values}


def assert_parsed(actual_parsed, expected_parsed):
    parsed = {**actual_parsed['metadata'], **actual_parsed['registration_responses']}
    for key, value in expected_parsed.items():
        assert key in parsed
        actual = parsed[key]
        expected = value
        if actual and expected and isinstance(actual, list) and isinstance(expected, list):
            if isinstance(actual[0], str):
                assert actual.sort() == expected.sort(), f'"{key}" parsed correctly'
                continue
        assert actual == expected


def assert_errors(actual_errors, expected_errors):
    for error in actual_errors:
        assert 'header' in error
        assert 'column_index' in error
        assert 'row_index' in error
        assert 'external_id' in error
        assert error['header'] in expected_errors
        assert error['type'] == expected_errors[error['header']]
    assert len(actual_errors), len(expected_errors.keys())


@pytest.mark.django_db
class TestBulkUploadParserValidationErrors:

    @pytest.fixture()
    def open_ended_schema(self):
        return RegistrationSchema.objects.get(name='Open-Ended Registration', schema_version=3)

    @pytest.fixture()
    def provider_subjects(self):
        return [SubjectFactory() for _ in range(5)]

    @pytest.fixture()
    def registration_provider(self, open_ended_schema, provider_subjects):
        provider = RegistrationProvider.get_default()
        node_license = NodeLicense.objects.get(name='No license')
        provider.default_license = node_license
        provider.licenses_acceptable.add(node_license)
        provider.schemas.add(open_ended_schema)
        provider.subjects.add(*provider_subjects)
        provider.licenses_acceptable.add(NodeLicense.objects.get(name='No license'))
        provider.save()
        return provider

    @pytest.fixture()
    def question_headers(self):
        return ['summary']

    @pytest.fixture()
    def metadata_headers(self):
        return METADATA_FIELDS.keys()

    @pytest.fixture()
    def header_row(self, question_headers, metadata_headers):
        return [*metadata_headers, *question_headers]

    @pytest.fixture()
    def subjects_list(self, provider_subjects):
        return [subject.text for subject in provider_subjects]

    @pytest.fixture()
    def valid_row(self, subjects_list):
        subjects_text = (';').join(subjects_list)
        return make_row({'Subjects': subjects_text})

    def test_csv_parsed(self, header_row, open_ended_schema, subjects_list, registration_provider, valid_row):
        test_csv = write_csv(header_row, {'Title': open_ended_schema._id}, valid_row)
        upload = BulkRegistrationUpload(test_csv, registration_provider._id)
        assert not upload.is_validated
        upload.validate()
        parsed = upload.get_parsed()
        assert upload.is_validated
        assert upload.errors == []
        assert 'registrations' in parsed
        assert 'csv_raw' in parsed['registrations'][0]
        assert 'csv_parsed' in parsed['registrations'][0]
        assert_parsed(parsed['registrations'][0]['csv_parsed'], {
            'Title': 'Test title',
            'Description': 'Test description',
            'Admin Contributors': [{'full_name': 'jane doe', 'email': 'jane.doe@email.com'}, {'full_name': 'joan doe', 'email': 'joan.doe@email.com'}],
            'Read-Write Contributors': [],
            'Read-Only Contributors': [],
            'Bibliographic Contributors': [{'full_name': 'jane doe', 'email': 'jane.doe@email.com'}, {'full_name': 'joan doe', 'email': 'joan.doe@email.com'}],
            'Category': 'project',
            'Affiliated Institutions': [],
            'License': {'name': 'No license', 'required_fields': {'year': '2030', 'copyright_holders': ['jane doe', 'john doe', 'joan doe']}},
            'Subjects': subjects_list,
            'Tags': [],
            'Project GUID': '',
            'External ID': '',
            'summary': 'Test study',
        })
        test_csv.close()

    def test_missing_required_metadata_errors(self, header_row, registration_provider, open_ended_schema):
        missing_required_metadata = {
            'Title': '',
            'Description': '',
            'License': '',
            'Subjects': '',
            'Admin Contributors': '',
            'Bibliographic Contributors': ''}
        test_row = make_row(missing_required_metadata)
        test_csv = write_csv(header_row, {'Title': open_ended_schema._id}, test_row)
        upload = BulkRegistrationUpload(test_csv, registration_provider._id)
        assert upload.is_validated is False
        upload.validate()
        assert upload.is_validated is True
        assert hasattr(upload, 'errors') is True
        assert_errors(upload.errors, {
            'Title': METADATA_FIELDS['Title']['error_type']['missing'],
            'Description': METADATA_FIELDS['Description']['error_type']['missing'],
            'License': METADATA_FIELDS['License']['error_type']['missing'],
            'Subjects': METADATA_FIELDS['Subjects']['error_type']['missing'],
            'Admin Contributors': METADATA_FIELDS['Admin Contributors']['error_type']['missing'],
            'Bibliographic Contributors': METADATA_FIELDS['Bibliographic Contributors']['error_type']['missing'],
        })
        test_csv.close()

    def test_required_schema_question_errors(self, header_row, open_ended_schema, registration_provider, valid_row):
        missing_required_response = {'summary': ''}
        test_row = make_row({**valid_row, **missing_required_response})
        test_csv = write_csv(header_row, {'Title': open_ended_schema._id}, test_row)
        upload = BulkRegistrationUpload(test_csv, registration_provider._id)
        upload.validate()
        assert hasattr(upload, 'errors') is True
        assert_errors(upload.errors, {'summary': 'invalidResponse'})
        test_csv.close()

    def test_invalid_schema_id(self, registration_provider, header_row, valid_row):
        test_csv = write_csv(header_row, {'Title': ''}, valid_row)

        with pytest.raises(NotFound) as exc_info:
            BulkRegistrationUpload(test_csv, registration_provider._id)
        assert str(exc_info.value.detail) == 'Schema with id "" was not found'
        test_csv.close()

    def test_duplicate_headers_validation_error(self, open_ended_schema, registration_provider, valid_row):
        header_row = [
            'Title', 'Description', 'Admin Contributors', 'Read-Write Contributors', 'Read-Only Contributors',
            'Bibliographic Contributors', 'Category', 'Affiliated Institutions', 'License',
            'Subjects', 'Subjects', 'Tags', 'Project GUID', 'External ID', 'summary', 'summary']
        test_csv = write_csv(header_row, {'Title': open_ended_schema._id}, valid_row)

        with pytest.raises(DuplicateHeadersError) as exc_info:
            BulkRegistrationUpload(test_csv, registration_provider._id)

        assert exc_info.value.args[0]['duplicate_headers'] == ['Subjects', 'summary']
        test_csv.close()

    def test_file_upload_not_supported_validation_error(self, header_row, open_ended_schema, registration_provider, valid_row):
        file_input_block = open_ended_schema.schema_blocks.get(block_type='file-input')
        file_input_block.required = True
        file_input_block.display_text = 'N/A'
        file_input_block.help_text = 'N/A'
        file_input_block.example_text = 'N/A'
        file_input_block.save()
        test_csv = write_csv(header_row, {'Title': open_ended_schema._id}, valid_row)

        with pytest.raises(FileUploadNotSupportedError) as exc_info:
            BulkRegistrationUpload(test_csv, registration_provider._id)

        assert exc_info.value.args[0] == 'File uploads are not supported'
        test_csv.close()

    def test_invalid_headers_validation_error(self, open_ended_schema, registration_provider, valid_row):
        header_row = [
            'Title', 'description', 'Admin Contributors', 'Read-Write Contributors', 'Read-Only Contributors',
            'Bibliographic Contributors', 'Category', 'Affiliated Institutions', 'license',
            'Subjects', 'Tags', 'Project GUID', 'External ID', 'Uploader', 'Summary']
        test_csv = write_csv(header_row, {'Title': open_ended_schema._id})
        expected_missing_headers = ['Description', 'summary', 'License']
        expected_invalid_headers = ['Uploader', 'license', 'description', 'Summary']

        with pytest.raises(InvalidHeadersError) as exc_info:
            BulkRegistrationUpload(test_csv, registration_provider._id)

        actual_invalid_headers = exc_info.value.args[0]['invalid_headers']
        actual_missing_headers = exc_info.value.args[0]['missing_headers']

        assert actual_invalid_headers.sort() == expected_invalid_headers.sort()
        assert actual_missing_headers.sort() == expected_missing_headers.sort()
        test_csv.close()

    def test_contributor_regex(self, registration_provider):
        store = Store(registration_provider)
        validations = METADATA_FIELDS['Admin Contributors']
        errors = []
        log_error = lambda **kwargs: errors.append(kwargs['type'])
        sort_func = lambda item: item['full_name']
        valid_contributors = [
            ['Jane Doe<jane.doe@email.com>', [{'full_name': 'Jane Doe', 'email': 'jane.doe@email.com'}]],
            ['成龙<jane.doe@email.com>', [{'full_name': '成龙', 'email': 'jane.doe@email.com'}]],
            ['Jane Doe<jane.doeemail.com>', [{'full_name': 'Jane Doe', 'email': 'jane.doeemail.com'}]],
            ['Jane L. Doe-Smith<jane.doeemail.com>', [{'full_name': 'Jane L. Doe-Smith', 'email': 'jane.doeemail.com'}]],
            ['Jane Doe<jane.doe@email.com>;John Doe<john.doe@email.com>', [{'full_name': 'Jane Doe', 'email': 'jane.doe@email.com'},
                                                                           {'full_name': 'Jane Doe', 'email': 'jane.doe@email.com'}]],
        ]
        for contributors_value, contributors_parsed in valid_contributors:
            contributor_field = ContributorField(contributors_value, validations, log_error, store)
            contributor_field._validate()
            assert contributor_field._parsed_value.sort(key=sort_func) == contributors_parsed.sort(key=sort_func)
        assert not errors

        invalid_contributors = [
            ['', validations['error_type']['missing']],
            ['<>', validations['error_type']['invalid']],
            ['<>;<>', validations['error_type']['invalid']],
            ['Jane Doe<>', validations['error_type']['invalid']],
            ['<jane.doe@email.com>', validations['error_type']['invalid']],
            ['Jane L. Doe-Smith', validations['error_type']['invalid']],
            ['Jane Doe; John Doe', validations['error_type']['invalid']],
            ['<jane.doe@email.com>;<john.doe@email.com>', validations['error_type']['invalid']],
        ]
        for contributors_value, expected_error_type in invalid_contributors:
            contributor_field = ContributorField(contributors_value, validations, log_error, store)
            contributor_field._validate()
            assert errors[-1] == expected_error_type
            assert contributor_field._parsed_value is None

    def test_license_regex(self, registration_provider):
        store = Store(registration_provider)
        validations = METADATA_FIELDS['License']
        errors = []
        log_error = lambda **kwargs: errors.append(kwargs['type'])

        valid_licenses = [
            ['No license;2021;Joan M. Doe', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['Joan M. Doe']}}],
            ['No License;2021;Joan Joe Doe', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['Joan Joe Doe']}}],
            ['No license; 2021; Joan Doe-Smith', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['Joan Doe-Smith']}}],
            ['No license; 2021; 成龙, 李连杰', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['成龙', '李连杰']}}],
            ['No license; 2021; N/A', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['N/A']}}],
            [' No license;2021;Joan Doe ', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['Joan Doe']}}],
            [' No license ; 2021 ; Joan Doe ', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['Joan Doe']}}],
            ['No license; 2021; John Doe, Joan Doe', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['John Doe', 'Joan Doe']}}],
            ['No license;2021;John Doe; Joan Doe', {'name': 'No license', 'required_fields': {'year': '2021', 'copyright_holders': ['John Doe; Joan Doe']}}],
        ]
        for license_value, expected_parsed in valid_licenses:
            license = LicenseField(license_value, validations, log_error, store)
            license._validate()
            assert license._parsed_value == expected_parsed
        assert not errors

        invalid_licenses = [
            ['', validations['error_type']['missing']],
            [';;', validations['error_type']['invalid']],
            ['MIT License;2021;Joan M. Doe', validations['error_type']['invalid']],
            ['No license;;Joan M. Doe', validations['error_type']['invalid']],
            ['No license;202;Joan M. Doe', validations['error_type']['invalid']],
            ['No license;2021;', validations['error_type']['invalid']],
        ]
        for license_value, expected_error_type in invalid_licenses:
            license = LicenseField(license_value, validations, log_error, store)
            license._validate()
            assert errors[-1] == expected_error_type
            assert license._parsed_value is None

    def test_category_field(self):
        valid_categories = [
            ['Analysis', 'analysis'], ['Communication', 'communication'], ['Data', 'data'],
            ['Hypothesis', 'hypothesis'], ['Instrumentation', 'Instrumentation'],
            ['Methods and Measures', 'methods and measures'], ['Procedure', 'procedure'],
            ['Project', 'project'], ['Software', 'software'],
            ['Other', 'other'], ['Uncategorized', ''], ['', ''],
        ]
        store = {}
        validations = METADATA_FIELDS['Category']
        errors = []
        log_error = lambda **kwargs: errors.append(kwargs['type'])
        for category_value, expected_category in valid_categories:
            category = CategoryField(category_value, validations, log_error, store)
            category._validate()
            category._parsed_value == expected_category
        assert not errors

    def test_get_excel_column_name(self):
        columns = [*[[i, string.ascii_uppercase[i]] for i in range(26)], [MAX_EXCEL_COLUMN_NUMBER - 1, 'XFD']]
        for index, expected_column_name in columns:
            assert get_excel_column_name(index) == expected_column_name
