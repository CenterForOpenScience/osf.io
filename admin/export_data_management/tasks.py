from __future__ import absolute_import

from datetime import date

import requests

from django.db import transaction
from api.base.utils import waterbutler_api_url_for
# from osf.models import ExportDataRestore
from celery.contrib.abortable import AbortableTask
from framework.celery_tasks import app as celery_app


@celery_app.task(bind=True, base=AbortableTask)
def pre_restore_export_data(self, source_id, export_id, destination_id):
    # Try to add new process record to DB
    # export_data_restore = ExportDataRestore(status="Running")
    # export_data_restore.save()

    # Get export file (export_data_{institution_guid}_{yyyymmddhhMMSS}.json)
    export_file = "export_data_{export_id}_{timestamp}.json".format(export_id=export_id, timestamp=date.today())
    export_file_url = waterbutler_api_url_for(export_file, provider="S3")
    res = requests.get(export_file_url)
    response_body = res.content
    if res.status_code != 200:
        # Error
        print("Error: ", response_body)
        # export_data_restore = ExportDataRestore(status="Stopped")
        # export_data_restore.save()
        return "Cannot connect to the export data storage location"

    # Validate schema
    # {
    #     "institution": {
    #         "institution_id": 3,
    #         "institution_guid": "tiqr",
    #         "institution_name": "GakuNin RDM IdP"
    #     },
    #     "export_start": "2021-12-21T18:30:00",
    #     "export_end": "2021-12-21T19:30:00",
    #     "storage": {
    #         "name": "NII Storage",
    #         "type": "NII Storage"
    #     },
    #     "projects_numb": 1,
    #     "files_numb": 3,
    #     "size": 483,
    #     "file_path": "./"
    # }

    # return "The export data files are corrupted"

    # Check whether the restore destination storage is not empty
    destination_storage_check_api = waterbutler_api_url_for("*", provider="S3")
    res = requests.get(destination_storage_check_api)
    response_body = res.content
    if res.status_code != 200:
        # Error
        print("Error: ", response_body)
        # export_data_restore = ExportDataRestore(status="Stopped")
        # export_data_restore.save()
        return "Cannot connect to destination storage"

    data = response_body.data
    if len(data) != 0:
        # Show dialog
        return 'Open Dialog'

    # Start restore process
    return self.restore_export_data(source_id, export_id, destination_id)


@celery_app.task(bind=True, base=AbortableTask)
def restore_export_data(self, source_id, export_id, destination_id):
    # Check destination storage type

    # If destination storage is add-on institutional storage,
    # move all old data in restore destination storage to a folder to backup (such as '_backup' folder)

    with transaction.atomic():
        # Get file which have same information between export data and database
        # File info file: file_info_{institution_guid}_{yyyymmddhhMMSS}.json
        info_file = "file_info_{institution_guid}_{timestamp}.json".format(institution_guid=export_id,
                                                                           timestamp=date.today())
        info_file_url = waterbutler_api_url_for(info_file, provider="S3")
        res = requests.get(info_file_url)
        response_body = res.content
        if res.status_code != 200:
            # Error
            print("Error: ", response_body)
            # export_data_restore = ExportDataRestore(status="Stopped")
            # export_data_restore.save()
            return "Cannot get file infomation list"

        files = []
        for file in files:
            # Add matched file information to related tables

            # Download file from source storage
            download_api = waterbutler_api_url_for("*", provider="S3")
            res = requests.get(download_api)

            # Prepare file name and file path for uploading

            # Upload downloaded file to destination storage
            upload_api = waterbutler_api_url_for("*", provider="S3")
            res = requests.post(upload_api)

        # Update process data with process_end timestamp
        # Update process data with "Completed" status
        # export_data_restore = ExportDataRestore(status="Completed")
        # export_data_restore.save()

    return 'Done'
