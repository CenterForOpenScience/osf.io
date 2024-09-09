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
    UNIQUE_TOGETHER_FIELDS = ('report_date',)  # override in subclasses for multiple reports per day

    report_date = metrics.Date(format='strict_date', required=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert 'report_date' in cls.UNIQUE_TOGETHER_FIELDS, f'DailyReport subclasses must have "report_date" in UNIQUE_TOGETHER_FIELDS (on {cls.__qualname__}, got {cls.UNIQUE_TOGETHER_FIELDS})'

    class Meta:
        abstract = True
        dynamic = metrics.MetaField('strict')
        source = metrics.MetaField(enabled=True)


class YearmonthField(metrics.Date):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, format='strict_year_month')

    def deserialize(self, data):
        if isinstance(data, YearMonth):
            return data
        elif isinstance(data, str):
            return YearMonth.from_str(data)
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return YearMonth.from_date(data)
        elif data is None:
            return None
        else:
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
    UNIQUE_TOGETHER_FIELDS = ('report_yearmonth',)  # override in subclasses for multiple reports per month

    report_yearmonth = YearmonthField(required=True)

    class Meta:
        abstract = True
        dynamic = metrics.MetaField('strict')
        source = metrics.MetaField(enabled=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert 'report_yearmonth' in cls.UNIQUE_TOGETHER_FIELDS, f'MonthlyReport subclasses must have "report_yearmonth" in UNIQUE_TOGETHER_FIELDS (on {cls.__qualname__}, got {cls.UNIQUE_TOGETHER_FIELDS})'


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
    user_name = metrics.Text()
    department_name = metrics.Text()
    month_last_login = YearmonthField()
    account_creation_date = YearmonthField()
    orcid_id = metrics.Keyword()
    # counts:
    public_project_count = metrics.Integer()
    private_project_count = metrics.Integer()
    public_registration_count = metrics.Integer()
    embargoed_registration_count = metrics.Integer()
    published_preprint_count = metrics.Integer()
    public_file_count = metrics.Integer()
    storage_byte_count = metrics.Integer()
