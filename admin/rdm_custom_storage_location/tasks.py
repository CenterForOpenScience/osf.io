from __future__ import absolute_import

import requests

from django.db import transaction
from api.base.utils import waterbutler_api_url_for
from celery.contrib.abortable import AbortableTask
from framework.celery_tasks import app as celery_app
from osf.models import ExportData, ExportDataLocation, ExportDataRestore
from addons.osfstorage.models import Region
from website.settings import WATERBUTLER_URL

__all__ = [
    'check_before_restore_export_data',
    'restore_export_data',
]

@celery_app.task(bind=True, base=AbortableTask)
def check_before_restore_export_data(self, cookie, export_id, destination_id):
    # Try to add new process record to DB
    # export_data_restore = ExportDataRestore(export_id=export_id, destination_id=destination_id, status="Running", process_start=date.today())
    # export_data_restore.save()

    # Get export file (export_data_{institution_guid}_{yyyymmddhhMMSS}.json)
    export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
    export_base_url, export_settings, export_institution_guid = ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url', 'waterbutler_settings',
                                                                              'institution_guid')[0]
    export_provider = export_settings["storage"]["provider"]
    export_file_path = "/export_data_{institution_guid}_{timestamp}.json".format(institution_guid=export_institution_guid,
                                                                                 timestamp=export_data.modified.strftime(
                                                                                     "%Y%m%d%H%M%S"))
    internal = export_base_url == WATERBUTLER_URL
    export_file_url = waterbutler_api_url_for(export_institution_guid, export_provider, path=export_file_path, _internal=internal, meta="",
                                              base_url=export_base_url, cookie=cookie)
    response = requests.get(export_file_url)
    if response.status_code != 200:
        # Error
        print("Error: ", response.content)
        # export_data_restore.status = "Stopped"
        # export_data_restore.save()
        return "Cannot connect to the export data storage location"

    response_body = response.json()
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

    # export_data_restore.status = "Stopped"
    # export_data_restore.save()
    # return "The export data files are corrupted"

    # Check whether the restore destination storage is not empty
    destination_region = Region.objects.filter(id=destination_id)
    destination_base_url, destination_guid, destination_settings = destination_region.values_list("waterbutler_url", "_id", "waterbutler_settings")[0]
    destination_provider = destination_settings["storage"]["provider"]
    internal = destination_base_url == WATERBUTLER_URL
    destination_storage_check_api = waterbutler_api_url_for(destination_id, destination_provider, path="/", meta="", _internal=internal,
                                                            base_url=destination_base_url, cookie=cookie)
    response = requests.head(destination_storage_check_api)
    if response.status_code != 200:
        # Error
        print("Error: ", response.content)
        # export_data_restore.status = "Stopped"
        # export_data_restore.save()
        return "Cannot connect to destination storage"

    response_body = response.json()
    data = response_body.data
    if len(data) != 0:
        # Destination storage is not empty, show confirm dialog
        return 'Open Confirm Dialog'

    # Destination storage is empty, start restore process
    return restore_export_data(cookie, export_id, destination_id)


@celery_app.task(bind=True, base=AbortableTask)
def restore_export_data(self, cookie, export_id, destination_id):
    # Check destination storage type

    # If destination storage is add-on institutional storage,
    # move all old data in restore destination storage to a folder to backup (such as '_backup' folder)

    with transaction.atomic():
        # export_data_restore = ExportDataRestore.objects.get(export_id=export_id, destination_id=destination_id)
        # Get file which have same information between export data and database
        # File info file: file_info_{institution_guid}_{yyyymmddhhMMSS}.json
        export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
        export_base_url, export_settings, export_institution_guid = ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url', 'waterbutler_settings', 'institution_guid')[0]
        export_provider = export_settings["storage"]["provider"]
        file_info_path = "/file_info_{institution_guid}_{timestamp}.json".format(institution_guid=export_institution_guid,
                                                                                 timestamp=export_data.modified.strftime(
                                                                                     "%Y%m%d%H%M%S"))
        internal = export_base_url == WATERBUTLER_URL
        file_info_url = waterbutler_api_url_for(export_institution_guid, export_provider, path=file_info_path,
                                                _internal=internal, base_url=export_base_url, cookie=cookie)
        response = requests.get(file_info_url)
        if response.status_code != 200:
            # Error
            print("Error: ", response.content)
            # export_data_restore.status = "Stopped"
            # export_data_restore.save()
            return "Cannot get file infomation list"

        response_body = response.json()
        source_institution = response_body["institution"]
        source_id = source_institution["id"]
        files = response_body["files"]
        for file in files:
            file_path = file["path"]
            file_materialized_path = file["materialized_path"]

            # Add matched file information to related tables

            # Download file from source storage
            download_api = waterbutler_api_url_for(source_id, "S3", path=file_path, cookie=cookie)
            response = requests.get(download_api)

            # Prepare file name and file path for uploading

            # Upload downloaded file to destination storage
            upload_api = waterbutler_api_url_for(destination_id, "S3", path=file_path, cookie=cookie)
            response = requests.put(upload_api)

        # Update process data with process_end timestamp
        # Update process data with "Completed" status
        # export_data_restore.process_end = date.today()
        # export_data_restore.status = "Completed"
        # export_data_restore.save()

    return 'Done'

def rollback_restore(cookie, export_id, destination_id, transaction=None):
    # Rollback transaction
    if transaction is not None:
        transaction.set_rollback(True)

    # export_data_restore = ExportDataRestore.objects.get(export_id=export_id, destination_id=destination_id)

    # Rollback file movements
    # Get export data with the file information from the source storage via API call
    export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
    export_base_url, export_settings, export_institution_guid = ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url', 'waterbutler_settings', 'institution_guid')[0]
    export_provider = export_settings["storage"]["provider"]
    file_info_path = "/file_info_{institution_guid}_{timestamp}.json".format(institution_guid=export_institution_guid,
                                                                             timestamp=export_data.modified.strftime(
                                                                                 "%Y%m%d%H%M%S"))
    internal = export_base_url == WATERBUTLER_URL
    file_info_url = waterbutler_api_url_for(export_institution_guid, export_provider, path=file_info_path,
                                            _internal=internal, base_url=export_base_url, cookie=cookie)
    response = requests.get(file_info_url)
    if response.status_code != 200:
        # Error
        print("Error: ", response.content)
        # export_data_restore.status = "Stopped"
        # export_data_restore.save()
        return "Cannot get file infomation list"

    response_body = response.json()
    source_institution = response_body["institution"]
    source_id = source_institution["id"]
    files = response_body["files"]
    for file in files:
        file_path = file["path"]
        file_materialized_path = file["materialized_path"]
        # In add-on institutional storage: Delete files, except the backup folder.
        # In bulk-mounted institutional storage: Delete only files created during the restore process.
        delete_api = waterbutler_api_url_for(destination_id, "S3", path=file_path, cookie=cookie)
        response = requests.delete(delete_api)

    # If destination storage is add-on institutional storage
    # Move all files from the backup folder out
    # Delete the backup folder

    # export_data_restore.status = "Stopped"
    # export_data_restore.save()
    return 'Aborted'
