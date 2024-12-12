import logging
import jsonschema

from admin.base import settings
from admin.base.schemas.utils import from_json
from admin.base.settings import SETTING_TYPE
from osf.models.user import UserExtendedData

logger = logging.getLogger(__name__)


# Map for attribute that use attribute_value to query
ATTRIBUTE_STRING_QUERY_MAP = {
    'mail': 'email',
    'sn': 'family_name',
    'ou': 'organization_unit',
    'givenName': 'given_name',
    'displayName': 'fullname',
    'eduPersonUniqueId': 'unique_id',
    'jasn': 'family_name_ja',
    'jaGivenName': 'given_name_ja',
    'jaDisplayName': 'fullname_ja',
    'jaou': 'organization_unit_ja',
    'gakuninIdentityAssuranceOrganization': 'gakunin_identity_assurance_organization',
    'gakuninIdentityAssuranceMethodReference': 'gakunin_identity_assurance_method_reference',
}

# Map for attribute that need to split attribute_value into array before query
ATTRIBUTE_ARRAY_QUERY_MAP = {
    'o': 'organization_name',
    'eduPersonAffiliation': 'edu_person_affiliation',
    'eduPersonEntitlement': 'entitlement',
    'eduPersonScopedAffiliation': 'edu_person_scoped_affiliation',
    'eduPersonTargetedID': 'edu_person_targeted_id',
    'eduPersonAssurance': 'edu_person_assurance',
    'eduPersonOrcid': 'edu_person_orc_id',
    'isMemberOf': 'groups',
    'jao': 'organization_name_ja',
    'gakuninScopedPersonalUniqueCode': 'gakunin_scoped_personal_unique_code',
}

MAIL_GRDM = 'Primary Email from GRDM'
EDU_PERSON_PRINCIPAL_NAME = 'eduPersonPrincipalName'
NO_LIMIT = -1
LEFT_SUFFIX_MATCH_SETTING_TYPE_LIST = [item[0] for item in settings.SETTING_TYPE if item[1].endswith('left_suffix_match')]
SETTING_TYPE_ID_LIST = [item[0] for item in SETTING_TYPE]
REQUIRED_SCHEMA = 'required'


def validate_file_json(file_data, json_schema_file_name):
    try:
        schema = from_json(json_schema_file_name)
        jsonschema.validate(file_data, schema)
        return True, ''
    except jsonschema.ValidationError as e:
        logger.error(f'jsonschema.ValidationError: {e.message}')
        if e.validator == REQUIRED_SCHEMA:
            # If error is due to required then get the field name in the message
            field_name = e.message.split(' ')[0].strip('\'')
        else:
            # Otherwise, get from last item in path
            field_name = e.path[-1] if e.path else 'Unknown field'
        if field_name == 'setting_type':
            setting_type = e.instance
            if not setting_type:
                return False, 'setting_type is required.'
        if e.validator == 'minLength' or e.validator == 'required':
            return False, f'{field_name} is required.'
        else:
            return False, f'{field_name} is invalid.'
    except jsonschema.SchemaError as e:
        logger.error(f'jsonschema.SchemaError: {e.message}')
        return False, ''


