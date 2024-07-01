from datetime import date
from unittest import mock

import pytest
from elasticsearch_metrics import metrics

from osf.metrics.reports import DailyReport, ReportInvalid


class TestDailyReportKey:
    @pytest.fixture
    def mock_save(self):
        with mock.patch('elasticsearch6_dsl.Document.save', autospec=True) as mock_save:
            yield mock_save

    def test_default(self, mock_save):
        # only one of this type of report per day
        class UniqueByDate(DailyReport):
            blah = metrics.Keyword()

            class Meta:
                app_label = 'osf'

        today = date(2022, 5, 18)

        reports = [
            UniqueByDate(report_date=today),
            UniqueByDate(report_date=today, blah='blah'),
            UniqueByDate(report_date=today, blah='fleh'),
        ]
        expected_key = '6fe48593af0f9d34159616759bd4678f383c912fdff3e8a338c51ecb1cf9d0d5'

        for report in reports:
            report.save()
            assert mock_save.call_count == 1
            assert mock_save.call_args[0][0] is report
            assert report.meta.id == expected_key
            mock_save.reset_mock()

    def test_with_duf(self, mock_save):
        # multiple reports of this type per day, unique by given field
        class UniqueByDateAndField(DailyReport):
            DAILY_UNIQUE_FIELD = 'duf'
            duf = metrics.Keyword()

            class Meta:
                app_label = 'osf'

        today = date(2022, 5, 18)

        expected_blah = 'dca57e6cde89b19274ea24bc713971dab137a896b8e06d43a11a3f437cd1d151'
        blah_report = UniqueByDateAndField(report_date=today, duf='blah')
        blah_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is blah_report
        assert blah_report.meta.id == expected_blah
        mock_save.reset_mock()

        expected_fleh = 'e7dd5ff6b087807efcfa958077dc713878f21c65af79b3ccdb5dc2409bf5ad99'
        fleh_report = UniqueByDateAndField(report_date=today, duf='fleh')
        fleh_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is fleh_report
        assert fleh_report.meta.id == expected_fleh
        mock_save.reset_mock()

        bad_report = UniqueByDateAndField(report_date=today)
        with pytest.raises(ReportInvalid):
            bad_report.save()
