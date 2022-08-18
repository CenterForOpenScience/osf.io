# -*- coding: utf-8 -*-
import logging

from django.forms import model_to_dict
from django.views.generic import ListView, DetailView

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


class ExportDataInstitutionalStorageView(ExportStorageLocationViewBaseView, DetailView):
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
        storages_dict = [{"id": storage.id, "name": storage.name, "provider_name": storage.waterbutler_settings["storage"]["provider"],
                          "has_export_data": ExportData.objects.filter(source_id=storage.id).exists()}
                         for storage in storages]
        # page_size = self.get_paginate_by(query_set)
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs['institution'] = institution_dict
        kwargs['logohost'] = settings.OSF_URL
        kwargs['node_count'] = institution.nodes.count()
        kwargs['storages'] = storages_dict

        # paginator, page, locations, is_paginated = self.paginate_queryset(storages_dict, page_size)
        # kwargs.setdefault('page', page)
        return kwargs
