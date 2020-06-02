import pytest
import time

from website.app import setup_django
setup_django()

from waffle.testutils import override_switch

from osf import features
from osf_tests.factories import AuthUserFactory
from api.base.settings import API_PRIVATE_BASE as API_BASE


pytestmark = pytest.mark.django_db


@pytest.mark.es
class TestRawMetrics:

    @pytest.fixture(autouse=True)
    def enable_elasticsearch_metrics(self):
        with override_switch(features.ENABLE_RAW_METRICS, active=True):
            yield

    @pytest.fixture
    def user(self):
        user = AuthUserFactory()
        user.is_staff = True
        user.add_system_tag('raw_es6')
        user.save()
        return user

    @pytest.fixture
    def other_user(self):
        return AuthUserFactory()

    @pytest.fixture
    def base_url(self):
        return '/{}metrics/raw/'.format(API_BASE)

    def test_delete(self, app, user, base_url):
        res = app.delete_json_api(base_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'DELETE not supported. Use GET/POST/PUT'

    def test_put(self, app, user, base_url):
        put_return = {
            '_index': 'customer',
            '_type': '_doc',
            '_id': '1',
            '_version': 1,
            'result': 'created',
            '_shards': {
                'total': 2,
                'successful': 1,
                'failed': 0
            },
            '_seq_no': 0,
            '_primary_term': 1
        }

        put_url = '{}customer/_doc/1'.format(base_url)
        put_data = {
            'name': 'John Doe'
        }
        res = app.put_json_api(put_url, put_data, auth=user.auth)
        assert res.json == put_return

    def test_put_no_perms(self, app, other_user, base_url):
        put_url = '{}customer/_doc/1'.format(base_url)
        put_data = {
            'name': 'John Doe'
        }
        res = app.put_json_api(put_url, put_data, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_post(self, app, user, base_url):
        post_return = {
            '_index': 'customer',
            '_type': '_doc',
            '_id': '1',
            '_version': 1,
            'result': 'created',
            '_shards': {
                'total': 2,
                'successful': 1,
                'failed': 0
            },
            '_seq_no': 0,
            '_primary_term': 1
        }

        post_url = '{}customer/_doc/1'.format(base_url)
        post_data = {
            'name': 'Jane Doe'
        }
        res = app.post_json_api(post_url, post_data, auth=user.auth)
        assert res.json == post_return

    def test_post_no_perms(self, app, other_user, base_url):
        post_url = '{}customer/_doc/1'.format(base_url)
        post_data = {
            'name': 'John Doe'
        }
        res = app.post_json_api(post_url, post_data, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_post_and_get(self, app, user, base_url):
        post_return = {
            '_index': 'customer',
            '_type': '_doc',
            '_id': '1',
            '_version': 1,
            'result': 'created',
            '_shards': {
                'total': 2,
                'successful': 1,
                'failed': 0
            },
            '_seq_no': 0,
            '_primary_term': 1
        }

        post_url = '{}customer/_doc/1'.format(base_url)
        post_data = {
            'name': 'Beyonce'
        }
        res = app.post_json_api(post_url, post_data, auth=user.auth)
        assert res.json == post_return

        time.sleep(3)

        get_url = '{}_search?q=*'.format(base_url)
        res = app.get(get_url, auth=user.auth)

        assert res.json['hits']['total'] == 1
        assert res.json['hits']['hits'][0]['_source']['name'] == 'Beyonce'

        get_url = '{}customer/_doc/1/'.format(base_url)
        res = app.get(get_url, auth=user.auth)

        assert res.json['_source']['name'] == 'Beyonce'
