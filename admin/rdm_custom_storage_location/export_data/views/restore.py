from celery.result import AsyncResult
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location.tasks import pre_restore_export_data
from osf.models.institution import Institution

class ExportDataRestore(RdmPermissionMixin, APIView):
    raise_exception = True

    def get_object(self, queryset=None):
        return Institution.objects.get(id=self.kwargs.get('institution_id'))

    def post(self, request, **kwargs):
        institution = self.get_object()
        institution_guid = institution._id
        destination_id = request.POST.get('destination_id', default='1')
        source_id = request.POST.get('source_id', default='1')
        export_id = request.POST.get('export_id', default='1')
        cookies = request.COOKIES
        process = pre_restore_export_data.delay(cookies, institution_guid, source_id, export_id, destination_id)
        return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


class ExportDataRestoreTaskStatus(RdmPermissionMixin, APIView):
    def get(self, request, **kwargs):
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
