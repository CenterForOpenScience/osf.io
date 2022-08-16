from __future__ import absolute_import

from datetime import date

import requests

from django.db import transaction
from api.base.utils import waterbutler_api_url_for
from osf.models import ExportDataRestore
from celery.contrib.abortable import AbortableTask
from framework.celery_tasks import app as celery_app


@celery_app.task(bind=True, base=AbortableTask)
def pre_restore_export_data(self, cookie, institution_guid, source_id, export_id, destination_id):
    # Try to add new process record to DB
    # export_data_restore = ExportDataRestore(status="Running")
    # export_data_restore.save()

    # Get export file (export_data_{institution_guid}_{yyyymmddhhMMSS}.json)
    export_file_path = "/export_data_{institution_guid}_{timestamp}.json".format(institution_guid=institution_guid,
                                                                                 timestamp=date.today().strftime("%Y%m%d%H%M%S"))
    export_file_url = waterbutler_api_url_for(institution_guid, "S3", path=export_file_path, cookie=cookie)
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

    # export_data_restore = ExportDataRestore(status="Stopped")
    # export_data_restore.save()
    # return "The export data files are corrupted"

    # Check whether the restore destination storage is not empty
    destination_storage_check_api = waterbutler_api_url_for(destination_id, "S3", path="/", cookie=cookie)
    res = requests.head(destination_storage_check_api)
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
    return self.restore_export_data(cookie, institution_guid, source_id, export_id, destination_id)


@celery_app.task(bind=True, base=AbortableTask)
def restore_export_data(self, cookie, institution_guid, source_id, export_id, destination_id):
    # Check destination storage type

    # If destination storage is add-on institutional storage,
    # move all old data in restore destination storage to a folder to backup (such as '_backup' folder)

    with transaction.atomic():
        # Get file which have same information between export data and database
        # File info file: file_info_{institution_guid}_{yyyymmddhhMMSS}.json
        info_file_path = "/file_info_{institution_guid}_{timestamp}.json".format(institution_guid=institution_guid,
                                                                                 timestamp=date.today().strftime("%Y%m%d%H%M%S"))
        info_file_url = waterbutler_api_url_for(institution_guid, "S3", path=info_file_path, cookie=cookie)
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
            # TODO: Get path from file
            file_path = "/"

            # Add matched file information to related tables

            # Download file from source storage
            download_api = waterbutler_api_url_for(source_id, "S3", path=file_path, cookie=cookie)
            res = requests.get(download_api)

            # Prepare file name and file path for uploading

            # Upload downloaded file to destination storage
            upload_api = waterbutler_api_url_for(destination_id, "S3", path=file_path, cookie=cookie)
            res = requests.put(upload_api)

        # Update process data with process_end timestamp
        # Update process data with "Completed" status
        # export_data_restore = ExportDataRestore(status="Completed")
        # export_data_restore.save()

    return 'Done'
