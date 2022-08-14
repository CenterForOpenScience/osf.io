from django.contrib.auth.mixins import UserPassesTestMixin
from django.forms.models import model_to_dict
from django.views.generic import ListView, DetailView
from django.views.generic import TemplateView

from admin.base import settings
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
from osf.models import Institution
from website import settings as osf_settings


class ExportStorageLocationViewBaseView(RdmPermissionMixin, UserPassesTestMixin):
    """ Base class for all the Institutional Storage Views """
    PROVIDERS_AVAILABLE = ['s3', 's3compat']

    def test_func(self):
        """ Check user permissions """
        if self.is_admin and self.is_affiliated_institution:
            self.PROVIDERS_AVAILABLE += ['dropboxbusiness', 'nextcloudinstitutions']

        return self.is_super_admin or (self.is_admin and self.is_affiliated_institution)


class ExportStorageLocationView(ExportStorageLocationViewBaseView, TemplateView):
    """ View that shows the Export Data Storage Location's template """
    model = Institution
    template_name = 'rdm_custom_storage_location/export_data_storage_location.html'

    def get_context_data(self, *args, **kwargs):
        if self.is_affiliated_institution:
            institution = self.request.user.affiliated_institutions.first()
            kwargs['institution'] = institution

        kwargs['providers'] = utils.get_providers(self.PROVIDERS_AVAILABLE)
        kwargs['osf_domain'] = osf_settings.DOMAIN
        return kwargs


class ExportDataInstitutionList(ExportStorageLocationViewBaseView, ListView):
    paginate_by = 10
    template_name = 'rdm_custom_storage_location/export_data_institutions.html'
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
