# -*- coding: utf-8 -*-
import copy
import inspect  # noqa
import logging
import os
import time
import traceback
from celery import states
from celery.contrib.abortable import AbortableAsyncResult, ABORTED
from celery.exceptions import Ignore, CeleryError
from celery.result import AsyncResult
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import authentication as drf_authentication
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from requests.exceptions import ReadTimeout, ConnectionError

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import tasks
from osf.models import Institution, ExportDataLocation, ExportData
from website.util import inspect_info  # noqa
from .location import ExportStorageLocationViewBaseView
from ..utils import write_json_file

logger = logging.getLogger(__name__)
TASK_NO_WORKING_STATES = [
    states.SUCCESS,
    states.FAILURE,
    states.REVOKED,
    states.IGNORED,
    states.REJECTED,
]
MSG_EXPORT_DENY_PERM_INST = f'Permission denied for this institution'
MSG_EXPORT_DENY_PERM_STORAGE = f'Permission denied for this storage'
MSG_EXPORT_DENY_PERM_LOCATION = f'Permission denied for this export storage location'
MSG_EXPORT_DUP_IN_SECOND = f'The equivalent process is running'
MSG_EXPORT_ABORTED = f'The export data process is aborted'
MSG_EXPORT_REMOVED = f'The export data process is removed'
MSG_EXPORT_UNSTOPPABLE = f'Cannot stop this export process'
MSG_EXPORT_UNABORTABLE = f'Cannot abort this export process'
MSG_EXPORT_DENY_PERM = f'Permission denied for this export process'
MSG_EXPORT_COMPLETED = f'The data export process is successfully completed'
MSG_EXPORT_STOPPED = f'The data export process is successfully stopped'
MSG_EXPORT_FORCE_STOPPED = (f'The export data process is stopped'
                            f' without completely deleting the export data file')
MSG_EXPORT_FAILED_UPLOAD_TO_LOCATION = f'Cannot create folder or upload file to the export storage location'
# the delta seconds between call check data function
# it is used to avoid too many check calls in a short period of time
CHECK_DATA_INTERVAL_MIN_SECS = 10
MSG_EXPORT_INVALID_INPUT = f'The input data must be a integer'
MSG_EXPORT_MISSING_REQUIRED_INPUT = f'The required input data is missing'
MSG_EXPORT_NOT_EXIST_INPUT = f'The data for input value is not exist'


class ExportDataTaskException(CeleryError):
    pass


def get_task_result(result):
    task_result = {}
    if isinstance(result, dict):
        task_result = result
    elif isinstance(result, str) or isinstance(result, Exception):
        task_result = {'message': str(result)}

    return task_result


