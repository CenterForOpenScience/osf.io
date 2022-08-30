# -*- coding: utf-8 -*-
import inspect
import logging
import os

from celery.contrib.abortable import AbortableAsyncResult, ABORTED
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import authentication as drf_authentication
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import tasks
from osf.models import Institution, ExportDataLocation
from osf.models.export_data import *
from website import settings as web_settings
from website.util import inspect_info
from .location import ExportStorageLocationViewBaseView
from ..utils import write_json_file

logger = logging.getLogger(__name__)


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

        # admin not affiliated with this institution
        if not institution_id or (not request.user.is_super_admin and not request.user.is_affiliated_with_institution_id(institution_id)):
            return Response({'message': f'Permission denied for this institution'}, status=status.HTTP_400_BAD_REQUEST)

        institution = Institution.objects.get(pk=institution_id)

        # this institutional storage is not allowed
        if not source_id or not institution.is_allowed_institutional_storage_id(source_id):
            return Response({'message': f'Permission denied for this storage'}, status=status.HTTP_400_BAD_REQUEST)

        source_storage = Region.objects.get(pk=source_id)

        # this storage location is not allowed
        if not location_id or not institution.have_allowed_storage_location_id(location_id):
            return Response({'message': f'Permission denied for this export storage location'}, status=status.HTTP_400_BAD_REQUEST)

        location = ExportDataLocation.objects.get(pk=location_id)

        return institution, source_storage, location


class ExportDataActionView(ExportDataBaseActionView):

    def post(self, request, *args, **kwargs):
        institution, source_storage, location = self.extract_input(request)

        # Create new process record
        try:
            export_data = ExportData.objects.create(
                source=source_storage,
                location=location,
                status=ExportData.STATUS_RUNNING,
            )
        except IntegrityError:
            return Response({'message': f'The equivalent process is running'}, status=status.HTTP_400_BAD_REQUEST)

        export_data_folder_name = export_data.export_data_folder_name
        export_data_filename = export_data.get_export_data_filename(institution.guid)
        file_info_filename = export_data.get_file_info_filename(institution.guid)

        # Todo create new task
        cookies = request.COOKIES
        cookie = request.user.get_or_create_cookie().decode()
        task = tasks.run_export_data_process.delay(cookies, export_data.id, cookie=cookie)
        task_id = task.task_id
        export_data.task_id = task_id
        export_data.save()

        return Response({
            'task_id': task_id,
            'task_state': task.state,
            'export_data_folder_name': export_data_folder_name,
            'export_data_filename': export_data_filename,
            'file_info_filename': file_info_filename,
        }, status=status.HTTP_200_OK)


def export_data_process(cookies, export_data_id, **kwargs):
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))
    # get corresponding export data record
    export_data_set = ExportData.objects.filter(pk=export_data_id)
    export_data = export_data_set.first()
    assert export_data

    # create folder
    response = export_data.create_export_data_folder(cookies, **kwargs)
    if response.status_code != 201:
        return export_data_rollback_process(cookies, export_data_id, **kwargs)

    export_data_json, file_info_json = export_data.extract_file_information_json_from_source_storage()

    # create files' information file
    file_path = os.path.join(web_settings.ROOT, 'admin', '_' + export_data.export_data_folder_name + '.json')
    write_json_file(file_info_json, file_path)
    response = export_data.upload_file_info_file(cookies, file_path, **kwargs)
    if response.status_code != 201:
        return export_data_rollback_process(cookies, export_data_id, **kwargs)

    process_end = timezone.make_naive(timezone.now(), timezone.utc)

    # create export data file
    export_data_json['export_end'] = process_end.strftime('%Y-%m-%d %H:%M:%S')
    file_path = os.path.join(web_settings.ROOT, 'admin', '_' + export_data.export_data_folder_name + '.json')
    write_json_file(export_data_json, file_path)
    response = export_data.upload_export_data_file(cookies, file_path, **kwargs)
    if response.status_code != 201:
        return export_data_rollback_process(cookies, export_data_id, **kwargs)

    if os.path.exists(file_path):
        os.remove(file_path)

    # complete process
    export_data_set.update(
        status=ExportData.STATUS_COMPLETED,
        process_end=process_end,
        export_file=export_data.get_export_data_file_path(),
        project_number=export_data_json.get('projects_numb', 0),
        file_number=export_data_json.get('files_numb', 0),
        total_size=export_data_json.get('size', 0),
    )


class StopExportDataActionView(ExportDataBaseActionView):

    def post(self, request, **kwargs):
        institution, source_storage, location = self.extract_input(request)
        task_id = request.data.get('task_id')

        # get corresponding export data record
        export_data_set = ExportData.objects.filter(source=source_storage, location=location, task_id=task_id)
        if not task_id or not export_data_set.exists():
            return Response({'message': f'Permission denied for this export process'}, status=status.HTTP_400_BAD_REQUEST)

        export_data = export_data_set.first()
        task = AbortableAsyncResult(task_id)
        if export_data.status != ExportData.STATUS_RUNNING:
            return Response({
                'task_id': task_id,
                'task_state': task.state,
                'status': export_data.status,
                'message': f'Cannot stop this export process'
            }, status=status.HTTP_400_BAD_REQUEST)

        export_data_folder_name = export_data.export_data_folder_name
        export_data_filename = export_data.get_export_data_filename(institution.guid)
        file_info_filename = export_data.get_file_info_filename(institution.guid)

        # stop it
        export_data_set.update(
            status=ExportData.STATUS_STOPPING,
        )

        # Abort the corresponding task_id
        task.abort()
        # task.revoke(terminate=True)
        if task.state != ABORTED:
            return Response({'message': f'Cannot abort this export process'}, status=status.HTTP_400_BAD_REQUEST)

        # Delete export data file which created on export process
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES
        task = tasks.run_export_data_rollback_process.delay(cookies, export_data.id, cookie=cookie)

        return Response({
            'task_id': task_id,
            'task_state': task.state,
            'export_data_folder_name': export_data_folder_name,
            'export_data_filename': export_data_filename,
            'file_info_filename': file_info_filename,
        }, status=status.HTTP_200_OK)


def export_data_rollback_process(cookies, export_data_id, **kwargs):
    # logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))
    # get corresponding export data record
    export_data_set = ExportData.objects.filter(pk=export_data_id)
    export_data = export_data_set.first()
    assert export_data

    export_data_status = ExportData.STATUS_STOPPED
    # delete export data file
    response = export_data.delete_export_data_folder(cookies, **kwargs)
    if response.status_code != 204:
        export_data_status = ExportData.STATUS_ERROR

    # stop it
    export_data_set.update(
        status=export_data_status,
        process_end=timezone.make_naive(timezone.now(), timezone.utc),
        export_file=None,
    )
