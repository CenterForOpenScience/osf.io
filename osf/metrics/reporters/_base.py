import logging

from osf.metrics.utils import YearMonth


logger = logging.getLogger(__name__)


class MonthlyReporter:
    def report(self, report_yearmonth: YearMonth):
        """build a report for the given month
        """
        raise NotImplementedError(f'{self.__name__} must implement `report`')

    def run_and_record_for_month(self, report_yearmonth: YearMonth):
        reports = self.report(report_yearmonth)
        for report in reports:
            assert report.report_yearmonth == str(report_yearmonth)
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