class ExportDataBaseActionView(ExportStorageLocationViewBaseView, APIView):
    raise_exception = True
    parser_classes = (JSONParser,)
    authentication_classes = (
        drf_authentication.SessionAuthentication,
    )

    def extract_input(self, request, *args, **kwargs):
        try:
            institution_id = request.data.get('institution_id')
            source_id = request.data.get('source_id')
            location_id = request.data.get('location_id')

            if (not institution_id or not source_id or not location_id):
                return self.response_render({
                    'message': MSG_EXPORT_MISSING_REQUIRED_INPUT
                }, status_code=status.HTTP_400_BAD_REQUEST)

            if (not Institution.objects.filter(pk=int(institution_id), is_deleted=False).exists()
                    or not Region.objects.filter(pk=int(source_id)).exists()
                    or not ExportDataLocation.objects.filter(pk=int(location_id)).exists()):
                return self.response_render({
                    'message': MSG_EXPORT_NOT_EXIST_INPUT
                }, status_code=status.HTTP_404_NOT_FOUND)

            # admin isn't affiliated with this institution
            if not (request.user.is_super_admin
                    or (request.user.is_staff
                        and request.user.is_affiliated_with_institution_id(institution_id))):
                return self.response_render({
                    'message': MSG_EXPORT_DENY_PERM_INST
                }, status_code=status.HTTP_403_FORBIDDEN)

            institution = Institution.objects.get(pk=institution_id)

            # this institutional storage is not allowed
            if not institution.is_allowed_institutional_storage_id(source_id):
                return self.response_render({
                    'message': MSG_EXPORT_DENY_PERM_STORAGE
                }, status_code=status.HTTP_403_FORBIDDEN)

            source_storage = Region.objects.get(pk=source_id)

            # this storage location is not allowed
            if not institution.have_allowed_storage_location_id(location_id):
                return self.response_render({
                    'message': MSG_EXPORT_DENY_PERM_LOCATION
                }, status_code=status.HTTP_403_FORBIDDEN)

            location = ExportDataLocation.objects.get(pk=location_id)

            return institution, source_storage, location
        except ValueError:
            return self.response_render({
                'message': MSG_EXPORT_INVALID_INPUT
            }, status_code=status.HTTP_400_BAD_REQUEST)

    def response_render(self, data, status_code):
        """render json response instance of rest framework"""
        response = Response(data=data, status=status_code)
        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = 'application/json'
        response.renderer_context = {}
        response.render()

        return response


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ExportDataActionView(ExportDataBaseActionView):

    def post(self, request, *args, **kwargs):
        input_set = self.extract_input(request)
        if isinstance(input_set, Response):
            return input_set
        institution, source_storage, location = input_set

        storage_credentials = source_storage.waterbutler_credentials['storage']
        source_waterbutler_credentials = None
        if storage_credentials and 'host' in storage_credentials:
            source_waterbutler_credentials = {
                'host': storage_credentials['host'],
            }

        # Create new process record
        try:
            export_data = ExportData.objects.create(
                source=source_storage,
                location=location,
                status=ExportData.STATUS_PENDING,
                creator=request.user,
                source_name=f'{source_storage.name} ({source_storage.provider_full_name})',
                source_waterbutler_credentials=source_waterbutler_credentials,
                source_waterbutler_settings=source_storage.waterbutler_settings
            )
        except IntegrityError:
            return Response({
                'message': MSG_EXPORT_DUP_IN_SECOND
            }, status=status.HTTP_400_BAD_REQUEST)

        # create a new task
        cookies = request.COOKIES
        cookie = request.user.get_or_create_cookie().decode()
        task = tasks.run_export_data_process.delay(
            cookies, export_data.id, location.id, source_storage.id, cookie=cookie)
        # try to replace by the exporting task
        export_data_set = ExportData.objects.filter(pk=export_data.id)
        export_data_set.update(
            task_id=task.task_id
        )
        export_data = export_data_set.first()

        return Response({
            'task_id': task.task_id,
            'task_state': task.state,
            'result': get_task_result(task.result),
            'status': export_data.status,
        }, status=status.HTTP_200_OK)


def check_export_data_process_status(
        _prev_time, task_id, export_data_id=None, location_id=None, source_id=None, is_force=False
):
    drift_seconds = time.time() - _prev_time
    # If is_force=True -> check
    # or If drift_seconds >= interval -> check
    if not is_force and drift_seconds < CHECK_DATA_INTERVAL_MIN_SECS:
        return _prev_time

    _check_time = time.time()

    # check if the export storage location / the export storage destination is deleted
    if location_id and not ExportDataLocation.objects.filter(pk=location_id).exists():
        raise ExportDataTaskException(MSG_EXPORT_REMOVED)
    # check if the institutional storage / the export storage source is deleted
    if source_id and not Region.objects.filter(pk=source_id).exists():
        raise ExportDataTaskException(MSG_EXPORT_REMOVED)
    # check if the export data record is deleted
    # * with cascading deletion, the export data record is deleted accordingly
    #   according to the parent object
    if export_data_id and not ExportData.objects.filter(pk=export_data_id).exists():
        raise ExportDataTaskException(MSG_EXPORT_REMOVED)

    # check if the task is aborted (can be 'Stop Export Data')
    task = AbortableAsyncResult(task_id)
    if task and task.is_aborted():
        raise ExportDataTaskException(MSG_EXPORT_ABORTED)

    return _check_time


