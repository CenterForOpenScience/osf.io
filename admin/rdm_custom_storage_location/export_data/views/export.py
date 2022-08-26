# -*- coding: utf-8 -*-
import inspect
import logging

import requests
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
from api.base.utils import waterbutler_api_url_for
from osf.models import Institution, ExportDataLocation, AbstractNode
from osf.models.export_data import *
from website.util import inspect_info
from .location import ExportStorageLocationViewBaseView

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
        if not location_id or not (institution.have_storage_location_id(location_id) or self.have_default_storage_location_id(location_id)):
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

        export_data_folder = export_data.export_data_folder
        export_data_filename = export_data.get_export_data_filename(institution.guid)
        file_info_filename = export_data.get_file_info_filename(institution.guid)

        # Todo create new task
        cookies = request.COOKIES
        task = tasks.run_export_data_process.delay(cookies, export_data.id)
        task_id = task.task_id
        export_data.export_file = task_id
        export_data.save()

        return Response({
            'task_id': task_id,
            'task_state': task.state,
            'export_data_folder': export_data_folder,
            'export_data_filename': export_data_filename,
            'file_info_filename': file_info_filename,
        }, status=status.HTTP_200_OK)


def extract_data():
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))


def extract_file_information():
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))


def export_data_process(cookies, export_data_id):
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))

    # get corresponding export data record
    export_data_set = ExportData.objects.filter(pk=export_data_id)
    export_data = export_data_set.first()
    location = export_data.location

    extract_data()
    extract_file_information()

    node_id = AbstractNode.objects.get(pk=3)._id
    provider = location.provider_name
    path = '/' + export_data.export_data_folder
    url = waterbutler_api_url_for(
        node_id, provider, path=path, _internal=True, meta=''
    )
    logger.debug(f'url: {url}')
    response = requests.get(
        url,
        headers={'content-type': 'application/json'},
        cookies=cookies,
    )
    logger.debug(f'response: {response}')


class StopExportDataActionView(ExportDataBaseActionView):

    def post(self, request, **kwargs):
        institution, source_storage, location = self.extract_input(request)
        task_id = request.data.get('task_id')

        # get corresponding export data record
        export_data_set = ExportData.objects.filter(source=source_storage, location=location, export_file=task_id)
        if not task_id or not export_data_set.exists():
            return Response({'message': f'Permission denied for this export process'}, status=status.HTTP_400_BAD_REQUEST)

        export_data = export_data_set.first()
        export_data_folder = export_data.export_data_folder
        export_data_filename = export_data.get_export_data_filename(institution.guid)
        file_info_filename = export_data.get_file_info_filename(institution.guid)

        # stop it
        export_data_set.update(
            status=ExportData.STATUS_STOPPING,
            export_file=None,
        )

        # Abort the corresponding task_id
        task = AbortableAsyncResult(task_id)
        task.abort()
        # task.revoke(terminate=True)
        if task.state != ABORTED:
            return Response({'message': f'Cannot abort this export process'}, status=status.HTTP_400_BAD_REQUEST)

        # Delete export data file which created on export process
        cookies = request.COOKIES
        task = tasks.run_export_data_rollback_process.delay(cookies, export_data.id)

        return Response({
            'task_id': task_id,
            'task_state': task.state,
            'export_data_folder': export_data_folder,
            'export_data_filename': export_data_filename,
            'file_info_filename': file_info_filename,
        }, status=status.HTTP_200_OK)


def export_data_rollback_process(cookies, export_data_id):
    logger.debug('----{}:{}::{} from {}:{}::{}'.format(*inspect_info(inspect.currentframe(), inspect.stack())))

    # get corresponding export data record
    export_data_set = ExportData.objects.filter(pk=export_data_id)

    # stop it
    export_data_set.update(
        status=ExportData.STATUS_STOPPED,
        process_end=timezone.make_naive(timezone.now(), timezone.utc),
        export_file=None,
    )
