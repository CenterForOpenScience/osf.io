import datetime
import logging


from django.core.management import call_command
from django.core.management.base import BaseCommand
from elasticsearch6 import helpers as es6_helpers
from elasticsearch8 import helpers as es8_helpers
from elasticsearch_metrics.registry import djelme_registry
from elasticsearch_metrics.imps import elastic8 as djel8me
from elasticsearch_metrics.util.timeparts import format_timeparts

from framework.celery_tasks import app as celery_app
from osf.metrics.preprint_metrics import (
    PreprintView as PreprintViewEs6,
    PreprintDownload as PreprintDownloadEs6,
)
from osf.metrics.counted_usage import CountedAuthUsage as CountedUsageEs6
from osf.metrics import reports as es6_reports
from osf.metrics import es8_metrics, RegistriesModerationMetrics


_logger = logging.getLogger(__name__)

_UNCHANGED_RECORDTYPES = {
    # reports
    es6_reports.StorageAddonUsage: es8_metrics.StorageAddonUsageEs8,
    es6_reports.DownloadCountReport: es8_metrics.DownloadCountReportEs8,
    es6_reports.InstitutionSummaryReport: es8_metrics.InstitutionSummaryReportEs8,
    es6_reports.NewUserDomainReport: es8_metrics.NewUserDomainReportEs8,
    es6_reports.NodeSummaryReport: es8_metrics.NodeSummaryReportEs8,
    es6_reports.OsfstorageFileCountReport: es8_metrics.OsfstorageFileCountReportEs8,
    es6_reports.PreprintSummaryReport: es8_metrics.PreprintSummaryReportEs8,
    es6_reports.UserSummaryReport: es8_metrics.UserSummaryReportEs8,
    es6_reports.SpamSummaryReport: es8_metrics.SpamSummaryReportEs8,
    es6_reports.InstitutionalUserReport: es8_metrics.InstitutionalUserReportEs8,
    es6_reports.InstitutionMonthlySummaryReport: es8_metrics.InstitutionMonthlySummaryReportEs8,
    es6_reports.PrivateSpamMetricsReport: es8_metrics.PrivateSpamMetricsReportEs8,
    # events
    RegistriesModerationMetrics: es8_metrics.RegistriesModerationMetricsEs8,
}


def _debug_migrate(es8_client, each_new):
    for _each in each_new:
        print(_each)


def _do_migrate(es8_client, each_new):
    es8_helpers.bulk(es8_client, each_new, ..., stats_only=True)


def _es6_scan(es6_recordtype, from_when: str, until_when: str):
    return es6_helpers.scan(
        es6_client,
        index=es6_recordtype._template_pattern,
        query={"range": {"timestamp": {"gte": from_when, "lt": until_when}}},
    )


def _cycle_coverage_daily(report_date): ...


def _cycle_coverage_monthly(report_yearmonth): ...


def _unchanged_report_kwargs(es6_recordtype, hit):
    if issubclass(es6_recordtype, es6_reports.DailyReport):
        _cycle_coverage = format_timeparts(
            datetime.date.fromisoformat(hit.pop("report_date")), djel8me.DAILY
        )
    elif issubclass(es6_recordtype, es6_reports.MonthlyReport):
        _cycle_coverage = format_timeparts(hit.pop("report_yearmonth"), djel8me.MONTHLY)
    return {
        **hit,
        'cycle_coverage': _cycle_coverage,
    }


@celery_app.task
def migrate_unchanged_recordtype(
    es6_recordtype_name: str,
):
    _es6_recordtype = djelme_registry.get_recordtype("osf", es6_recordtype_name)
    _es8_recordtype = _UNCHANGED_RECORDTYPES[_es6_recordtype]

    def _each_new():
        for _hit in _es6_scan(_es6_recordtype, from_when, until_when):
            breakpoint()
            yield _es8_recordtype.record(
                ...,
                using=False,  # saved in bulk
            )

    _debug_migrate(_each_new())
    # _do_migrate(_each_new())


