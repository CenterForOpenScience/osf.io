# -*- coding: utf-8 -*-
import inspect  # noqa
import logging
import os
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
        institution_id = request.data.get('institution_id')
        source_id = request.data.get('source_id')
        location_id = request.data.get('location_id')

        # admin isn't affiliated with this institution
        if (not institution_id
                or not Institution.objects.filter(pk=institution_id).exists()
                or not (request.user.is_super_admin
                        or (request.user.is_staff
                            and request.user.is_affiliated_with_institution_id(institution_id)))):
            return self.response_render({
                'message': MSG_EXPORT_DENY_PERM_INST
            }, status_code=status.HTTP_400_BAD_REQUEST)

        institution = Institution.objects.get(pk=institution_id)

        # this institutional storage is not allowed
        if (not source_id
                or not Region.objects.filter(pk=source_id).exists()
                or not institution.is_allowed_institutional_storage_id(source_id)):
            return self.response_render({
                'message': MSG_EXPORT_DENY_PERM_STORAGE
            }, status_code=status.HTTP_400_BAD_REQUEST)

        source_storage = Region.objects.get(pk=source_id)

        # this storage location is not allowed
        if (not location_id
                or not ExportDataLocation.objects.filter(pk=location_id).exists()
                or not institution.have_allowed_storage_location_id(location_id)):
            return self.response_render({
                'message': MSG_EXPORT_DENY_PERM_LOCATION
            }, status_code=status.HTTP_400_BAD_REQUEST)

        location = ExportDataLocation.objects.get(pk=location_id)

        return institution, source_storage, location

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
        task = tasks.run_export_data_process.delay(cookies, export_data.id, cookie=cookie)
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


