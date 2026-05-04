import datetime
from unittest import mock

from django.test import TestCase
from elasticsearch_metrics.tests.util import RealElasticTestCase

from osf.metrics.es8_metrics import OsfCountedUsageEvent
from osf_tests.factories import NodeFactory, AuthUserFactory


class TestNodeAnalyticsQueryErrors:
    def test_private_node_anon(self, app):
        _node = NodeFactory(is_public=False)
        with mock.patch('elasticsearch8.Elasticsearch.search') as _mock_search:
            for timespan in ['week', 'fortnight', 'month']:
                resp = app.get(
                    f'/_/metrics/query/node_analytics/{_node._id}/{timespan}/',
                    expect_errors=True,
                )
                assert resp.status_code == 401
        assert _mock_search.call_count == 0

    def test_private_node_rando(self, app):
        _node = NodeFactory(is_public=False)
        _user = AuthUserFactory()
        with mock.patch('elasticsearch8.Elasticsearch.search') as _mock_search:
            for timespan in ['week', 'fortnight', 'month']:
                resp = app.get(
                    f'/_/metrics/query/node_analytics/{_node._id}/{timespan}/',
                    expect_errors=True,
                    auth=_user.auth,
                )
                assert resp.status_code == 403
        assert _mock_search.call_count == 0


