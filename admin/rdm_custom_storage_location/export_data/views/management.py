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
from admin.rdm_custom_storage_location.export_data.utils import process_data_infomation, get_list_file_info, \
    get_link_delete_export_data
from osf.models import ExportDataLocation, ExportData, Institution
from .location import ExportStorageLocationViewBaseView

logger = logging.getLogger(__name__)

CURRENT_DATA_INFORMATION = []


def get_export_data(user_institution_guid, selected_export_location=None, selected_source=None, deleted=False,
                    check_delete=True):
    # Get export data following user_institution_guid
    list_source_id = Region.objects.filter(_id=user_institution_guid).values_list('id', flat=True)
    list_location_id = ExportDataLocation.objects.filter(institution_guid=user_institution_guid).values_list('id',
                                                                                                             flat=True)
    list_export_data = ExportData.objects.filter(is_deleted=deleted, location_id__in=list_location_id,
                                                 source_id__in=list_source_id).order_by(
        'id') if check_delete else ExportData.objects.filter(location_id__in=list_location_id,
                                                             source_id__in=list_source_id).order_by('id')
    list_data = []
    for export_data in list_export_data:
        data = {'export_data': export_data}
        for location in ExportDataLocation.objects.filter(institution_guid=user_institution_guid):
            if export_data.location_id == location.id:
                if selected_export_location:
                    if selected_export_location == str(location.id):
                        data['location_name'] = location.name
                else:
                    data['location_name'] = location.name
        for source in Region.objects.filter(_id=user_institution_guid):
            if export_data.source_id == source.id:
                data['source_id'] = source.id
                if selected_source:
                    if selected_source == str(source.id):
                        data['source_name'] = source.name
                else:
                    data['source_name'] = source.name
        if 'location_name' in data and 'source_name' in data:
            list_data.append(data)
    logger.info('get_export_data function')
    logger.info(list_data)
    return list_data


class ExportBaseView(ExportStorageLocationViewBaseView, ListView):
    raise_exception = True
    paginate_by = 10

    def get_queryset(self):
        list_export_data = self.get_export_data_list()
        return list_export_data

    def get_context_data(self, **kwargs):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        user_institution_name = Institution.objects.get(
            id=self.request.user.representative_affiliated_institution.id).name
        self.query_set = self.get_queryset()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)
        kwargs['institution_name'] = user_institution_name
        kwargs['list_export_data'] = self.query_set
        kwargs['list_location'] = ExportDataLocation.objects.filter(institution_guid=user_institution_guid)
        kwargs['list_storage'] = Region.objects.filter(_id=user_institution_guid)
        kwargs['selected_source'] = 0
        kwargs['selected_location_export'] = 0
        kwargs['page'] = self.page
        kwargs['source_id'] = self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0
        return super(ExportBaseView, self).get_context_data(**kwargs)

    def get_export_data_list(self):
        raise NotImplementedError(
            '{0} is missing the implementation of the get_export_data_list() method.'.format(self.__class__.__name__)
        )

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
        storage_id = self.kwargs.get('storage_id')

        selected_storage = request.GET.get('storage_name') if 'storage_name' in dict(request.GET) else 0
        selected_location_export = request.GET.get('location_export_name') if 'location_export_name' in dict(
            request.GET) else 0
        self.query_set = get_export_data(self.institution_guid, selected_location_export, selected_storage)
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = self.paginate_queryset(self.query_set,
                                                                                              self.page_size)
        locations = self.get_default_storage_location().union(self.institution.get_storage_location())
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_export),
            'list_storage': Region.objects.filter(_id=self.institution_guid),
            'selected_source': int(selected_storage),
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)

    def get_export_data_list(self):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        return get_export_data(user_institution_guid)


class ExportDataDeletedListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'

    def get(self, request, *args, **kwargs):
        self.load_institution()
        storage_id = self.kwargs.get('storage_id')

        selected_storage = request.GET.get('storage_name') if 'storage_name' in dict(request.GET) else 0
        selected_location_export = request.GET.get('location_export_name') if 'location_export_name' in dict(
            request.GET) else 0
        self.query_set = get_export_data(self.institution_guid, selected_location_export, selected_storage,
                                         deleted=True)
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = self.paginate_queryset(self.query_set,
                                                                                              self.page_size)
        locations = self.get_default_storage_location().union(self.institution.get_storage_location())
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_export),
            'list_storage': Region.objects.filter(_id=self.institution_guid),
            'selected_source': int(selected_storage),
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)

    def get_export_data_list(self):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        return get_export_data(user_institution_guid, deleted=True)


