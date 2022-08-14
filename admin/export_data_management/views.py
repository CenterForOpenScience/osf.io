from osf.models import Institution
from django.views.generic import ListView
from admin.rdm.utils import RdmPermissionMixin
from admin.base import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from admin.export_data_management.tasks import pre_restore_export_data
from celery.result import AsyncResult

class ExportDataManagement(RdmPermissionMixin, ListView):
    paginate_by = 100
    ordering = 'name'
    template_name = 'export_data_management/list_export_data.html'
    raise_exception = True
    model = Institution

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set,
            page_size
        )
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(ExportDataManagement, self).get_context_data(**kwargs)


class ExportDataRestore(RdmPermissionMixin, APIView):
    raise_exception = True

    def post(self, request, *args, **kwargs):
        destination_id = request.POST.get('destination_id', default='-1')
        process = pre_restore_export_data.delay(1, 1, destination_id)
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
