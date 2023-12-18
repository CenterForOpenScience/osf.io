# -*- coding: utf-8 -*-
import inspect  # noqa
import logging

from django.views.generic import ListView

from addons.osfstorage.models import Region
from admin.base import settings
from osf.models import Institution
from website.util import inspect_info  # noqa
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
        if not self.institution:
            institution_id = self.kwargs.get('institution_id')
            self.institution = Institution.objects.get(pk=institution_id)
        storages = self.institution.get_institutional_storage()
        return storages

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)

        kwargs.setdefault('institution', self.institution)
        kwargs.setdefault('storages', query_set)
        locations = self.institution.get_allowed_storage_location_order_by()
        kwargs.setdefault('locations', locations)
        location_id = locations[0].id if locations else None
        kwargs.setdefault('location_id', location_id)
        kwargs.setdefault('page', page)

        return super(ExportDataInstitutionalStorageListView, self).get_context_data(**kwargs)


class ExportDataListInstitutionListView(ExportStorageLocationViewBaseView, ListView):
    template_name = 'rdm_custom_storage_location/export_data_list_institutions.html'
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
        return super(ExportDataListInstitutionListView, self).get_context_data(**kwargs)
