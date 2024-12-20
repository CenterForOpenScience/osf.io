import jsonschema

from django.test import TestCase
from unittest.mock import patch

from admin.project_limit_number.utils import (
    ATTRIBUTE_STRING_QUERY_MAP,
    ATTRIBUTE_ARRAY_QUERY_MAP,
    check_logic_condition,
    MAIL_GRDM,
    EDU_PERSON_PRINCIPAL_NAME,
    validate_file_json,
    generate_logic_condition_from_attribute
)
from osf.models import UserExtendedData
from osf_tests.factories import AuthUserFactory


class TestValidateFileJson(TestCase):
    def setUp(self):
        """Set up test data"""
        self.valid_schema = {
            'type': 'object',
            'properties': {
                'attribute_name': {
                    'type': 'string',
                    'minLength': 1
                },
                'setting_type': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 6,
                    'message': {
                        'required': 'Date of Birth is Required Property',
                        'pattern': 'Correct format of Date Of Birth is dd-mmm-yyyy'
                    }
                },
                'attribute_value': {
                    'type': 'string'
                }
            },
            'required': ['attribute_name', 'setting_type']
        }

    @patch('admin.project_limit_number.utils.from_json')
    def test_valid_data(self, mock_from_json):
        """Test with valid data"""
        mock_from_json.return_value = self.valid_schema

        file_data = {
            'attribute_name': 'Test Setting',
            'setting_type': 3,
            'attribute_value': 'test'
        }

        is_valid, error_message = validate_file_json(file_data, 'test_schema.json')
        self.assertTrue(is_valid)
        self.assertEqual(error_message, '')

    @patch('admin.project_limit_number.utils.from_json')
    def test_missing_required_field(self, mock_from_json):
        """Test with missing required field"""
        mock_from_json.return_value = self.valid_schema

        file_data = {
            'attribute_name': 'Test Setting',
            # missing setting_type
        }

        is_valid, error_message = validate_file_json(file_data, 'test_schema.json')
        self.assertFalse(is_valid)
        self.assertEqual(error_message, 'setting_type is required.')

    @patch('admin.project_limit_number.utils.from_json')
    def test_empty_setting_type(self, mock_from_json):
        """Test with empty setting_type"""
        mock_from_json.return_value = self.valid_schema

        file_data = {
            'attribute_name': 'Test Setting',
            'setting_type': ''
        }

        is_valid, error_message = validate_file_json(file_data, 'test_schema.json')
        self.assertFalse(is_valid)
        self.assertEqual(error_message, 'setting_type is invalid.')

    @patch('admin.project_limit_number.utils.from_json')
    def test_invalid_field_type(self, mock_from_json):
        """Test with invalid field type"""
        mock_from_json.return_value = self.valid_schema

        file_data = {
            'attribute_name': 123,  # should be string
            'setting_type': 3
        }

        is_valid, error_message = validate_file_json(file_data, 'test_schema.json')
        self.assertFalse(is_valid)
        self.assertEqual(error_message, 'attribute_name is invalid.')

    @patch('admin.project_limit_number.utils.from_json')
    def test_schema_error(self, mock_from_json):
        """Test with invalid schema"""
        mock_from_json.side_effect = jsonschema.SchemaError('Invalid schema')

        file_data = {
            'attribute_name': 'Test Setting',
            'setting_type': 3
        }

        is_valid, error_message = validate_file_json(file_data, 'test_schema.json')
        self.assertFalse(is_valid)
        self.assertEqual(error_message, '')

    @patch('admin.project_limit_number.utils.from_json')
    def test_unknown_field_error(self, mock_from_json):
        """Test with unknown field error"""
        mock_from_json.return_value = self.valid_schema

        # Simulate a ValidationError with no path
        with patch('jsonschema.validate') as mock_validate:
            mock_validate.side_effect = jsonschema.ValidationError('Error')

            is_valid, error_message = validate_file_json({}, 'test_schema.json')
            self.assertFalse(is_valid)
            self.assertEqual(error_message, 'Unknown field is invalid.')