def export_data_process(task, cookies, export_data_id, location_id, source_id, **kwargs):
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))
    _start_time = time.time()
    task_id = task.request.id
    try:
        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _start_time, task_id, export_data_id, location_id, source_id, True)
        # get corresponding export data record to update
        export_data = ExportData.objects.get(pk=export_data_id)

        # start process - update record in DB
        export_data.task_id = task.request.id
        export_data.status = ExportData.STATUS_RUNNING
        export_data.save()
        logger.info(f'Export process status is changed to {export_data.status}.')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        # extract file information
        _step_start_time = time.time()
        export_data_json, file_info_json = export_data.extract_file_information_json_from_source_storage()
        logger.info(f'Extracted file information.'
                    f' ({time.time() - _step_start_time}s)')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        # create export data process folder
        logger.debug(f'creating export data process folder')
        _step_start_time = time.time()
        response = export_data.create_export_data_folder(cookies, **kwargs)
        if not task.is_aborted() and response.status_code != 201:
            raise ExportDataTaskException(MSG_EXPORT_FAILED_UPLOAD_TO_LOCATION)
        logger.info(f'Created \'{export_data.export_data_folder_path}\' folder path.'
                    f' ({time.time() - _step_start_time}s)')

        # temporary file
        temp_file_path = export_data.export_data_temp_file_path
        logger.debug(f'created temporary file')

        if task.is_aborted():  # check before each steps
            raise ExportDataTaskException(MSG_EXPORT_ABORTED)
        # create files' information file
        logger.debug(f'creating files information file')
        write_json_file(file_info_json, temp_file_path)
        response = export_data.upload_file_info_full_data_file(cookies, temp_file_path, **kwargs)
        if not task.is_aborted() and response.status_code not in [201, 204]:
            raise ExportDataTaskException(MSG_EXPORT_FAILED_UPLOAD_TO_LOCATION)
        logger.debug(f'created files information file')

        # export target file and accompanying data

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        # create 'files' folder
        logger.debug(f'creating files folder')
        _step_start_time = time.time()
        response = export_data.create_export_data_files_folder(cookies, **kwargs)
        if not task.is_aborted() and response.status_code != 201:
            raise ExportDataTaskException(MSG_EXPORT_FAILED_UPLOAD_TO_LOCATION)
        logger.info(f'Created \'{export_data.export_data_files_folder_path}\' folder path.'
                    f' ({time.time() - _step_start_time}s)')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        logger.debug(f'prepare list of file versions data to upload')
        _step_start_time = time.time()
        file_versions = export_data.get_source_file_versions_min(file_info_json)
        _length = len(file_versions)
        logger.info(f'There is {_length} file versions needed to upload to the export storage destination.'
                    f' ({time.time() - _step_start_time}s)')

        # upload file versions
        logger.debug(f'upload file versions')
        _step_start_time = time.time()
        # cached the filename in hash value
        created_filename_list = []
        files_versions_not_found = {}
        for index, file in enumerate(file_versions):
            project_id, provider, file_path, version, file_name, file_id = file
            logger.debug(f'[{1 + index}/{_length}] file: '
                         f'projects/{project_id}/providers/{provider}/files/{file_id}/versions/{version}/'
                         f'?hash={file_name}&path={file_path}')

            # prevent uploading duplicate file_name in hash value
            if file_name in created_filename_list:
                logger.debug(f'Ignore uploaded file')
                continue

            # [Important] check process status before each step
            _prev_time = check_export_data_process_status(
                _prev_time, task_id, export_data_id, location_id, source_id)

            _up_file_start_time = time.time()
            kwargs.update({'version': version})
            # copy data file from source storage to location storage

            try:
                response = export_data.copy_export_data_file_to_location(
                    cookies, project_id, provider, file_path, file_name, **kwargs)
                # 201: created -> update cache list
                if response.status_code == 201:
                    created_filename_list.append(file_name)
                    logger.debug(f'Upload file successfully.'
                                 f' ({time.time() - _up_file_start_time}s)')
                else:
                    if file_id not in files_versions_not_found:
                        files_versions_not_found[file_id] = [version]
                    else:
                        files_versions_not_found[file_id].append(version)
                    logger.debug(f'File upload failed.'
                                 f' ({time.time() - _up_file_start_time}s)')
                    continue
            except (ReadTimeout, ConnectionError):
                logger.error(f'Timeout exception occurs. Add file_id to list failed files. file_id: {file_id}')
                if file_id not in files_versions_not_found:
                    files_versions_not_found[file_id] = [version]
                else:
                    files_versions_not_found[file_id].append(version)
                continue
        logger.info(f'Have gone through the entire list of file versions.'
                    f' ({time.time() - _step_start_time}s)')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        # Separate the failed file list from the file_info_json
        logger.debug('Separate the failed file list from the file_info_json')
        _step_start_time = time.time()
        files = file_info_json.get('files', [])
        files_not_found, sub_size, sub_files_numb = separate_failed_files(files, files_versions_not_found)
        export_data_json['size'] -= sub_size
        export_data_json['files_numb'] -= sub_files_numb
        logger.info(f'Separated the failed file list from the file_info_json.')
        logger.info(f'Uploaded {_length - sub_files_numb}/{_length} file versions.'
                    f' Failed {sub_files_numb} file versions.'
                    f' ({time.time() - _step_start_time}s)')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        # temporary file
        # temp_file_path = export_data.export_data_temp_file_path

        # create files' information JSON file
        logger.debug(f'creating files information JSON file')
        _step_start_time = time.time()
        write_json_file(file_info_json, temp_file_path)
        response = export_data.upload_file_info_file(cookies, temp_file_path, **kwargs)
        if not task.is_aborted() and response.status_code not in [201, 204]:
            raise ExportDataTaskException(MSG_EXPORT_FAILED_UPLOAD_TO_LOCATION)
        logger.info(f'Created files information JSON file.'
                    f' ({time.time() - _step_start_time}s)')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        # create export data JSON file
        logger.debug(f'creating export data JSON file')
        _step_start_time = time.time()
        process_end = timezone.make_naive(timezone.now(), timezone.utc)
        export_data_json['process_end'] = process_end.strftime('%Y-%m-%d %H:%M:%S')
        write_json_file(export_data_json, temp_file_path)
        response = export_data.upload_export_data_file(cookies, temp_file_path, **kwargs)
        if not task.is_aborted() and response.status_code != 201:
            raise ExportDataTaskException(MSG_EXPORT_FAILED_UPLOAD_TO_LOCATION)
        logger.info(f'Created export data JSON file.'
                    f' ({time.time() - _step_start_time}s)')

        # remove temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.debug(f'removed temporary file')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)
        # get corresponding export data record to update
        export_data = ExportData.objects.get(pk=export_data_id)

        # ignore condition `if export_data.status == ExportData.STATUS_RUNNING:`
        # complete process - update record in DB
        export_data.status = ExportData.STATUS_COMPLETED
        export_data.process_end = process_end
        export_data.export_file = export_data.get_export_data_file_path()
        export_data.project_number = export_data_json.get('projects_numb', 0)
        export_data.file_number = export_data_json.get('files_numb', 0)
        export_data.total_size = export_data_json.get('size', 0)
        export_data.save()
        logger.info(f'Export process status is changed to {export_data.status}.')

        institution_guid = export_data_json.get('institution').get('guid')
        return {
            'message': MSG_EXPORT_COMPLETED,
            'export_data_id': export_data.id,
            'export_data_status': export_data.status,
            'list_file_info_export_not_found': files_not_found,
            'file_name_export_fail':
                f'failed_files_export_{institution_guid}_{export_data.process_start_timestamp}.csv',
        }
    except Exception as e:
        logger.error(f'Exception {e}')
        # terminate process
        # export_data_task = AbortableAsyncResult(task_id)
        # export_data_task.abort()
        kwargs['is_rollback'] = True
        kwargs['export_data_task'] = task_id
        export_data_rollback_process(
            task, cookies, export_data_id, location_id, source_id, **kwargs)


