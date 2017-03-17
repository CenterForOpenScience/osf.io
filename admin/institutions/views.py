from __future__ import unicode_literals

import json

from django.core import serializers
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseForbidden, HttpResponse
from django.views.generic import ListView, FormView, DetailView, View, CreateView
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base import settings
from admin.institutions.forms import InstitutionForm
from osf.models import Institution


class InstitutionList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'institutions/list.html'
    ordering = 'name'
    permission_required = 'osf.view_institution'
    raise_exception = True
    model = Institution

    def get_queryset(self):
        return Institution.objects.all().sort(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        return {
            'institutions': query_set,
            'page': page,
            'logohost': settings.OSF_URL
        }


class InstitutionDisplay(PermissionRequiredMixin, DetailView):
    model = Institution
    template_name = 'institutions/detail.html'
    permission_required = 'osf.view_institution'
    raise_exception = True

    def get_object(self, queryset=None):
        return Institution.objects.get(id=self.kwargs.get('institution_id'))

    def get_context_data(self, *args, **kwargs):
        institution = self.get_object()
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs['institution'] = institution
        kwargs['logohost'] = settings.OSF_URL
        fields = json.loads(serializers.serialize('json', [institution, ]))[0]['fields']
        kwargs['change_form'] = InstitutionForm(initial=fields)

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


class InstitutionChangeForm(PermissionRequiredMixin, SingleObjectMixin, FormView):
    template_name = 'institutions/detail.html'
    form_class = InstitutionForm
    model = Institution
    permission_required = 'osf.change_institution'
    raise_exception = True

    def get_object(self, queryset=None):
        return Institution.objects.get(id=self.kwargs.get('institution_id'))

    def update_institution_attributes(self, institution):
        form = InstitutionForm(self.request.POST or None, instance=institution)
        if form.is_valid():
            form.save()
        return reverse('institutions:detail', kwargs={'institution_id': self.object.pk})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        self.update_institution_attributes(self.object)
        return super(InstitutionChangeForm, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('institutions:detail', kwargs={'institution_id': self.object.pk})


class InstitutionExport(PermissionRequiredMixin, View):

    permission_required = 'osf.change_institution'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        institution = Institution.objects.get(id=self.kwargs['institution_id'])
        data = serializers.serialize("json", [institution])

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
    fields = [
        'banner_name', 'login_url', 'domains', 'email_domains',
        'logo_name', 'logout_url', 'name', 'description'
    ]
