from __future__ import absolute_import

import logging

import requests
import json
from celery.contrib.abortable import AbortableTask
from django.db import transaction
from django.utils import timezone

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location.export_data import serializers, utils
from admin.rdm_custom_storage_location.export_data.views.export import (
    export_data_process,
    export_data_rollback_process
)
from api.base.utils import waterbutler_api_url_for
from framework.celery_tasks import app as celery_app
from osf.models import ExportData, ExportDataLocation, ExportDataRestore
from osf.models.export_data import STATUS_RUNNING, STATUS_COMPLETED, STATUS_STOPPED
from addons.osfstorage.models import Region
from website.settings import WATERBUTLER_URL

__all__ = [
    'check_before_restore_export_data',
    'restore_export_data',
    'rollback_restore',
    'run_export_data_process',
]

logger = logging.getLogger(__name__)
DATETIME_FORMAT = "%Y%m%dT%H%M%S"
EXPORT_FILE_PATH = "/export_{source_id}_{process_start}/export_data_{institution_guid}_{process_start}.json"
EXPORT_FILE_INFO_PATH = "/export_{source_id}_{process_start}/file_info_{institution_guid}_{process_start}.json"


def check_before_restore_export_data(cookies, export_id, source_id, destination_id):
    # Get export file (/export_{process_start}/export_data_{institution_guid}_{process_start}.json)
    export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
    export_base_url, export_settings, export_institution_guid = ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url', 'waterbutler_settings', 'institution_guid')[0]
    export_provider = export_settings["storage"]["provider"]
    export_file_path = EXPORT_FILE_PATH.format(institution_guid=export_institution_guid, source_id=source_id,
                                               process_start=export_data.process_start.strftime(DATETIME_FORMAT))
    internal = export_base_url == WATERBUTLER_URL
    export_file_url = waterbutler_api_url_for('emx94', export_provider, path=export_file_path, _internal=internal,
                                              base_url=export_base_url)
    # export_file_url = waterbutler_api_url_for('emx94', "s3", path="/export_test/export_data_vcu.json",
    #                                           _internal=internal, base_url=export_base_url)
    try:
        response = requests.get(export_file_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies)
        if response.status_code != 200:
            # Error
            logger.error("Return error with response: {}".format(response.content))
            response.close()
            return {'open_dialog': False, "error_message": "Cannot connect to the export data storage location"}
    except Exception as e:
        logger.error("Exception: {}".format(e))
        response.close()
        return {'open_dialog': False, "error_message": "Cannot connect to the export data storage location"}

    response_body = response.content
    response_file_content = response_body.decode('utf-8')
    response.close()

    # Validate export file
    try:
        json_data = json.loads(response_file_content)
    except Exception as e:
        logger.error("Exception: {}".format(e))
        return {'open_dialog': False, "error_message": "The export data files are corrupted"}

    schema = serializers.ExportDataSerializer(data=json_data)
    if not schema.is_valid():
        return {'open_dialog': False, "error_message": "The export data files are corrupted"}

    # Check whether the restore destination storage is not empty
    destination_region = Region.objects.filter(id=destination_id)
    destination_base_url, destination_guid, destination_settings = destination_region.values_list("waterbutler_url", "_id", "waterbutler_settings")[0]
    destination_provider = destination_settings["storage"]["provider"]
    internal = destination_base_url == WATERBUTLER_URL
    destination_storage_check_api = waterbutler_api_url_for('emx94', destination_provider, path="/", meta="",
                                                            _internal=internal, base_url=destination_base_url)
    # destination_storage_check_api = waterbutler_api_url_for('emx94', "s3", path="/", meta="",
    #                                                         _internal=internal, base_url=destination_base_url)
    try:
        response = requests.get(destination_storage_check_api,
                                headers={'content-type': 'application/json'},
                                cookies=cookies)
        if response.status_code != 200:
            # Error
            logger.error("Return error with response: {}".format(response.content))
            response.close()
            return {'open_dialog': False, "error_message": "Cannot connect to destination storage"}
    except Exception as e:
        logger.error("Exception: {}".format(e))
        response.close()
        return {'open_dialog': False, "error_message": "Cannot connect to destination storage"}

    response_body = response.json()
    data = response_body["data"]
    response.close()
    if len(data) != 0:
        # Destination storage is not empty, show confirm dialog
        return {'open_dialog': True}

    # Destination storage is empty, return False
    return {'open_dialog': False}


