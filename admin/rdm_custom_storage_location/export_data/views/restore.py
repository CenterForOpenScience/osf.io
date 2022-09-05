from __future__ import absolute_import

import logging
import json

from celery.contrib.abortable import AbortableAsyncResult
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import tasks

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location.export_data import utils

from django.db import transaction
from osf.models import ExportData, ExportDataLocation, ExportDataRestore, BaseFileNode
from django.utils import timezone

from website.settings import WATERBUTLER_URL

logger = logging.getLogger(__name__)
DATETIME_FORMAT = "%Y%m%dT%H%M%S"
NODE_ID = 'export_location'


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ExportDataRestoreView(RdmPermissionMixin, APIView):
    raise_exception = True

    def post(self, request, **kwargs):
        destination_id = request.POST.get('destination_id')
        export_id = self.kwargs.get('export_id')
        cookies = request.COOKIES
        is_from_confirm_dialog = request.POST.get('is_from_confirm_dialog', default=False)
        if destination_id is None or export_id is None:
            return Response({"error_message": f"Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)

        if not is_from_confirm_dialog:
            # Check the destination is available (not in restore process or checking restore data process)
            any_process_running = utils.check_any_running_restore_process(destination_id)
            if any_process_running:
                return Response({"error_message": f"Cannot restore in this time."}, status=status.HTTP_400_BAD_REQUEST)

            result = check_before_restore_export_data(cookies, export_id, destination_id)
            if result.get("open_dialog"):
                # If open_dialog is True, return HTTP 200 with empty response
                return Response({}, status=status.HTTP_200_OK)
            elif result.get("error_message"):
                # If there is error message, return HTTP 400
                return Response({'error_message': result.get("error_message")}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Otherwise, start restore data task and return task id
                # Recheck the destination is available (not in restore process or checking restore data process)
                any_process_running = utils.check_any_running_restore_process(destination_id)
                if any_process_running:
                    return Response({"error_message": f"Cannot restore in this time."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Try to add new process record to DB
                export_data_restore = ExportDataRestore(export_id=export_id, destination_id=destination_id,
                                                        status=ExportData.STATUS_RUNNING)
                export_data_restore.save()
                process = tasks.run_restore_export_data_process.delay(cookies, export_id, destination_id,
                                                                      export_data_restore.pk)
                export_data_restore.update(task_id=process.task_id)
                return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)
        else:
            # Check the destination is available (not in restore process or checking restore data process)
            any_process_running = utils.check_any_running_restore_process(destination_id)
            if any_process_running:
                return Response({"error_message": f"Cannot restore in this time."}, status=status.HTTP_400_BAD_REQUEST)

            # Try to add new process record to DB
            export_data_restore = ExportDataRestore(export_id=export_id, destination_id=destination_id,
                                                    status=ExportData.STATUS_RUNNING)
            export_data_restore.save()
            # If user clicked 'Restore' button in confirm dialog, start restore data task and return task id
            process = tasks.run_restore_export_data_process.delay(cookies, export_id, destination_id,
                                                                  export_data_restore.pk)
            export_data_restore.update(task_id=process.task_id)
            return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ExportDataStopRestoreView(RdmPermissionMixin, APIView):
    raise_exception = True

    def post(self, request, *args, **kwargs):
        task_id = request.POST.get('task_id')
        destination_id = request.POST.get('destination_id')
        export_id = self.kwargs.get('export_id')
        cookies = request.COOKIES

        if destination_id is None or export_id is None or task_id is None:
            return Response({"error_message": f"Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)

        # Rollback restore data
        try:
            export_data_restore = ExportDataRestore.objects.get(task_id=task_id)
        except Exception:
            return Response({"error_message": f"Cannot get export data restore info."}, status=status.HTTP_400_BAD_REQUEST)

        # Update process status
        export_data_restore.update(status=ExportData.STATUS_STOPPING)

        # Abort current task
        task = AbortableAsyncResult(task_id)
        result = task.result
        current_progress_step = result.get("current", -1)
        if current_progress_step == 3:
            return Response({"error_message": f"Cannot stop restore process."}, status=status.HTTP_400_BAD_REQUEST)
        task.abort()
        if task.state != 'ABORTED' and not task.is_aborted():
            return Response({"error_message": f"Cannot stop restore process."}, status=status.HTTP_400_BAD_REQUEST)
        # Rollback file movements
        process = restore_export_data_rollback_process.delay(cookies, export_id, destination_id, export_data_restore.pk,
                                                             current_progress_step)
        export_data_restore.update(task_id=task_id)
        # Get export data with the file information from the source storage via API call
        # Get file which have same information between export data and database
        # File info file: /export_{process_start}/file_info_{institution_guid}_{process_start}.json
        # export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
        # export_base_url, export_settings, export_institution_guid = \
        #     ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url',
        #                                                                               'waterbutler_settings',
        #                                                                               'institution_guid')[0]
        # export_provider = export_settings.get("storage", {}).get("provider")
        # file_info_path = f"/{export_data.get_file_info_file_path(export_institution_guid)}"
        # internal = export_base_url == WATERBUTLER_URL
        # try:
        #     response = utils.get_file_data(NODE_ID, export_provider, file_info_path, cookies, internal,
        #                                    export_base_url)
        #     if response.status_code != 200:
        #         # Error
        #         logger.error(f"Return error with response: {response.content}")
        #         return {"error_message": f"Cannot get file infomation list"}
        # except Exception as e:
        #     logger.error(f"Exception: {e}")
        #     return {"error_message": f"Cannot get file infomation list"}

        # response_body = response.content
        # response_file_content = response_body.decode('utf-8')

        # Validate file info schema
        # is_file_valid = utils.validate_file_json(response_file_content, "file-info-schema.json")
        # if not is_file_valid:
        #     return {"error_message": f"The export data files are corrupted"}
        return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


class ExportDataRestoreTaskStatusView(RdmPermissionMixin, APIView):
    def get(self, request, **kwargs):
        task_id = request.GET.get('task_id')
        if task_id is None:
            return Response({"error_message": f"Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)
        task = AbortableAsyncResult(task_id)
        response = {
            'state': task.state,
        }
        if task.result is not None:
            response = {
                'state': task.state,
                'result': task.result if isinstance(task.result, str) or isinstance(task.result, dict) else {},
            }
        return Response(response, status=status.HTTP_200_OK if task.state != 'FAILURE' else status.HTTP_400_BAD_REQUEST)


def check_before_restore_export_data(cookies, export_id, destination_id):
    # Get export file (/export_{process_start}/export_data_{institution_guid}_{process_start}.json)
    export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
    export_base_url, export_settings, export_institution_guid = \
        ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url',
                                                                                  'waterbutler_settings',
                                                                                  'institution_guid')[0]
    export_provider = export_settings.get("storage", {}).get("provider")
    export_file_path = f"/{export_data.get_export_data_file_path(export_institution_guid)}"
    internal = export_base_url == WATERBUTLER_URL
    try:
        response = utils.get_file_data(NODE_ID, export_provider, export_file_path, cookies, internal, export_base_url)
        if response.status_code != 200:
            # Error
            logger.error(f"Return error with response: {response.content}")
            return {'open_dialog': False, "error_message": f"Cannot connect to the export data storage location"}
        response_body = response.content
        response_file_content = response_body.decode('utf-8')
        response_file_json = json.loads(response_file_content)
    except Exception as e:
        logger.error(f"Exception: {e}")
        return {'open_dialog': False, "error_message": f"Cannot connect to the export data storage location"}

    # Validate export file schema
    is_file_valid = utils.validate_file_json(response_file_json, "export-data-schema.json")
    if not is_file_valid:
        return {'open_dialog': False, "error_message": f"The export data files are corrupted"}

    # Check whether the restore destination storage is not empty
    destination_region = Region.objects.filter(id=destination_id)
    destination_base_url, destination_settings = \
        destination_region.values_list("waterbutler_url", "waterbutler_settings")[0]
    destination_provider = destination_settings.get("storage", {}).get("provider")
    internal = destination_base_url == WATERBUTLER_URL
    try:
        response = utils.get_file_data(NODE_ID, destination_provider, "/", cookies, internal, destination_base_url,
                                       get_file_info=True)
        if response.status_code != 200:
            # Error
            logger.error(f"Return error with response: {response.content}")
            return {'open_dialog': False, "error_message": f"Cannot connect to destination storage"}

        response_body = response.json()
        data = response_body.get("data")
        if len(data) != 0:
            # Destination storage is not empty, show confirm dialog
            return {'open_dialog': True}
    except Exception as e:
        logger.error(f"Exception: {e}")
        return {'open_dialog': False, "error_message": f"Cannot connect to destination storage"}

    # Destination storage is empty, return False
    return {'open_dialog': False}


def restore_export_data_process(task, cookies, export_id, destination_id, export_data_restore_id):
    export_data_restore = ExportDataRestore.objects.get(pk=export_data_restore_id)
    current_process_step = 0
    task.update_state(state='PROGRESS',
                      meta={'current': current_process_step})
    try:
        # Check destination storage type (bulk-mounted or add-on)
        is_destination_addon_storage = utils.check_storage_type(destination_id)
        try:
            destination_region = Region.objects.filter(id=destination_id)
            destination_base_url, destination_guid, destination_settings = \
                destination_region.values_list("waterbutler_url", "_id", "waterbutler_settings")[0]
            destination_provider = destination_settings.get("storage", {}).get("provider")
            internal = destination_base_url == WATERBUTLER_URL

            check_if_restore_process_stopped(task, current_process_step)
            # move all old data in restore destination storage to a folder to back up folder
            if is_destination_addon_storage:
                response = utils.move_addon_folder_to_backup(NODE_ID, destination_provider,
                                                             process_start=export_data_restore.process_start.strftime(DATETIME_FORMAT),
                                                             cookies=cookies, internal=internal,
                                                             base_url=destination_base_url)
            else:
                response = utils.move_bulk_mount_folder_to_backup(NODE_ID, destination_provider,
                                                                  process_start=export_data_restore.process_start.strftime(DATETIME_FORMAT),
                                                                  cookies=cookies, internal=internal,
                                                                  base_url=destination_base_url)
            check_if_restore_process_stopped(task, current_process_step)
            current_process_step = 1
            task.update_state(state='PROGRESS',
                              meta={'current': current_process_step})
            if "error" in response:
                # Error
                logger.error(f"Return error with response: {response.get('error')}")
                restore_export_data_rollback_process(cookies, destination_id, export_data_restore_id,
                                                     current_process_step)
                return {"error_message": f""}
        except Exception as e:
            logger.error(f"Exception: {e}")
            restore_export_data_rollback_process(cookies, destination_id, export_data_restore_id, current_process_step)
            return {"error_message": f""}

        with transaction.atomic():
            # Get file which have same information between export data and database
            # File info file: /export_{process_start}/file_info_{institution_guid}_{process_start}.json
            export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
            export_base_url, export_settings, export_institution_guid = \
                ExportDataLocation.objects.filter(id=export_data.location_id).values_list('waterbutler_url',
                                                                                          'waterbutler_settings',
                                                                                          'institution_guid')[0]
            export_provider = export_settings.get("storage", {}).get("provider")
            file_info_path = f"/{export_data.get_file_info_file_path(export_institution_guid)}"
            internal = export_base_url == WATERBUTLER_URL
            try:
                response = utils.get_file_data(NODE_ID, export_provider, file_info_path, cookies, internal,
                                               export_base_url)
                if response.status_code != 200:
                    # Error
                    logger.error(f"Return error with response: {response.content}")
                    restore_export_data_rollback_process(cookies, destination_id, export_data_restore_id,
                                                         current_process_step)
                    return {"error_message": f"Cannot get file infomation list"}
            except Exception as e:
                logger.error(f"Exception: {e}")
                restore_export_data_rollback_process(cookies, destination_id, export_data_restore_id,
                                                     current_process_step)
                return {"error_message": f"Cannot get file infomation list"}

            response_body = response.content
            response_file_content = response_body.decode('utf-8')

            # Validate file info schema
            is_file_valid = utils.validate_file_json(response_file_content, "file-info-schema.json")
            if not is_file_valid:
                restore_export_data_rollback_process(cookies, destination_id, export_data_restore_id,
                                                     current_process_step)
                return {"error_message": f"The export data files are corrupted"}

            files = response_body.get("files", [])
            is_export_addon_storage = utils.check_storage_type(export_id)
            for file in files:
                check_if_restore_process_stopped(task, current_process_step)

                file_path = file.get("path")
                file_materialized_path = file.get("materialized_path")
                file_created_at = file.get("created_at")
                file_modified_at = file.get("modified_at")
                file_versions = file.get("version")
                file_node_id = file.get("project", {}).get("id")
                # Sort file by version id
                file_versions.sort(key=lambda k: k.get('identifier', 0))

                # Get file which have the following information that is the same between export data and database
                file_node = BaseFileNode.active.filter(path=file_path, materialzed_path=file_materialized_path,
                                                       created_at=file_created_at, modified_at=file_modified_at)
                if len(file_node) == 0:
                    # File not match with DB, pass this file
                    continue

                try:
                    for index, version in enumerate(file_versions):
                        check_if_restore_process_stopped(task, current_process_step)

                        # Prepare file name and file path for uploading
                        # If the destination storage is add-on institutional storage and export data storage is bulk-mounted storage:
                        # - for past version files, rename and save each version as filename_{version} in '_version_files' folder
                        # - the latest version is saved as the original
                        file_hash = version.get("metadata", {}).get("sha256")
                        if file_hash is None:
                            file_hash = version.get("metadata", {}).get("md5")
                        if file_hash is None:
                            # Cannot get path in export data storage, pass this file
                            continue

                        file_hash_path = f"/{export_data.export_data_folder_name}/{ExportData.EXPORT_DATA_FILES_FOLDER}/{file_hash}"
                        if is_destination_addon_storage and not is_export_addon_storage:
                            new_file_materialized_path = file_materialized_path
                            if len(file_materialized_path) > 0 and index < len(file_versions) - 1:
                                # for past version files, rename and save each version as filename_{version} in '_version_files' folder
                                path_splits = new_file_materialized_path.split("/")

                                # add _{version} to file name
                                file_name = path_splits[len(path_splits) - 1]
                                file_splits = file_name.split(".")
                                file_splits[0] = f"{file_splits[0]}_{version}"
                                versioned_file_name = ".".join(file_splits)

                                # add _version_files to folder path
                                path_splits.insert(len(path_splits) - 2, "_version_files")
                                path_splits[len(path_splits) - 1] = versioned_file_name
                                new_file_materialized_path = "/".join(path_splits)
                            new_file_path = new_file_materialized_path
                        else:
                            new_file_path = file_path if is_export_addon_storage else file_materialized_path

                        # Download file from export data storage by version then upload that file to destination storage
                        destination_region = Region.objects.filter(id=destination_id)
                        destination_base_url, destination_settings = \
                            destination_region.values_list("waterbutler_url", "waterbutler_settings")[0]
                        destination_provider = destination_settings.get("storage", {}).get("provider")
                        response_body = utils.download_then_upload_file(file_node_id, NODE_ID, export_provider,
                                                                        destination_provider, file_hash_path,
                                                                        new_file_path, cookies, export_base_url,
                                                                        destination_base_url, version)
                        if response_body is None:
                            continue

                        # Add additional file info to related table (tags, version, metadata,...)
                except Exception:
                    # Did not download or upload, pass this file
                    continue

            current_process_step = 2
            task.update_state(state='PROGRESS',
                              meta={'current': current_process_step})
            check_if_restore_process_stopped(task, 2)

            # Update process data with process_end timestamp and "Completed" status
            export_data_restore.update(process_end=timezone.now(), status=ExportData.STATUS_COMPLETED)

            current_process_step = 3
            task.update_state(state='PROGRESS',
                              meta={'current': current_process_step})
    except Exception as e:
        logger.error(f"Exception: {e}")
        restore_export_data_rollback_process(cookies, destination_id, export_data_restore_id, current_process_step)
        raise e

    return {}


def restore_export_data_rollback_process(cookies, destination_id, export_data_restore_id, process_step):
    export_data_restore = ExportDataRestore.objects.get(pk=export_data_restore_id)
    # Check destination storage type (bulk-mounted or add-on)
    is_destination_addon_storage = utils.check_storage_type(destination_id)

    destination_region = Region.objects.filter(id=destination_id)
    destination_base_url, destination_guid, destination_settings = \
        destination_region.values_list("waterbutler_url", "_id", "waterbutler_settings")[0]
    destination_provider = destination_settings.get("storage", {}).get("provider")
    internal = destination_base_url == WATERBUTLER_URL

    # Delete files, except the backup folder.
    if 0 < process_step <= 2:
        try:
            utils.delete_all_files_except_backup(NODE_ID, destination_provider, cookies, internal, destination_base_url)
        except Exception as e:
            logger.error(f"Exception: {e}")
            export_data_restore.update(status=ExportData.STATUS_STOPPED)
            return {"error_message": f"Cannot connect to destination storage"}

    # Move all files from the backup folder out and delete backup folder
    if 0 <= process_step <= 2:
        try:
            if is_destination_addon_storage:
                response = utils.move_addon_folder_from_backup(NODE_ID, destination_provider,
                                                               process_start=export_data_restore.process_start.strftime(
                                                                   DATETIME_FORMAT),
                                                               cookies=cookies, internal=internal,
                                                               base_url=destination_base_url)
            else:
                response = utils.move_bulk_mount_folder_from_backup(NODE_ID, destination_provider,
                                                                    process_start=export_data_restore.process_start.strftime(
                                                                        DATETIME_FORMAT),
                                                                    cookies=cookies, internal=internal,
                                                                    base_url=destination_base_url)
            if "error" in response:
                # Error
                logger.error(f"Return error with response: {response.get('error')}")
                export_data_restore.update(status=ExportData.STATUS_STOPPED)
                return {"error_message": f"Failed to move backup folder to root"}
        except Exception as e:
            logger.error(f"Exception: {e}")
            export_data_restore.update(status=ExportData.STATUS_STOPPED)
            return {"error_message": f"Failed to move backup folder to root"}

    export_data_restore.update(status=ExportData.STATUS_STOPPED)
    return {}


def check_if_restore_process_stopped(task, current):
    if task.is_aborted():
        task.update_state(state='ABORTED',
                          meta={'current': current})
        raise Exception('Restore process is stopped')
