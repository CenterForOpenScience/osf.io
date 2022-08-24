# -*- coding: utf-8 -*-
import logging

from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from admin.rdm.utils import RdmPermissionMixin

logger = logging.getLogger(__name__)


class ExportDataActionView(RdmPermissionMixin, APIView):
    raise_exception = True
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        institution_id = request.data.get('institution_id')
        source_id = request.data.get('source_id')
        location_id = request.data.get('location_id')
        logger.debug(f'institution_id: {institution_id}')
        logger.debug(f'source_id: {source_id}')
        logger.debug(f'location_id: {location_id}')
        return Response({'task_id': f'task_{institution_id}_{source_id}_{location_id}'}, status=status.HTTP_200_OK)


class StopExportDataActionView(RdmPermissionMixin, APIView):
    raise_exception = True
    parser_classes = [JSONParser]

    def post(self, request, **kwargs):
        institution_id = request.data.get('institution_id')
        source_id = request.data.get('source_id')
        location_id = request.data.get('location_id')
        task_id = request.data.get('task_id')
        logger.debug(f'institution_id: {institution_id}')
        logger.debug(f'source_id: {source_id}')
        logger.debug(f'location_id: {location_id}')
        logger.debug(f'task_id: {task_id}')
        return Response({'task_id': task_id}, status=status.HTTP_200_OK)
