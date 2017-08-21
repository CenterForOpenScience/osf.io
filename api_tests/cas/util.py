import faker
import json

import jwt
import jwe

from api.base.settings.defaults import JWE_SECRET, JWT_SECRET
from api.cas.util import parse_external_credential

fake = faker.Factory.create()

bad_jwe_secret = 'b23_terces_twj_nigol_sac_ipa_fso'
bad_jwt_secret = 'b23_terces_ewj_nigol_sac_ipa_fso'


def make_request_payload(user_credentials, bad_secret=False):

    data = {
        'user': user_credentials
    }
    return encrypt_request_data(data, bad_secret=bad_secret)


def make_request_payload_register_external(email, external_id, external_id_provider, attributes):

    user_credentials = {
        'email': email,
        'externalId': external_id,
        'externalIdProvider': external_id_provider,
        'attributes': attributes
    }
    return make_request_payload(user_credentials)


def make_payload_login_osf(email, password=None, remote_authenticated=False, verification_key=None, one_time_password=None):

    user_credentials = {
        'email': email,
        'password': password,
        'remoteAuthenticated': remote_authenticated,
        'verificationKey': verification_key,
        'oneTimePassword': one_time_password,
    }
    return make_request_payload(user_credentials)


def make_payload_login_institution(institution_id, username='', fullname='', given_name='', family_name='', bad_secret=False):

    data = {
        'provider': {
            'id': institution_id,
            'user': {
                'username': username,
                'fullname': fullname,
                'givenName': given_name,
                'familyName': family_name,
                'middleNames': '',
                'suffix': '',
            }
        }
    }

    return encrypt_request_data(data, bad_secret=bad_secret)


def make_payload_login_external(external_id_with_provider, bad_secret=False):

    data = {
        'user': {
            'externalIdWithProvider': external_id_with_provider
        }
    }
    return encrypt_request_data(data, bad_secret)


def make_payload_service_institutions():

    data = {
        'description': 'load institutions as registered services'
    }
    return encrypt_request_data(data)


def make_payload_service_oauth_apps():

    data = {
        'description': 'load OSF developer apps as registered services'
    }
    return encrypt_request_data(data)


def make_payload_service_oauth_token(token_id):

    data = {
        'tokenId': token_id
    }
    return encrypt_request_data(data)


def make_payload_service_oauth_scope(scope_name):
    data = {
        'scopeName': scope_name
    }
    return encrypt_request_data(data)


def encrypt_request_data(data, bad_secret=False):

    jwe_secret = JWE_SECRET if not bad_secret else bad_jwe_secret
    jwt_secret = JWT_SECRET if not bad_secret else bad_jwt_secret

    return jwe.encrypt(
        jwt.encode(
            {
                'sub': 'data',
                'data': json.dumps(data)
            },
            jwt_secret, algorithm='HS256',
        ),
        jwe_secret
    )


def add_external_identity_to_user(user, external_identity_with_provider, status='VERIFIED'):

    parsed_external_identity = parse_external_credential(external_identity_with_provider)
    if not parsed_external_identity:
        return None

    user.external_identity = {
        parsed_external_identity['provider']: {
            parsed_external_identity['id']: status
        }
    }
    # TODO: add unconfirmed email for 'LINK' and 'CREATE'
    user.save()
    user.reload()
    return user
