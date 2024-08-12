from collections import defaultdict
from datetime import datetime
import logging
import pytz

from keen.client import KeenClient

from osf.metrics.utils import YearMonth
from website.settings import KEEN as keen_settings


logger = logging.getLogger(__name__)


class MonthlyReporter:
    def report(self, report_yearmonth: YearMonth):
        """build a report for the given month"""
        raise NotImplementedError(f"{self.__name__} must implement `report`")

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
        raise NotImplementedError(f"{self.__name__} must implement `report`")

    def keen_events_from_report(self, report):
        """given one of this reporter's own reports, build equivalent keen events
        (for back-compat; to be deleted once we don't need keen anymore)

        return a mapping from keen collection name to iterable of events
        e.g. {'my_keen_collection': [event1, event2, ...]}
        """
        raise NotImplementedError(
            f"{self.__name__} should probably implement keen_events_from_report"
        )

    def run_and_record_for_date(self, report_date, *, also_send_to_keen=False):
        reports = self.report(report_date)

        # expecting each reporter to spit out only a handful of reports per day;
        # not bothering with bulk-create
        for report in reports:
            report.save()

        if also_send_to_keen:
            self.send_to_keen(reports)

    def send_to_keen(self, reports):
        keen_project = keen_settings["private"]["project_id"]
        write_key = keen_settings["private"]["write_key"]
        if not (keen_project and write_key):
            logger.warning(
                f"keen not configured; not sending events for {self.__class__.__name__}"
            )
            return

        keen_events_by_collection = defaultdict(list)
        for report in reports:
            keen_event_timestamp = datetime(
                report.report_date.year,
                report.report_date.month,
                report.report_date.day,
                tzinfo=pytz.utc,
            )

            for collection_name, keen_events in self.keen_events_from_report(
                report
            ).items():
                for event in keen_events:
                    event["keen"] = {
                        "timestamp": keen_event_timestamp.isoformat()
                    }
                keen_events_by_collection[collection_name].extend(keen_events)

        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_events(keen_events_by_collection)
