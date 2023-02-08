from unittest import mock

import pytest
from elasticsearch_metrics import metrics

from osf.metrics.reports import MonthlyReport, ReportInvalid
from osf.metrics.utils import YearMonth


class TestMonthlyReportKey:
    @pytest.fixture
    def mock_save(self):
        with mock.patch('elasticsearch_dsl.Document.save', autospec=True) as mock_save:
            yield mock_save

    def test_default(self, mock_save):
        # only one of this type of report per day
        class UniqueByDate(MonthlyReport):
            blah = metrics.Keyword()

            class Meta:
                app_label = 'osf'

        this_month = YearMonth(2022, 5)

        reports = [
            UniqueByDate(report_yearmonth=this_month),
            UniqueByDate(report_yearmonth=this_month, blah='blah'),
            UniqueByDate(report_yearmonth=this_month, blah='fleh'),
        ]
        expected_key = '8463aac67c1e5a038049196781d8f100f069225352d1829651892cf3fbfc50e2'

        for report in reports:
            report.save()
            assert mock_save.call_count == 1
            assert mock_save.call_args[0][0] is report
            assert report.meta.id == expected_key
            mock_save.reset_mock()

    def test_with_unique_together(self, mock_save):
        # multiple reports of this type per day, unique by given field
        class UniqueByDateAndField(MonthlyReport):
            UNIQUE_TOGETHER = ('report_yearmonth', 'my_uniq_field',)
            my_uniq_field = metrics.Keyword()

            class Meta:
                app_label = 'osf'

        this_month = YearMonth(2022, 5)

        expected_blah = '62ebf38317cd8402e27a50ce99f836d1734b3f545adf7d144d0e1cf37a0d9d08'
        blah_report = UniqueByDateAndField(report_yearmonth=this_month, my_uniq_field='blah')
        blah_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is blah_report
        assert blah_report.meta.id == expected_blah
        mock_save.reset_mock()

        expected_fleh = '385700db282f6d6089a0d21836db5ee8423f548615e515b6e034bcc90a14500f'
        fleh_report = UniqueByDateAndField(report_yearmonth=this_month, my_uniq_field='fleh')
        fleh_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is fleh_report
        assert fleh_report.meta.id == expected_fleh
        mock_save.reset_mock()

        bad_report = UniqueByDateAndField(report_yearmonth=this_month)
        with pytest.raises(ReportInvalid):
            bad_report.save()
