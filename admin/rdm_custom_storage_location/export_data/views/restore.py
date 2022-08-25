from celery.contrib.abortable import AbortableAsyncResult
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location.tasks import check_before_restore_export_data, restore_export_data, rollback_restore
from osf.models import ExportDataRestore


class ExportDataRestoreView(RdmPermissionMixin, APIView):
    raise_exception = True

    def post(self, request, **kwargs):
        source_id = request.POST.get('source_id')
        destination_id = request.POST.get('destination_id')
        export_id = self.kwargs.get('export_id')
        cookies = request.COOKIES
        is_from_confirm_dialog = request.POST.get('is_from_confirm_dialog', default=False)
        if source_id is None or destination_id is None or export_id is None:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        if not is_from_confirm_dialog:
            result = check_before_restore_export_data(cookies, export_id, source_id, destination_id)
            if result["open_dialog"]:
                # If open_dialog is True, return HTTP 200 with empty response
                return Response({}, status=status.HTTP_200_OK)
            elif result["error_message"]:
                # If there is error message, return HTTP 400
                return Response({'error_message': result["error_message"]}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Otherwise, start restore data task and return task id
                process = restore_export_data.delay(cookies, export_id, source_id, destination_id)
                return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)
        else:
            # If user clicked 'Restore' button in confirm dialog, start restore data task and return task id
            export_data_restore_id = request.POST.get('export_data_restore_id')
            process = restore_export_data.delay(cookies, export_id, source_id, destination_id, export_data_restore_id)
            return Response({'task_id': process.task_id}, status=status.HTTP_200_OK)


@api_view(http_method_names=["POST"])
def stop_export_data_restore(request, *args, **kwargs):
    task_id = request.POST.get('task_id')
    source_id = request.POST.get('source_id')
    destination_id = request.POST.get('destination_id', default='-1')
    export_id = kwargs.get('export_id')
    export_data_restore_id = request.POST.get('export_data_restore_id')
    cookies = request.COOKIES

    if source_id is None or destination_id is None or export_id is None or task_id is None:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    # Update process status
    export_data_restore = ExportDataRestore.objects.get(id=export_data_restore_id)
    export_data_restore.status = "Stopping"
    export_data_restore.save()

    # Abort current task
    task = AbortableAsyncResult(task_id)
    task.abort()

    # Rollback restore data
    rollback_restore(cookies, export_id, source_id, destination_id)
    return Response({}, status=status.HTTP_200_OK)


class ExportDataRestoreTaskStatusView(RdmPermissionMixin, APIView):
    def get(self, request, **kwargs):
        task_id = request.GET.get('task_id')
        if task_id is None:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
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