def export_data_process(task, cookies, export_data_id, **kwargs):
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))
    try:
        # get corresponding export data record
        export_data_set = ExportData.objects.filter(pk=export_data_id)
        export_data = export_data_set.first()

        if export_data is None:
            # missing info to create a new process
            raise ExportDataTaskException(MSG_EXPORT_REMOVED)

        # start process
        export_data.task_id = task.request.id
        export_data.status = ExportData.STATUS_RUNNING
        export_data.save()

        # extract file information
        export_data_json, file_info_json = export_data.extract_file_information_json_from_source_storage()

        if task.is_aborted():  # check before each steps
            raise ExportDataTaskException(MSG_EXPORT_ABORTED)
        # create export data process folder
        logger.debug(f'creating export data process folder')
        response = export_data.create_export_data_folder(cookies, **kwargs)
        if not task.is_aborted() and response.status_code != 201:
            kwargs['is_rollback'] = True
            return export_data_rollback_process(task, cookies, export_data_id, **kwargs)
        logger.debug(f'created export data process folder')

        # export target file and accompanying data
        if task.is_aborted():  # check before each steps
            raise ExportDataTaskException(MSG_EXPORT_ABORTED)
        # create 'files' folder
        logger.debug(f'creating files folder')
        response = export_data.create_export_data_files_folder(cookies, **kwargs)
        if not task.is_aborted() and response.status_code != 201:
            kwargs['is_rollback'] = True
            return export_data_rollback_process(task, cookies, export_data_id, **kwargs)
        logger.debug(f'created files folder')

        if task.is_aborted():  # check before each steps
            raise ExportDataTaskException(MSG_EXPORT_ABORTED)
        # upload file versions
        logger.debug(f'uploading file versions')
        file_versions = export_data.get_source_file_versions_min(file_info_json)
        # logger.debug(f'file_versions: {file_versions}')
        _length = len(file_versions)
        # cached the filename in hash value
        created_filename_list = []
        list_file_id_not_found = []
        institution_guid = ''
        if export_data_json and 'institution' in export_data_json:
            institution_guid = export_data_json.get('institution').get('guid')
        for index, file in enumerate(file_versions):
            logger.debug(f'[{1 + index}/{_length}] file: {file}')
            project_id, provider, file_path, version, file_name, file_id = file
            # prevent uploading duplicate file_name in hash value
            if file_name in created_filename_list:
                logger.debug(f'file created -> ignore')
                continue
            kwargs.update({'version': version})
            # kwargs.setdefault('version', version)
            if task.is_aborted():  # check before each steps
                raise ExportDataTaskException(MSG_EXPORT_ABORTED)
            # copy data file from source storage to location storage
            response = export_data.copy_export_data_file_to_location(
                cookies, project_id, provider, file_path, file_name, **kwargs)
            # 201: created -> update cache list
            if response.status_code == 201:
                created_filename_list.append(file_name)
            else:
                list_file_id_not_found.append(file_id)
                continue

        list_file_info_not_found = []
        if len(list_file_id_not_found) > 0:
            list_file_info = file_info_json.get('files', [])
            for index_file, file_info in enumerate(list_file_info):
                if file_info['id'] in list_file_id_not_found:
                    list_file_info_not_found.append(file_info)
                    export_data_json['size'] -= file_info.get('size')
                    export_data_json['files_numb'] -= len(file_info.get('version'))
            list_file_info = [d for d in list_file_info if d['id'] not in list_file_id_not_found]
            file_info_json['files'] = list_file_info
        logger.debug(f'uploaded file versions')

        # temporary file
        temp_file_path = export_data.export_data_temp_file_path

        if task.is_aborted():  # check before each steps
            raise ExportDataTaskException(MSG_EXPORT_ABORTED)
        # create files' information file
        logger.debug(f'creating files information file')
        write_json_file(file_info_json, temp_file_path)
        response = export_data.upload_file_info_file(cookies, temp_file_path, **kwargs)
        if not task.is_aborted() and response.status_code != 201:
            kwargs['is_rollback'] = True
            return export_data_rollback_process(task, cookies, export_data_id, **kwargs)
        logger.debug(f'created files information file')

        process_end = timezone.make_naive(timezone.now(), timezone.utc)

        if task.is_aborted():  # check before each steps
            raise ExportDataTaskException(MSG_EXPORT_ABORTED)
        # create export data file
        logger.debug(f'creating export data file')
        export_data_json['process_end'] = process_end.strftime('%Y-%m-%d %H:%M:%S')
        write_json_file(export_data_json, temp_file_path)
        response = export_data.upload_export_data_file(cookies, temp_file_path, **kwargs)
        if not task.is_aborted() and response.status_code != 201:
            kwargs['is_rollback'] = True
            return export_data_rollback_process(task, cookies, export_data_id, **kwargs)
        logger.debug(f'created export data file')

        # remove temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.debug(f'removed temporary file')

        if task.is_aborted():  # check before each steps
            raise ExportDataTaskException(MSG_EXPORT_ABORTED)
        # re-check status to ensure that it is not in stopping process
        export_data_set = ExportData.objects.filter(pk=export_data_id)
        export_data = export_data_set.first()

        if export_data is None:
            raise ExportDataTaskException(MSG_EXPORT_REMOVED)

        if export_data.status == ExportData.STATUS_RUNNING:
            # complete process
            export_data_set.update(
                status=ExportData.STATUS_COMPLETED,
                process_end=process_end,
                export_file=export_data.get_export_data_file_path(),
                project_number=export_data_json.get('projects_numb', 0),
                file_number=export_data_json.get('files_numb', 0),
                total_size=export_data_json.get('size', 0),
            )
        logger.debug(f'completed process')
        export_data = export_data_set.first()
        return {
            'message': MSG_EXPORT_COMPLETED,
            'export_data_id': export_data.id,
            'export_data_status': export_data.status,
            'list_file_info_export_not_found': list_file_info_not_found,
            'file_name_export_fail': 'failed_files_export_{}_{}.csv'.format(
                institution_guid, export_data.process_start_timestamp
            ),
        }
    except Exception as e:
        logger.debug(f'Exception {e}')
        # terminate process

        task_meta = {
            'exc_type': type(e).__name__,
            'exc_message': str(e),
            'export_data_id': export_data_id,
        }
        if not isinstance(e, ExportDataTaskException):
            task_meta['traceback'] = traceback.format_exc().split('\n')

        export_data_set = ExportData.objects.filter(pk=export_data_id)
        if export_data_set.exists():
            export_data = export_data_set.first()
            export_data.status = ExportData.STATUS_ERROR
            export_data.save()
            task_meta['export_data_status'] = export_data.status

        task.update_state(state=states.FAILURE, meta=task_meta)
        raise Ignore(str(e))


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
                'message': MSG_EXPORT_DENY_PERM
            }, status=status.HTTP_400_BAD_REQUEST)

        export_data = export_data_set.first()
        task = AbortableAsyncResult(task_id)
        # if tasks are finished
        if task.state in TASK_NO_WORKING_STATES:
            return Response({
                'task_id': task_id,
                'task_state': task.state,
                'status': export_data.status,
                'message': MSG_EXPORT_UNSTOPPABLE
            }, status=status.HTTP_400_BAD_REQUEST)

        # Abort the corresponding task_id
        task.abort()
        # task.revoke(terminate=True)
        if task.state != ABORTED:
            return Response({
                'task_id': task_id,
                'task_state': task.state,
                'status': export_data.status,
                'message': MSG_EXPORT_UNABORTABLE
            }, status=status.HTTP_400_BAD_REQUEST)

        # Delete export data file which created on the export process
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES
        task = tasks.run_export_data_rollback_process.delay(
            cookies, export_data.id, cookie=cookie, export_data_task=task_id)
        # try to replace by the stopping task
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


