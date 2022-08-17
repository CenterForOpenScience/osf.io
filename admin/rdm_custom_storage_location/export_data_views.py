# -*- coding: utf-8 -*-

import json

from django.contrib.auth.mixins import UserPassesTestMixin
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import ListView, DetailView, View
from django.views.generic import TemplateView
from rest_framework import status as http_status

from admin.base import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
from admin.rdm_custom_storage_location.export_data import utils as export_data_utils
from osf.models import Institution, ExportData, ExportDataLocation
from website import settings as osf_settings
from django.http import HttpResponse
from addons.osfstorage.models import Region
import csv
import datetime
import logging

logger = logging.getLogger(__name__)


def getExportData(ins_user_id, selected_export_location=None, selected_source=None, deleted=False, check_delete=True):
    list_source_id = Region.objects.filter(_id=ins_user_id).values_list('id', flat=True)
    list_location_id = ExportDataLocation.objects.filter(institution_guid=ins_user_id).values_list('id', flat=True)
    list_export_data = ExportData.objects.filter(is_deleted=deleted, location_id__in=list_location_id,
                                                 source_id__in=list_source_id).order_by(
        'id') if check_delete else ExportData.objects.filter(location_id__in=list_location_id,
                                                             source_id__in=list_source_id).order_by('id')
    list_data = []
    for export_data in list_export_data:
        data = {'export_data': export_data}
        for location in ExportDataLocation.objects.filter(institution_guid=ins_user_id):
            if export_data.location_id == location.id:
                if selected_export_location:
                    if selected_export_location == str(location.id):
                        data['location_name'] = location.name
                else:
                    data['location_name'] = location.name
        for source in Region.objects.filter(_id=ins_user_id):
            if export_data.source_id == source.id:
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


class SaveCredentialsView(ExportStorageLocationViewBaseView, View):
    """ View for saving the credentials to the provider into the database.
    Called when clicking the 'Save' Button.
    """

    def post(self, request):
        data = json.loads(request.body)
        institution_guid = self.INSTITUTION_DEFAULT

        if not self.is_super_admin and self.is_affiliated_institution:
            institution = request.user.affiliated_institutions.first()
            institution_guid = institution.guid

        provider_short_name = data.get('provider_short_name')
        if not provider_short_name:
            response = {
                'message': 'Provider is missing.'
            }
            return JsonResponse(response, status=http_status.HTTP_400_BAD_REQUEST)

        storage_name = data.get('storage_name')
        if not storage_name and utils.have_storage_name(provider_short_name):
            return JsonResponse({
                'message': 'Storage name is missing.'
            }, status=http_status.HTTP_400_BAD_REQUEST)

        if provider_short_name == 's3':
            result = export_data_utils.save_s3_credentials(
                institution_guid,
                storage_name,
                data.get('s3_access_key'),
                data.get('s3_secret_key'),
                data.get('s3_bucket'),
            )
        elif provider_short_name == 's3compat':
            result = export_data_utils.save_s3compat_credentials(
                institution_guid,
                storage_name,
                data.get('s3compat_endpoint_url'),
                data.get('s3compat_access_key'),
                data.get('s3compat_secret_key'),
                data.get('s3compat_bucket'),
            )
        elif provider_short_name == 'nextcloudinstitutions':
            result = utils.save_nextcloudinstitutions_credentials(
                institution,
                storage_name,
                data.get('nextcloudinstitutions_host'),
                data.get('nextcloudinstitutions_username'),
                data.get('nextcloudinstitutions_password'),
                data.get('nextcloudinstitutions_folder'),  # base folder
                data.get('nextcloudinstitutions_notification_secret'),
                provider_short_name,
            )
        elif provider_short_name == 'dropboxbusiness':
            result = utils.save_dropboxbusiness_credentials(
                institution,
                storage_name,
                provider_short_name)
        else:
            result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)

        status = result[1]
        if status == http_status.HTTP_200_OK:
            pass
            # utils.change_allowed_for_institutions(institution, provider_short_name)
        return JsonResponse(result[0], status=status)


class ExportStorageLocationView(ExportStorageLocationViewBaseView, TemplateView):
    """ View that shows the Export Data Storage Location's template """
    template_name = 'rdm_custom_storage_location/export_data_storage_location.html'
    model = ExportDataLocation
    paginate_by = 10
    ordering = 'pk'

    def get_context_data(self, *args, **kwargs):
        institution_guid = self.INSTITUTION_DEFAULT

        if not self.is_super_admin and self.is_affiliated_institution:
            institution = self.request.user.affiliated_institutions.first()
            institution_guid = institution.guid
            kwargs['institution'] = institution

        kwargs['providers'] = utils.get_providers(self.PROVIDERS_AVAILABLE)
        kwargs['locations'] = location_list = export_data_utils.get_export_location_list(institution_guid)
        kwargs['osf_domain'] = osf_settings.DOMAIN
        # paginator, page, locations, is_paginated = self.paginate_queryset(location_list, page_size)
        # kwargs.setdefault('page', page)
        return kwargs


