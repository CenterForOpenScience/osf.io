import pytest
import mock
from datetime import datetime

from website.app import setup_django
setup_django()

from django.utils import timezone
from waffle.testutils import override_switch
from elasticsearch.exceptions import RequestError

from osf import features
from api.base.settings import API_PRIVATE_BASE as API_BASE
from osf.metrics import PreprintDownload, PreprintView
from osf_tests.factories import AuthUserFactory, PreprintFactory, NodeFactory


pytestmark = pytest.mark.django_db


@pytest.mark.django_db
class TestPreprintMetrics:

    @pytest.fixture(autouse=True)
    def enable_elasticsearch_metrics(self):
        with override_switch(features.ELASTICSEARCH_METRICS, active=True):
            yield

    @pytest.fixture
    def user(self):
        user = AuthUserFactory()
        user.is_staff = True
        user.add_system_tag('preprint_metrics')
        user.save()
        return user

    @pytest.fixture
    def other_user(self):
        return AuthUserFactory()

    @pytest.fixture
    def other_admin_user(self):
        user = AuthUserFactory()
        user.is_staff = True
        user.save()
        return user

    @pytest.fixture
    def other_non_admin_user(self):
        user = AuthUserFactory()
        user.add_system_tag('preprint_metrics')
        user.save()
        return user

    @pytest.fixture
    def preprint(self, user):
        preprint = PreprintFactory(creator=user)
        return preprint

    @pytest.fixture
    def preprint_two(self):
        return PreprintFactory()

    @pytest.fixture
    def preprint_three(self):
        return PreprintFactory()

    @pytest.fixture
    def preprint_no_results(self):
        return PreprintFactory()

    @pytest.fixture
    def project(self):
        return NodeFactory()

    @pytest.fixture
    def project_two(self):
        return NodeFactory()

    @pytest.fixture
    def metric_dates(self):
        return ['2019-01-01', '2019-01-02', '2019-01-03']

    def add_views_and_downloads(self, preprint_to_add, user_to_use, dates_to_use):
        # create 3 timestamps for 3 days, 1 hour apart
        times = ['T00:05', 'T01:05', 'T02:05']

        metrics = [PreprintView, PreprintDownload]
        for metric in metrics:
            for date in dates_to_use:
                for time in times:
                    metric.record_for_preprint(
                        preprint=preprint_to_add,
                        user=user_to_use,
                        path=preprint_to_add.primary_file.path,
                        timestamp=datetime.strptime(date + time, '%Y-%m-%dT%H:%M')
                    )

    @pytest.fixture
    def base_url(self):
        return '/{}metrics/preprints/'.format(API_BASE)

    @mock.patch('api.metrics.views.PreprintDownloadMetrics.execute_search')
    def test_custom_metric_malformed_query(self, mock_execute, app, user, base_url):
        mock_execute.side_effect = RequestError
        post_url = '{}downloads/'.format(base_url)
        post_data = {
            'data': {
                'type': 'preprint_metric',
                'attributes': {
                    'query': {'not_a_field': 'Yay!'}
                }
            }
        }
        res = app.post_json_api(post_url, post_data, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Malformed elasticsearch query.'

    @pytest.mark.es
    def test_agg_query(self, app, user, base_url):

        post_url = '{}downloads/'.format(base_url)

        payload = {
            'data': {
                'type': 'preprint_metrics',
                'attributes': {
                    'query': {
                        'aggs': {
                            'preprints_by_year': {
                                'composite': {
                                    'sources': [{
                                        'date': {
                                            'date_histogram': {
                                                'field': 'timestamp',
                                                'interval': 'year'
                                            }
                                        }
                                    }]
                                }
                            }
                        }
                    }
                }
            }
        }
        resp = app.post_json_api(post_url, payload, auth=user.auth)
        assert resp.status_code == 200

    @mock.patch('api.metrics.views.PreprintDownloadMetrics.format_response')
    @mock.patch('api.metrics.views.PreprintDownloadMetrics.execute_search')
    def test_post_custom_metric(self, mock_execute, mock_format, app, user, base_url, preprint, other_user):
        mock_return = {'good': 'job'}
        mock_execute.return_value.to_dict.return_value = mock_return
        mock_format.return_value = mock_return
        post_url = '{}downloads/'.format(base_url)
        post_data = {
            'data': {
                'type': 'preprint_metrics',
                'attributes': {
                    'query': mock_return
                }
            }
        }
        res = app.post_json_api(post_url, post_data, auth=user.auth)
        assert res.json == mock_return

    @pytest.mark.parametrize('metric_name', ['downloads', 'views'])
    @mock.patch('api.metrics.utils.timezone.now')
    def test_preprint_list_with_metrics_fails(self, mock_timezone, app, user, base_url, preprint, preprint_two,
                                              preprint_three, metric_name, other_user, project, project_two,
                                              other_admin_user, other_non_admin_user):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        url = '{}{}/'.format(base_url, metric_name)

        one_preprint_url = '{}?guids={}'.format(url, preprint._id)
        # test non-logged in cannot access
        res = app.get(one_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # test logged in non-metrics, non-admin user cannot access
        res = app.get(one_preprint_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403

        # test logged in, non-metrics, admin user cannot access
        res = app.get(one_preprint_url, auth=other_admin_user.auth, expect_errors=True)
        assert res.status_code == 403

        # test logged in, metrics, non-admin user cannot access
        res = app.get(one_preprint_url, auth=other_non_admin_user.auth, expect_errors=True)
        assert res.status_code == 403

    @pytest.mark.skip('Return results will be entirely mocked so does not make a lot of sense to run on travis.')
    @mock.patch('api.metrics.utils.timezone.now')
    def test_preprint_with_metrics_succeeds(self, mock_timezone, app, user, base_url, preprint, other_user, preprint_no_results, metric_dates):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        self.add_views_and_downloads(preprint, other_user, metric_dates)
        metric_name = 'downloads'

        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)
        url = '{}{}/'.format(base_url, metric_name)
        one_preprint_url = '{}?guids={}'.format(url, preprint._id)

        # base url should return all results
        res = app.get(one_preprint_url, auth=user.auth)
        assert res.json['metric_type'] == metric_name
        assert len(res.json['data']) == 3

        # starting a day later only returns 2 results
        later_url = '{}&start_datetime=2019-01-02'.format(one_preprint_url)
        res = app.get(later_url, auth=user.auth)
        assert len(res.json['data']) == 2
        datetimes = [result.keys()[0] for result in res.json['data']]
        assert '2019-01-01T00:05:00.000Z' not in datetimes

        # filter between two specific datetimes
        two_times_url = '{}&start_datetime=2019-01-02T00:00&end_datetime=2019-01-02T02:00'.format(one_preprint_url)
        res = app.get(two_times_url, auth=user.auth)
        assert len(res.json['data']) == 1
        datetimes = [result.keys()[0] for result in res.json['data']]
        assert '2019-01-01T00:05:00.000Z' not in datetimes
        assert '2019-01-01T03:05:00.000Z' not in datetimes

        # test two specific datetimes with minute interval
        two_min_interval = '{}&start_datetime=2019-01-02T00:00&end_datetime=2019-01-02T02:00&interval=1m'.format(one_preprint_url)
        res = app.get(two_min_interval, auth=user.auth)
        assert len(res.json['data']) == 61
        first = res.json['data'][0]
        last = res.json['data'][-1]
        assert first.keys() == ['2019-01-02T00:05:00.000Z']
        assert first['2019-01-02T00:05:00.000Z'] == {preprint._id: 1}
        assert last.keys() == ['2019-01-02T01:05:00.000Z']
        assert last['2019-01-02T01:05:00.000Z'] == {preprint._id: 1}

        # make sure requesting one preprint with no results is OK
        non_preprint_url = '{}?guids={}'.format(url, preprint_no_results._id)
        res = app.get(non_preprint_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'] == []