def generate_logic_condition_from_attribute(attribute):
    """Generate a logic condition string based on an attribute."""
    params = []
    attribute_name = attribute.get('attribute_name')
    attribute_value = attribute.get('attribute_value', '')
    setting_type = attribute.get('setting_type')
    if setting_type not in SETTING_TYPE_ID_LIST:
        # If setting_type is not in SETTING_TYPE_ID_LIST, return empty string
        return '', params
    use_left_suffix_match = attribute.get('setting_type') in LEFT_SUFFIX_MATCH_SETTING_TYPE_LIST
    if use_left_suffix_match:
        params.append(f'%{attribute_value}')
        attribute_value_compare_string = f'LIKE %s'
    else:
        params.append(attribute_value)
        attribute_value_compare_string = f'= %s'

    extended_data_idp_attr = 'data -> \'idp_attr\' ->> \'{attribute_column}\''

    # Attributes match with ATTRIBUTE_STRING_QUERY_MAP
    if attribute_name in ATTRIBUTE_STRING_QUERY_MAP.keys():
        return f'{extended_data_idp_attr.format(attribute_column=ATTRIBUTE_STRING_QUERY_MAP[attribute_name])} {attribute_value_compare_string}', params

    # Attributes match with ATTRIBUTE_ARRAY_QUERY_MAP
    if attribute_name in ATTRIBUTE_ARRAY_QUERY_MAP.keys():
        return (
            f'EXISTS ('
            f'	SELECT 1 '
            f'	FROM unnest(string_to_array({extended_data_idp_attr.format(attribute_column=ATTRIBUTE_ARRAY_QUERY_MAP[attribute_name])}, \';\')) AS element '
            f'	WHERE element {attribute_value_compare_string}'
            f'	)'
        ), params

    # Attribute name is EDU_PERSON_PRINCIPAL_NAME
    if attribute_name == EDU_PERSON_PRINCIPAL_NAME:
        return (
            f'{extended_data_idp_attr.format(attribute_column="eppn")} {attribute_value_compare_string} OR '
            f'{extended_data_idp_attr.format(attribute_column="username")} {attribute_value_compare_string}'
        ), params + params

    # Attribute name is MAIL_GRDM
    if attribute_name == MAIL_GRDM:
        # Get query from osf_user table instead
        return f'u.username {attribute_value_compare_string}', params

    # Other cases, return empty string
    return '', []


def check_logic_condition(user, setting_attribute_list):
    """Check if a user meets the logic condition based on an attribute."""
    if not setting_attribute_list or len(setting_attribute_list) == 0:
        # If setting_attribute_list is empty, return False
        return False
    result = True
    user_extended_data_attribute = None
    for setting_attribute in setting_attribute_list:
        attribute_name = setting_attribute.get('attribute_name')
        setting_type = setting_attribute.get('setting_type')
        attribute_value = setting_attribute.get('attribute_value')
        if setting_type not in SETTING_TYPE_ID_LIST:
            # If setting_type is not in SETTING_TYPE_ID_LIST, return False
            return False
        use_left_suffix_match = setting_type in LEFT_SUFFIX_MATCH_SETTING_TYPE_LIST
        if attribute_name == MAIL_GRDM:
            # Get query from osf_user table instead
            result = result and (
                user.get('username', '').endswith(attribute_value)
                if use_left_suffix_match
                else user.get('username') == attribute_value
            )
        elif user_extended_data_attribute is None:
            # Only get user_extended_data_attribute if attribute name is not MAIL_GRDM
            user_extended_data_attribute = UserExtendedData.objects.filter(user_id=user.get('id')).first()
            if user_extended_data_attribute:
                user_extended_data_attribute = getattr(user_extended_data_attribute, 'data', {}).get('idp_attr', {})
            else:
                user_extended_data_attribute = {}

        if attribute_name == EDU_PERSON_PRINCIPAL_NAME:
            if use_left_suffix_match:
                result = result and (
                    user_extended_data_attribute.get('eppn', '').endswith(
                        attribute_value
                    )
                    or user_extended_data_attribute.get('username', '').endswith(
                        attribute_value
                    )
                )
            else:
                result = result and (
                    user_extended_data_attribute.get('eppn', '') == attribute_value
                    or user_extended_data_attribute.get('username', '')
                    == attribute_value
                )

        if attribute_name in ATTRIBUTE_STRING_QUERY_MAP.keys():
            if use_left_suffix_match:
                result = result and (
                    user_extended_data_attribute.get(
                        ATTRIBUTE_STRING_QUERY_MAP[attribute_name], ''
                    ).endswith(attribute_value)
                )
            else:
                result = result and (
                    user_extended_data_attribute.get(
                        ATTRIBUTE_STRING_QUERY_MAP[attribute_name], ''
                    )
                    == attribute_value
                )

        if attribute_name in ATTRIBUTE_ARRAY_QUERY_MAP.keys():
            user_extended_data_attribute_list = user_extended_data_attribute.get(
                ATTRIBUTE_ARRAY_QUERY_MAP[attribute_name], ''
            ).split(';')
            if use_left_suffix_match:
                result = result and (
                    any(
                        value.endswith(attribute_value)
                        for value in user_extended_data_attribute_list
                        if value.endswith(attribute_value)
                    )
                )
            else:
                result = result and (
                    attribute_value in user_extended_data_attribute_list
                )

    # Return result
    return result