def export_data_rollback_process(task, cookies, export_data_id, **kwargs):
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))
    is_rollback = kwargs.get('is_rollback', False)
    try:
        # get corresponding export data record
        export_data_set = ExportData.objects.filter(pk=export_data_id)
        export_data = export_data_set.first()

        if export_data is None:
            raise ExportDataTaskException(MSG_EXPORT_REMOVED)

        # if export processes can not be stopped
        if export_data.status not in ExportData.EXPORT_DATA_STOPPABLE:
            logger.debug(MSG_EXPORT_UNSTOPPABLE)
            raise ExportDataTaskException(MSG_EXPORT_UNSTOPPABLE)

        # start stopping it
        export_data_set.update(
            task_id=task.request.id,
            status=ExportData.STATUS_STOPPING,
        )
        logger.debug(f'stopping process')

        export_data = export_data_set.first()
        file_path = export_data.export_data_temp_file_path
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.debug(f'removed temporary file')

        # delete export data file
        logger.debug(f'deleting export data file')
        response = export_data.delete_export_data_folder(cookies, **kwargs)
        if response.status_code != 204:
            export_data_status = ExportData.STATUS_ERROR
            logger.debug(f'can not delete export data file')
        else:
            export_data_status = ExportData.STATUS_STOPPED
            logger.debug(f'deleted export data file')

        # stop it
        export_data_set.update(
            status=ExportData.STATUS_STOPPED,
            process_end=timezone.make_naive(timezone.now(), timezone.utc),
            export_file=None,
        )
        logger.debug(f'stopped process')

        _msg = MSG_EXPORT_FORCE_STOPPED if export_data_status == ExportData.STATUS_ERROR else MSG_EXPORT_STOPPED

        if is_rollback:
            raise ExportDataTaskException(_msg)

        export_data_task_id = kwargs.get('export_data_task')
        export_data_task = AsyncResult(export_data_task_id)
        return {
            'message': _msg,
            'export_data_id': export_data_id,
            'export_data_task_id': export_data_task_id,
            'export_data_status': export_data_status,
            'export_data_task_result': get_task_result(export_data_task.result),
        }
    except Exception as e:
        logger.debug(f'Exception {e}')
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
            export_data.status = ExportData.STATUS_ERROR
            export_data.save()
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
                'message': MSG_EXPORT_DENY_PERM
            }, status=status.HTTP_400_BAD_REQUEST)

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
