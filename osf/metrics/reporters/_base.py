import collections
import dataclasses
import logging

import celery

from osf.metrics.es8_metrics import (
    BaseDailyReport,
    BaseMonthlyReport,
)
from osf.metrics.utils import YearMonth


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class MonthlyReporter:
    yearmonth: YearMonth

    def iter_report_kwargs(self, continue_after: dict | None = None) -> collections.abc.Iterator[dict]:
        """yield kwargs that can be passed to `report` (in separate async tasks)

        by default, `report` is called once with empty kwargs
        (override for multiple reports per month)
        """
        if continue_after is None:
            yield {}

    def report(self, **report_kwargs) -> collections.abc.Iterator[BaseMonthlyReport]:
        """yield reports for the given month and kwargs (from iter_report_kwargs)
        """
        raise NotImplementedError(f'{self.__class__.__name__} must implement `report`')

    def followup_task(self, report) -> celery.Signature | None:
        """return a task signature that will be enqueued after the report is saved
        """
        return None


class DailyReporter:
    def report(self, report_date) -> collections.abc.Iterator[BaseDailyReport]:
        """build reports for the given date

        return an iterable of DailyReport (unsaved)
        """
        raise NotImplementedError(f'{self.__class__.__name__} must implement `report`')

    def run_and_record_for_date(self, report_date):
        # expecting each reporter to spit out only a handful of reports per day;
        # not bothering with bulk-create (this allows multiple types of reports)
        for report in self.report(report_date):
            report.save()
