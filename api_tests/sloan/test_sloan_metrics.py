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

from elasticsearch_metrics.field import Keyword
from api.base.settings.defaults import SLOAN_ID_COOKIE_NAME
from tests.json_api_test_app import JSONAPITestApp
from osf.metrics import PreprintDownload
from django.core.management import call_command


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
        self.app.set_cookie(SLOAN_COI_DISPLAY, 'True')
        self.app.set_cookie(SLOAN_DATA_DISPLAY, 'False')
        self.app.set_cookie(SLOAN_ID_COOKIE_NAME, sloan_cookie_value)
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

    @pytest.mark.es
    def test_reindexing(self, app, url, preprint, user, admin, es6_client):
        preprint_download = PreprintDownload.record_for_preprint(
            preprint,
            user,
            version=1,
            path='/MalcolmJenkinsKnockedBrandinCooksOutColdInTheSuperbowl',
            random_new_field='Hi!'  # Here's our unmapped field! It's a text field by default.
        )
        preprint_download.save()

        query = {
            'aggs': {
                'random_new_field': {
                    'terms': {
                        'field': 'random_new_field',  # Oh no, this is a text field, you can't query it like that!
                    }
                }
            }
        }

        payload = {
            'data': {
                'type': 'preprint_metrics',
                'attributes': {
                    'query': query
                }
            }
        }

        # Hacky way to simulate a re-mapped index template
        index_template = preprint_download._index
        mapping = index_template._mapping
        mapping.properties._params['properties']['random_new_field'] = Keyword(doc_values=True, index=True)
        index_template._mapping._update_from_dict(mapping.to_dict())

        # This should 400 because random_new_field is still stored as a text field despite the our index being remapped.
        res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Fielddata is disabled on text fields by default. Set ' \
                                                  'fielddata=true on [random_new_field] in order to load' \
                                                  ' fielddata in memory by uninverting the inverted inde' \
                                                  'x. Note that this can however use significant memory.' \
                                                  ' Alternatively use a keyword field instead.'

        call_command('reindex_with_current_metrics_mappings', f'--indices={preprint_download.meta["index"]}')
        time.sleep(2)  # ES is slow

        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 200
        assert res.json['hits']['hits'][0]['_source']['random_new_field'] == 'Hi!'

        # Just checking version number incremented properly
        es6_client.indices.get(f'{preprint_download.meta["index"]}_v2')
