# -*- coding: utf-8 -*-
import csv
import datetime
import logging

from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView, DetailView

from addons.osfstorage.models import Region
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location.export_data.utils import (
    process_data_infomation,
    validate_export_data,
    get_file_info_json,
    count_files_ng_ok,
)
from osf.models import ExportData, Institution, ExportDataLocation, ExportDataRestore
from .location import ExportStorageLocationViewBaseView

logger = logging.getLogger(__name__)

CURRENT_DATA_INFORMATION = []


def get_export_data(institution_guid, selected_location_id=None, selected_source_id=None, deleted=False,
                    check_delete=True):
    institution = Institution.load(institution_guid)
    locations = institution.get_allowed_storage_location()
    list_location_id = locations.values_list('id', flat=True)

    source_storages = institution.get_institutional_storage()
    list_source_id = source_storages.values_list('id', flat=True)

    # Get export data following user_institution_guid
    list_export_data = ExportData.objects.filter(
        location_id__in=list_location_id,
        source_id__in=list_source_id,
        status__in=ExportData.EXPORT_DATA_AVAILABLE
    )
    if check_delete:
        list_export_data = list_export_data.filter(is_deleted=deleted)
    if selected_location_id:
        list_export_data = list_export_data.filter(location_id=selected_location_id)
    if selected_source_id:
        list_export_data = list_export_data.filter(source_id=selected_source_id)
    list_export_data = list_export_data.order_by('id')

    list_data = []
    for export_data in list_export_data:
        data = {
            'export_data': export_data,
            'location_name': export_data.location.name,
            'source_id': export_data.source.id,
            'source_name': export_data.source.name
        }
        list_data.append(data)
    return list_data


class ExportBaseView(ExportStorageLocationViewBaseView, ListView):
    raise_exception = True
    paginate_by = 10

    def get_queryset(self):
        raise NotImplementedError(
            '{0} is missing the implementation of the get_queryset() method.'.format(self.__class__.__name__)
        )

    def get_context_data(self, **kwargs):
        return super(ExportBaseView, self).get_context_data(**kwargs)

    def load_institution(self):
        institution_id = self.kwargs.get('institution_id')

        if institution_id:
            # superuser admin can access it
            self.institution = Institution.objects.get(id=institution_id)
            self.institution_guid = self.institution.guid
        else:
            # institutional admin access without institution_id -> get from representative_affiliated_institution
            if not institution_id and self.request.user.is_affiliated_institution:
                self.institution = self.request.user.representative_affiliated_institution
                if self.institution:
                    self.institution_guid = self.institution.guid
                    institution_id = self.institution.id

            # skip if institution_id
            if not institution_id and self.is_super_admin:
                self.institution = Institution.objects.first()
                self.institution_guid = self.institution.guid
                institution_id = self.institution.id

        # skip if is_affiliated_institution
        # institutional admin access with invalid institution_id
        if not self.is_super_admin and not self.is_affiliated_institution(institution_id):
            self.handle_no_permission()


class ExportDataListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_list.html'

    def get(self, request, *args, **kwargs):
        self.load_institution()

        locations = self.institution.get_allowed_storage_location()
        selected_location_id = request.GET.get('location_id')
        if not selected_location_id and locations.exists():
            selected_location_id = locations.first().id

        source_storages = self.institution.get_institutional_storage()
        selected_source_id = self.kwargs.get('storage_id', request.GET.get('storage_id'))
        if not selected_source_id and source_storages.exists():
            selected_source_id = source_storages.first().id

        self.query_set = get_export_data(self.institution_guid, selected_location_id, selected_source_id)
        self.page_size = self.get_paginate_by(self.query_set)
        _, self.page, self.query_set, _ = self.paginate_queryset(self.query_set, self.page_size)
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_id) if selected_location_id else 0,
            'source_storages': source_storages,
            'selected_source_id': int(selected_source_id) if selected_source_id else 0,
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)


class ExportDataDeletedListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'

    def get(self, request, *args, **kwargs):
        self.load_institution()

        locations = self.institution.get_allowed_storage_location()
        selected_location_id = request.GET.get('location_id')
        if not selected_location_id and locations.exists():
            selected_location_id = locations.first().id

        source_storages = self.institution.get_institutional_storage()
        selected_source_id = self.kwargs.get('storage_id', request.GET.get('storage_id'))
        if not selected_source_id and source_storages.exists():
            selected_source_id = source_storages.first().id

        self.query_set = get_export_data(self.institution_guid, selected_location_id, selected_source_id, deleted=True)
        self.page_size = self.get_paginate_by(self.query_set)
        _, self.page, self.query_set, _ = self.paginate_queryset(self.query_set, self.page_size)
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_id) if selected_location_id else 0,
            'source_storages': source_storages,
            'selected_source_id': int(selected_source_id) if selected_source_id else 0,
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)


