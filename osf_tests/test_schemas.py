# -*- coding: utf-8 -*-
import pytest

from osf.models import RegistrationSchema
from osf.exceptions import ValidationValueError

@pytest.mark.django_db
class TestRegistrationSchema:

    @pytest.fixture()
    def schema_name(self):
        return 'Preregistration Template from AsPredicted.org'

    @pytest.fixture()
    def schema_v2(self, schema_name):
        v2 = RegistrationSchema.objects.create(name=schema_name, schema_version=2)
        return v2

    @pytest.fixture()
    def schema_v3(self, schema_name):
        return RegistrationSchema.objects.get(name=schema_name, schema_version=3)

    def test_get_latest_versions(self, schema_v2, schema_v3):
        latest_versions = RegistrationSchema.objects.get_latest_versions()
        assert schema_v3 in latest_versions
        assert schema_v2 not in latest_versions

    def test_get_latest_version(self, schema_name):
        assert RegistrationSchema.objects.get_latest_version(name=schema_name).schema_version == 3


@pytest.mark.django_db
class TestRegistrationSchemaValidation:

    @pytest.fixture()
    def prereg_schema(self):
        schema = RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)
        return schema

    @pytest.fixture()
    def osf_standard_schema(self):
        schema = RegistrationSchema.objects.get(name='OSF-Standard Pre-Data Collection Registration', schema_version=2)
        return schema

    @pytest.fixture()
    def registered_report_schema(self):
        schema = RegistrationSchema.objects.get(name='Registered Report Protocol Preregistration', schema_version=2)
        return schema

    @pytest.fixture()
    def prereg_test_data(self):
        return {
            'q1': 'This is a test.',
            'q3': 'Here is an answer to this question.',
            'q4': 'This is a hypothesis',
            'q5': 'Registration prior to creation of data',
            'q6': 'This is a test',
            'q7.question': 'This is a test',
            'q8': 'This is a test',
            'q9': 'This is a test',
            'q10': 'This is a test',
            'q11.question': 'This is a test',
            'q12.question': 'This is a test',
            'q13.question': 'This is a test',
            'q13.uploader': [{
                'file_name': 'Alphabet.txt',
                'file_id': '5d5d61704a445a02048ad476',
                'file_hashes': {
                    'sha256': 'asdfgj'
                },
                'file_urls': {
                    'html': '/aguid/files/osfstorage/5d5d61704a445a02048ad476'
                },
            }],
            'q14': 'Meta-Analysis - A systematic review of published studies.',
            'q15': ['No blinding is involved in this study.', 'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.'],
            'q16.question': 'This is a test',
            'q17': 'This is a test',
            'q19.question': 'This is a test',
            'q20': 'This is a test',
            'q21': 'This is a test',
            'q22': 'This is a test',
            'q23': 'This is a test',
            'q24': 'This is a test',
        }

    @pytest.fixture()
    def osf_standard_data(self):
        return {
            'looked': 'Yes',
            'datacompletion': 'No, data collection has not begun',
            'comments': 'test comments'
        }

    def test_successful_validation(self, prereg_schema, prereg_test_data, osf_standard_schema, osf_standard_data):
        validated = prereg_schema.validate_registration_responses(prereg_test_data)
        assert validated is True

        validated = osf_standard_schema.validate_registration_responses(osf_standard_data)
        assert validated is True

    def test_bad_validation(self, osf_standard_schema):
        # additional key
        bad_key_data = {
            'bad': 'key'
        }

        with pytest.raises(ValidationValueError) as excinfo:
            osf_standard_schema.validate_registration_responses(bad_key_data)
        assert excinfo.value.message == "Additional properties are not allowed ('bad' was unexpected)"

        # multiple choice does not match
        bad_multiple_choice = {
            'datacompletion': 'Of course!'
        }

        with pytest.raises(ValidationValueError) as excinfo:
            osf_standard_schema.validate_registration_responses(bad_multiple_choice)

        assert excinfo.value.message == 'For your registration, your response to ' + \
            "the 'Data collection status' field is invalid, your response must be one of the provided options."

    def test_uploader_validation(self, prereg_schema, prereg_test_data):
        """
        Expected format is array of nested dictionaries with name and id keys
        """
        prereg_test_data['q13.uploader'] = {}
        with pytest.raises(ValidationValueError) as excinfo:
            prereg_schema.validate_registration_responses(prereg_test_data)
        assert excinfo.value.message == "For your registration, your response to the 'q13.uploader' field is invalid. {} is not of type 'array'"

        prereg_test_data['q13.uploader'] = ['hello']
        with pytest.raises(ValidationValueError) as excinfo:
            prereg_schema.validate_registration_responses(prereg_test_data)
        assert excinfo.value.message == "For your registration, your response to the 'q13.uploader' field is invalid. 'hello' is not of type 'object'"

        prereg_test_data['q13.uploader'] = [{'bad_key': '12345'}]
        with pytest.raises(ValidationValueError) as excinfo:
            prereg_schema.validate_registration_responses(prereg_test_data)
        assert excinfo.value.message == "For your registration, your response to the 'q13.uploader' field is invalid. Additional properties are not allowed ('bad_key' was unexpected)"

        prereg_test_data['q13.uploader'] = [{'file_name': '12345'}]
        with pytest.raises(ValidationValueError) as excinfo:
            prereg_schema.validate_registration_responses(prereg_test_data)
        assert excinfo.value.message.startswith("For your registration, your response to the 'q13.uploader' field is invalid.")

        prereg_test_data['q13.uploader'] = [{'file_name': '12345', 'file_id': 'abcde'}]
        with pytest.raises(ValidationValueError) as excinfo:
            prereg_schema.validate_registration_responses(prereg_test_data)
        assert excinfo.value.message.startswith("For your registration, your response to the 'q13.uploader' field is invalid.")

    def test_validate_required_fields(self, registered_report_schema, prereg_schema, prereg_test_data):
        # Passing in required_fields is True enforces that required fields are present
        with pytest.raises(ValidationValueError) as excinfo:
            registered_report_schema.validate_registration_responses({}, required_fields=True)
        assert excinfo.value.message == "'q1' is a required property"

        validated = registered_report_schema.validate_registration_responses({})
        assert validated is True

        # Assert multiple choice questions accept empty strings if required_fields is False
        prereg_test_data['q5'] = ''
        validated = prereg_schema.validate_registration_responses(prereg_test_data)
        assert validated is True

        with pytest.raises(ValidationValueError) as excinfo:
            prereg_schema.validate_registration_responses(prereg_test_data, required_fields=True)
        assert excinfo.value.message == "For your registration, your response to the 'Existing Data' field is invalid, your response must be one of the provided options."