class ExportDataInformationView(ExportStorageLocationViewBaseView, DetailView, ListView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'
    raise_exception = True
    paginate_by = 1

    def get_object(self):
        user_institution_guid = self.request.user.representative_affiliated_institution.guid
        for item in get_export_data(user_institution_guid, check_delete=False):
            if str(item['export_data'].id) == self.kwargs.get('data_id'):
                return item
        raise Http404(
            'Export data with id "{}" not found.'.format(
                self.kwargs.get('data_id')
            ))

    def get_context_data(self, **kwargs):
        self.object_list = []
        self.query_set = []
        data = self.get_object()
        process_start = data['export_data'].process_start
        process_start = str(process_start).split('+')[0].replace('-', '').replace(':', '').replace(' ', '')
        provider = Region.objects.get(id=data['source_id'])
        processed_list_file_info = kwargs.pop('object_list', None)
        user_institution_name = Institution.objects.get(
            id=self.request.user.representative_affiliated_institution.id).name
        user_institution_guid = self.request.user.representative_affiliated_institution.guid
        list_file_info, status_code = get_list_file_info('28zuw', 'osfstorage', '/', self.request.COOKIES,
                                                         user_institution_guid, process_start)
        logger.info('status_code')
        logger.info(status_code)
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
            _id__in=self.request.user.representative_affiliated_institution.guid)
        context['page'] = self.page
        return context


class DeleteExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def post(self, request):
        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        if list_export_data:
            if check_delete_permanently:
                logger.info('check_delete_permanently = on')
                logger.info(list_export_data)
                user_institution_guid = request.user.representative_affiliated_institution.guid
                list_content, status_code = get_link_delete_export_data('28zuw', 'osfstorage', '/', request.COOKIES)
                if status_code == 200:
                    for item in get_export_data(user_institution_guid, check_delete=False):
                        if str(item['export_data'].id) in list_export_data:
                            logger.info(str(item['export_data'].id))
                            process_start = item['export_data'].process_start
                            process_start = str(process_start).split('+')[0].replace('-', '').replace(':', '').replace(
                                ' ',
                                '')
                            for export_file in list_content:
                                if export_file['attributes']['name'] == 'file_info_{}_{}.json'.format(
                                        user_institution_guid,
                                        process_start):
                                    logger.info(export_file['links'])
                            # try:
                            #     url = waterbutler_api_url_for(
                            #         '28zuw', 'osfstorage', path='/6306f97a0521a816bf92a319', _internal=True
                            #     )
                            #     response = requests.delete(
                            #         url,
                            #         headers={'content-type': 'application/json'},
                            #         cookies=request.COOKIES
                            #     )
                            # except Exception as err:
                            #     messages.error(err)
                            # status_code = response.status_code
                            # response.close()
                            # if status_code == 204:
                            #     ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
                            #     # ExportData.objects.filter(id__in=list_export_data).delete()
                            # else:
                            #     messages.error(request, 'Cannot connect to the export data storage location')
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

    def get(self, data_id):
        guid = self.request.user.representative_affiliated_institution.guid
        current_datetime = str('{date:%Y-%m-%d-%H%M%S}'.format(date=datetime.datetime.now())).replace('-', '')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=file_info_{}_{}.csv'.format(guid, current_datetime)
        writer = csv.writer(response)
        writer.writerow(
            ['project_id', 'project_name', 'owner', 'file_id', 'file_path', 'filename', 'versions', 'size'])
        # data = request.POST.get('list_data') if 'list_data' in request.POST else []
        # data = get_list_file_info('28zuw', 'osfstorage', '/', request.COOKIES, guid)
        # processed_list_file_info = process_data_infomation(data['files'])
        global CURRENT_DATA_INFORMATION
        for file in CURRENT_DATA_INFORMATION:
            writer.writerow(
                [file['project']['id'], file['project']['name'], file['version']['contributor'], file['id'],
                 file['materialized_path'],
                 file['name'],
                 file['version']['identifier'], file['version']['size']])
        CURRENT_DATA_INFORMATION = []
        return response
