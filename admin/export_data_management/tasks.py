from __future__ import absolute_import

import requests

from django.db import transaction
from api.base.utils import waterbutler_api_url_for
# from osf.models import ExportDataRestore
from celery.contrib.abortable import AbortableTask
from celery.app.task import Task
from framework.celery_tasks import app as celery_app


@celery_app.task(bind=True, base=AbortableTask)
def pre_restore_export_data(self, source_id, export_id, destination_id):
    with transaction.atomic():
        # Try to add new process record to DB
        # export_data_restore = ExportDataRestore(status="Running")
        # export_data_restore.save()

        # Get export file
        export_file_url = waterbutler_api_url_for("*", provider="S3")
        res = requests.get(export_file_url)

        response_body = res.content
        if res.status_code != 200:
            # Error
            print("Error: ", response_body)
            # export_data_restore = ExportDataRestore(status="Stopped")
            # export_data_restore.save()
            return

        # Validate schema

        # Check whether the restore destination storage is not empty
        destination_storage_check_api = waterbutler_api_url_for("*", provider="S3")
        res = requests.get(destination_storage_check_api)
        response_body = res.content
        if res.status_code != 200:
            # Error
            print("Error: ", response_body)
            # export_data_restore = ExportDataRestore(status="Stopped")
            # export_data_restore.save()
            return

        data = response_body.data
        if len(data) != 0:
            # Show dialog
            return 'Open Dialog'

        # Start restore process
        self.restore_export_data(source_id, export_id, destination_id)


def restore_export_data(self, source_id, export_id, destination_id):
    # TODO: Handle restoring export data
    # Check destination storage type
    # Get file which have same information between export data and database
    return
