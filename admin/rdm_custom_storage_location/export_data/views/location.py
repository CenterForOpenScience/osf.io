# -*- coding: utf-8 -*-
import inspect  # noqa
import json
import logging

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView
from rest_framework import status as http_status

from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
from admin.rdm_custom_storage_location.export_data import utils as export_data_utils
from osf.models import ExportDataLocation, Institution
from website import settings as osf_settings
from website.util import inspect_info  # noqa

logger = logging.getLogger(__name__)

__all__ = [
    'ExportStorageLocationViewBaseView',
    'ExportStorageLocationView',
    'SaveCredentialsView',
]


class ExportStorageLocationViewBaseView(RdmPermissionMixin, UserPassesTestMixin):
    """ Base class for all the Institutional Storage Views """
    PROVIDERS_AVAILABLE = ['s3', 's3compat']
    INSTITUTION_DEFAULT = Institution.INSTITUTION_DEFAULT
    institution_guid = INSTITUTION_DEFAULT
    institution = None
    raise_exception = True

    def get_default_storage_location(self):
        query_set = ExportDataLocation.objects.filter(institution_guid=self.INSTITUTION_DEFAULT)
        return query_set

    def have_default_storage_location_id(self, storage_id):
        return self.get_default_storage_location().filter(pk=storage_id).exists()

    def test_func(self):
        """ Check user permissions """
        if not self.is_authenticated:
            return False
        user = self.request.user
        if user.is_institutional_admin:
            self.PROVIDERS_AVAILABLE = ['s3', 's3compat',
                                        'dropboxbusiness', 'nextcloudinstitutions']

        return user.is_super_admin or user.is_institutional_admin

    def is_affiliated_institution(self, institution_id):
        """determine whether the user has affiliated institutions"""
        user = self.request.user
        return user.is_affiliated_with_institution_id(institution_id)


class ExportStorageLocationView(ExportStorageLocationViewBaseView, ListView):
    """ View that shows the Export Data Storage Location """
    template_name = 'rdm_custom_storage_location/export_data_storage_location.html'
    model = ExportDataLocation
    paginate_by = 10
    ordering = 'pk'

    def get(self, request, *args, **kwargs):
        self.institution_guid = self.INSTITUTION_DEFAULT
        self.institution = None

        if self.request.user.is_affiliated_institution:
            self.institution = request.user.affiliated_institutions.first()
            self.institution_guid = self.institution.guid

        return super(ExportStorageLocationView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        list_location = ExportDataLocation.objects.filter(institution_guid=self.institution_guid)
        list_location = list_location.order_by(self.ordering)
        return list_location

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)

        kwargs.setdefault('institution', self.institution)
        kwargs.setdefault('locations', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('providers', utils.get_providers(self.PROVIDERS_AVAILABLE))
        kwargs.setdefault('osf_domain', osf_settings.DOMAIN)

        return super(ExportStorageLocationView, self).get_context_data(**kwargs)


class TestConnectionView(ExportStorageLocationViewBaseView, View):
    """ View for testing the credentials to connect to a provider.
    Called when clicking the 'Connect' Button.
    """
    def post(self, request):
        data = json.loads(request.body)

        provider_short_name = data.get('provider_short_name')
        if not provider_short_name:
            response = {
                'message': 'Provider is missing.'
            }
            return JsonResponse(response, status=http_status.HTTP_400_BAD_REQUEST)

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
        elif provider_short_name == 'nextcloudinstitutions':
            result = utils.test_owncloud_connection(
                data.get('nextcloudinstitutions_host'),
                data.get('nextcloudinstitutions_username'),
                data.get('nextcloudinstitutions_password'),
                data.get('nextcloudinstitutions_folder'),
                provider_short_name,
            )
        elif provider_short_name == 'dropboxbusiness':
            institution = request.user.affiliated_institutions.first()
            result = export_data_utils.test_dropboxbusiness_connection(institution)

        else:
            result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)

        return JsonResponse(result[0], status=result[1])


class SaveCredentialsView(ExportStorageLocationViewBaseView, View):
    """ View for saving the credentials to the provider into the database.
    Called when clicking the 'Save' Button.
    """

    def post(self, request):
        data = json.loads(request.body)
        institution_guid = self.INSTITUTION_DEFAULT
        institution = None

        if self.request.user.is_affiliated_institution:
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

        # Check provider and save credentials
        result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)
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
        elif institution:
            result = ({'message': 'Affiliated institution is missing.'}, http_status.HTTP_400_BAD_REQUEST)
            if provider_short_name == 'nextcloudinstitutions':
                result = export_data_utils.save_nextcloudinstitutions_credentials(
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
                result = export_data_utils.save_dropboxbusiness_credentials(
                    institution,
                    storage_name,
                    provider_short_name)

        status = result[1]
        return JsonResponse(result[0], status=status)


class DeleteCredentialsView(ExportStorageLocationViewBaseView, View):
    """ View for deleting the credentials to the provider in the database.
    Called when clicking the 'Delete' Button.
    """
    raise_exception = True
    storage_location = None
    institution_guid = ExportStorageLocationViewBaseView.INSTITUTION_DEFAULT

    def test_func(self):
        """ Check user permissions """
        # login check
        if not self.is_authenticated:
            return False

        user = self.request.user
        if user.is_institutional_admin:
            self.PROVIDERS_AVAILABLE = ['s3', 's3compat',
                                        'dropboxbusiness', 'nextcloudinstitutions']
        location_id = self.kwargs.get('location_id')
        self.storage_location = ExportDataLocation.objects.filter(pk=location_id).first()
        if self.storage_location:
            if not self.is_super_admin and user.is_affiliated_institution:
                institution = user.affiliated_institutions.first()
                self.institution_guid = institution.guid
            return user.is_super_admin or (user.is_institutional_admin
                                           and self.storage_location.institution_guid == self.institution_guid)
        else:
            return user.is_super_admin or user.is_institutional_admin

    def delete(self, request, location_id, **kwargs):
        message = 'Do nothing'
        status = http_status.HTTP_400_BAD_REQUEST

        if not self.storage_location:
            return JsonResponse({
                'message': message
            }, status=status)

        if self.storage_location.institution_guid == self.institution_guid:
            # allow to delete
            self.storage_location.delete()
            message = 'storage_location.delete()'
            status = http_status.HTTP_200_OK

        return JsonResponse({
            'message': message
        }, status=status)
