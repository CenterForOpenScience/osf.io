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

    def report(self) -> abc.Iterable[MonthlyReport] | abc.Iterator[MonthlyReport]:
        """build a report for the given month
        """
        raise NotImplementedError(f'{self.__name__} must implement `report`')

    def run_and_record_for_month(self) -> None:
        reports = self.report()
        for report in reports:
            report.report_yearmonth = self.yearmonth
            report.save()


class DailyReporter:
    def report(self, report_date):
        """build reports for the given date

        return an iterable of DailyReport (unsaved)
        """
        raise NotImplementedError(f'{self.__name__} must implement `report`')

    def run_and_record_for_date(self, report_date):
        reports = self.report(report_date)

        # expecting each reporter to spit out only a handful of reports per day;
        # not bothering with bulk-create
        for report in reports:
            report.save()
