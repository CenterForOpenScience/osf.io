from celery.result import AsyncResult
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location.tasks import pre_restore_export_data


class ExportDataRestore(RdmPermissionMixin, APIView):
    raise_exception = True

    def post(self, request, *args, **kwargs):
        destination_id = request.POST.get('destination_id', default='-1')
        cookies = request.COOKIES
        process = pre_restore_export_data.delay(cookies, 'rdygz', 1, 1, destination_id)
        return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


class ExportDataRestoreTaskStatus(RdmPermissionMixin, APIView):
    def get(self, request, *args, **kwargs):
        task_id = request.GET.get('task_id', default='-1')
        task = AsyncResult(task_id)
        response = {
            'state': task.state,
        }
        if task.state != 'FAILURE':
            response = {
                'state': task.state,
                'result': task.result,
            }
        return Response(response, status=status.HTTP_200_OK)