class ExportDataInformationView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'

    def get_object(self, **kwargs):
        export_data = ExportData.objects.filter(id=self.kwargs.get('data_id')).first()
        if export_data:
            return export_data
        raise Http404(
            'Export data with id {} not found.'.format(
                self.kwargs.get('data_id')
            ))

    def get(self, request, *args, **kwargs):
        self.load_institution()

        cookie = self.request.user.get_or_create_cookie().decode()
        cookies = self.request.COOKIES

        kwargs.pop('object_list', None)
        self.object_list = []
        self.query_set = []
        export_data = self.get_object()

        source_storages = self.institution.get_institutional_storage()
        location = export_data.location
        storage_name = location.waterbutler_settings['storage']['provider']
        if storage_name == 'filesystem':
            storage_name = 'NII Storage'

        # get file_info from location
        response = export_data.read_file_info_from_location(cookies, cookie=cookie)
        status_code = response.status_code
        if status_code != 200:
            raise SuspiciousOperation('Cannot connect to the export data storage location.')
        # validate list_file_info
        list_file_info = response.json()
        check = validate_export_data(list_file_info)
        if not check:
            raise SuspiciousOperation('The export data files are corrupted.')

        processed_list_file_info = process_data_infomation(list_file_info['files'])
        global CURRENT_DATA_INFORMATION
        CURRENT_DATA_INFORMATION = processed_list_file_info
        self.object_list = processed_list_file_info
        self.query_set = processed_list_file_info

        self.page_size = self.get_paginate_by(self.query_set)
        _, self.page, self.query_set, _ = self.paginate_queryset(self.query_set, self.page_size)

        context = {
            'institution': self.institution,
            'destination_storages': source_storages,
            'export_data': export_data,
            'file_versions': self.query_set,
            'page': self.page,
        }
        return render(request, self.template_name, context)


class DeleteExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def post(self, request):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        list_export_data_delete = request.POST.get('list_id_export_data').split('#')
        list_export_data_delete = list(filter(None, list_export_data_delete))
        if check_delete_permanently:
            for item in ExportData.objects.filter(id__in=list_export_data_delete, is_deleted=False):
                response = item.delete_export_data_folder(cookies, cookie=cookie)
                if response.status_code == 204:
                    ExportData.objects.filter(id=item.id).delete()
                else:
                    raise SuspiciousOperation('Cannot connect to the export data storage location.')
        else:
            ExportData.objects.filter(id__in=list_export_data_delete).update(is_deleted=True)
        return redirect('custom_storage_location:export_data:export_data_list')


class RevertExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def post(self, request):
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        if list_export_data:
            ExportData.objects.filter(id__in=list_export_data).update(is_deleted=False)
        return redirect('custom_storage_location:export_data:export_data_deleted_list')


class ExportDataFileCSVView(RdmPermissionMixin, View):

    def get(self, *args, **kwargs):
        guid = self.request.user.representative_affiliated_institution.guid
        current_datetime = str('{date:%Y-%m-%d-%H%M%S}'.format(date=datetime.datetime.now())).replace('-', '')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=file_info_{}_{}.csv'.format(guid, current_datetime)
        writer = csv.writer(response)
        writer.writerow(
            ['project_id', 'project_name', 'owner', 'file_id', 'file_path', 'filename', 'versions', 'size'])
        global CURRENT_DATA_INFORMATION
        for file in CURRENT_DATA_INFORMATION:
            writer.writerow(
                [file['project']['id'], file['project']['name'], file['version']['contributor'], file['id'],
                 file['materialized_path'],
                 file['name'],
                 file['version']['identifier'], file['version']['size']])
        CURRENT_DATA_INFORMATION = []
        return response


class CheckExportData(RdmPermissionMixin, View):

    def get(self, request, data_id):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        export_data = ExportData.objects.filter(id=data_id).first()
        if export_data.status != 'Completed':
            return JsonResponse({'message': 'Cannot check in this time. The process is {}'.format(export_data.status)}, status=400)
        export_data.status = 'Checking'
        export_data.last_check = datetime.datetime.now()
        # Get list file info from source storage
        response = export_data.read_file_info_from_location(cookies, cookie=cookie)
        status_code = response.status_code
        if status_code != 200:
            return JsonResponse({'message': 'Cannot connect to the export data storage location.'}, status=400)
        list_file_info = response.json()
        check = validate_export_data(list_file_info)
        if not check:
            return JsonResponse({'message': 'The export data files are corrupted.'}, status=400)
        # Get data from current source from database
        data_from_source = get_file_info_json(export_data.source.id)
        data = count_files_ng_ok(list_file_info, data_from_source)
        export_data.status = 'Completed'
        return JsonResponse(data, status=200)


class CheckRestoreData(RdmPermissionMixin, View):

    def get(self, request, data_id):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        export_data_restore = ExportDataRestore.objects.filter(id=data_id).first()
        if export_data_restore.status != 'Completed':
            return JsonResponse({'message': 'Cannot check in this time. The process is {}'.format(export_data_restore.status)}, status=400)
        export_data_restore.status = 'Checking'
        export_data_restore.last_check = datetime.datetime.now()
        response = export_data_restore.export.read_file_info_from_location(cookies, cookie=cookie)
        if response.status_code != 200:
            return JsonResponse({'message': 'Cannot connect to the export data storage location.'}, status=400)
        list_file_info = response.json()
        check = validate_export_data(list_file_info)
        if not check:
            return JsonResponse({'message': 'The export data files are corrupted.'}, status=400)
        # Get data from current source from database
        destination_id = export_data_restore.destination.id
        data_from_destination = get_file_info_json(destination_id)
        data = count_files_ng_ok(list_file_info, data_from_destination)
        export_data_restore.status = 'Completed'
        return JsonResponse(data, status=200)
