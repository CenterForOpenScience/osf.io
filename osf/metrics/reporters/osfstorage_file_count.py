from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import logging

from osf.metrics.reports import OsfstorageFileCountReport, FileRunningTotals
from osf.models import AbstractNode, Preprint
from ._base import DailyReporter


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

        report = OsfstorageFileCountReport(
            report_date=date,
            files=FileRunningTotals(
                total=file_qs.count(),
                public=file_qs.filter(public_query).count(),
                private=file_qs.filter(private_query).count(),
                total_daily=file_qs.filter(daily_query).count(),
                public_daily=file_qs.filter(public_query & daily_query).count(),
                private_daily=file_qs.filter(private_query & daily_query).count(),
            ),
        )

        return [report]

    def keen_events_from_report(self, report):
        event = {
            'osfstorage_files': report.files.to_dict(),
        }
        return {'file_summary': [event]}
