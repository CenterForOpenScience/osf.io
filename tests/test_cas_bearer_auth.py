from __future__ import absolute_import

import datetime

import itsdangerous
import jwe
import jwt
import furl
import responses
from django.utils import timezone
from framework.auth.core import Auth
from tests.base import OsfTestCase
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    ApiOAuth2PersonalTokenFactory
)
from website import settings
from website.util import api_url_for


from tests.json_api_test_app import JSONAPITestApp

django_app = JSONAPITestApp()
from django.test import override_settings


class TestCASBearer(OsfTestCase):

    def setUp(self):
        super(TestCASBearer, self).setUp()
        self.user = AuthUserFactory()
        self.token = ApiOAuth2PersonalTokenFactory(owner=self.user)
        self.auth_obj = Auth(user=self.user)
        self.preprint = PreprintFactory(creator=self.user, is_public=True)
        self.JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))

    def build_url(self, **kwargs):
        options = {'payload': jwe.encrypt(jwt.encode({'data': dict(dict(
            action='download',
            nid=self.preprint._id,
            metrics={'uri': settings.MFR_SERVER_URL},
            provider='osfstorage'), **kwargs),
            'exp': timezone.now() + datetime.timedelta(seconds=settings.WATERBUTLER_JWT_EXPIRATION),
        }, settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM), self.JWE_KEY)}
        return api_url_for('get_auth', **options)

    @responses.activate
    @override_settings(CAS_SERVER_URL='http://accounts.test.test')
    def test_set_department_on_get_auth(self):
        headers = {'Authorization': f'Bearer {self.token.token_id}'}
        url = furl.furl('http://accounts.test.test')
        url.path.segments.extend(('oauth2', 'profile',))

        responses.add(
            responses.Response(
                responses.GET,
                f'{settings.CAS_SERVER_URL}/oauth2/profile',
                status=200,
                json={
                    'id': self.user._id,
                    'attributes': {
                        'lastName': 'Jenkins',
                        'firstName': 'Malcolm',
                        'department': 'Defense'
                    },
                    'scope':
                        ['investment']
                }
            )
        )

        self.app.get(self.build_url(), headers=headers)
        self.user.refresh_from_db()
        assert self.user.department == 'Defense'
