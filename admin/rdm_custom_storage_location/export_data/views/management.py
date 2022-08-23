# -*- coding: utf-8 -*-
import csv
import datetime
import logging
import requests

from admin.rdm.utils import RdmPermissionMixin
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render, redirect
from api.base.utils import waterbutler_api_url_for
from django.views import View
from django.views.generic import ListView, DetailView
from rest_framework import status as http_status

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import utils
from osf.models import ExportDataLocation, ExportData, Institution
from .location import ExportStorageLocationViewBaseView

logger = logging.getLogger(__name__)


def test_connection(data, institution=None):
    provider_short_name = data.get('provider')
    if not provider_short_name:
        response = {
            'message': 'Provider is missing.'
        }
        return JsonResponse(response, status=http_status.HTTP_400_BAD_REQUEST)

    result = None

    if provider_short_name == 's3':
        result = utils.test_s3_connection(
            data.get('access_key'),
            data.get('secret_key'),
            data.get('bucket'),
        )
    elif provider_short_name == 's3compat':
        result = utils.test_s3compat_connection(
            data.get('endpoint_url'),
            data.get('access_key'),
            data.get('secret_key'),
            data.get('bucket'),
        )
    elif provider_short_name == 's3compatb3':
        result = utils.test_s3compatb3_connection(
            data.get('endpoint_url'),
            data.get('access_key'),
            data.get('secret_key'),
            data.get('bucket'),
        )
    elif provider_short_name == 's3compatinstitutions':
        result = utils.test_s3compat_connection(
            data.get('endpoint_url'),
            data.get('access_key'),
            data.get('secret_key'),
            data.get('bucket'),
        )
    elif provider_short_name == 'ociinstitutions':
        result = utils.test_s3compatb3_connection(
            data.get('endpoint_url'),
            data.get('access_key'),
            data.get('secret_key'),
            data.get('bucket'),
        )
    elif provider_short_name == 'owncloud':
        result = utils.test_owncloud_connection(
            data.get('host'),
            data.get('username'),
            data.get('password'),
            data.get('folder'),
            provider_short_name,
        )
    elif provider_short_name == 'nextcloud':
        result = utils.test_owncloud_connection(
            data.get('host'),
            data.get('username'),
            data.get('password'),
            data.get('folder'),
            provider_short_name,
        )
    elif provider_short_name == 'nextcloudinstitutions':
        result = utils.test_owncloud_connection(
            data.get('host'),
            data.get('username'),
            data.get('password'),
            data.get('folder'),
            provider_short_name,
        )
    elif provider_short_name == 'swift':
        result = utils.test_swift_connection(
            data.get('auth_version'),
            data.get('auth_url'),
            data.get('access_key'),
            data.get('secret_key'),
            data.get('tenant_name'),
            data.get('user_domain_name'),
            data.get('project_domain_name'),
            data.get('container'),
        )
    elif provider_short_name == 'dropboxbusiness':
        result = utils.test_dropboxbusiness_connection(institution)
    else:
        result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)

    return JsonResponse(result[0], status=result[1])


def get_list_file_detail(data, pid, provider, request_cookie, guid=None):
    data_json = None
    for file_info in data:
        if file_info['attributes']['name'] == 'file_info_{}.json'.format(guid):
            try:
                url = waterbutler_api_url_for(
                    pid, provider, path=file_info['id'].replace(provider, ''), _internal=True
                )
                rs = requests.get(
                    url,
                    cookies=request_cookie,
                    stream=True,
                )
            except Exception as err:
                logger.error(err)
                return None
            if rs.status_code == 200:
                data_json = rs.json()
            rs.close()
            break
    return data_json


def get_list_file_info(pid, provider, path, request_cookie, guid=None):
    try:
        url = waterbutler_api_url_for(
            pid, provider, path=path, _internal=True, meta=''
        )
        response = requests.get(
            url,
            headers={'content-type': 'application/json'},
            cookies=request_cookie,
        )
    except Exception as err:
        logger.error(err)
        return None
    content = None
    if response.status_code == 200:
        content = response.json()
    response.close()
    return get_list_file_detail(content['data'], pid, provider, request_cookie, guid)


def get_export_data(user_institution_guid, selected_export_location=None, selected_source=None, deleted=False,
                    check_delete=True):
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


class ExportDataListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_list.html'

    def get(self, request, institution_id):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        user_institution_name = Institution.objects.get(id=institution_id).name
        selected_storage = request.GET.get('storage_name') if 'storage_name' in dict(request.GET) else 0
        selected_location_export = request.GET.get('location_export_name') if 'location_export_name' in dict(
            request.GET) else 0
        query = get_export_data(user_institution_guid, selected_location_export, selected_storage)
        page_size = self.get_paginate_by(query)
        _, page, _, _ = self.paginate_queryset(query, page_size)
        context = {
            'institution_name': user_institution_name,
            'list_export_data': query,
            'list_location': ExportDataLocation.objects.filter(institution_guid=user_institution_guid),
            'list_storage': Region.objects.filter(_id=user_institution_guid),
            'selected_source': int(selected_storage),
            'selected_location_export': int(selected_location_export),
            'source_id': query[0]['source_id'] if len(query) > 0 else 0,
            'page': page,
        }
        return render(request, self.template_name, context)

    def get_export_data_list(self):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        return get_export_data(user_institution_guid)


class ExportDataDeletedListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'

    def get(self, request, institution_id):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        user_institution_name = Institution.objects.get(id=institution_id).name
        selected_storage = request.GET.get('storage_name') if 'storage_name' in dict(request.GET) else 0
        selected_location_export = request.GET.get('location_export_name') if 'location_export_name' in dict(
            request.GET) else 0
        query = get_export_data(user_institution_guid, selected_location_export, selected_storage, deleted=True)
        page_size = self.get_paginate_by(query)
        _, page, _, _ = self.paginate_queryset(query, page_size)
        context = {
            'institution_name': user_institution_name,
            'list_export_data': query,
            'list_location': ExportDataLocation.objects.filter(institution_guid=user_institution_guid),
            'list_storage': Region.objects.filter(_id=user_institution_guid),
            'selected_source': int(selected_storage),
            'selected_location_export': int(selected_location_export),
            'source_id': query[0]['source_id'] if len(query) > 0 else 0,
            'page': page,
        }
        return render(request, self.template_name, context)

    def get_export_data_list(self):
        user_institution_guid = self.INSTITUTION_DEFAULT
        if not self.is_super_admin and self.is_affiliated_institution:
            user_institution_guid = self.request.user.representative_affiliated_institution.guid
        return get_export_data(user_institution_guid, deleted=True)


class ExportDataInformationView(ExportStorageLocationViewBaseView, DetailView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'
    raise_exception = True

    def get_object(self, **kwargs):
        user_institution_guid = self.request.user.representative_affiliated_institution.guid
        for item in get_export_data(user_institution_guid, check_delete=False):
            if str(item['export_data'].id) == self.kwargs.get('data_id'):
                return item
        raise Http404(
            'Export data with id "{}" not found.'.format(
                self.kwargs.get('data_id')
            ))

    def get_context_data(self, **kwargs):
        context = super(ExportDataInformationView, self).get_context_data(**kwargs)
        data = self.get_object()
        user_institution_name = Institution.objects.get(
            id=self.request.user.representative_affiliated_institution.id).name
        user_institution_guid = self.request.user.representative_affiliated_institution.guid
        list_file_info = get_list_file_info('nxsm2', 'osfstorage', '/', self.request.COOKIES, user_institution_guid)
        provider = Region.objects.get(id=data['source_id'])
        context['is_deleted'] = data['export_data'].is_deleted
        context['data_information'] = data
        context['list_file_info'] = list_file_info['files']
        context['institution_name'] = user_institution_name
        context['source_id'] = data['source_id'] if len(data) > 0 else 0
        context['provider_name'] = 'Export Data Information of {} storage'.format(
            provider.waterbutler_settings['storage']['provider'])
        context['storages'] = Region.objects.exclude(_id__in=self.request.user.representative_affiliated_institution.guid)
        return context


class DeleteExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def post(self, request):
        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        if list_export_data:
            if check_delete_permanently:
                # Check connection
                logger.info('check_delete_permanently')
                source = Region.objects.get(id=request.POST.get('source_id'))
                request_data = source.waterbutler_credentials['storage']
                request_data = {**request_data, **dict(source.waterbutler_settings['storage'])}
                logger.info(request_data)
                respone_test_connect = test_connection(request_data)
                logger.info('respone_test_connect')
                logger.info(respone_test_connect)
                try:
                    url = waterbutler_api_url_for(
                        'nxsm2', 'osfstorage', path='/62ff09aaa299d84a17c99f9d', _internal=True
                    )
                    response = requests.delete(
                        url,
                        headers={'content-type': 'application/json'},
                        cookies=request.COOKIES
                    )
                except Exception as err:
                    logger.error(err)
                    return None
                logger.info(response)
                response.close()
                # Delete export data in DB
                ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
                # ExportData.objects.filter(id__in=list_export_data).delete()
            else:
                ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
        return redirect('custom_storage_location:export_data:export_data_list',
                        institution_id=self.request.user.representative_affiliated_institution.id)


class RevertExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def post(self, request):
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        if list_export_data:
            ExportData.objects.filter(id__in=list_export_data).update(is_deleted=False)
        return redirect('custom_storage_location:export_data:export_data_deleted_list',
                        institution_id=self.request.user.representative_affiliated_institution.id)


class ExportDataFileCSVView(RdmPermissionMixin, View):

    def get(self, request):
        guid = self.request.user.representative_affiliated_institution.guid
        current_datetime = str('{date:%Y-%m-%d-%H%M%S}'.format(date=datetime.datetime.now())).replace('-', '')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=file_info_{}_{}.csv'.format(guid, current_datetime)
        writer = csv.writer(response)
        writer.writerow(
            ['project_id', 'project_name', 'owner', 'file_id', 'file_path', 'filename', 'versions', 'size'])
        data = get_list_file_info('nxsm2', 'osfstorage', '/', request.COOKIES, guid)
        logger.info(data)
        for file in data['files']:
            writer.writerow(
                [file['project']['id'], file['project']['name'], 'name_ierae07', file['id'], file['materialized_path'],
                 file['name'],
                 file['version'][0]['identifier'], file['size']])
        return response
