import collections
import datetime
import functools
import logging
from pprint import pprint

from django.core.management import call_command
from django.core.management.base import BaseCommand
from elasticsearch6 import helpers as es6_helpers
from elasticsearch8 import helpers as es8_helpers
from elasticsearch_metrics.registry import djelme_registry
from elasticsearch_metrics.imps import elastic8 as djel8me

from framework.celery_tasks import app as celery_app
from osf.metadata import rdfutils
from osf.metrics.preprint_metrics import (
    PreprintView as PreprintViewEs6,
    PreprintDownload as PreprintDownloadEs6,
)
from osf.metrics.counted_usage import CountedAuthUsage as CountedUsageEs6
from osf.metrics import reports as es6_reports
from osf.metrics import es8_metrics, RegistriesModerationMetrics
from osf.metrics.utils import YearMonth
from website import settings as website_settings


_logger = logging.getLogger(__name__)

###
# constants

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


###
# celery tasks


# TODO: @celery_app.task
def migrate_unchanged_recordtype(es6_recordtype_name: str):
    _es6_recordtype = djelme_registry.get_recordtype("osf", es6_recordtype_name)
    _es8_recordtype = _UNCHANGED_RECORDTYPES[_es6_recordtype]
    _assert_field_unchangedness(_es6_recordtype, _es8_recordtype)

    if issubclass(_es8_recordtype, djel8me.CyclicRecord):

        def _new_es8_record(source_dict):
            _kwargs = dict(_convert_cyclicrecord_kwargs(source_dict))
            return _es8_recordtype(**_kwargs)

    else:  # no conversion needed for event record with unchanged fields

        def _new_es8_record(source_dict):
            return _es8_recordtype(**source_dict)

    def _each_new():
        for _hit in _es6_scan_all(_es6_recordtype):
            yield _new_es8_record(_hit["_source"])

    _debug_migrate(_each_new())
    # TODO: _do_migrate(_es8_recordtype._get_connection(), _each_new())


# TODO: @celery_app.task
def migrate_counted_usages(from_when: str, until_when: str):
    # CountedAuthUsage => OsfCountedUsageRecord
    def _each_new():
        for _hit in _es6_scan_all(CountedUsageEs6, from_when, until_when):
            yield _convert_counted_usage(_hit["_source"])

    _debug_migrate(_each_new())


# TODO: @celery_app.task
def migrate_preprint_views(from_date: str, until_date: str):
    # convert to counted-usage
    ...


# TODO: @celery_app.task
def migrate_preprint_downloads(from_date: str, until_date: str):
    # convert to counted-usage
    ...


# TODO: @celery_app.task
def migrate_usage_reports(from_date, until_date):
    # from PublicItemUsageReport to PublicItemUsageReportEs8
    # add cumulative count
    ...


###
# various helper functions


def _delete_all(recordtype):
    # TODO: REMOVE THIS
    recordtype.search().query({"match_all": {}}).delete()
    recordtype.refresh()


def _delete_all_es8():
    # TODO: REMOVE THIS
    for _es8_recordtype in _UNCHANGED_RECORDTYPES.values():
        _delete_all(_es8_recordtype)
    _delete_all(es8_metrics.PublicItemUsageReportEs8)
    _delete_all(es8_metrics.OsfCountedUsageRecord)


def _debug_migrate(each_new):
    # TODO: remove this
    for _each in each_new:
        pprint(_each.to_dict())


def _do_migrate(es8_client, each_new):
    es8_helpers.bulk(es8_client, each_new, ..., stats_only=True)


def _date_range(
    range_start: datetime.date,
    range_end: datetime.date,
    step: datetime.timedelta = datetime.timedelta(days=1),
) -> collections.abc.Iterator[tuple[datetime.date, datetime.date]]:
    _from_date = range_start
    _until_date = range_start + step
    while _from_date < range_end:
        yield (_from_date, _until_date)
        (_from_date, _until_date) = (_until_date, _until_date + step)


