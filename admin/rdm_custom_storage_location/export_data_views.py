# -*- coding: utf-8 -*-

import json

from django.contrib.auth.mixins import UserPassesTestMixin
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.generic import TemplateView
from rest_framework import status as http_status

from admin.base import settings
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
from admin.rdm_custom_storage_location.export_data import utils as export_data_utils
from osf.models import Institution, ExportDataLocation
from website import settings as osf_settings


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
    model = Institution
    template_name = 'rdm_custom_storage_location/export_data_institutional_storages.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get_object(self, queryset=None):
        return Institution.objects.get(id=self.kwargs.get('institution_id'))

    def get_context_data(self, *args, **kwargs):
        institution = self.get_object()
        institution_dict = model_to_dict(institution)
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs['institution'] = institution_dict
        kwargs['logohost'] = settings.OSF_URL
        kwargs['node_count'] = institution.nodes.count()

        return kwargs


class ExportDataList(ExportStorageLocationViewBaseView, ListView):
    paginate_by = 10
    template_name = 'rdm_custom_storage_location/export_data_list.html'
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


class ExportDataDeletedList(ExportStorageLocationViewBaseView, ListView):
    paginate_by = 10
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'
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


class ExportDataInformation(ExportStorageLocationViewBaseView, DetailView):
    model = Institution
    template_name = 'rdm_custom_storage_location/export_data_information.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get_object(self, queryset=None):
        return Institution.objects.get(id=self.kwargs.get('institution_id'))

    def get_context_data(self, *args, **kwargs):
        institution = self.get_object()
        institution_dict = model_to_dict(institution)
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs['institution'] = institution_dict
        kwargs['logohost'] = settings.OSF_URL
        kwargs['node_count'] = institution.nodes.count()

        return kwargs