class TestNodeAnalyticsQuery(RealElasticTestCase, TestCase):
    def setUp(self):
        super().setUp()
        self._node = NodeFactory(is_public=True)
        self._osfid = self._node._id
        self._today = datetime.date.today()
        self._now = datetime.datetime(
            self._today.year,
            self._today.month,
            self._today.day,
            12,
            tzinfo=datetime.UTC,
        )
        ###
        # past week
        OsfCountedUsageEvent.record(
            sessionhour_id='s1',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(hours=1),
            pageview_info={
                'referer_url': 'http://somewhere.example.com/there',
                'page_url': 'http://osf.example/page/path',
                'route_name': 'page.route',
                'page_title': 'foo',
            }
        )
        OsfCountedUsageEvent.record(
            sessionhour_id='s2',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=1),
            pageview_info={
                'referer_url': 'http://somewhere.example.com/there',
                'page_url': 'http://osf.example/page/path',
                'route_name': 'page.route',
                'page_title': 'foo',
            }
        )
        OsfCountedUsageEvent.record(
            sessionhour_id='s3',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=1, hours=1),
            pageview_info={
                'referer_url': 'http://somewhere.example.com/there',
                'page_url': 'http://osf.example/page/another',
                'route_name': 'page.another',
                'page_title': 'blaz',
            }
        )
        OsfCountedUsageEvent.record(
            sessionhour_id='s4',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=1, hours=2),
            pageview_info={
                'referer_url': 'http://elsewhere.example.com/there',
                'page_url': 'http://osf.example/page/another',
                'route_name': 'page.another',
                'page_title': 'blaz',
            }
        )
        OsfCountedUsageEvent.record(
            sessionhour_id='s5',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=2, hours=1),
            pageview_info={
                'page_url': 'http://osf.example/page/another',
                'route_name': 'page.another',
                'page_title': 'blaz',
            }
        )
        OsfCountedUsageEvent.record(
            sessionhour_id='s6',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=2, hours=2),
            pageview_info={
                'page_url': 'http://osf.example/page/another',
                'route_name': 'page.another',
                'page_title': 'blaz',
            }
        )
        ###
        # past fortnight
        OsfCountedUsageEvent.record(
            sessionhour_id='s7',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=10, hours=1),
            pageview_info={
                'referer_url': 'http://elsewhere.example.com/there',
                'page_url': 'http://osf.example/page/another',
                'route_name': 'page.another',
                'page_title': 'blaz',
            }
        )
        ###
        # past month
        OsfCountedUsageEvent.record(
            sessionhour_id='s8',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=20, hours=1),
            pageview_info={
                'referer_url': 'http://somewhere.example.com/anothere',
                'page_url': 'http://osf.example/page/another',
                'route_name': 'page.another',
                'page_title': 'blaz',
            }
        )
        ###
        # older than a month
        OsfCountedUsageEvent.record(
            sessionhour_id='s9',
            item_osfid=self._osfid,
            action_labels=['view', 'web'],
            timestamp=self._now - datetime.timedelta(days=80, hours=7),
            pageview_info={
                'referer_url': 'http://somewhere.example.com/anothere',
                'page_url': 'http://osf.example/page/another',
                'route_name': 'page.another',
                'page_title': 'blaz',
            }
        )
        # refresh
        OsfCountedUsageEvent.refresh()

    def test_public_node(self):
        _week_resp = self.client.get(f'/_/metrics/query/node_analytics/{self._osfid}/week/')
        assert _week_resp.json()['data'] == {
            'id': f'{self._osfid}:week',
            'type': 'node-analytics',
            'attributes': {
                'popular_pages': [
                    {'route': 'page.another', 'path': '/page/another', 'title': 'blaz', 'count': 4},
                    {'route': 'page.route', 'path': '/page/path', 'title': 'foo', 'count': 2},
                ],
                'unique_visits': [
                    {'date': str(self._today - datetime.timedelta(days=2)), 'count': 2},
                    {'date': str(self._today - datetime.timedelta(days=1)), 'count': 3},
                    {'date': str(self._today), 'count': 1},
                ],
                'time_of_day': [
                    {'hour': 11, 'count': 3},
                    {'hour': 10, 'count': 2},
                    {'hour': 12, 'count': 1},
                ],
                'referer_domain': [
                    {'referer_domain': 'somewhere.example.com', 'count': 3},
                    {'referer_domain': 'elsewhere.example.com', 'count': 1},
                ],
            },
        }

        _fortnight_resp = self.client.get(f'/_/metrics/query/node_analytics/{self._osfid}/fortnight/')
        assert _fortnight_resp.json()['data'] == {
            'id': f'{self._osfid}:fortnight',
            'type': 'node-analytics',
            'attributes': {
                'popular_pages': [
                    {'route': 'page.another', 'path': '/page/another', 'title': 'blaz', 'count': 5},
                    {'route': 'page.route', 'path': '/page/path', 'title': 'foo', 'count': 2},
                ],
                'unique_visits': [
                    {'date': str(self._today - datetime.timedelta(days=10)), 'count': 1},
                    *(
                        {'date': str(self._today - datetime.timedelta(days=_n)), 'count': 0}
                        for _n in range(9, 2, -1)
                    ),
                    {'date': str(self._today - datetime.timedelta(days=2)), 'count': 2},
                    {'date': str(self._today - datetime.timedelta(days=1)), 'count': 3},
                    {'date': str(self._today), 'count': 1},
                ],
                'time_of_day': [
                    {'hour': 11, 'count': 4},
                    {'hour': 10, 'count': 2},
                    {'hour': 12, 'count': 1},
                ],
                'referer_domain': [
                    {'referer_domain': 'somewhere.example.com', 'count': 3},
                    {'referer_domain': 'elsewhere.example.com', 'count': 2},
                ],
            },
        }

        _month_resp = self.client.get(f'/_/metrics/query/node_analytics/{self._osfid}/month/')
        assert _month_resp.json()['data'] == {
            'id': f'{self._osfid}:month',
            'type': 'node-analytics',
            'attributes': {
                'popular_pages': [
                    {'route': 'page.another', 'path': '/page/another', 'title': 'blaz', 'count': 6},
                    {'route': 'page.route', 'path': '/page/path', 'title': 'foo', 'count': 2},
                ],
                'unique_visits': [
                    {'date': str(self._today - datetime.timedelta(days=20)), 'count': 1},
                    *(
                        {'date': str(self._today - datetime.timedelta(days=_n)), 'count': 0}
                        for _n in range(19, 10, -1)
                    ),
                    {'date': str(self._today - datetime.timedelta(days=10)), 'count': 1},
                    *(
                        {'date': str(self._today - datetime.timedelta(days=_n)), 'count': 0}
                        for _n in range(9, 2, -1)
                    ),
                    {'date': str(self._today - datetime.timedelta(days=2)), 'count': 2},
                    {'date': str(self._today - datetime.timedelta(days=1)), 'count': 3},
                    {'date': str(self._today), 'count': 1},
                ],
                'time_of_day': [
                    {'hour': 11, 'count': 5},
                    {'hour': 10, 'count': 2},
                    {'hour': 12, 'count': 1},
                ],
                'referer_domain': [
                    {'referer_domain': 'somewhere.example.com', 'count': 4},
                    {'referer_domain': 'elsewhere.example.com', 'count': 2},
                ],
            },
        }
