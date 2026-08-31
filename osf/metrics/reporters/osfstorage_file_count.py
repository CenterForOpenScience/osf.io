import collections.abc as cabc
import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum

from osf.models import (
    AbstractNode,
    FileVersion,
    Preprint,
    SpamStatus,
)
from osf.metrics.daily_reports import DailyOsfstorageFileCountReport
from osf.metrics.monthly_reports import (
    BaseMonthlyReport,
    MonthlyOsfstorageFileCountReport,
)
from osf.metrics.utils import cycle_coverage_date
from ._base import (
    DailyReporter,
    MonthlyReporter,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def osfstorage_file_qs(node_queryset, preprint_queryset, *, created_before=None, only_public=False):
    """get a queryset for non-deleted osfstorage files belonging to a public, non-spam osf object
    """
    from addons.osfstorage.models import OsfStorageFile
    if only_public:
        node_queryset = node_queryset.filter(is_public=True)
        preprint_queryset = Preprint.objects.can_view(base_queryset=preprint_queryset)
    if created_before:
        node_queryset = node_queryset.filter(created__lt=created_before)
        preprint_queryset = preprint_queryset.filter(created__lt=created_before)
    _target_node_q = Q(
        target_object_id__in=node_queryset.values('pk'),
        target_content_type=ContentType.objects.get_for_model(AbstractNode),
    )
    _target_preprint_q = Q(
        target_object_id__in=preprint_queryset.values('pk'),
        target_content_type=ContentType.objects.get_for_model(Preprint),
    )
    _file_qs = (
        OsfStorageFile.objects
        .filter(deleted__isnull=True, purged__isnull=True)
        .filter(_target_node_q | _target_preprint_q)
    )
    if created_before:
        _file_qs = _file_qs.filter(created__lt=created_before)
    return _file_qs


def sum_osfstorage_bytes(file_qs, *, created_before=None) -> int:
    _fileversion_qs = FileVersion.objects.filter(
        size__gt=0,
        purged__isnull=True,
        basefilenode__in=file_qs,
    )
    if created_before:
        _fileversion_qs = _fileversion_qs.filter(created__lt=created_before)
    return _fileversion_qs.aggregate(storage_bytes=Sum('size', default=0))['storage_bytes']


class MonthlyOsfstorageFileCountReporter(MonthlyReporter):
    """
    (note: this is a replacement for DailyOsfstorageFileCountReporter, with corrections)
    """
    def report(self, **report_kwargs) -> cabc.Iterator[BaseMonthlyReport]:
        # osfstorage files belong (via `target` relation) either to an AbstractNode
        # (registration, project, component...) or to a Preprint
        _month_end = self.yearmonth.month_end()
        _node_qs = (
            AbstractNode.objects
            .filter(deleted__isnull=True)
            .exclude(spam_status=SpamStatus.SPAM)
        )
        _preprint_qs = (
            Preprint.objects
            .filter(deleted__isnull=True)
            .exclude(spam_status=SpamStatus.SPAM)
        )
        _total_file_qs = osfstorage_file_qs(
            node_queryset=_node_qs,
            preprint_queryset=_preprint_qs,
            created_before=_month_end,
        )
        _public_file_qs = osfstorage_file_qs(
            node_queryset=_node_qs,
            preprint_queryset=_preprint_qs,
            created_before=_month_end,
            only_public=True,
        )
        _new_public_file_qs = _public_file_qs.filter(
            created__gte=self.yearmonth.month_start(),
        )
        yield MonthlyOsfstorageFileCountReport(
            report_yearmonth=self.yearmonth,
            total_file_count=_total_file_qs.count(),
            total_file_bytes=sum_osfstorage_bytes(_total_file_qs, created_before=_month_end),
            public_file_count=_public_file_qs.count(),
            public_file_bytes=sum_osfstorage_bytes(_public_file_qs, created_before=_month_end),
            new_public_file_count=_new_public_file_qs.count(),
            new_public_file_bytes=sum_osfstorage_bytes(_new_public_file_qs, created_before=_month_end),
        )


class OsfstorageFileCountReporter(DailyReporter):
    """NOTE: prefer MonthlyOsfstorageFileCountReporter -- this daily reporter should be phased out"""

    def report(self, date):
        from addons.osfstorage.models import OsfStorageFile

        file_qs = OsfStorageFile.objects
        abstract_node_content_type = ContentType.objects.get_for_model(AbstractNode)
        preprint_content_type = ContentType.objects.get_for_model(Preprint)

        public_query = Q(
            target_object_id__in=AbstractNode.objects.filter(is_public=True).values('id'),
            target_content_type__in=[abstract_node_content_type, preprint_content_type],
        )

        private_query = Q(
            target_object_id__in=AbstractNode.objects.filter(is_public=False).values('id'),
            target_content_type__in=[abstract_node_content_type, preprint_content_type],
        )

        daily_query = Q(created__date=date)

        yield DailyOsfstorageFileCountReport(
            cycle_coverage=cycle_coverage_date(date),
            files=dict(
                total=file_qs.count(),
                public=file_qs.filter(public_query).count(),
                private=file_qs.filter(private_query).count(),
                total_daily=file_qs.filter(daily_query).count(),
                public_daily=file_qs.filter(public_query & daily_query).count(),
                private_daily=file_qs.filter(private_query & daily_query).count(),
            ),
        )