def separate_failed_files(files, files_versions_not_found):
    files_not_found = []
    for file_id, ver_ids in files_versions_not_found.items():
        # empty ver_ids
        is_no_ver_ids = not ver_ids
        if is_no_ver_ids:
            continue

        idx, file = next(
            ((idx, _file) for idx, _file in enumerate(files) if file_id == _file['id']),
            (None, None)  # default
        )
        # file isn't found
        if file is None:
            continue

        # move all file versions
        versions = file.get('version', [])
        is_no_versions = not versions
        versions_ids_set = set([_ver['identifier'] for _ver in versions])
        is_same_ver_ids = versions_ids_set == set(ver_ids)
        if is_no_versions or is_same_ver_ids:
            files_not_found.append(files.pop(idx))
            continue

        # move some versions
        file_cop = copy.copy(file)
        file_cop['version'] = [_ver for _ver in file_cop['version'] if _ver['identifier'] in ver_ids]
        # not match any file versions
        if not file_cop['version']:
            continue
        files_not_found.append(file_cop)
        file['version'] = [_ver for _ver in versions if _ver['identifier'] not in ver_ids]

    # size and number of files are subtracted
    sub_size = sub_files_numb = 0
    for file in files_not_found:
        sub_size += sum([ver.get('size') for ver in file['version']])
        sub_files_numb += len(file.get('version', []))

    return files_not_found, sub_size, sub_files_numb


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class StopExportDataActionView(ExportDataBaseActionView):

    def post(self, request, **kwargs):
        input_set = self.extract_input(request)
        if isinstance(input_set, Response):
            return input_set
        institution, source_storage, location = input_set

        task_id = request.data.get('task_id')

        # get corresponding export data record
        export_data_set = ExportData.objects.filter(source=source_storage, location=location, task_id=task_id)
        if not task_id or not export_data_set.exists():
            return Response({
                'task_id': task_id,
                'message': MSG_EXPORT_NOT_EXIST_INPUT
            }, status=status.HTTP_404_NOT_FOUND)

        export_data = export_data_set.first()
        export_data_task = AbortableAsyncResult(task_id)
        # if tasks are finished
        if export_data_task.state in TASK_NO_WORKING_STATES:
            return Response({
                'task_id': task_id,
                'task_state': export_data_task.state,
                'status': export_data.status,
                'message': MSG_EXPORT_UNSTOPPABLE
            }, status=status.HTTP_400_BAD_REQUEST)

        # Abort the corresponding task_id
        export_data_task.abort()
        # task.revoke(terminate=True)
        if export_data_task.state != ABORTED:
            return Response({
                'task_id': task_id,
                'task_state': export_data_task.state,
                'status': export_data.status,
                'message': MSG_EXPORT_UNABORTABLE
            }, status=status.HTTP_400_BAD_REQUEST)

        # Delete export data file which created on the export process
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES
        task = tasks.run_export_data_rollback_process.delay(
            cookies, export_data.id, location.id, source_storage.id, cookie=cookie, export_data_task=task_id)

        # try to replace by the stopping task
        export_data = ExportData.objects.get(pk=export_data.id)
        export_data.task_id = task.task_id
        export_data.save()

        return Response({
            'task_id': task.task_id,
            'task_state': task.state,
            'result': get_task_result(task.result),
            'status': export_data.status,
        }, status=status.HTTP_200_OK)


