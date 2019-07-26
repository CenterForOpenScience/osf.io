from __future__ import unicode_literals

import json
from operator import itemgetter

from django.core import serializers
from django.shortcuts import redirect
from django.forms.models import model_to_dict
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from admin.rdm.utils import RdmPermissionMixin

from admin.base import settings
from admin.base.forms import ImportFileForm
from admin.institutions.forms import InstitutionForm
from osf.models import Institution, Node, OSFUser, UserQuota
from website.util import quota
from addons.osfstorage.models import Region
from django.http import HttpResponseRedirect
from api.base import settings as api_settings


class InstitutionList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'institutions/list.html'
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
        return super(InstitutionList, self).get_context_data(**kwargs)

class InstitutionUserList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'institutions/institution_list.html'
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
        return super(InstitutionUserList, self).get_context_data(**kwargs)


class InstitutionDisplay(PermissionRequiredMixin, DetailView):
    model = Institution
    template_name = 'institutions/detail.html'
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
        fields = institution_dict
        kwargs['change_form'] = InstitutionForm(initial=fields)
        kwargs['import_form'] = ImportFileForm()
        kwargs['node_count'] = institution.nodes.count()

        return kwargs


class InstitutionDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = InstitutionDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = InstitutionChangeForm.as_view()
        return view(request, *args, **kwargs)


