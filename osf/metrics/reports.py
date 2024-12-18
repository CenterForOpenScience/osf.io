from __future__ import annotations
from collections import abc
import datetime

from django.dispatch import receiver
from elasticsearch6_dsl import InnerDoc
from elasticsearch_metrics import metrics
from elasticsearch_metrics.signals import pre_save as metrics_pre_save

from osf.metrics.utils import stable_key, YearMonth


class ReportInvalid(Exception):
    """Tried to save a report with invalid something-or-other
    """
    pass


class DailyReport(metrics.Metric):
    """DailyReport (abstract base for report-based metrics)

    There's something we'd like to know about every so often,
    so let's regularly run a report and stash the results here.
    """
    UNIQUE_TOGETHER_FIELDS: tuple[str, ...] = ('report_date',)  # override in subclasses for multiple reports per day

    report_date = metrics.Date(format='strict_date', required=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert 'report_date' in cls.UNIQUE_TOGETHER_FIELDS, f'DailyReport subclasses must have "report_date" in UNIQUE_TOGETHER_FIELDS (on {cls.__qualname__}, got {cls.UNIQUE_TOGETHER_FIELDS})'

    def save(self, *args, **kwargs):
        if self.timestamp is None:
            self.timestamp = datetime.datetime(
                self.report_date.year,
                self.report_date.month,
                self.report_date.day,
                tzinfo=datetime.UTC,
            )
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        dynamic = metrics.MetaField('strict')
        source = metrics.MetaField(enabled=True)


class YearmonthField(metrics.Date):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, format='strict_year_month')

    def deserialize(self, data):
        if isinstance(data, int):
            # elasticsearch stores dates in milliseconds since the unix epoch
            _as_datetime = datetime.datetime.fromtimestamp(data // 1000)
            return YearMonth.from_date(_as_datetime)
        elif data is None:
            return None
        try:
            return YearMonth.from_any(data)
        except ValueError:
            raise ValueError(f'unsure how to deserialize "{data}" (of type {type(data)}) to YearMonth')

    def serialize(self, data):
        if isinstance(data, str):
            return data
        elif isinstance(data, YearMonth):
            return str(data)
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return str(YearMonth.from_date(data))
        elif data is None:
            return None
        else:
            raise ValueError(f'unsure how to serialize "{data}" (of type {type(data)}) as YYYY-MM')


class MonthlyReport(metrics.Metric):
    """MonthlyReport (abstract base for report-based metrics that run monthly)
    """
    UNIQUE_TOGETHER_FIELDS: tuple[str, ...] = ('report_yearmonth',)  # override in subclasses for multiple reports per month

    report_yearmonth = YearmonthField(required=True)

    class Meta:
        abstract = True
        dynamic = metrics.MetaField('strict')
        source = metrics.MetaField(enabled=True)

    @classmethod
    def most_recent_yearmonth(cls, base_search=None) -> YearMonth | None:
        _search = base_search or cls.search()
        _search = _search.update_from_dict({'size': 0})  # omit hits
        _search.aggs.bucket(
            'agg_most_recent_yearmonth',
            'terms',
            field='report_yearmonth',
            order={'_key': 'desc'},
            size=1,
        )
        _response = _search.execute()
        if not _response.aggregations:
            return None
        (_bucket,) = _response.aggregations.agg_most_recent_yearmonth.buckets
        return _bucket.key

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert 'report_yearmonth' in cls.UNIQUE_TOGETHER_FIELDS, f'MonthlyReport subclasses must have "report_yearmonth" in UNIQUE_TOGETHER_FIELDS (on {cls.__qualname__}, got {cls.UNIQUE_TOGETHER_FIELDS})'

    def save(self, *args, **kwargs):
        if self.timestamp is None:
            self.timestamp = YearMonth.from_any(self.report_yearmonth).month_start()
        super().save(*args, **kwargs)


@receiver(metrics_pre_save)
def set_report_id(sender, instance, **kwargs):
    try:
        _unique_together_fields = instance.UNIQUE_TOGETHER_FIELDS
    except AttributeError:
        pass
    else:
        # Set the document id to a hash of "unique together" fields
        # for "ON CONFLICT UPDATE" behavior -- if the document
        # already exists, it will be updated rather than duplicated.
        # Cannot detect/avoid conflicts this way, but that's ok.
        _key_values = []
        for _field_name in _unique_together_fields:
            _field_value = getattr(instance, _field_name)
            if not _field_value or (
                isinstance(_field_value, abc.Iterable) and not isinstance(_field_value, str)
            ):
                raise ReportInvalid(f'because "{_field_name}" is in {sender.__name__}.UNIQUE_TOGETHER_FIELDS, {sender.__name__}.{_field_name} MUST have a non-empty scalar value (got {_field_value} of type {type(_field_value)})')
            _key_values.append(_field_value)
        instance.meta.id = stable_key(*_key_values)


#### BEGIN reusable inner objects #####

class RunningTotal(InnerDoc):
    total = metrics.Integer()
    total_daily = metrics.Integer()

class FileRunningTotals(InnerDoc):
    total = metrics.Integer()
    public = metrics.Integer()
    private = metrics.Integer()
    total_daily = metrics.Integer()
    public_daily = metrics.Integer()
    private_daily = metrics.Integer()

class NodeRunningTotals(InnerDoc):
    total = metrics.Integer()
    total_excluding_spam = metrics.Integer()
    public = metrics.Integer()
    private = metrics.Integer()
    total_daily = metrics.Integer()
    total_daily_excluding_spam = metrics.Integer()
    public_daily = metrics.Integer()
    private_daily = metrics.Integer()

class RegistrationRunningTotals(InnerDoc):
    total = metrics.Integer()
    public = metrics.Integer()
    embargoed = metrics.Integer()
    embargoed_v2 = metrics.Integer()
    withdrawn = metrics.Integer()
    total_daily = metrics.Integer()
    public_daily = metrics.Integer()
    embargoed_daily = metrics.Integer()
    embargoed_v2_daily = metrics.Integer()
    withdrawn_daily = metrics.Integer()

##### END reusable inner objects #####


# TODO:
# class ActiveUsersReport(DailyReport):
#     past_day = metrics.Integer()
#     past_week = metrics.Integer()
#     past_30_days = metrics.Integer()
#     past_year = metrics.Integer()


class UsageByStorageAddon(InnerDoc):
    addon_shortname = metrics.Keyword()

    enabled_usersettings = metrics.Object(RunningTotal)
    linked_usersettings = metrics.Object(RunningTotal)
    deleted_usersettings = metrics.Object(RunningTotal)
    usersetting_links = metrics.Object(RunningTotal)

    connected_nodesettings = metrics.Object(RunningTotal)
    disconnected_nodesettings = metrics.Object(RunningTotal)
    deleted_nodesettings = metrics.Object(RunningTotal)


class StorageAddonUsage(DailyReport):
    usage_by_addon = metrics.Object(UsageByStorageAddon, multi=True)


class DownloadCountReport(DailyReport):
    daily_file_downloads = metrics.Integer()


class InstitutionSummaryReport(DailyReport):
    UNIQUE_TOGETHER_FIELDS = ('report_date', 'institution_id',)

    institution_id = metrics.Keyword()
    institution_name = metrics.Keyword()
    users = metrics.Object(RunningTotal)
    nodes = metrics.Object(NodeRunningTotals)
    projects = metrics.Object(NodeRunningTotals)
    registered_nodes = metrics.Object(RegistrationRunningTotals)
    registered_projects = metrics.Object(RegistrationRunningTotals)


class NewUserDomainReport(DailyReport):
    UNIQUE_TOGETHER_FIELDS = ('report_date', 'domain_name',)

    domain_name = metrics.Keyword()
    new_user_count = metrics.Integer()


class NodeSummaryReport(DailyReport):
    nodes = metrics.Object(NodeRunningTotals)
    projects = metrics.Object(NodeRunningTotals)
    registered_nodes = metrics.Object(RegistrationRunningTotals)
    registered_projects = metrics.Object(RegistrationRunningTotals)


class OsfstorageFileCountReport(DailyReport):
    files = metrics.Object(FileRunningTotals)


class PreprintSummaryReport(DailyReport):
    UNIQUE_TOGETHER_FIELDS = ('report_date', 'provider_key',)

    provider_key = metrics.Keyword()
    preprint_count = metrics.Integer()


class UserSummaryReport(DailyReport):
    active = metrics.Integer()
    deactivated = metrics.Integer()
    merged = metrics.Integer()
    new_users_daily = metrics.Integer()
    new_users_with_institution_daily = metrics.Integer()
    unconfirmed = metrics.Integer()


class SpamSummaryReport(MonthlyReport):
    node_confirmed_spam = metrics.Integer()
    node_confirmed_ham = metrics.Integer()
    node_flagged = metrics.Integer()
    registration_confirmed_spam = metrics.Integer()
    registration_confirmed_ham = metrics.Integer()
    registration_flagged = metrics.Integer()
    preprint_confirmed_spam = metrics.Integer()
    preprint_confirmed_ham = metrics.Integer()
    preprint_flagged = metrics.Integer()
    user_marked_as_spam = metrics.Integer()
    user_marked_as_ham = metrics.Integer()


class InstitutionalUserReport(MonthlyReport):
    UNIQUE_TOGETHER_FIELDS = ('report_yearmonth', 'institution_id', 'user_id',)
    institution_id = metrics.Keyword()
    # user info:
    user_id = metrics.Keyword()
    user_name = metrics.Keyword()
    department_name = metrics.Keyword()
    month_last_login = YearmonthField()
    month_last_active = YearmonthField()
    account_creation_date = YearmonthField()
    orcid_id = metrics.Keyword()
    # counts:
    public_project_count = metrics.Integer()
    private_project_count = metrics.Integer()
    public_registration_count = metrics.Integer()
    embargoed_registration_count = metrics.Integer()
    published_preprint_count = metrics.Integer()
    public_file_count = metrics.Long()
    storage_byte_count = metrics.Long()


class InstitutionMonthlySummaryReport(MonthlyReport):
    UNIQUE_TOGETHER_FIELDS = ('report_yearmonth', 'institution_id', )
    institution_id = metrics.Keyword()
    user_count = metrics.Integer()
    public_project_count = metrics.Integer()
    private_project_count = metrics.Integer()
    public_registration_count = metrics.Integer()
    embargoed_registration_count = metrics.Integer()
    published_preprint_count = metrics.Integer()
    storage_byte_count = metrics.Long()
    public_file_count = metrics.Long()
    monthly_logged_in_user_count = metrics.Long()
    monthly_active_user_count = metrics.Long()


class PublicItemUsageReport(MonthlyReport):
    UNIQUE_TOGETHER_FIELDS = ('report_yearmonth', 'item_osfid')

    # where noted, fields are meant to correspond to defined terms from COUNTER
    # https://cop5.projectcounter.org/en/5.1/appendices/a-glossary-of-terms.html
    # https://coprd.countermetrics.org/en/1.0.1/appendices/a-glossary.html
    item_osfid = metrics.Keyword()                    # counter:Item (or Dataset)
    item_type = metrics.Keyword(multi=True)           # counter:Data-Type
    provider_id = metrics.Keyword(multi=True)         # counter:Database(?)
    platform_iri = metrics.Keyword(multi=True)        # counter:Platform

    # view counts include views on components or files contained by this item
    view_count = metrics.Long()                       # counter:Total Investigations
    view_session_count = metrics.Long()               # counter:Unique Investigations

    # download counts of this item only (not including contained components or files)
    download_count = metrics.Long()                   # counter:Total Requests
    download_session_count = metrics.Long()           # counter:Unique Requests

    @classmethod
    def for_last_month(cls, item_osfid: str) -> PublicItemUsageReport | None:
        _search = (
            PublicItemUsageReport.search()
            .filter('term', item_osfid=item_osfid)
            # only last month's report
            .filter('range', report_yearmonth={
                'gte': 'now-2M/M',
                'lt': 'now/M',
            })
            .sort('-report_yearmonth')
            [:1]
        )
        _response = _search.execute()
        return _response[0] if _response else None


class PrivateSpamMetricsReport(MonthlyReport):
    node_oopspam_flagged = metrics.Integer()
    node_oopspam_hammed = metrics.Integer()
    node_akismet_flagged = metrics.Integer()
    node_akismet_hammed = metrics.Integer()
    preprint_oopspam_flagged = metrics.Integer()
    preprint_oopspam_hammed = metrics.Integer()
    preprint_akismet_flagged = metrics.Integer()
    preprint_akismet_hammed = metrics.Integer()