@celery_app.task
def migrate_preprint_views(from_date, until_date):
    # convert to counted-usage
    ...


@celery_app.task
def migrate_preprint_downloads(from_date, until_date):
    # convert to counted-usage
    ...


@celery_app.task
def migrate_usage_reports(from_date, until_date):
    # from PublicItemUsageReport to PublicItemUsageReportEs8
    # add cumulative count
    ...


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--start",
            action="store_true",
        )
        parser.add_argument(
            "--unchanged",
            action="store_true",
        )
        parser.add_argument(
            "--usage-events",
            action="store_true",
        )
        parser.add_argument(
            "--usage-reports",
            action="store_true",
        )

    def handle(self, *, start, unchanged, usage_events, usage_reports, **kwargs):
        call_command('djelme_backend_setup')  # ensure all index templates
        _default_all = not any((unchanged, usage_events, usage_reports))
        if unchanged or _default_all:
            self._handle_unchanged(start=start)
        if usage_events or _default_all:
            self._handle_usage_events(start=start)
        if usage_reports or _default_all:
            self._handle_usage_reports(start=start)

    def _handle_unchanged(self, *, start: bool):
        # for each (unchanged) report/event:
        for _es6_cls, _es8_cls in _UNCHANGED_RECORDTYPES.items():
            # display counts
            _es6_count = _es6_cls.search().count()
            _es8_count = _es8_cls.search().count()
            _style = (self.style.SUCCESS if (_es6_count == _es8_count) else self.style.NOTICE)
            self.stdout.write(f'{_es6_cls.__name__} (es6):\t{_es6_count}')
            self.stdout.write(f'{_es8_cls.__name__}:\t{_style(_es8_count)}')
            if start:  # schedule task
                self.stdout.write(f'starting {_es6_cls.__name__} => {_es8_cls.__name__}')
                # TODO: migrate_unchanged_recordtype.apply_async(...)
            self.stdout.write('---')

    def _handle_usage_events(self, *, start: bool):
        # for counted-usage events:
        # TODO: last X months only
        # display counts for each view/download event type
        _es6_pview_count = PreprintViewEs6.search().count()
        _es6_pdownload_count = PreprintDownloadEs6.search().count()
        _es6_usage_event_count = CountedUsageEs6.search().count()
        _es6_count = _es6_pview_count + _es6_pdownload_count + _es6_usage_event_count
        _es8_count = es8_metrics.OsfCountedUsageRecord.search().count()
        _style = (self.style.SUCCESS if (_es6_count == _es8_count) else self.style.NOTICE)
        self.stdout.write(f'{PreprintViewEs6.__name__} (es6):\t{_es6_pview_count}')
        self.stdout.write(f'{PreprintDownloadEs6.__name__} (es6):\t{_es6_pdownload_count}')
        self.stdout.write(f'{CountedUsageEs6.__name__} (es6):\t{_es6_pdownload_count}')
        self.stdout.write(f'total (es6):\t{_es6_count}')
        self.stdout.write(f'{es8_metrics.OsfCountedUsageRecord.__name__}:\t{_style(_es8_count)}')
        if start:  # schedule (per-day?) tasks (if --start)
            self.stdout.write(f'starting {_es6_cls.__name__} => {_es8_cls.__name__}')
            # TODO: migrate_usage_events.apply_async(...)

    def _handle_usage_reports(self, *, start: bool):
        # display total report counts
        _es6_count = es6_reports.PublicItemUsageReport.search().count()
        _es8_count = es8_metrics.PublicItemUsageReportEs8.search().count()
        _style = (self.style.SUCCESS if (_es6_count == _es8_count) else self.style.NOTICE)
        self.stdout.write(f'{es6_reports.PublicItemUsageReport.__name__} (es6):\t{_es6_count}')
        self.stdout.write(f'{es8_metrics.PublicItemUsageReportEs8.__name__}:\t{_style(_es8_count)}')
        # display distinct item counts
        _item_count
        # (if --start) schedule task per item (by composite agg on es6 public usage reports)
        # each item-task iter thru reports oldest to newest, adding cumulative counts
