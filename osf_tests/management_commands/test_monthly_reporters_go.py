import datetime

from django.core.management import call_command
from django.test import TestCase
from elasticsearch_metrics.tests.util import djelme_test_backends

from framework.celery_tasks import app as celery_app
from osf.metrics.es8_metrics import (
    MonthlyInstitutionSummaryReportEs8,
    MonthlyInstitutionalUserReportEs8,
    MonthlyPrivateSpamMetricsReportEs8,
    MonthlyPublicItemUsageReportEs8,
    MonthlySpamSummaryReportEs8,
    OsfCountedUsageEvent,
)
from osf.metrics.utils import YearMonth
from osf_tests import factories


class TestMonthlyReportersGo(TestCase):
    def setUp(self):
        self.enterContext(djelme_test_backends())
        celery_app.conf.update({
            'task_always_eager': True,
            'task_eager_propagates': True,
        })
        self._report_yearmonth = YearMonth.from_date(datetime.date.today())
        # set up for institutional-user report
        _inst = factories.InstitutionFactory()
        _user = factories.UserFactory()
        _user.add_or_update_affiliated_institution(_inst)
        # set up for public item usage report
        _reg = factories.RegistrationFactory(is_public=True)
        OsfCountedUsageEvent.record(
            item_osfid=_reg._id,
            action_labels=['view', 'web'],
            user_id=_user._id,
        )
        OsfCountedUsageEvent.refresh()

    def test_for_smoke(self):
        self._assert_count(MonthlyInstitutionSummaryReportEs8, 0)
        self._assert_count(MonthlyInstitutionalUserReportEs8, 0)
        self._assert_count(MonthlyPrivateSpamMetricsReportEs8, 0)
        self._assert_count(MonthlyPublicItemUsageReportEs8, 0)
        self._assert_count(MonthlySpamSummaryReportEs8, 0)
        call_command('monthly_reporters_go', yearmonth=str(self._report_yearmonth))
        self._assert_count(MonthlyInstitutionSummaryReportEs8, 1)
        self._assert_count(MonthlyInstitutionalUserReportEs8, 1)
        self._assert_count(MonthlyPrivateSpamMetricsReportEs8, 1)
        self._assert_count(MonthlyPublicItemUsageReportEs8, 1)
        self._assert_count(MonthlySpamSummaryReportEs8, 1)

    def _assert_count(self, recordtype, expected_count):
        if hasattr(recordtype, 'refresh'):
            recordtype.refresh()
        else:  # elasticsearch_metrics.imps.elastic6
            recordtype._get_connection().indices.refresh(recordtype._template_pattern)
        self.assertEqual(recordtype.search().count(), expected_count)
