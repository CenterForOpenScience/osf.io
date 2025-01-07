import datetime
from unittest import mock

import pytest
from elasticsearch_metrics import metrics

from osf.metrics.reports import MonthlyReport, ReportInvalid, PublicItemUsageReport
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
        expected_timestamp = datetime.datetime(yearmonth.year, yearmonth.month, 1, tzinfo=datetime.UTC)

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
            assert report.timestamp == expected_timestamp
            mock_save.reset_mock()

    def test_with_unique_together(self, mock_save):
        # multiple reports of this type per day, unique by given field
        class UniqueByMonthAndField(MonthlyReport):
            UNIQUE_TOGETHER_FIELDS = ('report_yearmonth', 'uniquefield',)
            uniquefield = metrics.Keyword()

            class Meta:
                app_label = 'osf'

        yearmonth = YearMonth(2022, 5)
        expected_timestamp = datetime.datetime(yearmonth.year, yearmonth.month, 1, tzinfo=datetime.UTC)

        expected_blah = '62ebf38317cd8402e27a50ce99f836d1734b3f545adf7d144d0e1cf37a0d9d08'
        blah_report = UniqueByMonthAndField(report_yearmonth=yearmonth, uniquefield='blah')
        blah_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is blah_report
        assert blah_report.meta.id == expected_blah
        assert blah_report.timestamp == expected_timestamp
        mock_save.reset_mock()

        expected_fleh = '385700db282f6d6089a0d21836db5ee8423f548615e515b6e034bcc90a14500f'
        fleh_report = UniqueByMonthAndField(report_yearmonth=yearmonth, uniquefield='fleh')
        fleh_report.save()
        assert mock_save.call_count == 1
        assert mock_save.call_args[0][0] is fleh_report
        assert fleh_report.meta.id == expected_fleh
        assert fleh_report.timestamp == expected_timestamp
        mock_save.reset_mock()

        for _bad_report in (
            UniqueByMonthAndField(report_yearmonth=yearmonth),
            UniqueByMonthAndField(report_yearmonth=yearmonth, uniquefield=['list']),
        ):
            with pytest.raises(ReportInvalid):
                _bad_report.save()


@pytest.mark.es_metrics
class TestLastMonthReport:
    @pytest.fixture
    def osfid(self):
        return 'abced'

    @pytest.fixture
    def this_month(self):
        return YearMonth.from_date(datetime.date.today())

    @pytest.fixture
    def last_month(self, this_month):
        return _prior_yearmonth(this_month)

    @pytest.fixture
    def two_months_back(self, last_month):
        return _prior_yearmonth(last_month)

    @pytest.fixture
    def three_months_back(self, two_months_back):
        return _prior_yearmonth(two_months_back)

    @pytest.fixture
    def this_month_report(self, osfid, this_month):
        return _item_usage_report(this_month, osfid, view_count=77)

    @pytest.fixture
    def last_month_report(self, osfid, last_month):
        return _item_usage_report(last_month, osfid, view_count=57)

    @pytest.fixture
    def diff_last_month_report(self, last_month):
        return _item_usage_report(last_month, 'zyxvt', view_count=17)

    @pytest.fixture
    def two_months_back_report(self, osfid, two_months_back):
        return _item_usage_report(two_months_back, osfid, view_count=27)

    @pytest.fixture
    def three_months_back_report(self, osfid, three_months_back):
        return _item_usage_report(three_months_back, osfid, view_count=37)

    def test_with_none(self, osfid):
        assert PublicItemUsageReport.for_last_month(osfid) is None

    def test_with_others(self, osfid, this_month_report, three_months_back_report, diff_last_month_report):
        assert PublicItemUsageReport.for_last_month(osfid) is None

    def test_with_prior_month(self, osfid, this_month_report, two_months_back_report, three_months_back_report, diff_last_month_report):
        assert PublicItemUsageReport.for_last_month(osfid) == two_months_back_report

    def test_with_last_month(self, osfid, this_month_report, last_month_report, two_months_back_report, three_months_back_report, diff_last_month_report):
        assert PublicItemUsageReport.for_last_month(osfid) == last_month_report


def _prior_yearmonth(ym: YearMonth) -> YearMonth:
    return (
        YearMonth(ym.year - 1, 12)
        if ym.month == 1
        else YearMonth(ym.year, ym.month - 1)
    )


def _item_usage_report(ym: YearMonth, osfid: str, **kwargs):
    _report = PublicItemUsageReport(
        report_yearmonth=ym,
        item_osfid=osfid,
        **kwargs
    )
    _report.save(refresh=True)
    return _report