class TestGenerateLogicConditionFromAttribute(TestCase):
    def test_string_attribute_exact_match(self):
        """Test string attribute with exact match"""
        attribute = {
            'attribute_name': 'mail',
            'attribute_value': 'test@example.com',
            'setting_type': 3
        }

        expected = 'data -> \'idp_attr\' ->> \'email\' = %s'
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['test@example.com'])

    def test_string_attribute_suffix_match(self):
        """Test string attribute with suffix match"""
        attribute = {
            'attribute_name': 'mail',
            'attribute_value': '@example.com',
            'setting_type': 4
        }

        expected = 'data -> \'idp_attr\' ->> \'email\' LIKE %s'
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['%@example.com'])

    def test_array_attribute_exact_match(self):
        """Test array attribute with exact match"""
        attribute = {
            'attribute_name': 'eduPersonAffiliation',
            'attribute_value': 'staff',
            'setting_type': 5
        }

        expected = (
            'EXISTS ('
            '	SELECT 1 '
            '	FROM unnest(string_to_array(data -> \'idp_attr\' ->> \'edu_person_affiliation\', \';\')) AS element '
            '	WHERE element = %s'
            '	)'
        )
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['staff'])

    def test_array_attribute_suffix_match(self):
        """Test array attribute with suffix match"""
        attribute = {
            'attribute_name': 'eduPersonAffiliation',
            'attribute_value': 'staff',
            'setting_type': 6
        }

        expected = (
            'EXISTS ('
            '	SELECT 1 '
            '	FROM unnest(string_to_array(data -> \'idp_attr\' ->> \'edu_person_affiliation\', \';\')) AS element '
            '	WHERE element LIKE %s'
            '	)'
        )
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['%staff'])

    def test_edu_person_principal_name(self):
        """Test eduPersonPrincipalName attribute"""
        attribute = {
            'attribute_name': EDU_PERSON_PRINCIPAL_NAME,
            'attribute_value': 'user@university.edu',
            'setting_type': 3
        }

        expected = (
            '( data -> \'idp_attr\' ->> \'eppn\' = %s OR '
            'data -> \'idp_attr\' ->> \'username\' = %s )'
        )
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['user@university.edu', 'user@university.edu'])

    def test_edu_person_principal_name_left_suffix_match(self):
        """Test eduPersonPrincipalName attribute"""
        attribute = {
            'attribute_name': EDU_PERSON_PRINCIPAL_NAME,
            'attribute_value': '@university.edu',
            'setting_type': 4
        }

        expected = (
            '( data -> \'idp_attr\' ->> \'eppn\' LIKE %s OR '
            'data -> \'idp_attr\' ->> \'username\' LIKE %s )'
        )
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['%@university.edu', '%@university.edu'])

    def test_mail_grdm(self):
        """Test MAIL_GRDM attribute"""
        attribute = {
            'attribute_name': MAIL_GRDM,
            'attribute_value': 'user@example.com',
            'setting_type': 3
        }

        expected = 'u.username = %s'
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['user@example.com'])

    def test_unknown_attribute(self):
        """Test unknown attribute"""
        attribute = {
            'attribute_name': 'unknown',
            'attribute_value': 'test',
            'setting_type': 3
        }

        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, '')
        self.assertEqual(params, [])

    def test_missing_attribute_fields(self):
        """Test with missing attribute fields"""
        attribute = {
            'attribute_name': 'mail'
            # missing attribute_value and setting_type
        }

        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, '')
        self.assertEqual(params, [])

    def test_special_characters_handling(self):
        """Test handling of special characters in attribute values"""
        attribute = {
            'attribute_name': 'mail',
            'attribute_value': 'O\'Connor@example.com',  # value with single quote
            'setting_type': 3
        }

        expected = 'data -> \'idp_attr\' ->> \'email\' = %s'
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, ['O\'Connor@example.com'])

    def test_empty_attribute_value(self):
        """Test with empty attribute value"""
        attribute = {
            'attribute_name': 'mail',
            'attribute_value': '',
            'setting_type': 3
        }

        expected = 'data -> \'idp_attr\' ->> \'email\' = %s'
        query, params = generate_logic_condition_from_attribute(attribute)
        self.assertEqual(query, expected)
        self.assertEqual(params, [''])


