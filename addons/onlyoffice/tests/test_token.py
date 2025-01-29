# -*- coding: utf-8 -*-
"""token tests for the onlyoffice addon."""
import pytest
import mock

from addons.onlyoffice.token import _check_schema, encrypt, decrypt, check_token
from framework.auth import Auth
from osf.exceptions import ValidationError
from osf.models import Guid
from osf_tests.factories import AuthUserFactory, UserFactory, ProjectFactory, NodeFactory
from tests.base import OsfTestCase
from datetime import datetime, timezone, timedelta

from .. import settings

Cookie = '67890f9f68b3c544fdd08572.LVImKq5n7UYcIzIGP1NX0hYLwME'
File_id = '660a5294e3c53a000a8165ed'

class TestOnlyofficeToken(OsfTestCase):
    def test_case1(self):
        # 'auth' is not exist : False
        data = {
            'data': {
                'file_id': File_id
                },
            'exp': int(datetime.now(timezone.utc).timestamp() +
                       timedelta(seconds=settings.WOPI_TOKEN_TTL).seconds) +
                       settings.WOPI_EXPIRATION_TIMER_DELAY
        }
        assert _check_schema(data) == False

    def test_case2(self):
        # 'file_id' is not exist : False
        data = {
            'data': {
                'auth': Cookie
                },
            'exp': int(datetime.now(timezone.utc).timestamp() +
                       timedelta(seconds=settings.WOPI_TOKEN_TTL).seconds) +
                       settings.WOPI_EXPIRATION_TIMER_DELAY
        }
        assert _check_schema(data) == False

    def test_case3(self):
        #  exp timeouted : False
        data = {
            'data': {
                'auth': Cookie,
                'file_id': File_id
                },
            'exp': int(datetime.now(timezone.utc).timestamp() -
                       timedelta(seconds=10).seconds)
            }
        assert check_token(data, File_id) == False

    def test_case4(self):
        # fair token : True
        data = {
            'data': {
                'auth': Cookie,
                'file_id': File_id
                },
            'exp': int(datetime.now(timezone.utc).timestamp() +
                       timedelta(seconds=settings.WOPI_TOKEN_TTL).seconds) +
                       settings.WOPI_EXPIRATION_TIMER_DELAY
            }
        assert _check_schema(data) == True

    def test_encrypt(self):
        encrypted = encrypt(Cookie, File_id)
        decrypted = decrypt(encrypted)

        assert decrypted['data']['auth'] == Cookie
        assert decrypted['data']['file_id'] == File_id