def export_data_rollback_process(task, cookies, export_data_id, location_id, source_id, **kwargs):
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))
    _start_time = time.time()
    task_id = task.request.id
    is_rollback = kwargs.get('is_rollback', False)
    try:
        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _start_time, task_id, export_data_id, location_id, source_id, True)
        # get corresponding export data record to update
        export_data = ExportData.objects.get(pk=export_data_id)

        # if export processes cannot be stopped
        if not is_rollback and export_data.status not in ExportData.EXPORT_DATA_STOPPABLE:
            logger.debug(MSG_EXPORT_UNSTOPPABLE)
            # ExportData.STATUS_ERROR is expected
            raise ExportDataTaskException(MSG_EXPORT_UNSTOPPABLE)

        # if an export process is stopped before rollback
        if is_rollback and export_data.status in [ExportData.STATUS_STOPPED]:
            # ExportData.STATUS_STOPPED is expected
            raise ExportDataTaskException(MSG_EXPORT_STOPPED)

        # start stopping export - update record in DB
        export_data.task_id = task.request.id
        export_data.status = ExportData.STATUS_STOPPING
        export_data.save()
        logger.info(f'Export process status is changed to {export_data.status}.')

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)

        file_path = export_data.export_data_temp_file_path
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.debug(f'Removed temporary file.')

        # delete export data file
        logger.debug(f'deleting export data file')
        _step_start_time = time.time()
        response = export_data.delete_export_data_folder(cookies, **kwargs)
        if response.status_code != 204:
            _msg = MSG_EXPORT_FORCE_STOPPED
            logger.info(f'Can not delete \'{export_data.export_data_folder_path}\' folder path.'
                        f' ({time.time() - _step_start_time}s)')
        else:
            _msg = MSG_EXPORT_STOPPED
            logger.info(f'Deleted \'{export_data.export_data_folder_path}\' folder path.'
                        f' ({time.time() - _step_start_time}s)')

        if is_rollback:
            # ExportData.STATUS_ERROR is expected
            raise ExportDataTaskException(_msg)

        # [Important] check process status before each step
        _prev_time = check_export_data_process_status(
            _prev_time, task_id, export_data_id, location_id, source_id)
        # get corresponding export data record to update
        export_data = ExportData.objects.get(pk=export_data_id)

        # stop export - update record in DB
        export_data.status = ExportData.STATUS_STOPPED
        export_data.process_end = timezone.make_naive(timezone.now(), timezone.utc)
        export_data.export_file = None
        export_data.save()
        logger.info(f'Export process status is changed to {export_data.status}.')

        export_data_task_id = kwargs.get('export_data_task')
        export_data_task = AsyncResult(export_data_task_id)
        return {
            'message': _msg,
            'export_data_id': export_data_id,
            'export_data_task_id': export_data_task_id,
            'export_data_status': export_data.status,
            'export_data_task_result': get_task_result(export_data_task.result),
        }
    except Exception as e:
        logger.error(f'Exception {e}')
        # terminate process

        task_meta = {
            'exc_type': type(e).__name__,
            'exc_message': str(e),
            'export_data_id': export_data_id,
            'export_data_task_id': kwargs.get('export_data_task'),
        }
        if not isinstance(e, ExportDataTaskException):
            task_meta['traceback'] = traceback.format_exc().split('\n')

        export_data_set = ExportData.objects.filter(pk=export_data_id)
        if export_data_set.exists():
            export_data = export_data_set.first()
            # Stop export can be finished before the export's rollback process
            if export_data.status not in [ExportData.STATUS_STOPPED]:
                export_data.status = ExportData.STATUS_ERROR
                export_data.process_end = timezone.make_naive(timezone.now(), timezone.utc)
                export_data.save()
            logger.info(f'Export process status is changed to {export_data.status}.')
            task_meta['export_data_status'] = export_data.status

        task.update_state(state=states.FAILURE, meta=task_meta)
        raise Ignore(str(e))


