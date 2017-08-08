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
