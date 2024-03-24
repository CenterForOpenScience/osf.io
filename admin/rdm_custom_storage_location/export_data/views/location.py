# -*- coding: utf-8 -*-
import inspect  # noqa
import json
import logging

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse, Http404
from django.views import View
from django.views.generic import ListView
from rest_framework import status as http_status

from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
from admin.rdm_custom_storage_location.export_data import utils as export_data_utils
from osf.models import ExportDataLocation, Institution
from website import settings as osf_settings
from website.util import inspect_info  # noqa
from admin.base import settings

logger = logging.getLogger(__name__)

__all__ = [
    'ExportStorageLocationViewBaseView',
    'ExportStorageLocationView',
    'ExportStorageLocationInstitutionListView',
    'SaveCredentialsView',
]

INSTITUTION_NOT_FOUND_MESSAGE = 'Institution does not exist'

class ExportStorageLocationViewBaseView(RdmPermissionMixin, UserPassesTestMixin):
    """ Base class for all the Institutional Storage Views """
    PROVIDERS_AVAILABLE = ['s3', 's3compat', 'nextcloudinstitutions']
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
            self.raise_exception = False
            return False
        user = self.request.user
        institution_id = self.kwargs.get('institution_id', None)
        if user.is_institutional_admin or (institution_id and user.is_super_admin):
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
    raise_exception = True

    def get(self, request, *args, **kwargs):

        institution_id = self.kwargs.get('institution_id', None)
        institution_id = int(institution_id) if institution_id else None

        institution = None

        if institution_id:
            institution = Institution.objects.filter(id=institution_id, is_deleted=False).first()
            if institution is None:
                # Navigate to 404 Not Found page
                raise Http404

            if request.user.is_institutional_admin:
                # If user is an administrator, get institution by user's first affiliated institution
                institution = request.user.affiliated_institutions.first()
                if institution.id != institution_id:
                    return self.handle_no_permission()

        else:
            if request.user.is_super_admin:
                self.institution_guid = self.INSTITUTION_DEFAULT
                self.institution = None
                return super(ExportStorageLocationView, self).get(request, *args, **kwargs)
            else:
                institution = self.request.user.affiliated_institutions.first()

        self.institution = institution
        self.institution_guid = institution.guid
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
        kwargs.setdefault('is_location_setting', True)

        return super(ExportStorageLocationView, self).get_context_data(**kwargs)


class ExportStorageLocationInstitutionListView(ExportStorageLocationViewBaseView, ListView):
    """ View for display list of Institution
    Called when clicking menu Export data storage location > Each institution
    """
    template_name = 'rdm_custom_storage_location/export_data_storage_location_list_institutions.html'
    paginate_by = 25
    ordering = 'name'
    model = Institution
    raise_exception = False

    def test_func(self):
        """ Check user permissions """
        if not self.is_authenticated:
            # If user is not authenticated, return False
            return False
        self.raise_exception = True
        # Only allow super administrators to access this view
        return self.is_super_admin

    def get_queryset(self):
        """ GET: set to self.object_list """
        return Institution.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(ExportStorageLocationInstitutionListView, self).get_context_data(**kwargs)


class TestConnectionView(ExportStorageLocationViewBaseView, View):
    """ View for testing the credentials to connect to a provider.
    Called when clicking the 'Connect' Button.
    """
    def post(self, request, *args, **kwargs):
        institution_id = kwargs.get('institution_id', None)
        institution_id = int(institution_id) if institution_id else None
        if institution_id:
            institution = Institution.objects.filter(id=institution_id, is_deleted=False).first()
            if not institution:
                return JsonResponse({'message': INSTITUTION_NOT_FOUND_MESSAGE}, status=http_status.HTTP_404_NOT_FOUND)
        if request.user.is_institutional_admin:
            if institution_id and institution.id != institution_id:
                return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)

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
            if request.user.is_institutional_admin:
                institution = request.user.affiliated_institutions.first()
                result = export_data_utils.test_dropboxbusiness_connection(institution)
            elif request.user.is_super_admin and institution_id:
                result = export_data_utils.test_dropboxbusiness_connection(institution)
            else:
                result = ({'message': 'Can not setting Dropbox business.'}, http_status.HTTP_400_BAD_REQUEST)

        else:
            result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)

        return JsonResponse(result[0], status=result[1])


class SaveCredentialsView(ExportStorageLocationViewBaseView, View):
    """ View for saving the credentials to the provider into the database.
    Called when clicking the 'Save' Button.
    """

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        institution_guid = self.INSTITUTION_DEFAULT
        institution = None

        institution_id = kwargs.get('institution_id', None)
        institution_id = int(institution_id) if institution_id else None
        if self.is_super_admin:
            if institution_id:
                institution = Institution.objects.filter(id=institution_id, is_deleted=False).first()
                if not institution:
                    # Return 404 Not Found
                    return JsonResponse({'message': INSTITUTION_NOT_FOUND_MESSAGE}, status=http_status.HTTP_404_NOT_FOUND)
                institution_guid = institution.guid
        elif self.is_admin:
            institution = self.request.user.affiliated_institutions.first()
            if institution_id and institution.id != institution_id:
                return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)
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
        elif provider_short_name == 'nextcloudinstitutions':
            result = export_data_utils.save_nextcloudinstitutions_credentials(
                institution,
                storage_name,
                data.get('nextcloudinstitutions_host'),
                data.get('nextcloudinstitutions_username'),
                data.get('nextcloudinstitutions_password'),
                data.get('nextcloudinstitutions_folder'),  # base folder
                provider_short_name,
            )
        elif institution:
            result = ({'message': 'Affiliated institution is missing.'}, http_status.HTTP_400_BAD_REQUEST)
            if provider_short_name == 'dropboxbusiness':
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
        if not user.is_super_admin and not user.is_institutional_admin:
            return False

        if user.is_institutional_admin:
            self.PROVIDERS_AVAILABLE = ['s3', 's3compat',
                                        'dropboxbusiness', 'nextcloudinstitutions']
        location_id = self.kwargs.get('location_id')
        institution_id = self.kwargs.get('institution_id')
        institution = None
        if institution_id:
            institution = Institution.objects.filter(id=institution_id, is_deleted=False).first()
            if not institution:
                # Raise 404 Not Found
                raise Http404
        self.storage_location = ExportDataLocation.objects.filter(pk=location_id).first()
        if self.storage_location:
            if user.is_institutional_admin:
                institution = user.affiliated_institutions.first()
                self.institution_guid = institution.guid
            elif institution:
                self.institution_guid = institution.guid
            return (self.storage_location.institution_guid == self.institution_guid)
        else:
            # Raise 404 Not Found if no location
            raise Http404

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
