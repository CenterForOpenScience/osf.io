# -*- coding: utf-8 -*-
import logging

from django.views.generic import ListView

from addons.osfstorage.models import Region
from admin.base import settings
from osf.models import Institution, ExportData
from .location import ExportStorageLocationViewBaseView

logger = logging.getLogger(__name__)


class ExportDataInstitutionListView(ExportStorageLocationViewBaseView, ListView):
    template_name = 'rdm_custom_storage_location/export_data_institutions.html'
    paginate_by = 10
    ordering = 'name'
    permission_required = 'osf.view_institution'
    raise_exception = True
    model = Institution

    def test_func(self):
        """ Check user permissions """
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
        return super(ExportDataInstitutionListView, self).get_context_data(**kwargs)


class ExportDataInstitutionalStorageListView(ExportStorageLocationViewBaseView, ListView):
    template_name = 'rdm_custom_storage_location/export_data_institutional_storages.html'
    paginate_by = 10
    ordering = 'pk'
    permission_required = None
    raise_exception = True
    model = Region

    def get(self, request, *args, **kwargs):
        institution_id = self.kwargs.get('institution_id')
        self.institution = Institution.objects.get(pk=institution_id)
        self.institution_guid = self.institution.guid

        if not self.is_super_admin and not self.is_affiliated_institution(institution_id):
            self.handle_no_permission()

        return super(ExportDataInstitutionalStorageListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        storages = Region.objects.filter(_id=self.institution_guid).order_by(self.ordering)
        storages_dict = [{
            "id": storage.id,
            "name": storage.name,
            "provider_name": storage.provider_name,
            "provider_full_name": storage.provider_full_name,
            "has_export_data": ExportData.objects.filter(source_id=storage.id).exists()
        } for storage in storages]
        return storages_dict

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)

        kwargs.setdefault('institution', self.institution)
        kwargs.setdefault('storages', query_set)
        locations = self.institution.get_allowed_storage_location()
        kwargs.setdefault('locations', locations)
        kwargs.setdefault('page', page)

        return super(ExportDataInstitutionalStorageListView, self).get_context_data(**kwargs)
