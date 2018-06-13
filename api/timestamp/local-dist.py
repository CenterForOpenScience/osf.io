# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''
#import inspect

#from . import defaults
#import os

# openssl cmd const
OPENSSL_MAIN_CMD = 'openssl'
OPENSSL_OPTION_TS = 'ts'
OPENSSL_OPTION_VERIFY = '-verify'
OPENSSL_OPTION_QUERY = '-query'
OPENSSL_OPTION_DATA = '-data'
OPENSSL_OPTION_CERT = '-cert'
OPENSSL_OPTION_IN = '-in'
OPENSSL_OPTION_SHA512 = '-sha512'
OPENSSL_OPTION_CAFILE = '-CAfile'
OPENSSL_OPTION_GENRSA = 'genrsa'
OPENSSL_OPTION_OUT = '-out'
OPENSSL_OPTION_RSA = 'rsa'
OPENSSL_OPTION_PUBOUT = '-pubout'

# UserKey Placement destination
KEY_NAME_PRIVATE = 'pvt'
KEY_NAME_PUBLIC = 'pub'
KEY_BIT_VALUE = '3072'
KEY_EXTENSION = '.pem'
KEY_SAVE_PATH = '/user_key_info/'
KEY_NAME_FORMAT = '{0}_{1}_{2}{3}'
PRIVATE_KEY_VALUE = 1
PUBLIC_KEY_VALUE = 2

# openssl ts verify check value
OPENSSL_VERIFY_RESULT_OK = 'OK'

# timestamp verify rootKey
VERIFY_ROOT_CERTIFICATE = 'root_cert_verifycate.pem'

# timestamp request const
REQUEST_HEADER = {'Content-Type': 'application/timestamp-query'}
TIME_STAMP_AUTHORITY_URL = 'http://eswg.jnsa.org/freetsa'
ERROR_HTTP_STATUS = [400, 401, 402, 403, 500, 502, 503, 504]
REQUEST_TIME_OUT = 5
RETRY_COUNT = 3

# TimeStamp Inspection Status
TIME_STAMP_TOKEN_UNCHECKED = 0
TIME_STAMP_TOKEN_CHECK_SUCCESS = 1
TIME_STAMP_TOKEN_CHECK_SUCCESS_MSG = 'OK'
TIME_STAMP_TOKEN_CHECK_NG = 2
TIME_STAMP_TOKEN_CHECK_NG_MSG = 'NG'
TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND = 3
TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG = 'TST missing(Unverify)'
TIME_STAMP_TOKEN_NO_DATA = 4
TIME_STAMP_TOKEN_NO_DATA_MSG = 'TST missing(Retrieving Failed)'
FILE_NOT_EXISTS = 5
FILE_NOT_EXISTS_MSG = 'FILE missing'
FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND = 6
FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG = 'FILE missing(Unverify)'
