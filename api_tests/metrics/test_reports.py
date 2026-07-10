import csv
import datetime
from io import StringIO
from unittest import mock

import pytest

from osf.metrics.daily_reports import DailyDownloadCountReport

expected_report_names = [
    # 'addon_usage',
    'download_count',
    'institution_summary',
    'node_summary',
    'osfstorage_file_count',
    'preprint_summary',
    'user_summary',
]

@pytest.mark.django_db
class TestMetricsReports:
    @pytest.fixture
    def mock_domain(self):
        with mock.patch('website.settings.API_DOMAIN', 'http://here/'):
            yield

    @pytest.fixture
    def mock_search(self):
        with mock.patch('elasticsearch8.Elasticsearch.search', autospec=True) as mock_search:
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
        mock_search.return_value.body = {
            'hits': {
                'hits': [
                    {'_id': 'hi-by', '_source': {'report_date': '1234-12-12', 'hello': 'goodbye', 'created': '1235-12-13T01:00:00Z'}},
                    {'_id': 'doof', '_source': {'report_date': '1234-12-11', 'hello': 'upwa', 'created': '1235-12-12T01:00:00Z'}},
                ],
            },
        }
        resp = app.get(f'/_/metrics/reports/{report_name}/recent/')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/vnd.api+json; charset=utf-8'
        assert resp.json['data'] == [
            {
                'id': 'hi-by',
                'type': f'cyclic-report:{report_name}',
                'attributes': {
                    'report_date': '1234-12-12',
                    'hello': 'goodbye',
                    'created': '1235-12-13T01:00:00Z',
                },
            }, {
                'id': 'doof',
                'type': f'cyclic-report:{report_name}',
                'attributes': {
                    'report_date': '1234-12-11',
                    'hello': 'upwa',
                    'created': '1235-12-12T01:00:00Z',
                },
            }
        ]

        resp = app.get(f'/_/metrics/reports/{report_name}/recent/?format=tsv')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/tab-separated-values; charset=utf-8'
        assert resp.unicode_body == '''report_date	created	hello
1234-12-12	1235-12-13 01:00:00+00:00	goodbye
1234-12-11	1235-12-12 01:00:00+00:00	upwa
'''.replace('\n', '\r\n')

        resp = app.get(f'/_/metrics/reports/{report_name}/recent/?format=csv')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/csv; charset=utf-8'
        assert resp.unicode_body == '''report_date,created,hello
1234-12-12,1235-12-13 01:00:00+00:00,goodbye
1234-12-11,1235-12-12 01:00:00+00:00,upwa
'''.replace('\n', '\r\n')


