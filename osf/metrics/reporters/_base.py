from collections import abc
import dataclasses
import logging

import celery

from osf.metrics.reports import MonthlyReport
from osf.metrics.utils import YearMonth


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class MonthlyReporter:
    yearmonth: YearMonth

    def iter_report_kwargs(self, continue_after: dict | None = None) -> abc.Iterator[dict]:
        # override for multiple reports per month
        if continue_after is None:
            yield {}  # by default, calls `.report()` once with no kwargs

    def report(self, **report_kwargs) -> MonthlyReport | None:
        """build a report for the given month
        """
        raise NotImplementedError(f'{self.__class__.__name__} must implement `report`')

    def followup_task(self, report) -> celery.Signature | None:
        return None


class DailyReporter:
    def report(self, report_date):
        """build reports for the given date

        return an iterable of DailyReport (unsaved)
        """
        raise NotImplementedError(f'{self.__class__.__name__} must implement `report`')

    def run_and_record_for_date(self, report_date):
        reports = self.report(report_date)

        # expecting each reporter to spit out only a handful of reports per day;
        # not bothering with bulk-create
        for report in reports:
            report.save()
