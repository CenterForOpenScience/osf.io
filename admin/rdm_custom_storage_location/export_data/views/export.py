# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from django.db import IntegrityError
from django.utils import timezone
from rest_framework import authentication as drf_authentication
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.osfstorage.models import Region
from osf.models import Institution, ExportDataLocation
from osf.models.export_data import *
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
                status=STATUS_RUNNING,
            )
        except IntegrityError:
            return Response({'message': f'The equivalent process is running'}, status=status.HTTP_400_BAD_REQUEST)

        process_start = datetime.timestamp(export_data.process_start)
        export_data_folder = f'export_{source_storage.id}_{process_start}'
        export_data_filename = f'export_data_{institution.guid}_{process_start}.json'
        file_info_filename = f'file_info_{institution.guid}_{process_start}.json'

        # Todo create new task
        task_id = f'task_{institution.id}_{source_storage.id}_{location.id}'
        export_data.export_file = task_id
        export_data.save()

        return Response({
            'task_id': task_id,
            'export_data_folder': export_data_folder,
            'export_data_filename': export_data_filename,
            'file_info_filename': file_info_filename,
        }, status=status.HTTP_200_OK)


class StopExportDataActionView(ExportDataBaseActionView):

    def post(self, request, **kwargs):
        institution, source_storage, location = self.extract_input(request)
        task_id = request.data.get('task_id')

        # get corresponding export data record
        export_data = ExportData.objects.filter(source=source_storage, location=location, export_file=task_id)

        process_start = datetime.timestamp(export_data.process_start)
        export_data_folder = f'export_{source_storage.id}_{process_start}'
        export_data_filename = f'export_data_{institution.guid}_{process_start}.json'
        file_info_filename = f'file_info_{institution.guid}_{process_start}.json'

        # stop it
        export_data.status = STATUS_STOPPING,
        export_data.process_end = timezone.make_naive(timezone.now(), timezone.utc)
        export_data.save()

        # Todo kill the corresponding task_id

        return Response({
            'task_id': task_id,
            'export_data_folder': export_data_folder,
            'export_data_filename': export_data_filename,
            'file_info_filename': file_info_filename,
        }, status=status.HTTP_200_OK)