@celery_app.task(bind=True, base=AbortableTask)
def restore_export_data(self, cookies, export_id, source_id, destination_id, export_data_restore_id):
    try:
        export_data_restore = ExportDataRestore.objects.get(id=export_data_restore_id)

        # Check destination storage type (bulk-mounted or add-on)
        is_addon_storage = utils.check_storage_type(destination_id)

        if is_addon_storage:
            logger.info("IS ADD-ON STORAGE")

            # If destination storage is add-on institutional storage,
            # move all old data in restore destination storage to a folder to back up (such as '_backup' folder)
            destination_region = Region.objects.filter(id=destination_id)
            destination_base_url, destination_guid, destination_settings = destination_region.values_list("waterbutler_url", "_id", "waterbutler_settings")[0]
            destination_provider = destination_settings["storage"]["provider"]
            internal = destination_base_url == WATERBUTLER_URL
            move_old_data_url = waterbutler_api_url_for('emx94', destination_provider, path="/", _internal=internal, base_url=destination_base_url)
            request_body = {
                "action": "move",
                "path": "/_backup/",
            }
            try:
                response = requests.post(move_old_data_url,
                                         headers={'content-type': 'application/json'},
                                         cookies=cookies,
                                         json=request_body)
                if response.status_code != 200 or response.status_code != 201:
                    # Error
                    logger.error("Return error with response: {}".format(response.content))
                    response.close()
                    export_data_restore.status = STATUS_STOPPED
                    export_data_restore.save()
                    return {"error_message": ""}
            except Exception as e:
                logger.error("Exception: {}".format(e))
                response.close()
                export_data_restore.status = STATUS_STOPPED
                export_data_restore.save()
                return {"error_message": ""}

        with transaction.atomic():
            # Get file which have same information between export data and database
            # File info file: /export_{process_start}/file_info_{institution_guid}_{process_start}.json
            export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
            export_base_url, export_settings, export_institution_guid = ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url', 'waterbutler_settings', 'institution_guid')[0]
            export_provider = export_settings["storage"]["provider"]
            file_info_path = EXPORT_FILE_INFO_PATH.format(
                institution_guid=export_institution_guid, source_id=source_id,
                process_start=export_data.process_start.strftime(DATETIME_FORMAT))
            internal = export_base_url == WATERBUTLER_URL
            file_info_url = waterbutler_api_url_for(export_institution_guid, export_provider, path=file_info_path,
                                                    _internal=internal, base_url=export_base_url)
            try:
                response = requests.get(file_info_url,
                                        headers={'content-type': 'application/json'},
                                        cookies=cookies)
                if response.status_code != 200:
                    # Error
                    logger.error("Return error with response: {}".format(response.content))
                    response.close()
                    export_data_restore.status = STATUS_STOPPED
                    export_data_restore.save()
                    return {"error_message": "Cannot get file infomation list"}
            except Exception as e:
                logger.error("Exception: {}".format(e))
                response.close()
                export_data_restore.status = STATUS_STOPPED
                export_data_restore.save()
                return {"error_message": "Cannot get file infomation list"}

            response_body = response.json()
            response.close()
            files = response_body["files"]
            for file in files:
                file_path = file["path"]
                file_materialized_path = file["materialized_path"]

                # Add matched file information to related tables


                # Download file from export data storage
                try:
                    download_api = waterbutler_api_url_for(export_id, "s3", path=file_path)
                    response = requests.get(download_api,
                                            headers={'content-type': 'application/json'},
                                            cookies=cookies)
                except Exception as e:
                    response.close()
                    raise e
                response.close()

                # Prepare file name and file path for uploading
                # If the destination storage is add-on institutional storage and source storage is bulk-mounted storage:
                # - for past version files, rename and save each version as filename_{version} in '_version_files' folder
                # - the latest version is saved as the original filename
                if is_addon_storage:
                    pass
                else:
                    pass

                # Upload downloaded file to destination storage
                try:
                    upload_api = waterbutler_api_url_for(destination_id, "s3", path=file_path)
                    response = requests.put(upload_api,
                                            headers={'content-type': 'application/json'},
                                            cookies=cookies)
                except Exception as e:
                    response.close()
                    raise e
                response.close()

            # Update process data with process_end timestamp and "Completed" status
            export_data_restore.process_end = timezone.now()
            export_data_restore.status = STATUS_COMPLETED
            export_data_restore.save()
    except Exception as e:
        logger.error("Exception: {}".format(e))
        export_data_restore = ExportDataRestore.objects.get(id=export_data_restore_id)
        export_data_restore.status = STATUS_STOPPED
        export_data_restore.save()
        raise e

    return {}


