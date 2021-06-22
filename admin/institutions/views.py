from __future__ import unicode_literals

import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core import serializers
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView

from admin.base import settings
from admin.base.forms import ImportFileForm
from admin.institutions.forms import InstitutionForm, InstitutionalMetricsAdminRegisterForm
from framework import sentry
from osf.models import Institution, Node, OSFUser
from website.mails import send_mail, INSTITUTION_DEACTIVATION
from website.settings import OSF_SUPPORT_EMAIL, DOMAIN

logger = logging.getLogger(__name__)


class InstitutionList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'institutions/list.html'
    ordering = 'name'
    permission_required = 'osf.view_institution'
    raise_exception = True
    model = Institution

    def get_queryset(self):
        return Institution.objects.get_all_institutions().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(InstitutionList, self).get_context_data(**kwargs)


class InstitutionDisplay(PermissionRequiredMixin, DetailView):
    model = Institution
    template_name = 'institutions/detail.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get_object(self, queryset=None):
        return Institution.objects.get_all_institutions().get(id=self.kwargs.get('institution_id'))

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
    template_name = 'institutions/detail.html'
    permission_required = 'osf.change_institution'
    raise_exception = True
    model = Institution
    form_class = InstitutionForm

    def get_object(self, queryset=None):
        provider_id = self.kwargs.get('institution_id')
        return Institution.objects.get_all_institutions().get(id=provider_id)

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        return super(InstitutionChangeForm, self).get_context_data(*args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('institutions:detail', kwargs={'institution_id': self.kwargs.get('institution_id')})


class InstitutionExport(PermissionRequiredMixin, View):
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        institution = Institution.objects.get_all_institutions().get(id=self.kwargs['institution_id'])
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
        kwargs.setdefault('institution', Institution.objects.get_all_institutions().get(id=self.kwargs['institution_id']))
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(InstitutionNodeList, self).get_context_data(**kwargs)


class DeleteInstitution(PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_institution'
    raise_exception = True
    template_name = 'institutions/confirm_delete.html'
    success_url = reverse_lazy('institutions:list')

    def delete(self, request, *args, **kwargs):
        institution = Institution.objects.get_all_institutions().get(id=self.kwargs['institution_id'])
        if institution.nodes.count() > 0:
            return redirect('institutions:cannot_delete', institution_id=institution.pk)
        return super(DeleteInstitution, self).delete(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        institution = Institution.objects.get_all_institutions().get(id=self.kwargs['institution_id'])
        if institution.nodes.count() > 0:
            return redirect('institutions:cannot_delete', institution_id=institution.pk)
        return super(DeleteInstitution, self).get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        institution = Institution.objects.get_all_institutions().get(id=self.kwargs['institution_id'])
        return institution


class DeactivateInstitution(PermissionRequiredMixin, UpdateView):
    template_name = 'institutions/confirm_deactivate.html'
    permission_required = 'osf.change_institution'
    raise_exception = True
    model = Institution
    form_class = InstitutionForm

    def get_object(self, queryset=None):
        return Institution.objects.get_all_institutions().get(id=self.kwargs.get('institution_id'))

    def post(self, request, *args, **kwargs):
        institution = self.get_object()
        institution.deactivated = timezone.now()
        institution.save()
        # Django mangers aren't used when querying on related models. Thus, we can query
        # affiliated users and send notification emails after the institution has been deactivated.
        self._send_deactivation_email(institution)
        return redirect('institutions:detail', institution_id=institution.id)

    @staticmethod
    def _send_deactivation_email(institution):
        forgot_password = 'forgotpassword' if DOMAIN.endswith('/') else '/forgotpassword'
        attempts = 0
        success = 0
        # Use iterator to reduce potential memory load when there are a lot of users. The side
        # effect is that this disables QuerySet caching. This is fine since it isn't used again.
        for user in OSFUser.objects.filter(affiliated_institutions___id=institution._id).iterator():
            try:
                attempts += 1
                send_mail(
                    to_addr=user.username,
                    mail=INSTITUTION_DEACTIVATION,
                    user=user,
                    forgot_password_link='{}{}'.format(DOMAIN, forgot_password),
                    osf_support_email=OSF_SUPPORT_EMAIL
                )
            except Exception:
                logger.error('Failed to send institution deactivation email to '
                             'user [{}] at [{}]'.format(user._id, institution._id))
                sentry.log_exception()
                continue
            else:
                success += 1
        logger.info('Institution deactivation notification email has been sent to '
                    '[{}/{}] users for [{}]'.format(success, attempts, institution._id))


class ReactivateInstitution(PermissionRequiredMixin, UpdateView):
    template_name = 'institutions/confirm_reactivate.html'
    permission_required = 'osf.change_institution'
    raise_exception = True
    model = Institution
    form_class = InstitutionForm

    def get_object(self, queryset=None):
        return Institution.objects.get_all_institutions().get(id=self.kwargs.get('institution_id'))

    def post(self, request, *args, **kwargs):
        institution = self.get_object()
        institution.deactivated = None
        institution.save()
        return redirect('institutions:detail', institution_id=institution.id)


class CannotDeleteInstitution(TemplateView):
    template_name = 'institutions/cannot_delete.html'

    def get_context_data(self, **kwargs):
        context = super(CannotDeleteInstitution, self).get_context_data(**kwargs)
        context['institution'] = Institution.objects.get_all_institutions().get(id=self.kwargs['institution_id'])
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
        context['institution_name'] = Institution.objects.get_all_institutions().get(id=self.kwargs['institution_id']).name
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
