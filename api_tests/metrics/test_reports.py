from unittest import mock

import pytest

expected_report_names = {
    # 'addon_usage',
    'download_count',
    'institution_summary',
    'node_summary',
    'osfstorage_file_count',
    'preprint_summary',
    'user_summary',
}

@pytest.mark.django_db
class TestMetricsReports:
    @pytest.fixture
    def mock_domain(self):
        with mock.patch('website.settings.API_DOMAIN', 'http://here/'):
            yield

    @pytest.fixture
    def mock_search(self):
        with mock.patch('elasticsearch6.Elasticsearch.search', autospec=True) as mock_search:
            yield mock_search

    def test_report_names(self, app, mock_domain):
        resp = app.get('/_/metrics/reports/')
        expected_data = {
            frozenset({
                'id': report_name,
                'type': 'metrics-report-name',
                'links': {
                    'recent': f'http://here/_/metrics/reports/{report_name}/recent/',
                },
            })
            for report_name in expected_report_names
        }
        actual_data = {
            frozenset(datum)
            for datum in resp.json['data']
        }
        assert actual_data == expected_data

    @pytest.mark.parametrize('report_name', expected_report_names)
    def test_recent_reports(self, app, mock_domain, mock_search, report_name):
        mock_search.return_value = {
            'hits': {
                'hits': [
                    {'_id': 'hi-by', '_source': {'report_date': '1234-12-12', 'hello': 'goodbye'}},
                    {'_id': 'doof', '_source': {'report_date': '1234-12-11', 'hello': 'upwa'}},
                ],
            },
        }
        resp = app.get(f'/_/metrics/reports/{report_name}/recent/')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/vnd.api+json; charset=utf-8'
        assert resp.json['data'] == [
            {
                'id': 'hi-by',
                'type': f'daily-report:{report_name}',
                'attributes': {
                    'report_date': '1234-12-12',
                    'hello': 'goodbye',
                },
            }, {
                'id': 'doof',
                'type': f'daily-report:{report_name}',
                'attributes': {
                    'report_date': '1234-12-11',
                    'hello': 'upwa',
                },
            }
        ]

        resp = app.get(f'/_/metrics/reports/{report_name}/recent/?format=tsv')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/tab-separated-values; charset=utf-8'
        assert resp.unicode_body == TSV_REPORTS

        resp = app.get(f'/_/metrics/reports/{report_name}/recent/?format=csv')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/csv; charset=utf-8'
        assert resp.unicode_body == CSV_REPORTS


TSV_REPORTS = '''report_date	hello
1234-12-12	goodbye
1234-12-11	upwa
'''.replace('\n', '\r\n')

CSV_REPORTS = '''report_date,hello
1234-12-12,goodbye
1234-12-11,upwa
'''.replace('\n', '\r\n')