@pytest.mark.django_db
@pytest.mark.osfmetrics_elastic_backends
class TestMetricsReportsRealElastic:
    @pytest.fixture(autouse=True)
    def mock_now(self):
        _now = datetime.datetime(1234, 12, 23, tzinfo=datetime.timezone.utc)
        with mock.patch('django.utils.timezone.now', return_value=_now):
            yield

    @pytest.fixture
    def daily_reports(self):
        _reports = [
            DailyDownloadCountReport.record(cycle_coverage='1234.12.6', daily_file_downloads=1),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.7', daily_file_downloads=2),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.8', daily_file_downloads=3),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.9', daily_file_downloads=4),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.10', daily_file_downloads=5),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.11', daily_file_downloads=17),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.12', daily_file_downloads=18),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.13', daily_file_downloads=10),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.14', daily_file_downloads=171),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.15', daily_file_downloads=1),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.16', daily_file_downloads=0),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.17', daily_file_downloads=34),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.18', daily_file_downloads=22),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.19', daily_file_downloads=50),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.20', daily_file_downloads=91),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.21', daily_file_downloads=12),
            DailyDownloadCountReport.record(cycle_coverage='1234.12.22', daily_file_downloads=11),
        ]
        DailyDownloadCountReport.refresh()
        return _reports

    def test_recent_reports(self, app, daily_reports):
        # test no params
        resp = app.get('/_/metrics/reports/download_count/recent/')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/vnd.api+json; charset=utf-8'
        _data = resp.json['data']
        _expected_dates = [
            '1234-12-22',
            '1234-12-21',
            '1234-12-20',
            '1234-12-19',
            '1234-12-18',
            '1234-12-17',
            '1234-12-16',
            '1234-12-15',
            '1234-12-14',
            '1234-12-13',
            '1234-12-12',
            '1234-12-11',
            '1234-12-10',
        ]
        _actual_dates = [_item['attributes']['report_date'] for _item in _data]
        assert _actual_dates == _expected_dates
        _expected_counts = [11, 12, 91, 50, 22, 34, 0, 1, 171, 10, 18, 17, 5]
        _actual_counts = [_item['attributes']['daily_file_downloads'] for _item in _data]
        assert _actual_counts == _expected_counts

        # test 3 days back
        resp = app.get('/_/metrics/reports/download_count/recent/?days_back=3')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/vnd.api+json; charset=utf-8'
        _data = resp.json['data']
        _expected_dates = [
            '1234-12-22',
            '1234-12-21',
            '1234-12-20',
        ]
        _actual_dates = [_item['attributes']['report_date'] for _item in _data]
        assert _actual_dates == _expected_dates
        _expected_counts = [11, 12, 91]
        _actual_counts = [_item['attributes']['daily_file_downloads'] for _item in _data]
        assert _actual_counts == _expected_counts

        # test range
        resp = app.get('/_/metrics/reports/download_count/recent/?start_date=1234-12-11&end_date=1234-12-15')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'application/vnd.api+json; charset=utf-8'
        _data = resp.json['data']
        _expected_dates = [
            '1234-12-14',
            '1234-12-13',
            '1234-12-12',
            '1234-12-11',
        ]
        _actual_dates = [_item['attributes']['report_date'] for _item in _data]
        assert _actual_dates == _expected_dates
        _expected_counts = [171, 10, 18, 17]
        _actual_counts = [_item['attributes']['daily_file_downloads'] for _item in _data]
        assert _actual_counts == _expected_counts

        # test tsv
        resp = app.get('/_/metrics/reports/download_count/recent/?format=tsv')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/tab-separated-values; charset=utf-8'
        _rows = list(csv.DictReader(StringIO(resp.unicode_body), dialect='excel-tab'))
        _expected_dates = [
            '1234-12-22',
            '1234-12-21',
            '1234-12-20',
            '1234-12-19',
            '1234-12-18',
            '1234-12-17',
            '1234-12-16',
            '1234-12-15',
            '1234-12-14',
            '1234-12-13',
            '1234-12-12',
            '1234-12-11',
            '1234-12-10',
        ]
        _actual_dates = [_row['report_date'] for _row in _rows]
        assert _actual_dates == _expected_dates
        _expected_counts = [11, 12, 91, 50, 22, 34, 0, 1, 171, 10, 18, 17, 5]
        _actual_counts = [int(_row['daily_file_downloads']) for _row in _rows]
        assert _actual_counts == _expected_counts

        # test csv
        resp = app.get('/_/metrics/reports/download_count/recent/?format=csv')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/csv; charset=utf-8'
        _rows = list(csv.DictReader(StringIO(resp.unicode_body)))
        _expected_dates = [
            '1234-12-22',
            '1234-12-21',
            '1234-12-20',
            '1234-12-19',
            '1234-12-18',
            '1234-12-17',
            '1234-12-16',
            '1234-12-15',
            '1234-12-14',
            '1234-12-13',
            '1234-12-12',
            '1234-12-11',
            '1234-12-10',
        ]
        _actual_dates = [_row['report_date'] for _row in _rows]
        assert _actual_dates == _expected_dates
        _expected_counts = [11, 12, 91, 50, 22, 34, 0, 1, 171, 10, 18, 17, 5]
        _actual_counts = [int(_row['daily_file_downloads']) for _row in _rows]
        assert _actual_counts == _expected_counts
