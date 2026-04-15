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

_USAGE_MONTHS_BACK = 3

_MAX_CARDINALITY_PRECISION = 40000  # https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-metrics-cardinality-aggregation.html#_precision_control

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


def _es6_usage_report_counts() -> tuple[int, int]:
    _search = (
        es6_reports.PublicItemUsageReport.search()
    )
    _search.aggs.metric(
        'agg_item_count',
        'cardinality',
        field='item_osfid',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _total_count = _response.hits.total
    _item_count = (
        _response.aggregations.agg_item_count.value
        if 'agg_item_count' in _response.aggregations
        else 0
    )
    return (_total_count, _item_count)


def _es8_usage_report_counts() -> tuple[int, int]:
    _search = (
        es8_metrics.PublicItemUsageReportEs8.search()
    )
    _search.aggs.metric(
        'agg_item_count',
        'cardinality',
        field='item_osfid',
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _total_count = _response.hits.total.value
    _item_count = (
        _response.aggregations.agg_item_count.value
        if 'agg_item_count' in _response.aggregations
        else 0
    )
    return (_total_count, _item_count)


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
        parser.add_argument(
            "--clear-state",
            action="store_true",
        )
        parser.add_argument(
            "--no-setup",
            action="store_true",
        )

    def handle(self, *, start, unchanged, usage_events, usage_reports, clear_state, no_setup, **kwargs):
        self._quiet_chatty_loggers()
        if not no_setup:
            call_command('djelme_backend_setup')
        if clear_state:
            self._clear_state()
        self._display_started_at(start=start)
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
            #_es8_count = _es8_cls.search().count()
            self._write_tabbed('es6', _es6_cls, _es6_count)
            self._write_tabbed('es8', _es8_cls, _es8_count, style=self._eq_style(_es8_count, _es6_count))
            if start:  # schedule task
                self._write_tabbed('starting', _es6_cls, '=>', _es8_cls)
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
        self._write_tabbed('es6', PreprintViewEs6, _es6_pview_count)
        self._write_tabbed('es6', PreprintDownloadEs6, _es6_pdownload_count)
        self._write_tabbed('es6', CountedUsageEs6, _es6_usage_event_count)
        self._write_tabbed('es6', '(total to migrate)', _es6_count)
        self._write_tabbed('es8', es8_metrics.OsfCountedUsageRecord, _es8_count, style=self._eq_style(_es8_count, _es6_count))
        if start:  # schedule (per-day?) tasks (if --start)
            self.stdout.write(f'starting usages => {es8_metrics.OsfCountedUsageRecord}')
            # TODO: migrate_usage_events.apply_async(...)
        self.stdout.write('---')

    def _handle_usage_reports(self, *, start: bool):
        # display counts of reports and distinct items
        _es6_count, _es6_item_count = _es6_usage_report_counts()
        _es8_count, _es8_item_count = _es8_usage_report_counts()
        self._write_tabbed('es6', es6_reports.PublicItemUsageReport, _es6_count)
        self._write_tabbed('es8', es8_metrics.PublicItemUsageReportEs8, _es8_count, style=self._eq_style(_es8_count, _es6_count))
        self._write_tabbed('es6', es6_reports.PublicItemUsageReport, '(items)', _es6_item_count)
        self._write_tabbed('es8', es8_metrics.PublicItemUsageReportEs8, '(items)', _es8_item_count,
                           style=self._eq_style(_es8_item_count, _es6_item_count))
        # (if --start) schedule task per item (by composite agg on es6 public usage reports)
        # each item-task iter thru reports oldest to newest, adding cumulative counts
        if start:  # schedule per-item tasks
            self.stdout.write(f'starting per-item {es6_reports.PublicItemUsageReport} => {es8_metrics.PublicItemUsageReportEs8}')
            # TODO: migrate_usage_events.apply_async(...)
        self.stdout.write('---')

    def _display_started_at(self, start):
        _started_at = es8_metrics.Elastic6To8State.get_started_at()
        if _started_at:
            self.stdout.write(
                f'osf.metrics 6->8 migration started previously, at {_started_at.isoformat()}'
            )
        elif start:
            _started_at = es8_metrics.Elastic6To8State.set_started_at_now()
            self.stdout.write(
                f'osf.metrics 6->8 migration starting now, at {_started_at.isoformat()}'
            )
        else:
            self.stdout.write(
                'osf.metrics 6->8 migration not started nor starting (run with `--start` to start)'
            )
        self.stdout.write('---')

    def _clear_state(self):
        es8_metrics.Elastic6To8State.search().delete()

    def _eq_style(self, num: int, should_be: int):
        return self.style.SUCCESS if (num == should_be) else self.style.NOTICE

    def _write_tabbed(self, *strables, style=None):
        def _to_str(strable):
            if isinstance(strable, type):
                return strable.__name__
            return str(strable)
        self.stdout.write('\t'.join(map(_to_str, strables)), style)

    def _quiet_chatty_loggers(self):
        _chatty_loggers = [
            'elasticsearch',
            'elastic_transport',
            'elasticsearch_metrics',
        ]
        for logger_name in _chatty_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
