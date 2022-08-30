# -*- coding: utf-8 -*-
import csv
import datetime
import logging

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
)
from osf.models import ExportData, Institution, ExportDataLocation
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
        status__in=[ExportData.STATUS_COMPLETED, ExportData.STATUS_CHECKING]
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
            if not institution_id and self.is_affiliated_institution:
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

        query_set = get_export_data(self.institution_guid, selected_location_id, selected_source_id)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        context = {
            'institution': self.institution,
            'list_export_data': query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_id) if selected_location_id else 0,
            'source_storages': source_storages,
            'selected_source_id': int(selected_source_id) if selected_source_id else 0,
            'source_id': query_set[0]['source_id'] if len(query_set) > 0 else 0,
            'page': page,
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

        query_set = get_export_data(self.institution_guid, selected_location_id, selected_source_id, deleted=True)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        context = {
            'institution': self.institution,
            'list_export_data': query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_id) if selected_location_id else 0,
            'source_storages': source_storages,
            'selected_source_id': int(selected_source_id) if selected_source_id else 0,
            'source_id': query_set[0]['source_id'] if len(query_set) > 0 else 0,
            'page': page,
        }
        return render(request, self.template_name, context)


class ExportDataInformationView(ExportStorageLocationViewBaseView, DetailView, ListView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'
    raise_exception = True
    paginate_by = 1

    def get_object(self, **kwargs):
        export_data = ExportData.objects.filter(id=self.kwargs.get('data_id')).first()
        if export_data:
            return export_data
        raise Http404(
            'Export data with id {} not found.'.format(
                self.kwargs.get('data_id')
            ))

    def get_context_data(self, **kwargs):
        kwargs.pop('object_list', None)
        institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            institution_guid = self.request.user.representative_affiliated_institution.guid
        self.object_list = []
        self.query_set = []
        export_data = self.get_object()

        location = export_data.location
        storage_name = location.waterbutler_settings['storage']['provider']
        if storage_name == 'filesystem':
            storage_name = 'NII Storage'

        user_institution_name = Institution.objects.get(_id=institution_guid).name
        response = export_data.read_file_info(self.request.COOKIES)
        status_code = response.status_code
        if status_code != 200:
            raise Http404('Cannot connect to the export data storage location.')
        else:
            list_file_info = response.json()
            check = validate_export_data(list_file_info)
            if not check:
                raise Http404('The export data files are corrupted.')
            processed_list_file_info = process_data_infomation(list_file_info['files'])
            global CURRENT_DATA_INFORMATION
            CURRENT_DATA_INFORMATION = processed_list_file_info
            self.object_list = processed_list_file_info
            self.query_set = processed_list_file_info

        self.page_size = self.get_paginate_by(self.query_set)
        _, self.page, self.query_set, _ = self.paginate_queryset(self.query_set, self.page_size)

        context = super(ExportDataInformationView, self).get_context_data(**kwargs)
        context['is_deleted'] = export_data.is_deleted
        context['data_information'] = export_data
        context['list_file_info'] = self.query_set
        context['institution_name'] = user_institution_name
        context['source_name'] = storage_name
        context['location'] = ExportDataLocation.objects.filter(id=export_data.location_id).first()
        context['title'] = 'Export Data Information of {} storage'.format(storage_name)
        context['storages'] = Region.objects.exclude(
            _id__in=institution_guid)
        context['page'] = self.page
        return context


class DeleteExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def post(self, request):
        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        list_export_data_delete = request.POST.get('list_id_export_data').split('#')
        list_export_data_delete = list(filter(None, list_export_data_delete))
        if check_delete_permanently:
            for item in ExportData.objects.filter(id__in=list_export_data_delete, is_deleted=False):
                response = item.delete_export_data_folder(request.COOKIES)
                if response.status_code == 204:
                    ExportData.objects.filter(id=item.id).delete()
                else:
                    raise Http404('Cannot connect to the export data storage location.')
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
        logger.info(data_id)
        export_data = ExportData.objects.filter(id=data_id).first()
        if export_data.status != 'Completed':
            return JsonResponse({'message': 'Cannot check in this time. The process is {}'.format(export_data.status)}, status=400)
        # export_data.status = 'Checking'
        # export_data.last_check = datetime.datetime.now()
        response = export_data.read_file_info(request.COOKIES)
        status_code = response.status_code
        if status_code != 200:
            return JsonResponse({'message': 'Cannot connect to the export data storage location.'}, status=400)
        list_file_info = response.json()
        check = validate_export_data(list_file_info)
        if not check:
            return JsonResponse({'message': 'The export data files are corrupted.'}, status=400)
        data_from_source = get_file_info_json(export_data.source.id)
        # logger.info(list_file_info)
        # logger.info(data_from_source)
        # export_data.status = 'Completed'
        return JsonResponse({'NG': 10, 'OK': 20, 'Total': 30}, status=200)
