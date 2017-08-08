import json

import jwt
import jwe

from api.base.settings.defaults import JWE_SECRET, JWT_SECRET

bad_jwe_secret = 'b23_terces_twj_nigol_sac_ipa_fso'
bad_jwt_secret = 'b23_terces_ewj_nigol_sac_ipa_fso'


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


def make_payload_login_osf(email, password=None, remote_authenticated=False, verification_key=None, one_time_password=None):
    data = {
        'user': {
            'email': email,
            'password': password,
            'remoteAuthenticated': remote_authenticated,
            'verificationKey': verification_key,
            'oneTimePassword': one_time_password,
        }
    }
    return encrypt_request_data(data)


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
