from __future__ import absolute_import
import time
import pytest
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
    SLOAN_COI_DISPLAY,
    SLOAN_DATA_DISPLAY
)

from api.base.settings.defaults import SLOAN_ID_COOKIE_NAME
from tests.json_api_test_app import JSONAPITestApp
from osf.metrics import PreprintDownload

django_app = JSONAPITestApp()


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

    @mock.patch('osf.metrics.PreprintDownload.record_for_preprint')
    def test_unauth_user_downloads_preprint(self, mock_record):
        test_file = create_test_preprint_file(self.preprint, self.user)
        resp = django_app.get('/v2/')

        # tests unauthenticated user gets cookie.
        assert f'{SLOAN_ID_COOKIE_NAME}=' in resp.headers.get('Set-Cookie')
        sloan_cookie_value = resp.headers['Set-Cookie'].split('=')[1].split(';')[0]

        # tests cookies get sent to impact
        self.app.set_cookie(f'dwf_{SLOAN_COI_DISPLAY}', 'True')
        self.app.set_cookie(f'dwf_{SLOAN_DATA_DISPLAY}', 'False')
        self.app.set_cookie(SLOAN_ID_COOKIE_NAME, sloan_cookie_value)
        with override_switch(ELASTICSEARCH_METRICS, active=True):
            self.app.get(self.build_url(path=test_file.path))

        mock_record.assert_called_with(
            path=test_file.path,
            preprint=self.preprint,
            user=None,
            version='1',
            sloan_coi=1,
            sloan_data=0,
            sloan_id=sloan_cookie_value,
        )


@pytest.mark.django_db
class TestSloanQueries:

    @pytest.fixture()
    def preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin(self):
        user = AuthUserFactory()
        user.is_staff = True
        user.add_system_tag('preprint_metrics')
        user.save()
        return user

    @pytest.fixture()
    def url(self):
        return f'{settings.API_DOMAIN}_/metrics/preprints/downloads/'

    @pytest.mark.es
    def test_sloan_id_query(self, app, url, preprint, user, admin):
        timestamp = datetime.datetime.now()
        PreprintDownload.record_for_preprint(
            preprint=preprint,
            user=user,
            version=1,
            path='/MalcolmJenkinsKnockedBrandinCooksOutColdInTheSuperbowl',
            sloan_id='my_sloan_id',
            slaon_coi=True,
            timestamp=timestamp
        ).save()

        data = {
            'data': {
                'size': 0,
                'aggs': {
                    'users': {
                        'terms': {
                            'field': 'sloan_id',
                        },
                    }
                }
            }
        }
        time.sleep(2)  # ES is slow
        res = app.post_json_api(url, data, auth=admin.auth)
        assert res.status_code == 200
        assert len(res.json['hits']['hits']) == 1
        assert res.json['hits']['hits'][0]['_source'] == {
            'timestamp': timestamp.isoformat(),
            'count': 1,
            'preprint_id': preprint._id,
            'user_id': user._id,
            'provider_id': preprint.provider._id,
            'version': 1,
            'path': '/MalcolmJenkinsKnockedBrandinCooksOutColdInTheSuperbowl',
            'sloan_id': 'my_sloan_id',
            'slaon_coi': True
        }