def rollback_restore(cookies, export_id, source_id, destination_id, export_data_restore_id=None, transaction=None):
    # Rollback transaction
    if transaction is not None:
        transaction.set_rollback(True)

    if export_data_restore_id is not None:
        try:
            export_data_restore = ExportDataRestore.objects.get(id = export_data_restore_id)
        except Exception as e:
            export_data_restore = ExportDataRestore.objects.get(export_id=export_id, destination_id=destination_id)
    else:
        export_data_restore = ExportDataRestore.objects.get(export_id=export_id, destination_id=destination_id)


    # Rollback file movements
    # Get export data with the file information from the source storage via API call
    export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
    export_base_url, export_settings, export_institution_guid = ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url', 'waterbutler_settings', 'institution_guid')[0]
    export_provider = export_settings["storage"]["provider"]
    file_info_path = EXPORT_FILE_INFO_PATH.format(
        institution_guid=export_institution_guid, source_id=source_id,
        process_start=export_data.modified.strftime(DATETIME_FORMAT))
    internal = export_base_url == WATERBUTLER_URL
    file_info_url = waterbutler_api_url_for(export_institution_guid, export_provider, path=file_info_path,
                                            _internal=internal, base_url=export_base_url)
    try:
        response = requests.get(file_info_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies)
        if response.status_code != 200:
            # Error
            logger.error("Return error with response: {}".format(response.content))
            response.close()
            export_data_restore.status = STATUS_STOPPED
            export_data_restore.save()
            return "Cannot get file infomation list"
    except Exception as e:
        logger.error("Exception: {}".format(e))
        response.close()
        export_data_restore.status = STATUS_STOPPED
        export_data_restore.save()
        return "Cannot get file infomation list"

    response_body = response.json()
    response.close()
    files = response_body["files"]

    # Check destination storage type (bulk-mounted or add-on)
    is_addon_storage = utils.check_storage_type(destination_id)

    for file in files:
        file_path = file["path"]
        file_materialized_path = file["materialized_path"]
        # In add-on institutional storage: Delete files, except the backup folder.
        # In bulk-mounted institutional storage: Delete only files created during the restore process.
        delete_api = waterbutler_api_url_for(destination_id, "S3", path=file_path)
        response = requests.delete(delete_api)
        response.close()

    # If destination storage is add-on institutional storage
    # Move all files from the backup folder out
    # Delete the backup folder

    export_data_restore.status = STATUS_STOPPED
    export_data_restore.save()
    return 'Stopped'


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_export_data_process(self, cookies, export_data_id, **kwargs):
    export_data_process(cookies, export_data_id, **kwargs)


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_export_data_rollback_process(self, cookies, export_data_id, **kwargs):
    export_data_rollback_process(cookies, export_data_id, **kwargs)
