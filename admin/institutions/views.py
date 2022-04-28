from __future__ import unicode_literals

import json
import logging
from operator import itemgetter

from django.db import connection
from django.db.models import Q
from django.http import Http404
from django.core import serializers
from django.shortcuts import redirect
from django.forms.models import model_to_dict
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from admin.rdm.utils import RdmPermissionMixin

from admin.base import settings
from admin.base.forms import ImportFileForm
from admin.institutions.forms import InstitutionForm, InstitutionalMetricsAdminRegisterForm
from django.contrib.auth.models import Group
from osf.models import Institution, Node, OSFUser, UserQuota, Email
from website.util import quota
from addons.osfstorage.models import Region
from api.base import settings as api_settings
import csv

logger = logging.getLogger(__name__)


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
            if isinstance(chunk, bytes):
                chunk = chunk.decode()
            parsed_file += chunk
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

class InstitutionalMetricsAdminRegister(PermissionRequiredMixin, FormView):
    permission_required = 'osf.change_institution'
    raise_exception = True
    template_name = 'institutions/register_institutional_admin.html'
    form_class = InstitutionalMetricsAdminRegisterForm

    def get_form_kwargs(self):
        kwargs = super(InstitutionalMetricsAdminRegister, self).get_form_kwargs()
        kwargs['institution_id'] = self.kwargs['institution_id']
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(InstitutionalMetricsAdminRegister, self).get_context_data(**kwargs)
        context['institution_name'] = Institution.objects.get(id=self.kwargs['institution_id']).name
        return context

    def form_valid(self, form):
        kwargs = self.get_form_kwargs()
        user_id = form.cleaned_data.get('user_id')
        osf_user = OSFUser.load(user_id)
        institution_id = kwargs['institution_id']
        target_institution = Institution.objects.filter(id=institution_id).first()

        if not osf_user:
            raise Http404('OSF user with id "{}" not found. Please double check.'.format(user_id))

        group = Group.objects.filter(name__startswith='institution_{}'.format(target_institution._id)).first()

        group.user_set.add(osf_user)
        group.save()

        osf_user.save()
        messages.success(self.request, 'Permissions update successful for OSF User {}!'.format(osf_user.username))
        return super(InstitutionalMetricsAdminRegister, self).form_valid(form)

    def get_success_url(self):
        return reverse('institutions:register_metrics_admin', kwargs={'institution_id': self.kwargs['institution_id']})

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
            'eppn': user.eppn or '',
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
        if order_by not in ['fullname', 'eppn', 'username', 'ratio', 'usage', 'remaining', 'quota']:
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

        if hasattr(institution, 'storage_name'):
            kwargs['institution_storage_name'] = institution.storage_name

        self.query_set = self.get_queryset()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)

        kwargs['requested_user'] = self.request.user
        kwargs['users'] = self.query_set
        kwargs['page'] = self.page
        kwargs['order_by'] = self.get_order_by()
        kwargs['direction'] = self.get_direction()
        return super(QuotaUserList, self).get_context_data(**kwargs)


class ExportFileTSV(PermissionRequiredMixin, QuotaUserList):
    permission_required = 'osf.view_osfuser'
    raise_exception = True

    def get(self, request, **kwargs):
        institution_id = self.kwargs['institution_id']
        response = HttpResponse(content_type='text/tsv')
        writer = csv.writer(response, delimiter='\t')
        writer.writerow(['GUID', 'Username', 'Fullname', 'Ratio (%)', 'Usage (Byte)', 'Remaining (Byte)', 'Quota (Byte)'])

        for user in OSFUser.objects.filter(affiliated_institutions=institution_id):
            max_quota, used_quota = quota.get_quota_info(user, UserQuota.NII_STORAGE)
            max_quota_bytes = max_quota * api_settings.SIZE_UNIT_GB
            remaining_quota = max_quota_bytes - used_quota

            writer.writerow([user.guids.first()._id, user.username,
                             user.fullname,
                             round(float(used_quota) / max_quota_bytes * 100, 1),
                             round(used_quota, 0),
                             round(remaining_quota, 0),
                             round(max_quota_bytes, 0)])
        query = 'attachment; filename=user_list_by_institution_{}_export.tsv'.format(
            institution_id)
        response['Content-Disposition'] = query
        return response


class UserListByInstitutionID(PermissionRequiredMixin, QuotaUserList):
    template_name = 'institutions/list_institute.html'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    paginate_by = 10

    def get_userlist(self):
        guid = self.request.GET.get('guid')
        name = self.request.GET.get('info')
        email = self.request.GET.get('email')
        queryset = OSFUser.objects.filter(affiliated_institutions=self.kwargs['institution_id'])

        if not email and not guid and not name:
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in queryset]

        query_email = query_guid = query_name = None

        if email:
            existing_user_ids = list(Email.objects.filter(Q(address__exact=email)).values_list('user_id', flat=True))
            query_email = queryset.filter(Q(pk__in=existing_user_ids) | Q(username__exact=email))
        if guid:
            query_guid = queryset.filter(guids___id=guid)
        if name:
            query_name = queryset.filter(Q(fullname__icontains=name) |
                                         # Q(family_name_ja__icontains=name) |  # add in (1)4.1.4
                                         # Q(given_name_ja__icontains=name) |  # add in (1)4.1.4
                                         # Q(middle_names_ja__icontains=name) |  # add in (1)4.1.4
                                         Q(given_name__icontains=name) |
                                         Q(middle_names__icontains=name) |
                                         Q(family_name__icontains=name))

        if query_email is not None and query_email.exists():
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in query_email]
        elif query_guid is not None and query_guid.exists():
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in query_guid]
        elif query_name is not None and query_name.exists():
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in query_name]
        else:
            return []

    def get_institution(self):
        return Institution.objects.get(id=self.kwargs['institution_id'])


class UpdateQuotaUserListByInstitutionID(PermissionRequiredMixin, View):
    permission_required = 'osf.change_osfuser'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        institution_id = self.kwargs['institution_id']
        min_value, max_value = connection.ops.integer_field_range('IntegerField')
        max_quota = min(int(self.request.POST.get('maxQuota')), max_value)
        for user in OSFUser.objects.filter(
                affiliated_institutions=institution_id):
            UserQuota.objects.update_or_create(
                user=user, storage_type=UserQuota.NII_STORAGE,
                defaults={'max_quota': max_quota})
        return redirect('institutions:institution_user_list',
                        institution_id=institution_id)

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


class RecalculateQuota(RdmPermissionMixin, RedirectView):

    def dispatch(self, request, *args, **kwargs):
        if self.is_super_admin:
            institutions_list = Institution.objects.all()

            for institution in institutions_list:
                user_list = OSFUser.objects.filter(affiliated_institutions=institution)
                for user in user_list:
                    quota.update_user_used_quota(user)

        return redirect('institutions:institution_list')


class RecalculateQuotaOfUsersInInstitution(RdmPermissionMixin, RedirectView):

    def dispatch(self, request, *args, **kwargs):
        if self.is_admin:
            institution = self.request.user.affiliated_institutions.first()
            if institution is not None and Region.objects.filter(_id=institution._id).exists():
                for user in OSFUser.objects.filter(affiliated_institutions=institution.id):
                    quota.update_user_used_quota(user, UserQuota.CUSTOM_STORAGE)

        return redirect('institutions:statistical_status_default_storage')
