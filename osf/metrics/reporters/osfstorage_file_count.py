from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import logging

from osf.metrics.reports import OsfstorageFileCountReport, FileRunningTotals
from osf.models import AbstractNode, Preprint
from ._base import DailyReporter
from osf.metrics.es8_metrics import (
    OsfstorageFileCountReportEs8,
    FileRunningTotals as FileRunningTotalsEs8
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class OsfstorageFileCountReporter(DailyReporter):

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

        reports = []

        report_es8 = OsfstorageFileCountReportEs8(
            cycle_coverage=f"{date:%Y.%m.%d}",
            files=FileRunningTotalsEs8(
                total=file_qs.count(),
                public=file_qs.filter(public_query).count(),
                private=file_qs.filter(private_query).count(),
                total_daily=file_qs.filter(daily_query).count(),
                public_daily=file_qs.filter(public_query & daily_query).count(),
                private_daily=file_qs.filter(private_query & daily_query).count(),
            ),
        )
        reports.append(report_es8)

        report = OsfstorageFileCountReport(
            report_date=date,
            files=FileRunningTotals(
                total=report_es8.files.total,
                public=report_es8.files.public,
                private=report_es8.files.private,
                total_daily=report_es8.files.total_daily,
                public_daily=report_es8.files.public_daily,
                private_daily=report_es8.files.private_daily,
            ),
        )
        reports.append(report)

        return reports
