import datetime
from functools import cached_property

from django.test import TestCase
from elasticsearch_metrics.tests.util import RealElasticTestCase

from osf.models.base import osfid_iri
from osf.metrics.reports import MonthlyPublicItemUsageReport
from osf.metrics.utils import YearMonth


class TestEachFromLastMonth(RealElasticTestCase, TestCase):
    osfid = 'abced'

    @cached_property
    def item_iri(self):
        return osfid_iri(self.osfid)

    @cached_property
    def this_month(self):
        return YearMonth.from_date(datetime.date.today())

    @cached_property
    def last_month(self):
        return self.this_month.prior()

    @cached_property
    def two_months_back(self):
        return self.last_month.prior()

    @cached_property
    def three_months_back(self):
        return self.two_months_back.prior()

    @cached_property
    def this_month_report(self):
        return _item_usage_report(self.this_month, self.osfid, view_count=77)

    @cached_property
    def last_month_report(self):
        return _item_usage_report(self.last_month, self.osfid, view_count=57)

    @cached_property
    def diff_last_month_report(self):
        return _item_usage_report(self.last_month, 'zyxvt', view_count=17)

    @cached_property
    def two_months_back_report(self):
        return _item_usage_report(self.two_months_back, self.osfid, view_count=27)

    @cached_property
    def three_months_back_report(self):
        return _item_usage_report(self.three_months_back, self.osfid, view_count=37)

    def test_with_none(self):
        self.assertEqual(
            MonthlyPublicItemUsageReport.from_last_month([self.item_iri]),
            [],
        )

    def test_with_others(self):
        self.this_month_report
        self.three_months_back_report
        self.diff_last_month_report
        MonthlyPublicItemUsageReport.refresh()
        self.assertEqual(
            MonthlyPublicItemUsageReport.from_last_month([self.item_iri]),
            [],
        )

    def test_with_prior_month(self):
        self.this_month_report
        self.two_months_back_report
        self.three_months_back_report
        self.diff_last_month_report
        MonthlyPublicItemUsageReport.refresh()
        self.assertEqual(
            MonthlyPublicItemUsageReport.from_last_month([self.item_iri]),
            [self.two_months_back_report],
        )

    def test_with_last_month(self):
        self.this_month_report
        self.last_month_report
        self.two_months_back_report
        self.three_months_back_report
        self.diff_last_month_report
        MonthlyPublicItemUsageReport.refresh()
        self.assertEqual(
            MonthlyPublicItemUsageReport.from_last_month([self.item_iri]),
            [self.last_month_report],
        )


def _item_usage_report(ym: YearMonth, osfid: str, **kwargs):
    _report = MonthlyPublicItemUsageReport(
        report_yearmonth=ym,
        item_iri=osfid_iri(osfid),
        item_osfids=osfid,
        **kwargs
    )
    _report.save(validate=False)
    return _report