class InstitutionDefaultStorageDetail(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    model = Institution
    template_name = 'institutions/default_storage.html'

    def test_func(self):
        """check user permissions"""
        return not self.is_super_admin and self.is_admin and \
            self.request.user.affiliated_institutions.exists()

    def get_context_data(self, *args, **kwargs):
        kwargs['institution'] = self.request.user.affiliated_institutions.first()._id
        kwargs['institution_pk'] = self.request.user.affiliated_institutions.first().id
        if Region.objects.filter(_id=kwargs['institution']).exists():
            kwargs['region'] = Region.objects.get(_id=kwargs['institution'])
        else:
            kwargs['region'] = Region.objects.first()
        kwargs['region'].waterbutler_credentials = json.dumps(kwargs['region'].waterbutler_credentials)
        kwargs['region'].waterbutler_settings = json.dumps(kwargs['region'].waterbutler_settings)
        return kwargs

    def post(self, request, *args, **kwargs):
        default_region = Region.objects.first()
        Region.objects.update_or_create(
            _id=self.request.user.affiliated_institutions.first()._id,
            defaults={
                'name': request.POST.get('name'),
                'waterbutler_credentials': eval(request.POST.get('waterbutler_credentials')),
                'waterbutler_url': default_region.waterbutler_url,
                'mfr_url': default_region.mfr_url,
                'waterbutler_settings': eval(request.POST.get('waterbutler_settings'))
            }
        )
        return HttpResponseRedirect(self.request.path_info)


class ImportInstitution(PermissionRequiredMixin, View):
    permission_required = 'osf.change_institution'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_str = self.parse_file(request.FILES['file'])
            file_json = json.loads(file_str)
            return JsonResponse(file_json[0]['fields'])

    def parse_file(self, f):
        parsed_file = ''
        for chunk in f.chunks():
            parsed_file += str(chunk)
        return parsed_file


class InstitutionChangeForm(PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.change_institution'
    raise_exception = True
    model = Institution
    form_class = InstitutionForm

    def get_object(self, queryset=None):
        provider_id = self.kwargs.get('institution_id')
        return Institution.objects.get(id=provider_id)

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        return super(InstitutionChangeForm, self).get_context_data(*args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('institutions:detail', kwargs={'institution_id': self.kwargs.get('institution_id')})


class InstitutionExport(PermissionRequiredMixin, View):
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        institution = Institution.objects.get(id=self.kwargs['institution_id'])
        data = serializers.serialize('json', [institution])

        filename = '{}_export.json'.format(institution.name)

        response = HttpResponse(data, content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response


class CreateInstitution(PermissionRequiredMixin, CreateView):
    permission_required = 'osf.change_institution'
    raise_exception = True
    template_name = 'institutions/create.html'
    success_url = reverse_lazy('institutions:list')
    model = Institution
    form_class = InstitutionForm

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        return super(CreateInstitution, self).get_context_data(*args, **kwargs)


class InstitutionNodeList(PermissionRequiredMixin, ListView):
    template_name = 'institutions/node_list.html'
    paginate_by = 25
    ordering = 'modified'
    permission_required = 'osf.view_node'
    raise_exception = True
    model = Node

    def get_queryset(self):
        inst = self.kwargs['institution_id']
        return Node.objects.filter(affiliated_institutions=inst).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('nodes', query_set)
        kwargs.setdefault('institution', Institution.objects.get(id=self.kwargs['institution_id']))
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(InstitutionNodeList, self).get_context_data(**kwargs)


class DeleteInstitution(PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_institution'
    raise_exception = True
    template_name = 'institutions/confirm_delete.html'
    success_url = reverse_lazy('institutions:list')

    def delete(self, request, *args, **kwargs):
        institution = Institution.objects.get(id=self.kwargs['institution_id'])
        if institution.nodes.count() > 0:
            return redirect('institutions:cannot_delete', institution_id=institution.pk)
        return super(DeleteInstitution, self).delete(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        institution = Institution.objects.get(id=self.kwargs['institution_id'])
        if institution.nodes.count() > 0:
            return redirect('institutions:cannot_delete', institution_id=institution.pk)
        return super(DeleteInstitution, self).get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        institution = Institution.objects.get(id=self.kwargs['institution_id'])
        return institution


class CannotDeleteInstitution(TemplateView):
    template_name = 'institutions/cannot_delete.html'

    def get_context_data(self, **kwargs):
        context = super(CannotDeleteInstitution, self).get_context_data(**kwargs)
        context['institution'] = Institution.objects.get(id=self.kwargs['institution_id'])
        return context


class QuotaUserList(ListView):
    """Base class for UserListByInstitutionID and StatisticalStatusDefaultStorage.
    """

    def custom_size_abbreviation(self, size, abbr):
        if abbr == 'B':
            return (size / api_settings.BASE_FOR_METRIC_PREFIX, 'KB')
        return size, abbr

    def get_user_quota_info(self, user, storage_type):
        max_quota, used_quota = quota.get_quota_info(user, storage_type)
        max_quota_bytes = max_quota * api_settings.SIZE_UNIT_GB
        remaining_quota = max_quota_bytes - used_quota
        used_quota_abbr = self.custom_size_abbreviation(*quota.abbreviate_size(used_quota))
        remaining_abbr = self.custom_size_abbreviation(*quota.abbreviate_size(remaining_quota))
        return {
            'id': user.guids.first()._id,
            'fullname': user.fullname,
            'username': user.username,
            'ratio': float(used_quota) / max_quota_bytes * 100,
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'remaining': remaining_quota,
            'remaining_value': remaining_abbr[0],
            'remaining_abbr': remaining_abbr[1],
            'quota': max_quota
        }

    def get_queryset(self):
        user_list = self.get_userlist()
        order_by = self.get_order_by()
        reverse = self.get_direction() != 'asc'
        user_list.sort(key=itemgetter(order_by), reverse=reverse)
        return user_list

    def get_order_by(self):
        order_by = self.request.GET.get('order_by', 'ratio')
        if order_by not in ['fullname', 'username', 'ratio', 'usage', 'remaining', 'quota']:
            return 'ratio'
        return order_by

    def get_direction(self):
        direction = self.request.GET.get('status', 'desc')
        if direction not in ['asc', 'desc']:
            return 'desc'
        return direction

    def get_context_data(self, **kwargs):
        institution = self.get_institution()
        kwargs['institution_id'] = institution.id
        kwargs['institution_name'] = institution.name

        self.query_set = self.get_queryset()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)

        kwargs['users'] = self.query_set
        kwargs['page'] = self.page
        kwargs['order_by'] = self.get_order_by()
        kwargs['direction'] = self.get_direction()
        return super(QuotaUserList, self).get_context_data(**kwargs)


class UserListByInstitutionID(QuotaUserList, PermissionRequiredMixin):
    template_name = 'institutions/list_institute.html'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    paginate_by = 10

    def get_userlist(self):
        user_list = []
        for user in OSFUser.objects.filter(affiliated_institutions=self.kwargs['institution_id']):
            user_list.append(self.get_user_quota_info(user, UserQuota.NII_STORAGE))
        return user_list

    def get_institution(self):
        return Institution.objects.get(id=self.kwargs['institution_id'])


class StatisticalStatusDefaultStorage(QuotaUserList, RdmPermissionMixin, UserPassesTestMixin):
    template_name = 'institutions/statistical_status_default_storage.html'
    permission_required = 'osf.view_institution'
    raise_exception = True
    paginate_by = 10

    def test_func(self):
        return not self.is_super_admin and self.is_admin \
            and self.request.user.affiliated_institutions.exists()

    def get_userlist(self):
        user_list = []
        institution = self.request.user.affiliated_institutions.first()
        if institution is not None and Region.objects.filter(_id=institution._id).exists():
            for user in OSFUser.objects.filter(affiliated_institutions=institution.id):
                user_list.append(self.get_user_quota_info(user, UserQuota.CUSTOM_STORAGE))
        return user_list

    def get_institution(self):
        return self.request.user.affiliated_institutions.first()