class TestCheckLogicCondition(TestCase):
    def setUp(self):
        """Set up test data for all test methods"""
        # Create test user
        self.user = AuthUserFactory()
        self.user_dict = {
            'id': self.user.id,
            'username': 'test.user@example.com'
        }

        # Create user extended data with comprehensive test data
        self.user_extended_data = UserExtendedData.objects.create(
            user=self.user,
            data={
                'idp_attr': {
                    'email': 'test.user@mail.com',
                    'family_name': 'Test',
                    'organizational_unit': 'Research',
                    'given_name': 'User',
                    'fullname': 'Test User',
                    'edu_person_unique_id': 'TU123',
                    'family_name_ja': 'テスト',
                    'given_name_ja': 'ユーザー',
                    'fullname_ja': 'テスト ユーザー',
                    'organizational_unit_ja': '研究部',
                    'gakunin_identity_assurance_organization': 'Test Org',
                    'gakunin_identity_assurance_method_reference': 'Method1',
                    'organization_name': 'Org1;Org2',
                    'edu_person_affiliation': 'staff;faculty',
                    'entitlement': 'ent1;ent2',
                    'edu_person_scoped_affiliation': 'member@test.edu',
                    'edu_person_targeted_id': 'target1;target2',
                    'edu_person_assurance': 'assurance1;assurance2',
                    'edu_person_orcid': 'orcid1;orcid2',
                    'groups': 'group1;group2',
                    'organization_name_ja': 'オーグ1;オーグ2',
                    'gakunin_scoped_personal_unique_code': 'code1;code2',
                    'eppn': 'test.user@university.edu',
                    'username': 'test.user'
                }
            }
        )

    def test_empty_attributes(self):
        """Test with empty attributes"""
        result = check_logic_condition(self.user_dict, [])
        self.assertFalse(result)

    def test_invalid_setting_type(self):
        """Test with invalid setting_type"""
        setting_attribute_list = [{
            'attribute_name': MAIL_GRDM,
            'setting_type': 'test',
            'attribute_value': 'test.user@example.com'
        }]

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertFalse(result)

    def test_string_attributes(self):
        """Test all string attributes from ATTRIBUTE_STRING_QUERY_MAP"""
        for ldap_attr, db_attr in ATTRIBUTE_STRING_QUERY_MAP.items():
            setting_attribute_list = [{
                'attribute_name': ldap_attr,
                'setting_type': 3,
                'attribute_value': self.user_extended_data.data['idp_attr'][db_attr]
            }]

            result = check_logic_condition(self.user_dict, setting_attribute_list)
            self.assertTrue(result, f'Failed matching for attribute {ldap_attr}')

    def test_array_attributes(self):
        """Test all array attributes from ATTRIBUTE_ARRAY_QUERY_MAP"""
        for ldap_attr, db_attr in ATTRIBUTE_ARRAY_QUERY_MAP.items():
            array_value = self.user_extended_data.data['idp_attr'][db_attr].split(';')[0]
            setting_attribute_list = [{
                'attribute_name': ldap_attr,
                'setting_type': 5,
                'attribute_value': array_value
            }]

            result = check_logic_condition(self.user_dict, setting_attribute_list)
            self.assertTrue(result, f'Failed matching for attribute {ldap_attr}')

    def test_mail_grdm_match(self):
        """Test MAIL_GRDM (Primary Email from GRDM) attribute"""
        setting_attribute_list = [{
            'attribute_name': MAIL_GRDM,
            'setting_type': 3,
            'attribute_value': 'test.user@example.com'
        }]

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertTrue(result)

    def test_edu_person_principal_name_match(self):
        """Test eduPersonPrincipalName attribute"""
        setting_attribute_list = [{
            'attribute_name': EDU_PERSON_PRINCIPAL_NAME,
            'setting_type': 3,
            'attribute_value': 'test.user@university.edu'
        }]

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertTrue(result)

    def test_left_suffix_match_for_edu_person_principal_name(self):
        """Test left suffix match for eduPersonPrincipalName attribute"""
        setting_attribute_list = [{
            'attribute_name': EDU_PERSON_PRINCIPAL_NAME,
            'setting_type': 4,
            'attribute_value': '@university.edu'
        }]

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertTrue(result)

    def test_left_suffix_match_for_string_attributes(self):
        """Test left suffix match for string attributes"""
        for ldap_attr, db_attr in ATTRIBUTE_STRING_QUERY_MAP.items():
            value = self.user_extended_data.data['idp_attr'][db_attr]
            if len(value) > 1:
                suffix = value[1:]
                setting_attribute_list = [{
                    'attribute_name': ldap_attr,
                    'setting_type': 4,
                    'attribute_value': suffix
                }]

                result = check_logic_condition(self.user_dict, setting_attribute_list)
                self.assertTrue(result, f'Failed suffix matching for attribute {ldap_attr}')

    def test_left_suffix_match_for_array_attributes(self):
        """Test left suffix match for array attributes"""
        for ldap_attr, db_attr in ATTRIBUTE_ARRAY_QUERY_MAP.items():
            array_value = self.user_extended_data.data['idp_attr'][db_attr].split(';')[0]
            if len(array_value) > 1:
                suffix = array_value[1:]
                setting_attribute_list = [{
                    'attribute_name': ldap_attr,
                    'setting_type': 6,
                    'attribute_value': suffix
                }]

                result = check_logic_condition(self.user_dict, setting_attribute_list)
                self.assertTrue(result, f'Failed suffix matching for attribute {ldap_attr}')

    def test_japanese_attributes(self):
        """Test Japanese-specific attributes"""
        japanese_attributes = {
            'jasn': 'family_name_ja',
            'jaGivenName': 'given_name_ja',
            'jaDisplayName': 'fullname_ja',
            'jaou': 'organizational_unit_ja',
            'jao': 'organization_name_ja'
        }

        for ldap_attr, db_attr in japanese_attributes.items():
            if ldap_attr in ATTRIBUTE_STRING_QUERY_MAP:
                setting_attribute_list = [{
                    'attribute_name': ldap_attr,
                    'setting_type': 3,
                    'attribute_value': self.user_extended_data.data['idp_attr'][db_attr]
                }]
            else:  # Array attribute
                array_value = self.user_extended_data.data['idp_attr'][db_attr].split(';')[0]
                setting_attribute_list = [{
                    'attribute_name': ldap_attr,
                    'setting_type': 5,
                    'attribute_value': array_value
                }]

            result = check_logic_condition(self.user_dict, setting_attribute_list)
            self.assertTrue(result, f'Failed matching for Japanese attribute {ldap_attr}')

    def test_complex_multiple_conditions(self):
        """Test multiple conditions with different attribute types"""
        setting_attribute_list = [
            {
                'attribute_name': MAIL_GRDM,
                'setting_type': 3,
                'attribute_value': 'test.user@example.com'
            },
            {
                'attribute_name': 'sn',
                'setting_type': 3,
                'attribute_value': 'Test'
            },
            {
                'attribute_name': 'eduPersonAffiliation',
                'setting_type': 3,
                'attribute_value': 'staff'
            }
        ]

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertTrue(result)

    def test_gakunin_specific_attributes(self):
        """Test Gakunin-specific attributes"""
        gakunin_attributes = [
            'gakuninIdentityAssuranceOrganization',
            'gakuninIdentityAssuranceMethodReference',
            'gakuninScopedPersonalUniqueCode'
        ]

        for attr in gakunin_attributes:
            if attr in ATTRIBUTE_STRING_QUERY_MAP:
                db_attr = ATTRIBUTE_STRING_QUERY_MAP[attr]
                value = self.user_extended_data.data['idp_attr'][db_attr]
                setting_type = 5
            else:
                db_attr = ATTRIBUTE_ARRAY_QUERY_MAP[attr]
                value = self.user_extended_data.data['idp_attr'][db_attr].split(';')[0]
                setting_type = 3

            setting_attribute_list = [{
                'attribute_name': attr,
                'setting_type': setting_type,
                'attribute_value': value
            }]

            result = check_logic_condition(self.user_dict, setting_attribute_list)
            self.assertTrue(result, f'Failed matching for Gakunin attribute {attr}')

    def test_attribute_not_in_extended_data(self):
        """Test behavior when attribute is not present in extended data"""
        setting_attribute_list = [{
            'attribute_name': 'sn',
            'setting_type': 3,
            'attribute_value': 'Test'
        }]

        # Remove the attribute from extended data
        data = self.user_extended_data.data
        del data['idp_attr']['family_name']
        self.user_extended_data.data = data
        self.user_extended_data.save()

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertFalse(result)

    def test_empty_array_value(self):
        """Test with empty array value in extended data"""
        data = self.user_extended_data.data
        data['idp_attr']['groups'] = ''
        self.user_extended_data.data = data
        self.user_extended_data.save()

        setting_attribute_list = [{
            'attribute_name': 'isMemberOf',
            'setting_type': 3,
            'attribute_value': 'group1'
        }]

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertFalse(result)

    def test_user_has_no_extended_data(self):
        """Test user with no extended data"""
        self.user_extended_data.delete()

        setting_attribute_list = [{
            'attribute_name': 'sn',
            'setting_type': 3,
            'attribute_value': 'Test'
        }]

        result = check_logic_condition(self.user_dict, setting_attribute_list)
        self.assertFalse(result)