class CheckStateExportDataActionView(ExportDataBaseActionView):

    def post(self, request, **kwargs):
        input_set = self.extract_input(request)
        if isinstance(input_set, Response):
            return input_set
        institution, source_storage, location = input_set

        task_id = request.data.get('task_id')

        # get corresponding export data record
        export_data_set = ExportData.objects.filter(source=source_storage, location=location, task_id=task_id)
        if not task_id or not export_data_set.exists():
            return Response({
                'message': MSG_EXPORT_NOT_EXIST_INPUT
            }, status=status.HTTP_404_NOT_FOUND)

        export_data = export_data_set.first()
        task = AbortableAsyncResult(task_id)

        return Response({
            'task_id': task_id,
            'task_state': task.state,
            'result': get_task_result(task.result),
            'status': export_data.status,
        }, status=status.HTTP_200_OK)


class CheckDataExportDataActionView(ExportDataBaseActionView):

    def post(self, request, **kwargs):
        input_set = self.extract_input(request)
        if isinstance(input_set, Response):
            return input_set
        institution, source_storage, location = input_set

        has_data = ExportData.objects.filter(
            location=location,
            source=source_storage,
            status__in=ExportData.EXPORT_DATA_AVAILABLE,
            is_deleted=False
        ).exists()

        return Response({
            'has_data': has_data,
        }, status=status.HTTP_200_OK)


class CheckRunningExportActionView(ExportDataBaseActionView):

    def post(self, request, **kwargs):
        input_set = self.extract_input(request)
        if isinstance(input_set, Response):
            return input_set
        institution, source_storage, location = input_set

        running_export = ExportData.objects.filter(
            location=location,
            source=source_storage,
            status=ExportData.STATUS_RUNNING,
            is_deleted=False
        )
        task_id = None
        if len(running_export) != 0:
            task_id = running_export[0].task_id

        return Response({
            'task_id': task_id,
        }, status=status.HTTP_200_OK)
