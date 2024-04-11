# -*- coding: utf-8 -*-
from __future__ import absolute_import

import inspect  # noqa
import json
import logging
from functools import partial

from celery.states import PENDING
from celery.contrib.abortable import AbortableAsyncResult, ABORTED
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Trunc
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import authentication as drf_authentication
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.osfstorage.models import Region, NodeSettings
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import tasks
from admin.rdm_custom_storage_location.export_data import utils
from admin.rdm_custom_storage_location.export_data.views import export
from osf.models import ExportData, ExportDataRestore, BaseFileNode, Tag, RdmFileTimestamptokenVerifyResult, Institution, OSFUser, FileVersion, AbstractNode, \
    ProjectStorageType, UserQuota
from framework.transactions.handlers import no_auto_transaction
from website.util.quota import update_user_used_quota
from django.contrib.auth.mixins import UserPassesTestMixin
from admin.rdm.utils import get_institution_id_by_region
from rest_framework.renderers import JSONRenderer

logger = logging.getLogger(__name__)
INSTITUTIONAL_STORAGE_PROVIDER_NAME = 'osfstorage'


class ProcessError(Exception):
    # Raise for exception found in process
    pass


@no_auto_transaction
@method_decorator(transaction.non_atomic_requests, name='dispatch')
class RestoreDataActionView(RdmPermissionMixin, UserPassesTestMixin, APIView):
    raise_exception = True
    authentication_classes = (
        drf_authentication.SessionAuthentication,
    )
    destination_id = None
    export_id = None
    export_data = None
    destination = None

    def dispatch(self, request, *args, **kwargs):
        # login check
        if not self.is_authenticated:
            return self.handle_no_permission()

        self.destination_id = request.POST.get('destination_id')
        self.export_id = kwargs.get('export_id')

        # Check required parameters
        if self.destination_id is None or self.export_id is None:
            return response_render({'message': f'Missing required parameters.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate format destination_id
        try:
            self.destination_id = int(self.destination_id)
        except ValueError:
            return response_render({'message': 'The destination_id must be a integer'}, status=status.HTTP_400_BAD_REQUEST)
        # Check exist data and store data
        self.export_data = ExportData.objects.filter(id=self.export_id, is_deleted=False).first()
        if not self.export_data:
            return response_render({'message': 'The export data does not exist'}, status=status.HTTP_404_NOT_FOUND)
        self.destination = Region.objects.filter(id=self.destination_id).first()
        if not self.destination:
            return response_render({'message': 'The destination storage does not exist'}, status=status.HTTP_404_NOT_FOUND)
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """check user permissions"""
        # allowed if superuser or admin
        if not self.is_super_admin and not self.is_institutional_admin:
            return False
        export_data_inst_id = get_institution_id_by_region(self.export_data.source)
        destination_inst_id = get_institution_id_by_region(self.destination)
        if not export_data_inst_id or not destination_inst_id:
            return False
        else:
            return (export_data_inst_id == destination_inst_id) and self.has_auth(export_data_inst_id)

    def post(self, request, **kwargs):
        cookie = request.user.get_or_create_cookie().decode()
        kwargs.setdefault('cookie', cookie)
        cookies = request.COOKIES
        creator = request.user
        is_from_confirm_dialog = request.POST.get('is_from_confirm_dialog', default=False)

        if not is_from_confirm_dialog:
            # Check the destination is available (not in restore process or checking restore data process)
            any_process_running = utils.check_for_any_running_restore_process(self.destination_id)
            if any_process_running:
                return Response({'message': f'Cannot restore in this time.'}, status=status.HTTP_400_BAD_REQUEST)

            result = check_before_restore_export_data(cookies, self.export_id, self.destination_id, cookie=cookie)
            if result.get('open_dialog'):
                # If open_dialog is True, return HTTP 200 with empty response
                return Response({}, status=status.HTTP_200_OK)
            elif 'not_found' in result:
                return Response({'message': result.get('message')}, status=status.HTTP_404_NOT_FOUND)
            elif result.get('message'):
                # If there is error message, return HTTP 400
                return Response({'message': result.get('message')}, status=status.HTTP_400_BAD_REQUEST)

        # Start restore data task and return task id
        source_storage_guid = self.export_data.source.guid
        institution = Institution.load(source_storage_guid)
        projects = institution.nodes.filter(type='osf.node', is_deleted=False)
        projects__ids = []
        for project in projects:
            projects__ids.append(project._id)
        return prepare_for_restore_export_data_process(cookies, self.export_id,
                                                        self.destination_id, projects__ids, creator, cookie=cookie)

def check_before_restore_export_data(cookies, export_id, destination_id, **kwargs):
    check_export_data = ExportData.objects.filter(id=export_id, is_deleted=False)
    # Check export file data: /export_{process_start}/export_data_{institution_guid}_{process_start}.json
    if not check_export_data:
        return {'open_dialog': False, 'message': f'Cannot be restored because export data does not exist', 'not_found': True}
    # Update status RUNNING for export data for checking connect to destination storage
    export_data = check_export_data[0]
    pre_status = export_data.status
    export_data.status = ExportData.STATUS_RUNNING
    export_data.save()
    try:
        is_export_data_file_valid = read_export_data_and_check_schema(export_data, cookies, **kwargs)
        if not is_export_data_file_valid:
            # Update status COMPLETED for export data if raise error
            export_data.status = pre_status
            export_data.save()
            return {'open_dialog': False, 'message': f'The export data files are corrupted'}
    except Exception as e:
        logger.error(f'Exception: {e}')
        # Update status COMPLETED for export data if raise exception when reading export data and checking schema
        export_data.status = pre_status
        export_data.save()
        return {'open_dialog': False, 'message': f'Cannot connect to the export data storage location'}

    # Get file info file: /export_{process_start}/file_info_{institution_guid}_{process_start}.json
    try:
        export_data_json = read_file_info_and_check_schema(export_data=export_data, cookies=cookies, **kwargs)
        export_data_folders = export_data_json.get('folders', [])
    except Exception as e:
        logger.error(f'Exception: {e}')
        export_data.status = pre_status
        export_data.save()
        return {'open_dialog': False, 'message': str(e)}

    if not len(export_data_folders):
        export_data.status = pre_status
        export_data.save()
        return {'open_dialog': False, 'message': f'The export data files are corrupted'}
    destination_first_project_id = export_data_folders[0].get('project', {}).get('id')

    # Check whether the restore destination storage is not empty
    destination_region = Region.objects.filter(id=destination_id).first()
    if not destination_region:
        export_data.status = pre_status
        export_data.save()
        return {'open_dialog': False, 'message': f'Failed to get destination storage information'}

    destination_provider = destination_region.provider_name
    if utils.is_add_on_storage(destination_provider):
        try:
            destination_base_url = destination_region.waterbutler_url
            response = utils.get_file_data(destination_first_project_id, destination_provider, '/', cookies,
                                           destination_base_url, get_file_info=True, **kwargs)
            if response.status_code != status.HTTP_200_OK:
                # Error
                logger.error(f'Return error with response: {response.content}')
                export_data.status = pre_status
                export_data.save()
                return {'open_dialog': False, 'message': f'Cannot connect to destination storage'}

            response_body = response.json()
            data = response_body.get('data')
            if len(data) != 0:
                # Destination storage is not empty, show confirm dialog
                export_data.status = pre_status
                export_data.save()
                return {'open_dialog': True}
        except Exception as e:
            logger.error(f'Exception: {e}')
            export_data.status = pre_status
            export_data.save()
            return {'open_dialog': False, 'message': f'Cannot connect to destination storage'}

    export_data.status = pre_status
    export_data.save()
    # Destination storage is empty, return False
    return {'open_dialog': False}


def prepare_for_restore_export_data_process(cookies, export_id, destination_id, list_project_id, creator, **kwargs):
    # Check the destination is available (not in restore process or checking restore data process)
    any_process_running = utils.check_for_any_running_restore_process(destination_id)
    if any_process_running:
        return Response({'message': f'Cannot restore in this time.'}, status=status.HTTP_400_BAD_REQUEST)

    # Try to add new process record to DB
    export_data_restore = ExportDataRestore(export_id=export_id, destination_id=destination_id,
                                            status=ExportData.STATUS_RUNNING, creator=creator)
    export_data_restore.save()
    # If user clicked 'Restore' button in confirm dialog, start restore data task and return task id
    process = tasks.run_restore_export_data_process.delay(cookies, export_id, export_data_restore.pk, list_project_id, **kwargs)
    return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


def restore_export_data_process(task, cookies, export_id, export_data_restore_id, list_project_id, **kwargs):
    current_process_step = 0
    try:
        update_restore_process_state(task, current_process_step)
        export_data_restore = ExportDataRestore.objects.get(pk=export_data_restore_id)
        export_data_restore.update(task_id=task.request.id)

        export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]

        # Get file which have same information between export data and database
        # File info file: /export_{process_start}/file_info_{institution_guid}_{process_start}.json
        export_data_json = read_file_info_and_check_schema(export_data=export_data, cookies=cookies, **kwargs)
        export_data_files = export_data_json.get('files', [])
        export_data_folders = export_data_json.get('folders', [])

        if len(export_data_files) == 0:
            export_data_restore.update(process_end=timezone.make_naive(timezone.now(), timezone.utc),
                                       status=ExportData.STATUS_COMPLETED)
            return {'message': 'Restore data successfully.'}

        check_if_restore_process_stopped(task, current_process_step)
        current_process_step = 1
        update_restore_process_state(task, current_process_step)

        destination_region = export_data_restore.destination
        destination_provider = destination_region.provider_name
        if utils.is_add_on_storage(destination_provider):
            # Move all existing files/folders in destination to backup_{process_start} folder
            for project_id in list_project_id:
                move_all_files_to_backup_folder(task, current_process_step, project_id, export_data_restore, cookies, **kwargs)

        check_if_restore_process_stopped(task, current_process_step)
        current_process_step = 2
        update_restore_process_state(task, current_process_step)

        # create folders in destination
        create_folder_in_destination(task, current_process_step, export_data_folders, export_data_restore, cookies, **kwargs)

        # Download files from export data, then upload files to destination. Returns list of created file node in DB
        list_created_file_nodes, list_file_restore_fail = copy_files_from_export_data_to_destination(
            task, current_process_step,
            export_data_files, export_data_restore,
            cookies, **kwargs)

        check_if_restore_process_stopped(task, current_process_step)
        current_process_step = 3
        update_restore_process_state(task, current_process_step)

        # Add tags, timestamp to created file nodes
        add_tag_and_timestamp_to_database(task, current_process_step, list_created_file_nodes)

        # Update process data with process_end timestamp and 'Completed' status
        export_data_restore.update(process_end=timezone.make_naive(timezone.now(), timezone.utc),
                                   status=ExportData.STATUS_COMPLETED)

        check_if_restore_process_stopped(task, current_process_step)
        current_process_step = 4
        update_restore_process_state(task, current_process_step)
        institution_guid = ''
        if export_data_json and 'institution' in export_data_json:
            institution_guid = export_data_json.get('institution').get('guid')
        return {'message': 'Restore data successfully.', 'list_file_restore_fail': list_file_restore_fail,
                'file_name_restore_fail': 'failed_files_restore_{}_{}.csv'.format(institution_guid, export_data.process_start_timestamp)}
    except Exception as e:
        logger.error(f'Restore data process exception: {e}')
        if task.is_aborted():
            task.update_state(state=ABORTED,
                              meta={'current_restore_step': current_process_step})
        else:
            restore_export_data_rollback_process(
                task, cookies, export_id, export_data_restore_id,
                process_step=current_process_step, **kwargs)
        raise e


def update_restore_process_state(task, current_process_step):
    new_meta = {
        'current_restore_step': current_process_step
    }
    current_result = AbortableAsyncResult(task.request.id)
    # Update current data to task's result
    task.update_state(state=current_result.state, meta=new_meta)


def check_if_restore_process_stopped(task, current_process_step):
    if task.is_aborted():
        task.update_state(state=ABORTED,
                          meta={'current_restore_step': current_process_step})
        raise ProcessError(f'Restore process is stopped')


@no_auto_transaction
@method_decorator(transaction.non_atomic_requests, name='dispatch')
class StopRestoreDataActionView(RdmPermissionMixin, UserPassesTestMixin, APIView):
    raise_exception = True
    authentication_classes = (
        drf_authentication.SessionAuthentication,
    )
    task_id = None
    destination_id = None
    destination_inst_id = None
    export_id = None
    export_data_inst_id = None
    export_data_restore = None
    export_data_restore_inst_id = None

    def dispatch(self, request, *args, **kwargs):
        # login check
        if not self.is_authenticated:
            return self.handle_no_permission()

        self.task_id = request.POST.get('task_id')
        self.destination_id = request.POST.get('destination_id')
        self.export_id = kwargs.get('export_id')

        # Check required parameters
        if not self.destination_id or not self.export_id or not self.task_id:
            return response_render({'message': f'Missing required parameters.'},
                                    status=status.HTTP_400_BAD_REQUEST)

        # Validate format destination_id
        try:
            self.destination_id = int(self.destination_id)
        except ValueError:
            return response_render({'message': 'The destination_id must be a integer'},
                                    status=status.HTTP_400_BAD_REQUEST)

        # Check exist and store data with task_id,destination_id and export_id
        check_export_data = ExportData.objects.filter(id=self.export_id, is_deleted=False).first()
        if check_export_data:
            self.export_data_inst_id = get_institution_id_by_region(check_export_data.source)
        else:
            return response_render({'message': f'The export data is not exist'},
                            status=status.HTTP_404_NOT_FOUND)

        destination_region = Region.objects.filter(id=self.destination_id).first()
        if destination_region:
            self.destination_inst_id = get_institution_id_by_region(destination_region)
        else:
            return response_render({'message': f'The destination storage does not exist'},
                            status=status.HTTP_404_NOT_FOUND)

        self.export_data_restore = ExportDataRestore.objects.filter(task_id=self.task_id,
                                                                    destination_id=self.destination_id).first()
        if self.export_data_restore:
            self.export_data_restore_inst_id = get_institution_id_by_region(self.export_data_restore.export.source)
        else:
            return response_render({'message': f'The restore export data is not exist'},
                            status=status.HTTP_404_NOT_FOUND)
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # allowed if superuser or admin
        if not self.is_super_admin and not self.is_institutional_admin:
            return False

        return (self.export_data_restore_inst_id == self.export_data_inst_id == self.destination_inst_id)\
                    and self.has_auth(self.export_data_restore_inst_id)

    def post(self, request, *args, **kwargs):
        cookie = request.user.get_or_create_cookie().decode()
        kwargs.setdefault('cookie', cookie)
        cookies = request.COOKIES

        # Get current task's result
        task = AbortableAsyncResult(self.task_id)
        result = task.result

        # If result is None then update status to Stopped
        if not result:
            self.export_data_restore.update(process_end=timezone.make_naive(timezone.now(), timezone.utc),
                                       status=ExportData.STATUS_STOPPED)
            return Response({'message': f'Stop restore data successfully.'}, status=status.HTTP_200_OK)

        # If process state is not STARTED and not PENDING then update status to Stopped
        if task.state != 'STARTED' and task.state != PENDING:
            self.export_data_restore.update(process_end=timezone.make_naive(timezone.now(), timezone.utc),
                                       status=ExportData.STATUS_STOPPED)
            return Response({'message': f'Stop restore data successfully.'}, status=status.HTTP_200_OK)

        # Get current restore progress step
        current_progress_step = result.get('current_restore_step')
        logger.debug(f'Current progress step before abort: {current_progress_step}')
        if current_progress_step >= 4 or current_progress_step is None:
            return Response({'message': f'Cannot stop restore process at this time.'},
                             status=status.HTTP_400_BAD_REQUEST)

        # Update process status
        self.export_data_restore.update(status=ExportData.STATUS_STOPPING)

        # Abort current task
        task.abort()

        # If task does not abort then return error response
        if task.state != ABORTED:
            self.export_data_restore.update(status=ExportData.STATUS_ERROR)
            return Response({'message': f'Cannot stop restore process at this time.'},
                             status=status.HTTP_400_BAD_REQUEST)

        # Start rollback restore export data process
        process = tasks.run_restore_export_data_rollback_process.delay(
            cookies,
            self.export_id,
            self.export_data_restore.pk,
            current_progress_step,
            cookie=cookie,
        )
        return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


def restore_export_data_rollback_process(task, cookies, export_id,
                                          export_data_restore_id, process_step, **kwargs):
    export_data_restore = ExportDataRestore.objects.get(pk=export_data_restore_id)
    export_data_restore.update(task_id=task.request.id)

    destination_provider = export_data_restore.destination.provider_name
    if process_step == 0 or not utils.is_add_on_storage(destination_provider):
        # If storage is bulk-mount method or the restore process has not changed anything related to files, then do nothing
        export_data_restore.update(process_end=timezone.make_naive(timezone.now(), timezone.utc),
                                   status=ExportData.STATUS_STOPPED)
        return {'message': 'Stop restore data successfully.'}

    try:
        with transaction.atomic():
            export_data = ExportData.objects.filter(id=export_id, is_deleted=False)[0]
            # File info file: /export_{process_start}/file_info_{institution_guid}_{process_start}.json
            file_info_json = read_file_info_and_check_schema(export_data, cookies, **kwargs)
            if file_info_json is None:
                raise ProcessError(f'Cannot get file information list')
            file_info_files = file_info_json.get('files', [])

            if len(file_info_files) == 0:
                export_data_restore.update(process_end=timezone.make_naive(timezone.now(), timezone.utc),
                                           status=ExportData.STATUS_STOPPED)
                return {'message': 'Stop restore data successfully.'}
            destination_first_project_id = file_info_files[0].get('project', {}).get('id')

            location_id = export_data.location.id
            # Delete files, except the backup folder.
            if process_step == 2 or process_step == 3:
                delete_all_files_except_backup_folder(
                    export_data_restore, location_id, destination_first_project_id,
                    cookies, **kwargs)

            # Move all files from the backup folder out and delete backup folder
            if 0 < process_step < 4:
                move_all_files_from_backup_folder_to_root(export_data_restore,
                                                           destination_first_project_id, cookies, **kwargs)

        export_data_restore.update(process_end=timezone.make_naive(timezone.now(), timezone.utc),
                                   status=ExportData.STATUS_STOPPED)
    except Exception as e:
        export_data_restore.update(status=ExportData.STATUS_ERROR)
        raise e

    return {'message': 'Stop restore data successfully.'}


class CheckTaskStatusRestoreDataActionView(RdmPermissionMixin, UserPassesTestMixin, APIView):
    raise_exception = True
    authentication_classes = (
        drf_authentication.SessionAuthentication,
    )

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # allowed if superuser or admin
        if not self.is_super_admin and not self.is_institutional_admin:
            return False

        task_id = self.request.GET.get('task_id')
        export_id = self.kwargs.get('export_id')
        if not task_id:
            return True
        else:
            # Check exist ExportDataRestore with task_id and export_id
            restore_data_inst_id = None
            check_restore_data = ExportDataRestore.objects.filter(task_id=task_id).first()
            if check_restore_data:
                restore_data_inst_id = get_institution_id_by_region(check_restore_data.export.source)
            export_data_inst_id = None
            check_export_data = ExportData.objects.filter(id=export_id, is_deleted=False).first()
            if check_export_data:
                export_data_inst_id = get_institution_id_by_region(check_export_data.source)
            return (restore_data_inst_id == export_data_inst_id) and self.has_auth(restore_data_inst_id)

    def get(self, request, **kwargs):
        task_id = request.GET.get('task_id')
        task_type = request.GET.get('task_type')
        if task_id is None:
            return Response({'message': f'Missing required parameters.'}, status=status.HTTP_400_BAD_REQUEST)
        task = AbortableAsyncResult(task_id)
        response = {
            'state': task.state,
            'task_id': task_id,
            'task_type': task_type,
        }
        if task.result is not None:
            response['result'] = task.result if isinstance(task.result, dict) else str(task.result)
        return Response(response, status=status.HTTP_200_OK if task.state != 'FAILURE' else status.HTTP_400_BAD_REQUEST)


def add_tags_to_file_node(file_node, tags):
    if len(tags) == 0 or not file_node:
        return

    for tag in tags:
        if not file_node.tags.filter(system=False, name=tag).exists():
            new_tag = Tag.load(tag)
            if not new_tag:
                new_tag = Tag(name=tag)
            new_tag.save()
            file_node.tags.add(new_tag)
            file_node.save()


def add_timestamp_to_file_node(file_node, project_id, timestamp):
    if not file_node or not project_id or not timestamp:
        return
    verify_data = None
    timestamp_obj = RdmFileTimestamptokenVerifyResult.objects.filter(id=timestamp.get('timestamp_id')).first()
    try:
        verify_data = RdmFileTimestamptokenVerifyResult.objects.get(
            file_id=file_node._id)
    except RdmFileTimestamptokenVerifyResult.DoesNotExist:
        verify_data = RdmFileTimestamptokenVerifyResult()
        verify_data.file_id = file_node._id
        verify_data.project_id = timestamp.get('project_id', project_id)
        verify_data.provider = timestamp.get('provider', file_node.provider)

    if timestamp_obj:
        verify_data.timestamp_token = timestamp_obj.timestamp_token
        verify_data.verify_date = timestamp_obj.verify_date
        verify_data.verify_file_modified_at = timestamp_obj.verify_file_modified_at
        verify_data.upload_file_created_at = timestamp_obj.upload_file_created_at
        verify_data.upload_file_modified_at = timestamp_obj.upload_file_modified_at
        verify_data.verify_file_created_at = timestamp_obj.verify_file_created_at
    verify_data.path = timestamp.get('path', file_node.path)
    verify_data.inspection_result_status = timestamp.get('inspection_result_status', 0)
    verify_data.key_file_name = timestamp.get('key_file_name', file_node.path)
    verify_data.upload_file_created_user = timestamp.get('upload_file_created_user', None)
    verify_data.upload_file_modified_user = timestamp.get('upload_file_modified_user', None)
    verify_data.upload_file_size = timestamp.get('upload_file_size', None)
    verify_data.verify_file_size = timestamp.get('verify_file_size', None)
    verify_data.verify_user = timestamp.get('verify_user', None)
    verify_data.save()


def read_export_data_and_check_schema(export_data, cookies, **kwargs):
    # Get export file (/export_{process_start}/export_data_{institution_guid}_{process_start}.json)
    try:
        response = export_data.read_export_data_from_location(cookies, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            # Error
            raise ProcessError(f'Cannot connect to the export data storage location')
        response_body = response.content
        response_file_content = response_body.decode('utf-8')
        response_file_json = json.loads(response_file_content)
    except Exception:
        raise ProcessError(f'Cannot connect to the export data storage location')

    # Validate export file schema
    return utils.validate_file_json(response_file_json, 'export-data-schema.json')


def read_file_info_and_check_schema(export_data, cookies, **kwargs):
    # Get file info file: /export_{process_start}/file_info_{institution_guid}_{process_start}.json
    try:
        response = export_data.read_file_info_from_location(cookies, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            raise ProcessError(f'Cannot get file information list')
        response_body = response.content
        response_file_content = response_body.decode('utf-8')
        response_file_json = json.loads(response_file_content)
    except Exception:
        raise ProcessError(f'Cannot get file information list')

    # Validate file info schema
    is_file_valid = utils.validate_file_json(response_file_json, 'file-info-schema.json')
    if not is_file_valid:
        raise ProcessError(f'The export data files are corrupted')

    return response_file_json


def update_region_id(task, current_process_step, destination_region, project_id, list_updated_projects):
    # Update region_id for a United States project
    check_if_restore_process_stopped(task, current_process_step)
    project = AbstractNode.load(project_id, select_for_update=False)
    if not project:
        return list_updated_projects

    project_region = project.osfstorage_region
    if project_region and project_region.guid == Institution.INSTITUTION_DEFAULT:
        # Update region of addons_osfstorage_nodesettings
        node_settings = NodeSettings.objects.filter(region=project_region, owner=project)
        node_settings.update(region=destination_region)
        list_updated_projects.append(project.id)

        # Update storage type of project
        project_storage_type = ProjectStorageType.objects.filter(node=project)
        project_storage_type.update(storage_type=ProjectStorageType.CUSTOM_STORAGE)

        # Update file versions' region_id of this project
        file_ids = BaseFileNode.objects.filter(target_object_id=project.id).values_list('id', flat=True)
        file_versions = FileVersion.objects.filter(basefilenode__id__in=file_ids,
                                                    region___id=Institution.INSTITUTION_DEFAULT)
        if file_versions.exists():
            file_versions.update(region=destination_region)

    return list_updated_projects


def recalculate_user_quota(destination_region):
    # Recalculate quota of default storage and custom storage
    institution = Institution.load(destination_region.guid)
    for user in OSFUser.objects.filter(affiliated_institutions=institution.id):
        update_user_used_quota(user)
        update_user_used_quota(user, storage_type=UserQuota.CUSTOM_STORAGE)


def generate_new_file_path(file_materialized_path, version_id, is_file_not_latest_version):
    new_file_materialized_path = file_materialized_path
    if len(file_materialized_path) > 0 and is_file_not_latest_version:
        # for past version files, rename and save each version as filename_{version} in '_version_files' folder
        path_splits = new_file_materialized_path.split('/')

        # add _{version} to file name
        file_name = path_splits[len(path_splits) - 1]
        file_splits = file_name.split('.')
        file_splits[0] = f'{file_splits[0]}_{version_id}'
        versioned_file_name = '.'.join(file_splits)

        # add _version_files to folder path
        path_splits.insert(len(path_splits) - 1, '_version_files')
        path_splits[len(path_splits) - 1] = versioned_file_name
        new_file_materialized_path = '/'.join(path_splits)
    return new_file_materialized_path


def move_all_files_to_backup_folder(task, current_process_step,
                                     destination_first_project_id, export_data_restore, cookies, **kwargs):
    try:
        destination_region = export_data_restore.destination
        destination_provider = INSTITUTIONAL_STORAGE_PROVIDER_NAME
        destination_base_url = destination_region.waterbutler_url
        is_destination_addon_storage = utils.is_add_on_storage(destination_provider)
        with transaction.atomic():
            # Preload params to function
            check_task_aborted_function = partial(
                check_if_restore_process_stopped,
                task=task,
                current_process_step=current_process_step)

            # move all old data in restore destination storage to a folder to back up folder
            if is_destination_addon_storage:
                move_folder_to_backup = partial(utils.move_addon_folder_to_backup)
            else:
                move_folder_to_backup = partial(utils.move_bulk_mount_folder_to_backup)
            response = move_folder_to_backup(
                destination_first_project_id,
                destination_provider,
                process_start=export_data_restore.process_start_timestamp,
                cookies=cookies,
                callback_log=False,
                base_url=destination_base_url,
                check_abort_task=check_task_aborted_function, **kwargs)
            check_if_restore_process_stopped(task, current_process_step)
            if response and 'error' in response:
                # Error
                error_msg = response.get('error')
                logger.error(f'Move all files to backup folder error message: {error_msg}')
                raise ProcessError(f'Failed to move files to backup folder.')
    except Exception as e:
        logger.error(f'Move all files to backup folder exception: {e}')
        raise ProcessError(f'Failed to move files to backup folder.')


def create_folder_in_destination(task, current_process_step, export_data_folders,
                                 export_data_restore, cookies, **kwargs):
    destination_region = export_data_restore.destination
    destination_base_url = destination_region.waterbutler_url
    list_updated_projects = []
    for folder in export_data_folders:
        check_if_restore_process_stopped(task, current_process_step)
        folder_materialized_path = folder.get('materialized_path')
        folder_project_id = folder.get('project', {}).get('id')

        # Update region_id for folder's project
        list_updated_projects = update_region_id(task, current_process_step,
                                                  destination_region, folder_project_id, list_updated_projects)

        utils.create_folder_path(folder_project_id, destination_region, folder_materialized_path,
                                 cookies, base_url=destination_base_url, **kwargs)

    # recalculate user quota for all updated projects
    if list_updated_projects:
        # recalculate user quota
        recalculate_user_quota(destination_region)


def copy_files_from_export_data_to_destination(task, current_process_step,
                                                export_data_files, export_data_restore, cookies, **kwargs):
    export_data = export_data_restore.export

    destination_region = export_data_restore.destination
    destination_provider = INSTITUTIONAL_STORAGE_PROVIDER_NAME
    destination_base_url = destination_region.waterbutler_url
    is_destination_addon_storage = utils.is_add_on_storage(destination_provider)

    list_created_file_nodes = []
    files_versions_restore_fail = {}
    for file in export_data_files:
        check_if_restore_process_stopped(task, current_process_step)

        file_id = file.get('id')
        file_materialized_path = file.get('materialized_path')
        file_versions = file.get('version')
        file_project_id = file.get('project', {}).get('id')
        file_tags = file.get('tags')
        file_timestamp = file.get('timestamp', {})
        file_checkout_id = file.get('checkout_id')
        file_created = file.get('created_at')
        file_modified = file.get('modified_at')

        # Sort file by version id
        file_versions.sort(key=lambda k: k.get('identifier', 0))

        for index, version in enumerate(file_versions):
            try:
                check_if_restore_process_stopped(task, current_process_step)

                # Prepare file name and file path for uploading
                metadata = version.get('metadata', {})
                file_hash = metadata.get('sha256', metadata.get('md5'))
                version_id = version.get('identifier')
                if file_hash is None or version_id is None:
                    # Cannot get path in export data storage, pass this file
                    continue

                file_hash_path = f'/{export_data.export_data_folder_name}/{ExportData.EXPORT_DATA_FILES_FOLDER}/{file_hash}'

                # If the destination storage is add-on institutional storage:
                # - for past version files, rename and save each version as filename_{version} in '_version_files' folder
                # - the latest version is saved as the original
                if is_destination_addon_storage:
                    is_file_not_latest_version = index < len(file_versions) - 1
                    new_file_path = generate_new_file_path(
                        file_materialized_path=file_materialized_path,
                        version_id=version_id,
                        is_file_not_latest_version=is_file_not_latest_version)
                else:
                    new_file_path = file_materialized_path

                # Copy file from location to destination storage
                response_body = utils.copy_file_from_location_to_destination(
                    export_data, file_project_id, destination_provider, file_hash_path, new_file_path,
                    cookies, base_url=destination_base_url, **kwargs)
                if response_body is None:
                    if file_id not in files_versions_restore_fail:
                        files_versions_restore_fail[file_id] = [version_id]
                    else:
                        files_versions_restore_fail[file_id].append(version_id)
                    continue

                response_id = response_body.get('data', {}).get('id')
                response_file_version_id = response_body.get('data', {}).get('attributes', {}).get('extra', {}).get('version', version_id)
                if response_id.startswith('osfstorage'):
                    # If id is osfstorage/[_id] then get _id
                    file_path_splits = response_id.split('/')
                    # Check if path is file (/_id)
                    if len(file_path_splits) == 2:
                        file_node_id = file_path_splits[1]
                        node_set = BaseFileNode.objects.filter(_id=file_node_id)
                        if node_set.exists():
                            node = node_set.first()

                            # update creator, created, modified back to the file version
                            file_version = node.get_version(response_file_version_id, required=False)

                            if file_version is not None:
                                contributor = version.get('contributor')
                                user = OSFUser.objects.filter(username=contributor)
                                file_version_created_at = version.get('created_at')
                                file_version_modified = version.get('modified_at')
                                same_file_versions = node.versions.annotate(
                                    created_trunc=Trunc('created', 'second'),
                                    modified_trunc=Trunc('modified', 'second')
                                ).exclude(
                                    identifier=response_file_version_id
                                ).filter(
                                    created_trunc=file_version_created_at,
                                    modified_trunc=file_version_modified
                                )

                                if same_file_versions.exists():
                                    file_version.delete()
                                else:
                                    if user.exists():
                                        file_version.creator = user.first()
                                    file_version.created = file_version_created_at
                                    file_version.modified = file_version_modified
                                    file_version.save()
                                    FileVersion.objects.filter(id=file_version.id).update(created=file_version_created_at,
                                                                                          modified=file_version_created_at)

                            if file_checkout_id:
                                node.checkout_id = file_checkout_id

                            # update created/modified date to basefilenode
                            node.created = file_created
                            node.modified = file_modified
                            node.save()
                            BaseFileNode.objects.filter(id=node.id).update(created=file_created,
                                                                           modified=file_modified)

                            list_created_file_nodes.append({
                                'node': node,
                                'file_tags': file_tags,
                                'file_timestamp': file_timestamp,
                                'project_id': file_project_id
                            })
            except Exception as e:
                logger.error(f'Download or upload exception: {e}')
                check_if_restore_process_stopped(task, current_process_step)
                # Did not download or upload, pass this file
                continue

    # Separate the failed file list from the file_info_json
    list_file_restore_fail, _, _ = export.separate_failed_files(export_data_files, files_versions_restore_fail)
    return list_created_file_nodes, list_file_restore_fail


def add_tag_and_timestamp_to_database(task, current_process_step, list_created_file_nodes):
    with transaction.atomic():
        for item in list_created_file_nodes:
            check_if_restore_process_stopped(task, current_process_step)

            node = item.get('node')
            file_tags = item.get('file_tags')
            file_timestamp = item.get('file_timestamp')
            project_id = item.get('project_id')

            # Add tags to DB
            add_tags_to_file_node(node, file_tags)

            # Add timestamp to DB
            add_timestamp_to_file_node(node, project_id, file_timestamp)
        check_if_restore_process_stopped(task, current_process_step)


def delete_all_files_except_backup_folder(export_data_restore, location_id,
                                           destination_first_project_id, cookies, **kwargs):
    destination_region = export_data_restore.destination
    destination_base_url = destination_region.waterbutler_url
    destination_provider = INSTITUTIONAL_STORAGE_PROVIDER_NAME

    try:
        utils.delete_all_files_except_backup(
            destination_first_project_id, destination_provider,
            cookies, location_id, destination_base_url, **kwargs)
    except Exception as e:
        logger.error(f'Delete all files exception: {e}')
        raise ProcessError(f'Cannot delete files except backup folders')


def move_all_files_from_backup_folder_to_root(export_data_restore, destination_first_project_id, cookies, **kwargs):
    destination_region = export_data_restore.destination
    destination_provider = INSTITUTIONAL_STORAGE_PROVIDER_NAME
    destination_base_url = destination_region.waterbutler_url
    is_destination_addon_storage = utils.is_add_on_storage(destination_provider)

    try:
        if is_destination_addon_storage:
            move_folder_from_backup = partial(utils.move_addon_folder_from_backup)
        else:
            move_folder_from_backup = partial(utils.move_bulk_mount_folder_from_backup)
        response = move_folder_from_backup(
            destination_first_project_id,
            destination_provider,
            process_start=export_data_restore.process_start_timestamp,
            cookies=cookies,
            callback_log=False,
            base_url=destination_base_url,
            **kwargs)
        if 'error' in response:
            # Error
            error_msg = response.get('error')
            logger.error(f'Move all files from back up error message: {error_msg}')
            raise ProcessError(f'Failed to move backup folder to root')
    except Exception as e:
        logger.error(f'Move all files from back up exception: {e}')
        raise ProcessError(f'Failed to move backup folder to root')


class CheckRunningRestoreActionView(RdmPermissionMixin, UserPassesTestMixin, APIView):
    raise_exception = True
    authentication_classes = (
        drf_authentication.SessionAuthentication,
    )
    destination_id = None
    export_id = None
    export_data = None

    def dispatch(self, request, *args, **kwargs):
        # login check
        if not self.is_authenticated:
            return self.handle_no_permission()

        self.destination_id = request.GET.get('destination_id')
        self.export_id = kwargs.get('export_id')

        # Validate format destination_id
        try:
            if self.destination_id:
                self.destination_id = int(self.destination_id)
        except ValueError:
            return response_render({'message': 'The destination_id must be a integer'},
                                    status=status.HTTP_400_BAD_REQUEST)

        # Check exist data and store data
        self.export_data = ExportData.objects.filter(id=self.export_id, is_deleted=False).first()
        if not self.export_data:
            return response_render({'message': 'The export data does not exist'},
                                    status=status.HTTP_404_NOT_FOUND)
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """check user permissions"""
        # allowed if superuser or admin
        if not self.is_super_admin and not self.is_institutional_admin:
            return False

        if not self.destination_id:
            return True
        else:
            export_data_inst_id = get_institution_id_by_region(self.export_data.source)
            destination_inst_id = get_institution_id_by_region(Region.objects.filter(id=self.destination_id).first())
            return (export_data_inst_id == destination_inst_id) and self.has_auth(export_data_inst_id)

    def get(self, request, **kwargs):
        running_restore = ExportDataRestore.objects.filter(destination_id=self.destination_id).exclude(
            Q(status=ExportData.STATUS_STOPPED) | Q(status=ExportData.STATUS_COMPLETED) | Q(
                status=ExportData.STATUS_ERROR))
        task_id = None
        if len(running_restore) != 0:
            task_id = running_restore[0].task_id
        response = {
            'task_id': task_id
        }
        return Response(response, status=status.HTTP_200_OK)


def response_render(data, status):
    """render json response instance of rest framework"""
    response = Response(data=data, status=status)
    response.accepted_renderer = JSONRenderer()
    response.accepted_media_type = 'application/json'
    response.renderer_context = {}
    response.render()
    return response
