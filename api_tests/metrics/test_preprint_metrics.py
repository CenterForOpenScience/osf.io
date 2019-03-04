import pytest
import mock
from datetime import datetime

from website.app import setup_django
setup_django()

from django.utils import timezone
from waffle.testutils import override_switch
from elasticsearch.exceptions import RequestError

from osf import features
from api.base.settings import API_BASE
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

    @mock.patch('api.metrics.views.timezone.now')
    def test_incorrect_dates(self, mock_timezone, app, user, base_url, preprint):
        mock_timezone.return_value = datetime(2019, 1, 4, tzinfo=timezone.utc)

        base_url = '{}downloads/?guids={}'.format(base_url, preprint._id)

        start_date = '2019-01-01'
        end_date = '2019-02-01'

        # test on_date and start_date fails
        url = '{}&on_date={}&start_datetime={}'.format(base_url, start_date, start_date)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # test on_date and end_date fails
        url = '{}&on_date={}&end_datetime={}'.format(base_url, start_date, start_date)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # test end date before start date fails
        url = '{}&start_datetime={}&end_datetime={}'.format(base_url, end_date, start_date)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # error if both on_date and a date range
        url = '{}&on_date={}&end_datetime={}'.format(base_url, end_date, start_date)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # error if a time is used for a specific date request
        url = '{}&on_date=2018-01-01T01:01'.format(base_url)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # error if an end_datetime is provided without a start_datetime
        url = '{}&end_datetime={}'.format(base_url, end_date)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # error if a time is used in one datetime and not the other
        url = '{}&start_datetime={}&end_datetime={}'.format(base_url, start_date, end_date + 'T01:01:01')
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    @mock.patch('api.metrics.views.PreprintDownloadMetrics.execute_search')
    def test_custom_metric_misformed_query(self, mock_execute, app, user, base_url):
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
        assert res.json['errors'][0]['detail'] == 'Misformed elasticsearch query.'

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
    @mock.patch('api.metrics.views.timezone.now')
    def test_preprint_list_with_metrics_fails(self, mock_timezone, app, user, base_url, preprint, preprint_two,
                                                preprint_three, metric_name, other_user, project, project_two):
        url = '{}{}/'.format(base_url, metric_name)

        one_preprint_url = '{}?guids={}'.format(url, preprint._id)
        # test non-logged in cannot access
        res = app.get(one_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # test logged in non-metrics user cannot access
        res = app.get(one_preprint_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403

        # all non-guids
        fake_guids_list = ['nota', 'reallist', 'of', 'guids']
        fake_guids_url = '{}?guids={}'.format(url, ','.join(fake_guids_list))
        res = app.get(fake_guids_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # one non-guid fails
        one_fake_list = [preprint._id, preprint_two._id, 'notanid']
        one_fake_url = '{}?guids={}'.format(url, ','.join(one_fake_list))
        res = app.get(one_fake_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # guids of non-preprints fails
        projs = [project._id, project_two._id]
        projs_url = '{}?guids={}'.format(url, ','.join(projs))
        res = app.get(projs_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # one guid of a non-preprint fails
        one_non_preprint_list = [preprint._id, preprint_two._id, project._id]
        one_non_preprint_url = '{}?guids={}'.format(url, ','.join(one_non_preprint_list))
        res = app.get(one_non_preprint_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    @pytest.mark.skip('Return results will be entirely mocked so does not make a lot of sense to run on travis.')
    @mock.patch('api.metrics.views.timezone.now')
    def test_preprint_with_metrics_succeeds(self, mock_timezone, app, user, base_url, preprint, other_user, preprint_no_results, metric_dates):
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
