from unittest import mock

import pytest

from osf_tests.factories import NodeFactory, AuthUserFactory

@pytest.mark.django_db
class TestNodeAnalyticsQuery:
    @pytest.fixture
    def mock_search(self):
        with mock.patch('elasticsearch6.Elasticsearch.search', autospec=True) as mock_search:
            yield mock_search

    @pytest.mark.parametrize('timespan', ['week', 'fortnight', 'month'])
    def test_private_node(self, app, mock_search, timespan):
        node = NodeFactory(is_public=False)
        guid = node._id
        resp = app.get(
            f'/_/metrics/query/node_analytics/{guid}/{timespan}/',
            expect_errors=True,
        )
        assert resp.status_code == 401

        user = AuthUserFactory()
        resp = app.get(
            f'/_/metrics/query/node_analytics/{guid}/{timespan}/',
            auth=user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

        assert mock_search.call_count == 0

    @pytest.mark.parametrize('timespan', ['week', 'fortnight', 'month'])
    def test_public_node(self, app, mock_search, timespan):
        node = NodeFactory(is_public=True)
        guid = node._id
        mock_search.return_value = {
            'aggregations': {
                'popular-pages': {
                    'buckets': [
                        {
                            'key': '/page/path',
                            'doc_count': 17,
                            'route-for-path': {
                                'buckets': [{'key': 'page.route'}],
                            },
                            'title-for-path': {
                                'buckets': [{'key': 'foo'}],
                            },
                        },
                        {
                            'key': '/page/another',
                            'doc_count': 7,
                            'route-for-path': {
                                'buckets': [{'key': 'page.another'}],
                            },
                            'title-for-path': {
                                'buckets': [{'key': 'blaz'}],
                            },
                        },
                    ],
                },
                'unique-visits': {
                    'buckets': [
                        {'key': 1646265600000, 'key_as_string': '2022-03-03', 'doc_count': 8},
                        {'key': 1646352000000, 'key_as_string': '2022-03-04', 'doc_count': 1},
                    ],
                },
                'time-of-day': {
                    'buckets': [
                        {'key': 8, 'doc_count': 1},
                        {'key': 9, 'doc_count': 2},
                        {'key': 10, 'doc_count': 3},
                    ],
                },
                'referer-domain': {
                    'buckets': [
                        {'key': 'somewhere.example.com', 'doc_count': 9},
                        {'key': 'elsewhere.example.com', 'doc_count': 4},
                    ],
                },
            },
        }
        resp = app.get(f'/_/metrics/query/node_analytics/{guid}/{timespan}/')

        assert resp.json['data'] == {
            'id': f'{guid}:{timespan}',
            'type': 'node-analytics',
            'attributes': {
                'popular_pages': [
                    {'route': 'page.route', 'path': '/page/path', 'title': 'foo', 'count': 17},
                    {'route': 'page.another', 'path': '/page/another', 'title': 'blaz', 'count': 7},
                ],
                'unique_visits': [
                    {'date': '2022-03-03', 'count': 8},
                    {'date': '2022-03-04', 'count': 1},
                ],
                'time_of_day': [
                    {'hour': 8, 'count': 1},
                    {'hour': 9, 'count': 2},
                    {'hour': 10, 'count': 3},
                ],
                'referer_domain': [
                    {'referer_domain': 'somewhere.example.com', 'count': 9},
                    {'referer_domain': 'elsewhere.example.com', 'count': 4},
                ],
            },
        }

        assert mock_search.call_count == 1