def _es6_scan_all(es6_recordtype):
    return es6_helpers.scan(
        es6_recordtype._get_connection(),
        index=es6_recordtype._template_pattern,
    )


def _es6_scan_range(es6_recordtype, from_when: str, until_when: str):
    return es6_helpers.scan(
        es6_recordtype._get_connection(),
        index=es6_recordtype._template_pattern,
        query={"range": {"timestamp": {"gte": from_when, "lt": until_when}}},
    )


def _es6_usage_report_counts() -> tuple[int, int]:
    _search = es6_reports.PublicItemUsageReport.search()
    _search.aggs.metric(
        "agg_item_count",
        "cardinality",
        field="item_osfid",
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _total_count = _response.hits.total
    _item_count = (
        _response.aggregations.agg_item_count.value
        if "agg_item_count" in _response.aggregations
        else 0
    )
    return (_total_count, _item_count)


def _es8_usage_report_counts() -> tuple[int, int]:
    _search = es8_metrics.PublicItemUsageReportEs8.search()
    _search.aggs.metric(
        "agg_item_count",
        "cardinality",
        field="item_osfid",
        precision_threshold=_MAX_CARDINALITY_PRECISION,
    )
    _response = _search.execute()
    _total_count = _response.hits.total.value
    _item_count = (
        _response.aggregations.agg_item_count.value
        if "agg_item_count" in _response.aggregations
        else 0
    )
    return (_total_count, _item_count)


def _get_es6_field_names(es6_recordtype):
    """
    adapted from DocumentBase._get_field_names in elasticsearch8.dsl
    """
    for _field_name in es6_recordtype._doc_type.mapping:
        _field = es6_recordtype._doc_type.mapping[_field_name]
        if hasattr(_field, "_doc_class"):
            for _sub_field in _get_es6_field_names(_field._doc_class):
                yield f"{_field_name}.{_sub_field}"
        else:
            yield _field_name


def _assert_field_unchangedness(es6_recordtype, es8_recordtype):
    _es6_fields = set(_get_es6_field_names(es6_recordtype))
    _es8_fields = set(es8_recordtype._get_field_names())

    # remove fields intentionally removed/renamed in migration
    if issubclass(es6_recordtype, es6_reports.DailyReport):
        assert issubclass(es8_recordtype, djel8me.CyclicRecord)
        _es6_fields.remove("timestamp")
        _es6_fields.remove("report_date")
    elif issubclass(es6_recordtype, es6_reports.MonthlyReport):
        assert issubclass(es8_recordtype, djel8me.CyclicRecord)
        _es6_fields.remove("timestamp")
        _es6_fields.remove("report_yearmonth")
    else:
        assert issubclass(es8_recordtype, djel8me.EventRecord)

    # remove fields intentionally added in migration
    _es8_fields.remove("timeseries_timeparts")
    if issubclass(es8_recordtype, djel8me.CyclicRecord):
        _es8_fields.remove("created")
        _es8_fields.remove("cycle_coverage")

    # all remaining fields should match
    assert _es6_fields == _es8_fields


def _semverish_from_yearmonth(given_yearmonth: str):
    _ym = YearMonth.from_str(given_yearmonth)
    return f"{_ym.year}.{_ym.month}"


def _semverish_from_date(given_date: str):
    _d = datetime.date.fromisoformat(given_date)
    return f"{_d.year}.{_d.month}.{_d.day}"


def _convert_cyclicrecord_kwargs(es6_source: dict):
    for _key, _val in es6_source.items():
        if _key == "report_yearmonth":
            # report_yearmonth converts to cycle_coverage Y.M
            yield ("cycle_coverage", _semverish_from_yearmonth(_val))
        elif _key == "report_date":
            # report_date converts to cycle_coverage Y.M.D
            yield ("cycle_coverage", _semverish_from_date(_val))
        elif _key != "timestamp":
            # skipping timestamp; on daily/monthly reports just copied from yearmonth/date
            yield (_key, _val)


def _convert_counted_usage(source_dict) -> es8_metrics.OsfCountedUsageRecord:
    _item_iri = _iri_from_osfid(source_dict["item_guid"])
    return es8_metrics.OsfCountedUsageRecord(
        # fields from djelme.CountedUsageRecord
        timestamp=source_dict["timestamp"],
        sessionhour_id=source_dict["session_id"],
        platform_iri=source_dict["platform_iri"],
        # TODO: database_iri=provider iri
        item_iri=_item_iri,
        within_iris=[
            _item_iri,  # correct mistake; make inclusive-within aggregations easier
            *(
                _iri_from_osfid(_within_osfid)
                for _within_osfid in source_dict["surrounding_guids"]
            ),
        ],
        # fields from OsfCountedUsageRecord
        item_osfid=source_dict["item_guid"],
        item_type=_convert_item_type(source_dict),
        item_public=source_dict["item_public"],
        provider_id=source_dict["provider_id"],
        user_is_authenticated=source_dict["user_is_authenticated"],
        action_labels=source_dict["action_labels"],
        pageview_info=source_dict[
            "pageview_info"
        ],  # TODO: does this need the PageviewInfo object?
    )


def _iri_from_osfid(osfid: str) -> str:
    return f"{website_settings.DOMAIN}{osfid}"


def _convert_item_type(es6_usage_dict):
    """convert model-name item types to OSFMAP item types

    previous item_types use `type(osf_model).__name__.lower()`
    """
    _modelname = es6_usage_dict["item_type"]
    assert isinstance(_modelname, str)
    match _modelname:
        case "osfuser":
            return rdfutils.DCTERMS.Agent
        case "preprint":
            return rdfutils.OSF.Preprint
        case "registration":
            return (
                rdfutils.OSF.RegistrationComponent
                if es6_usage_dict.get("surrounding_guids")
                else rdfutils.OSF.Registration
            )
        case "node":
            return (
                rdfutils.OSF.ProjectComponent
                if es6_usage_dict.get("surrounding_guids")
                else rdfutils.OSF.Project
            )
        case _ if "file" in _modelname:
            return rdfutils.OSF.File
        case _:
            _logger.error(f"unknown item type: {_modelname}")
            return _modelname  # give up


###
# the command itself


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--no-setup",
            action="store_true",
        )
        parser.add_argument(
            "--clear-state",
            action="store_true",
        )
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

    def handle(
        self,
        *,
        start,
        unchanged,
        usage_events,
        usage_reports,
        clear_state,
        no_setup,
        **kwargs,
    ):
        self._quiet_chatty_loggers()
        if not no_setup:
            call_command("djelme_backend_setup")
        if clear_state:
            self._clear_state()
        self._check_started_at(start_now=start)
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
            self._write_tabbed("es6", _es6_cls, _es6_count)
            self._write_tabbed(
                "es8",
                _es8_cls,
                _es8_count,
                style=self._eq_style(_es8_count, _es6_count),
            )
            if start:  # schedule task
                self._write_tabbed("starting", _es6_cls, "=>", _es8_cls)
                migrate_unchanged_recordtype(_es6_cls.__name__)
                # TODO: migrate_unchanged_recordtype.apply_async(...)
            self.stdout.write("---")

    def _handle_usage_events(self, *, start: bool):
        # for counted-usage events:
        # TODO: last X months only
        # display counts for each view/download event type
        _es6_pview_count = PreprintViewEs6.search().count()
        _es6_pdownload_count = PreprintDownloadEs6.search().count()
        _es6_usage_event_count = CountedUsageEs6.search().count()
        _es6_count = _es6_pview_count + _es6_pdownload_count + _es6_usage_event_count
        _es8_count = es8_metrics.OsfCountedUsageRecord.search().count()
        self._write_tabbed("es6", PreprintViewEs6, _es6_pview_count)
        self._write_tabbed("es6", PreprintDownloadEs6, _es6_pdownload_count)
        self._write_tabbed("es6", CountedUsageEs6, _es6_usage_event_count)
        self._write_tabbed("es6", "(total to migrate)", _es6_count)
        self._write_tabbed(
            "es8",
            es8_metrics.OsfCountedUsageRecord,
            _es8_count,
            style=self._eq_style(_es8_count, _es6_count),
        )
        if start:  # schedule (per-day?) tasks (if --start)
            self.stdout.write(f"starting usages => {es8_metrics.OsfCountedUsageRecord}")
            _started = self._migration_started_at
            _range_start = (
                _started - datetime.timedelta(months=_USAGE_MONTHS_BACK)
            ).date
            _range_end = _started.date() + datetime.timedelta(days=1)
            for _from_date, _until_date in _date_range(_range_start, _range_end):
                _from_str = _from_date.isoformat()
                _until_str = _until_date.isoformat()
                # TODO: .apply_async(...)
                migrate_counted_usages(_from_str, _until_str)
                migrate_preprint_views(_from_str, _until_str)
                migrate_preprint_downloads(_from_str, _until_str)
        self.stdout.write("---")

    def _handle_usage_reports(self, *, start: bool):
        # display counts of reports and distinct items
        _es6_count, _es6_item_count = _es6_usage_report_counts()
        _es8_count, _es8_item_count = _es8_usage_report_counts()
        self._write_tabbed("es6", es6_reports.PublicItemUsageReport, _es6_count)
        self._write_tabbed(
            "es8",
            es8_metrics.PublicItemUsageReportEs8,
            _es8_count,
            style=self._eq_style(_es8_count, _es6_count),
        )
        self._write_tabbed(
            "es6", es6_reports.PublicItemUsageReport, "(items)", _es6_item_count
        )
        self._write_tabbed(
            "es8",
            es8_metrics.PublicItemUsageReportEs8,
            "(items)",
            _es8_item_count,
            style=self._eq_style(_es8_item_count, _es6_item_count),
        )
        # (if --start) schedule task per item (by composite agg on es6 public usage reports)
        # each item-task iter thru reports oldest to newest, adding cumulative counts
        if start:  # schedule per-item tasks
            self.stdout.write(
                f"starting per-item {es6_reports.PublicItemUsageReport} => {es8_metrics.PublicItemUsageReportEs8}"
            )
            # TODO: migrate_usage_reports.apply_async(...)
        self.stdout.write("---")

    @functools.cached_property
    def _migration_started_at(self):
        return es8_metrics.Elastic6To8State.get_started_at()

    def _check_started_at(self, start_now):
        _started_at = self._migration_started_at
        if _started_at:
            self.stdout.write(
                f"osf.metrics 6->8 migration started previously, at {_started_at.isoformat()}"
            )
        elif start_now:
            del self._migration_started_at  # clear cache
            _started_at = es8_metrics.Elastic6To8State.set_started_at_now()
            self.stdout.write(
                f"osf.metrics 6->8 migration starting now, at {_started_at.isoformat()}"
            )
        else:
            self.stdout.write(
                "osf.metrics 6->8 migration not started nor starting (run with `--start` to start)"
            )
        self.stdout.write("---")

    def _clear_state(self):
        self.stdout.write(
            "clearing all migration state (start time, etc)", self.style.NOTICE
        )
        es8_metrics.Elastic6To8State.search().query({"match_all": {}}).delete()
        es8_metrics.Elastic6To8State.refresh()
        # TODO: REMOVE THIS
        self.stdout.write("deleting all migration target data in es8", self.style.ERROR)
        _delete_all_es8()

    def _eq_style(self, num: int, should_be: int):
        return self.style.SUCCESS if (num == should_be) else self.style.WARNING

    def _write_tabbed(self, *strables, style=None):
        def _to_str(strable):
            if isinstance(strable, type):
                return strable.__name__
            return str(strable)

        self.stdout.write("\t".join(map(_to_str, strables)), style)

    def _quiet_chatty_loggers(self):
        _chatty_loggers = [
            "elasticsearch",
            "elastic_transport",
            "elasticsearch_metrics",
        ]
        for logger_name in _chatty_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
