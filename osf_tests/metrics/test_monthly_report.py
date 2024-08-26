from unittest import mock

import pytest
from elasticsearch_metrics import metrics

from osf.metrics.reports import MonthlyReport, ReportInvalid
from osf.metrics.utils import YearMonth


class TestMonthlyReportKey:
    @pytest.fixture
    def mock_save(self):
        with mock.patch('elasticsearch6_dsl.Document.save', autospec=True) as mock_save:
            yield mock_save

    def test_default(self, mock_save):
        # only one of this type of report per month
        class UniqueByMonth(MonthlyReport):
            blah = metrics.Keyword()

            class Meta:
                app_label = 'osf'

        yearmonth = YearMonth(2022, 5)

        reports = [
            UniqueByMonth(report_yearmonth=yearmonth),
            UniqueByMonth(report_yearmonth=yearmonth, blah='blah'),
            UniqueByMonth(report_yearmonth=yearmonth, blah='fleh'),
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
        class UniqueByMonthAndField(MonthlyReport):
            UNIQUE_TOGETHER_FIELDS = ('report_yearmonth', 'uniquefield',)
            uniquefield = metrics.Keyword()

            class Meta:
                app_label = 'osf'

        yearmonth = YearMonth(2022, 5)

        expected_blah = '62ebf38317cd8402e27a50ce99f836d1734b3f545adf7d144d0e1cf37a0d9d08'
        blah_report = UniqueByMonthAndField(report_yearmonth=yearmonth, uniquefield='blah')
        blah_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is blah_report
        assert blah_report.meta.id == expected_blah
        mock_save.reset_mock()

        expected_fleh = '385700db282f6d6089a0d21836db5ee8423f548615e515b6e034bcc90a14500f'
        fleh_report = UniqueByMonthAndField(report_yearmonth=yearmonth, uniquefield='fleh')
        fleh_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is fleh_report
        assert fleh_report.meta.id == expected_fleh
        mock_save.reset_mock()

        for _bad_report in (
            UniqueByMonthAndField(report_yearmonth=yearmonth),
            UniqueByMonthAndField(report_yearmonth=yearmonth, uniquefield=['list']),
        ):
            with pytest.raises(ReportInvalid):
                _bad_report.save()
