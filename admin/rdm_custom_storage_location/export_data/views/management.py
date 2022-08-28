# -*- coding: utf-8 -*-
import csv
import datetime
import logging

from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView, DetailView

from addons.osfstorage.models import Region
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location.export_data.utils import (
    process_data_infomation,
    get_list_file_info,
    get_files_from_waterbutler,
    delete_file_export
)
from osf.models import ExportData, Institution
from .location import ExportStorageLocationViewBaseView

logger = logging.getLogger(__name__)

CURRENT_DATA_INFORMATION = []


def get_export_data(institution_guid, selected_location_id=None, selected_source_id=None, deleted=False,
                    check_delete=True):
    institution = Institution.load(institution_guid)
    locations = institution.get_allowed_storage_location()
    list_location_id = locations.values_list('id', flat=True)
    logger.debug(f'list_location_id: {list_location_id}')

    source_storages = institution.get_institutional_storage()
    list_source_id = source_storages.values_list('id', flat=True)
    logger.debug(f'list_source_id: {list_source_id}')

    # Get export data following user_institution_guid
    list_export_data = ExportData.objects.filter(location_id__in=list_location_id, source_id__in=list_source_id)
    if check_delete:
        list_export_data = list_export_data.filter(is_deleted=deleted)
    if selected_location_id:
        list_export_data = list_export_data.filter(location_id=selected_location_id)
    if selected_source_id:
        list_export_data = list_export_data.filter(source_id=selected_source_id)
    list_export_data = list_export_data.order_by('id')

    list_data = []
    logger.debug(f'list_export_data: {len(list_export_data)}')
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
        user_institution_guid = self.institution_guid
        # storage_id = self.kwargs.get('storage_id')
        selected_storage = int(request.GET.get('storage_name'))
        selected_location_export = int(request.GET.get('location_export_name'))
        self.query_set = get_export_data(user_institution_guid, selected_location_export, selected_storage)
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = self.paginate_queryset(self.query_set,
                                                                                              self.page_size)
        locations = self.institution.get_allowed_storage_location()
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': selected_location_export,
            'list_storage': Region.objects.filter(_id=user_institution_guid).order_by('pk'),
            'selected_source': selected_storage,
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)


class ExportDataDeletedListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'

    def get(self, request, *args, **kwargs):
        self.load_institution()
        user_institution_guid = self.institution_guid
        # storage_id = self.kwargs.get('storage_id')
        selected_storage = int(request.GET.get('storage_name'))
        selected_location_export = int(request.GET.get('location_export_name'))
        self.query_set = get_export_data(user_institution_guid, selected_location_export, selected_storage,
                                         deleted=True)
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = self.paginate_queryset(self.query_set,
                                                                                              self.page_size)
        locations = self.institution.get_allowed_storage_location()
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': selected_location_export,
            'list_storage': Region.objects.filter(_id=user_institution_guid).order_by('pk'),
            'selected_source': selected_storage,
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)


class ExportDataInformationView(ExportStorageLocationViewBaseView, DetailView, ListView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'
    raise_exception = True
    paginate_by = 1

    def get_object(self, **kwargs):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        for item in get_export_data(user_institution_guid, check_delete=False):
            if str(item['export_data'].id) == self.kwargs.get('data_id'):
                return item
        raise Http404(
            'Export data with id {} not found.'.format(
                self.kwargs.get('data_id')
            ))

    def get_context_data(self, **kwargs):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        self.object_list = []
        self.query_set = []
        data = self.get_object()
        process_start = data['export_data'].process_start
        process_start = str(process_start).split('+')[0].replace('-', '').replace(':', '').replace(' ', 'T')
        provider = Region.objects.get(id=data['source_id'])
        pid = '28zuw'
        provider_name = 'osfstorage'
        processed_list_file_info = kwargs.pop('object_list', None)
        user_institution_name = Institution.objects.get(
            id=self.request.user.representative_affiliated_institution.id).name
        list_file_info, status_code = get_list_file_info(pid, provider_name, '/', self.request.COOKIES,
                                                         user_institution_guid, process_start)
        if status_code == 555:
            messages.error(self.request, 'The export data files are corrupted')
        elif status_code != 200:
            messages.error(self.request, 'Cannot connect to the export data storage location')
        else:
            processed_list_file_info = process_data_infomation(list_file_info['files'])
            global CURRENT_DATA_INFORMATION
            CURRENT_DATA_INFORMATION = processed_list_file_info
            self.object_list = processed_list_file_info
            self.query_set = processed_list_file_info
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = self.paginate_queryset(self.query_set,
                                                                                              self.page_size)
        context = super(ExportDataInformationView, self).get_context_data(**kwargs)
        context['is_deleted'] = data['export_data'].is_deleted
        context['data_information'] = data
        context['list_file_info'] = self.query_set
        context['institution_name'] = user_institution_name
        context['source_id'] = data['source_id'] if len(data) > 0 else 0
        context['provider_name'] = 'Export Data Information of {} storage'.format(
            provider.waterbutler_settings['storage']['provider'])
        context['storages'] = Region.objects.exclude(
            _id__in=user_institution_guid)
        context['page'] = self.page
        return context


class DeleteExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def post(self, request):
        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        pid = '28zuw'
        provider = 'osfstorage'
        if list_export_data:
            if check_delete_permanently:
                user_institution_guid = request.user.representative_affiliated_institution.guid
                list_content, status_code = get_files_from_waterbutler(pid, provider, '/', request.COOKIES)
                if status_code == 200:
                    for item in get_export_data(user_institution_guid, check_delete=False):
                        if str(item['export_data'].id) in list_export_data:
                            process_start = item['export_data'].process_start
                            process_start = str(process_start).split('+')[0].replace('-', '').replace(':', '').replace(
                                ' ',
                                'T')
                            link_delete = None
                            for export_file in list_content:
                                if export_file['attributes']['name'] == 'file_info_{}_{}.json'.format(
                                        user_institution_guid,
                                        process_start):
                                    link_delete = export_file['links']['delete']
                                    break
                            if link_delete:
                                link_delete = link_delete.split('/')
                                status_code = delete_file_export(pid, provider, link_delete[-1], request.COOKIES)
                                if status_code == 204:
                                    ExportData.objects.filter(id=item['export_data'].id).delete()
                                else:
                                    messages.error(request, 'Cannot connect to the export data storage location')
                else:
                    messages.error(request, 'Cannot connect to the export data storage location')
            else:
                ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
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
