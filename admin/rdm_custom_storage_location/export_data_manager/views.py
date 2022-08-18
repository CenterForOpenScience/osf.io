# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import ListView, DetailView, View
from rest_framework import status as http_status

from django.contrib.auth.mixins import PermissionRequiredMixin
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
from osf.models import ExportData, ExportDataLocation
from django.http import HttpResponse
from addons.osfstorage.models import Region
import csv
import datetime
import logging

logger = logging.getLogger(__name__)

def test_connection(data, institution=None):
        provider_short_name = data.get('provider_short_name')
        if not provider_short_name:
            response = {
                'message': 'Provider is missing.'
            }
            return JsonResponse(response, status=http_status.HTTP_400_BAD_REQUEST)

        result = None

        if provider_short_name == 's3':
            result = utils.test_s3_connection(
                data.get('s3_access_key'),
                data.get('s3_secret_key'),
                data.get('s3_bucket'),
            )
        elif provider_short_name == 's3compat':
            result = utils.test_s3compat_connection(
                data.get('s3compat_endpoint_url'),
                data.get('s3compat_access_key'),
                data.get('s3compat_secret_key'),
                data.get('s3compat_bucket'),
            )
        elif provider_short_name == 's3compatb3':
            result = utils.test_s3compatb3_connection(
                data.get('s3compatb3_endpoint_url'),
                data.get('s3compatb3_access_key'),
                data.get('s3compatb3_secret_key'),
                data.get('s3compatb3_bucket'),
            )
        elif provider_short_name == 's3compatinstitutions':
            result = utils.test_s3compat_connection(
                data.get('s3compatinstitutions_endpoint_url'),
                data.get('s3compatinstitutions_access_key'),
                data.get('s3compatinstitutions_secret_key'),
                data.get('s3compatinstitutions_bucket'),
            )
        elif provider_short_name == 'ociinstitutions':
            result = utils.test_s3compatb3_connection(
                data.get('ociinstitutions_endpoint_url'),
                data.get('ociinstitutions_access_key'),
                data.get('ociinstitutions_secret_key'),
                data.get('ociinstitutions_bucket'),
            )
        elif provider_short_name == 'owncloud':
            result = utils.test_owncloud_connection(
                data.get('owncloud_host'),
                data.get('owncloud_username'),
                data.get('owncloud_password'),
                data.get('owncloud_folder'),
                provider_short_name,
            )
        elif provider_short_name == 'nextcloud':
            result = utils.test_owncloud_connection(
                data.get('nextcloud_host'),
                data.get('nextcloud_username'),
                data.get('nextcloud_password'),
                data.get('nextcloud_folder'),
                provider_short_name,
            )
        elif provider_short_name == 'nextcloudinstitutions':
            result = utils.test_owncloud_connection(
                data.get('nextcloudinstitutions_host'),
                data.get('nextcloudinstitutions_username'),
                data.get('nextcloudinstitutions_password'),
                data.get('nextcloudinstitutions_folder'),
                provider_short_name,
            )
        elif provider_short_name == 'swift':
            result = utils.test_swift_connection(
                data.get('swift_auth_version'),
                data.get('swift_auth_url'),
                data.get('swift_access_key'),
                data.get('swift_secret_key'),
                data.get('swift_tenant_name'),
                data.get('swift_user_domain_name'),
                data.get('swift_project_domain_name'),
                data.get('swift_container'),
            )
        elif provider_short_name == 'dropboxbusiness':
            result = utils.test_dropboxbusiness_connection(institution)
        else:
            result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)

        return JsonResponse(result[0], status=result[1])



def getExportData(user_institution_guid, selected_export_location=None, selected_source=None, deleted=False, check_delete=True):
    list_source_id = Region.objects.filter(_id=user_institution_guid).values_list('id', flat=True)
    list_location_id = ExportDataLocation.objects.filter(institution_guid=user_institution_guid).values_list('id', flat=True)
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


class ExportStorageLocationViewBaseView(RdmPermissionMixin, UserPassesTestMixin):
    """ Base class for all the Institutional Storage Views """
    PROVIDERS_AVAILABLE = ['s3', 's3compat']
    INSTITUTION_DEFAULT = 'us'
    institution_guid = INSTITUTION_DEFAULT

    def test_func(self):
        """ Check user permissions """
        if self.is_admin and self.is_affiliated_institution:
            self.PROVIDERS_AVAILABLE += ['dropboxbusiness', 'nextcloudinstitutions']

        return self.is_super_admin or (self.is_admin and self.is_affiliated_institution)


class ExportBaseView(ExportStorageLocationViewBaseView, ListView):
    permission_required = 'osf.view_institution'
    raise_exception = True
    paginate_by = 10

    def get_queryset(self):
        list_export_data = self.get_exportlist()
        return list_export_data

    def get_context_data(self, **kwargs):
        user_institution_guid = self.request.user.affiliated_institutions.first()._id
        self.query_set = self.get_queryset()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)
        kwargs['institution_name'] = self.request.user.affiliated_institutions.first().name
        kwargs['list_export_data'] = self.query_set
        kwargs['list_location'] = ExportDataLocation.objects.filter(institution_guid=user_institution_guid)
        kwargs['list_storage'] = Region.objects.filter(_id=user_institution_guid)
        kwargs['selected_source'] = 0
        kwargs['selected_location_export'] = 0
        kwargs['page'] = self.page
        kwargs['source_id'] = self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0
        return super(ExportBaseView, self).get_context_data(**kwargs)


