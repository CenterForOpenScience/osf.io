from celery.contrib.abortable import AbortableAsyncResult
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location.tasks import check_before_restore_export_data, restore_export_data


class ExportDataRestore(RdmPermissionMixin, APIView):
    raise_exception = True

    def post(self, request, **kwargs):
        destination_id = request.POST.get('destination_id', default='-1')
        export_id = self.kwargs.get('export_id')
        cookies = request.COOKIES
        from_confirm_dialog = request.POST.get('from_confirm_dialog', default=False)
        if not from_confirm_dialog:
            process = check_before_restore_export_data.delay(cookies, export_id, destination_id)
        else:
            process = restore_export_data.delay(cookies, export_id, destination_id)
        return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


class ExportDataRestoreTaskStatus(RdmPermissionMixin, APIView):
    def get(self, request, **kwargs):
        task_id = request.GET.get('task_id', default='')
        task = AbortableAsyncResult(task_id)
        response = {
            'state': task.state,
        }
        if task.result is not None:
            response = {
                'state': task.state,
                'result': task.result if isinstance(task.result, str) else task.result.__dict__,
            }
        return Response(response, status=status.HTTP_200_OK)