class ExportDataInstitutionList(ExportStorageLocationViewBaseView, ListView):
    template_name = 'rdm_custom_storage_location/export_data_institutions.html'
    paginate_by = 10
    ordering = 'name'
    permission_required = 'osf.view_institution'
    raise_exception = True
    model = Institution

    def get_queryset(self):
        return Institution.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(ExportDataInstitutionList, self).get_context_data(**kwargs)


class ExportDataInstitutionalStorages(ExportStorageLocationViewBaseView, DetailView):
    model = Region
    paginate_by = 10
    ordering = 'pk'
    template_name = 'rdm_custom_storage_location/export_data_institutional_storages.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get_object(self, queryset=None):
        return Institution.objects.get(id=self.kwargs.get('institution_id'))

    def get_context_data(self, *args, **kwargs):
        institution = self.get_object()
        institution_dict = model_to_dict(institution)
        institution_guid = institution._id
        storages = Region.objects.filter(_id=institution_guid)
        storages_dict = [{"id": storage.id, "name": storage.name, "provider_name": storage.waterbutler_settings["storage"]["provider"], "has_export_data": ExportData.objects.filter(source_id=storage.id).exists()} for storage in storages]
        # page_size = self.get_paginate_by(query_set)
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs['institution'] = institution_dict
        kwargs['logohost'] = settings.OSF_URL
        kwargs['node_count'] = institution.nodes.count()
        kwargs['storages'] = storages_dict

        # paginator, page, locations, is_paginated = self.paginate_queryset(storages_dict, page_size)
        # kwargs.setdefault('page', page)
        return kwargs


class ExportBaseView(ListView):

    def get_queryset(self):
        list_export_data = self.get_exportlist()
        return list_export_data

    def get_context_data(self, **kwargs):
        ins_user_id = self.request.user.affiliated_institutions.first()._id
        self.query_set = self.get_queryset()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)
        kwargs['institution_name'] = self.request.user.affiliated_institutions.first().name
        kwargs['list_export_data'] = self.query_set
        kwargs['list_location'] = ExportDataLocation.objects.filter(institution_guid=ins_user_id)
        kwargs['list_storage'] = Region.objects.filter(_id=ins_user_id)
        kwargs['selected_source'] = 0
        kwargs['selected_location_export'] = 0
        kwargs['page'] = self.page
        return super(ExportBaseView, self).get_context_data(**kwargs)


class ExportDataList(PermissionRequiredMixin, ExportBaseView):
    paginate_by = 10
    template_name = 'rdm_custom_storage_location/export_data_list.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def post(self, request):
        logger.info('ExportDataList post method')
        logger.info(request.POST)
        ins_user_id = self.request.user.affiliated_institutions.first()._id
        storage_name = request.POST.get('storage_name')
        location_export_name = request.POST.get('location_export_name')
        query = getExportData(ins_user_id, location_export_name, storage_name)
        context = {'institution_name': self.request.user.affiliated_institutions.first().name,
                   'list_export_data': query,
                   'list_location': ExportDataLocation.objects.filter(institution_guid=ins_user_id),
                   'list_storage': Region.objects.filter(_id=ins_user_id),
                   'selected_source': int(storage_name),
                   'selected_location_export': int(location_export_name),
                   'page': 1}
        return render(request, self.template_name, context)

    def get_exportlist(self):
        return getExportData(self.request.user.affiliated_institutions.first()._id)


class ExportDataDeletedList(PermissionRequiredMixin, ExportBaseView):
    paginate_by = 10
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def post(self, request):
        logger.info('ExportDataDeletedList post method')
        logger.info(request.POST)
        ins_user_id = self.request.user.affiliated_institutions.first()._id
        storage_name = request.POST.get('storage_name')
        location_export_name = request.POST.get('location_export_name')
        query = getExportData(ins_user_id, location_export_name, storage_name, deleted=True)
        context = {'institution_name': self.request.user.affiliated_institutions.first().name,
                   'list_export_data': query,
                   'list_location': ExportDataLocation.objects.filter(institution_guid=ins_user_id),
                   'list_storage': Region.objects.filter(_id=ins_user_id),
                   'selected_source': int(storage_name),
                   'selected_location_export': int(location_export_name),
                   'page': 1}
        return render(request, self.template_name, context)

    def get_exportlist(self):
        ins_user_id = self.request.user.affiliated_institutions.first()._id
        return getExportData(ins_user_id, deleted=True)


class ExportDataInformation(ExportStorageLocationViewBaseView, DetailView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get_object(self):
        ins_user_id = self.request.user.affiliated_institutions.first()._id
        for item in getExportData(ins_user_id, check_delete=False):
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
        logger.info(check_delete_permanently)
        if list_export_data:
            ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
            # if(check_delete_permanently):
            #     ExportData.objects.filter(id__in=list_export_data).delete()
            # else:
            #     ExportData.objects.filter(id__in=list_export_data).update(is_deleted=True)
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

    def get(self, request, **kwargs):
        guid = self.request.user.affiliated_institutions.first()._id
        current_datetime = str('{date:%Y-%m-%d-%H%M%S}'.format(date=datetime.datetime.now())).replace('-', '')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=file_info_{}_{}.csv'.format(guid, current_datetime)
        writer = csv.writer(response)
        writer.writerow(
            ['project_id', 'project_name', 'owner', 'file_id', 'file_path', 'filename', 'versions', 'size'])
        return response