class ExportDataList(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_list.html'

    def post(self, request):
        logger.info('ExportDataList post method')
        logger.info(request.POST)
        user_institution_guid = self.request.user.affiliated_institutions.first()._id
        storage_name = request.POST.get('storage_name')
        location_export_name = request.POST.get('location_export_name')
        query = getExportData(user_institution_guid, location_export_name, storage_name)
        context = {'institution_name': self.request.user.affiliated_institutions.first().name,
                   'list_export_data': query,
                   'list_location': ExportDataLocation.objects.filter(institution_guid=user_institution_guid),
                   'list_storage': Region.objects.filter(_id=user_institution_guid),
                   'selected_source': int(storage_name),
                   'selected_location_export': int(location_export_name),
                   'source_id': query[0]['source_id'] if len(query) > 0 else 0,
                   'page': 1}
        return render(request, self.template_name, context)

    def get_exportlist(self):
        return getExportData(self.request.user.affiliated_institutions.first()._id)


class ExportDataDeletedList(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'

    def post(self, request):
        logger.info('ExportDataDeletedList post method')
        logger.info(request.POST)
        user_institution_guid = self.request.user.affiliated_institutions.first()._id
        storage_name = request.POST.get('storage_name')
        location_export_name = request.POST.get('location_export_name')
        query = getExportData(user_institution_guid, location_export_name, storage_name, deleted=True)
        context = {'institution_name': self.request.user.affiliated_institutions.first().name,
                   'list_export_data': query,
                   'list_location': ExportDataLocation.objects.filter(institution_guid=user_institution_guid),
                   'list_storage': Region.objects.filter(_id=user_institution_guid),
                   'selected_source': int(storage_name),
                   'selected_location_export': int(location_export_name),
                   'source_id': query[0]['source_id'] if len(query) > 0 else 0,
                   'page': 1}
        return render(request, self.template_name, context)

    def get_exportlist(self):
        user_institution_guid = self.request.user.affiliated_institutions.first()._id
        return getExportData(user_institution_guid, deleted=True)


class ExportDataInformation(ExportStorageLocationViewBaseView, DetailView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get_object(self):
        user_institution_guid = self.request.user.affiliated_institutions.first()._id
        for item in getExportData(user_institution_guid, check_delete=False):
            if str(item['export_data'].id) == self.kwargs.get('data_id'):
                return item
        return None

    def get_context_data(self, *args, **kwargs):
        context = super(ExportDataInformation, self).get_context_data(*args, **kwargs)
        data = self.get_object()
        logger.info(data)
        context['is_deleted'] = data['export_data'].is_deleted
        context['data'] = data
        context['institution_name'] = self.request.user.affiliated_institutions.first().name
        return context


class DeleteExportData(ExportStorageLocationViewBaseView, View):
    permission_required = 'osf.view_institution'
    raise_exception = True

    def post(self, request):
        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        if list_export_data:
            if(check_delete_permanently):
                # Check connection
                logger.info('check_delete_permanently')
                logger.info(check_delete_permanently)
                source = Region.objects.get(id=request.POST.get('source_id'))
                request_data = source.waterbutler_credentials['storage']
                request_data['provider_short_name'] = source.waterbutler_settings['storage']['provider']
                respone_test_connect = test_connection(request_data)
                logger.info('respone_test_connect')
                logger.info(respone_test_connect)
                # Delete export data in DB
                ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
                # ExportData.objects.filter(id__in=list_export_data).delete()
            else:
                ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
        return redirect('custom_storage_location:export_data_list')


class RevertExportData(ExportStorageLocationViewBaseView, View):
    permission_required = 'osf.view_institution'
    raise_exception = True

    def post(self, request):
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        if list_export_data:
            ExportData.objects.filter(id__in=list_export_data).update(is_deleted=False)
            # if(check_delete_permanently):
            #     ExportData.objects.filter(id__in=list_export_data).delete()
            # else:
            #     ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
        return redirect('custom_storage_location:export_data_deleted_list')


class ExportDataFileCSV(PermissionRequiredMixin, View):
    permission_required = 'osf.view_osfuser'

    def get(self):
        guid = self.request.user.affiliated_institutions.first()._id
        current_datetime = str('{date:%Y-%m-%d-%H%M%S}'.format(date=datetime.datetime.now())).replace('-', '')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=file_info_{}_{}.csv'.format(guid, current_datetime)
        writer = csv.writer(response)
        writer.writerow(
            ['project_id', 'project_name', 'owner', 'file_id', 'file_path', 'filename', 'versions', 'size'])
        return response
