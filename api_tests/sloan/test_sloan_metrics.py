from __future__ import absolute_import

import datetime

import itsdangerous
import jwe
import jwt
import mock
from django.utils import timezone
from framework.auth.core import Auth
from tests.base import OsfTestCase
from api_tests.utils import create_test_preprint_file
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
)
from website import settings
from website.util import api_url_for
from waffle.testutils import override_switch

from osf.models import Session
from osf.features import (
    ELASTICSEARCH_METRICS,
    SLOAN_COI,
    SLOAN_DATA
)


class TestSloanMetrics(OsfTestCase):

    def setUp(self):
        super(TestSloanMetrics, self).setUp()
        self.user = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.preprint = PreprintFactory(creator=self.user, is_public=True)
        self.session = Session(data={'auth_user_id': self.user._id})
        self.session.save()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session._id).decode()
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

    def test_unauth_user_gets_cookie(self):
        resp = self.app.get('/dashboard/')
        assert 'sloan_id=' in resp.headers.get('Set-Cookie')

    @mock.patch('osf.metrics.PreprintDownload.record_for_preprint')
    def test_unauth_user_downloads_preprint(self, mock_record):
        test_file = create_test_preprint_file(self.preprint, self.user)
        resp = self.app.get('/dashboard/')
        sloan_cookie_value = resp.headers['Set-Cookie'].split('=')[1].split(';')[0]

        self.app.set_cookie(SLOAN_COI, 'True')
        self.app.set_cookie(SLOAN_DATA, 'False')
        with override_switch(ELASTICSEARCH_METRICS, active=True):
            self.app.get(self.build_url(path=test_file.path))

        mock_record.assert_called_with(
            path=test_file.path,
            preprint=self.preprint,
            user=None,
            version='1',
            sloan_coi='True',
            sloan_data='False',
            sloan_id=sloan_cookie_value,
            sloan_prereg=None,
        )
