from __future__ import unicode_literals

import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, View

from osf.models import Institution
from osf.models import InstitutionEntitlement


class InstitutionEntitlementList(ListView):
    paginate_by = 25
    template_name = 'entitlements/list.html'
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True
    model = InstitutionEntitlement

    def get_queryset(self):
        institutions = Institution.objects.all().order_by('name')
        return InstitutionEntitlement.objects.filter(institution_id=institutions.first().id)

    def get_context_data(self, **kwargs):
        institutions = Institution.objects.all().order_by('name')

        selected_id = kwargs.pop('selected_id', institutions.first().id)
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', institutions)
        kwargs.setdefault('selected_id', selected_id)
        kwargs.setdefault('entitlements', query_set)
        kwargs.setdefault('page', page)
        return super(InstitutionEntitlementList, self).get_context_data(**kwargs)


class AddInstitutionEntitlement(PermissionRequiredMixin, View):
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True
    success_url = reverse_lazy('entitlements:list')

    def post(self, request):
        input_dict = json.loads(request.body)
        institution_id = input_dict.get('institution_id')
        entitlements = input_dict.get('entitlements')
        login_availability_list = input_dict.get('login_availability')
        for idx, entitlement in enumerate(entitlements):
            InstitutionEntitlement.objects.create(institution_id=institution_id,
                                                  entitlement=entitlement,
                                                  login_availability=login_availability_list[idx],
                                                  modifier=request.user)
        return redirect('entitlements:list', selected_id=institution_id)


class DeleteInstitutionEntitlement(PermissionRequiredMixin, View):
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True
    success_url = reverse_lazy('entitlements:list')

    def get_object(self, queryset=None):
        entitlement = InstitutionEntitlement.objects.get(id=self.kwargs['entitlement_id'])
        return entitlement

    def delete(self, request, *args, **kwargs):
        entitlement = InstitutionEntitlement.objects.get(id=self.kwargs['entitlement_id'])
        return super(DeleteInstitutionEntitlement, self).delete(request, *args, **kwargs)
