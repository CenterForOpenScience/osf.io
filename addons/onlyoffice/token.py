import jwe
import jwt

import jsonschema
from datetime import datetime, timezone, timedelta
import logging

from . import settings

logger = logging.getLogger(__name__)

OFFICESERVER_JWE_KEY = jwe.kdf(settings.OFFICESERVER_JWE_SECRET.encode('utf-8'), settings.OFFICESERVER_JWE_SALT.encode('utf-8'))

token_schema = {
    'type': 'object',
    'required': ['exp', 'data'],
    'properties': {
        'exp': {'type': 'number'},
        'data': {
            'type': 'object',
            'required': ['auth', 'file_id'],
            'properties': {
                'auth': {'type': 'string'},
                'file_id': {'type': 'string'}
            }
        }
    }
}

def _get_timestamp():
    nt = datetime.now(timezone.utc).timestamp()
    return nt


def _check_schema(token):
    try:
        jsonschema.validate(instance=token, schema=token_schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logger.warning('onlyoffice: token schema error : {}'.format(e))
        return False


def encrypt(cookie, file_id):
    jwte = jwt.encode(
        {
            'data': {
                'auth': cookie,
                'file_id': file_id
            },
            'exp': int(datetime.now(timezone.utc).timestamp() +
                       timedelta(seconds=settings.WOPI_TOKEN_TTL).seconds) +
            settings.WOPI_EXPIRATION_TIMER_DELAY
        },
        settings.OFFICESERVER_JWT_SECRET, algorithm=settings.OFFICESERVER_JWT_ALGORITHM)
    encstr = jwe.encrypt(jwte, OFFICESERVER_JWE_KEY).decode()
    logger.debug('onlyoffice: token encstr = {}'.format(encstr))
    return encstr


def decrypt(encstr):
    try:
        decstr = jwe.decrypt(encstr.encode('utf-8'), OFFICESERVER_JWE_KEY)
        jsonobj = jwt.decode(decstr, settings.OFFICESERVER_JWT_SECRET, algorithms=settings.OFFICESERVER_JWT_ALGORITHM)
    except Exception:
        logger.warning('onlyoffice: token decrypt failed.')
        jsonobj = None
    return jsonobj


def check_token(jsonobj, file_id):
    # token schema check
    if _check_schema(jsonobj) is False:
        logger.warning('onlyoffice: check_schema failed.')
        return False

    # file_id check
    if file_id != jsonobj['data']['file_id']:
        logger.warning('onlyoffice: token file_id check failed.')
        logger.debug('onlyoffice: file_id, token file_id : {}  {}'.format(file_id, jsonobj['data']['file_id']))
        return False

    # expiration check
    nt = int(_get_timestamp())
    if nt > jsonobj['exp']:
        logger.warning('onlyoffice: token time expire failed.')
        logger.debug('onlyoffice: nt, token expire : {}  {}'.format(nt, jsonobj['exp']))
        return False

    return True


def get_cookie(jsonobj):
    return jsonobj['data']['auth']
