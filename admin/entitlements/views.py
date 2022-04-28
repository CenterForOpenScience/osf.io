from __future__ import unicode_literals

import logging
from urllib.parse import urlencode

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, View

from admin.rdm.utils import RdmPermissionMixin
from osf.models import Institution
from osf.models import InstitutionEntitlement

logger = logging.getLogger(__name__)


class InstitutionEntitlementList(RdmPermissionMixin, ListView):
    paginate_by = 25
    template_name = 'entitlements/list.html'
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True
    model = InstitutionEntitlement

    def get_queryset(self):
        return InstitutionEntitlement.objects.order_by('entitlement')

    def get_context_data(self, **kwargs):
        user = self.request.user
        # superuser
        if self.is_super_admin:
            institutions = Institution.objects.all().order_by('name')
        # institution administrator
        elif self.is_admin and user.affiliated_institutions.first():
            institutions = Institution.objects.filter(pk__in=user.affiliated_institutions.all()).order_by('name')
        else:
            raise PermissionDenied('Not authorized to view the entitlements.')

        selected_id = institutions.first().id

        institution_id = int(self.kwargs.get('institution_id', self.request.GET.get('institution_id', selected_id)))
        object_list = self.object_list.filter(institution_id=institution_id)

        page_size = self.get_paginate_by(object_list)
        paginator, page, query_set, is_paginated = self.paginate_queryset(object_list, page_size)

        kwargs.setdefault('institutions', institutions)
        kwargs.setdefault('institution_id', institution_id)
        kwargs.setdefault('selected_id', institution_id)
        kwargs.setdefault('entitlements', query_set)
        kwargs.setdefault('page', page)

        return super(InstitutionEntitlementList, self).get_context_data(**kwargs)


class BulkAddInstitutionEntitlement(PermissionRequiredMixin, View):
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True

    def post(self, request):
        institution_id = request.POST.get('institution_id')
        entitlements = request.POST.getlist('entitlements')
        login_availability_list = request.POST.getlist('login_availability')

        existing_set = InstitutionEntitlement.objects.filter(institution_id=institution_id, entitlement__in=entitlements)
        existing_list = existing_set.values_list('entitlement', flat=True)
        for idx, entitlement in enumerate(entitlements):
            if entitlement not in existing_list:
                InstitutionEntitlement.objects.create(institution_id=institution_id,
                                                      entitlement=entitlement,
                                                      login_availability=login_availability_list[idx] == 'on',
                                                      modifier=request.user)

        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': institution_id})
        return redirect('{}?{}'.format(base_url, query_string))


class ToggleInstitutionEntitlement(PermissionRequiredMixin, View):
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        entitlement = InstitutionEntitlement.objects.get(id=self.kwargs['entitlement_id'])
        entitlement.login_availability = not entitlement.login_availability
        entitlement.modifier = request.user
        entitlement.save()

        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': self.kwargs['institution_id'], 'page': request.GET.get('page', 1)})
        return redirect('{}?{}'.format(base_url, query_string))


class DeleteInstitutionEntitlement(PermissionRequiredMixin, View):
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        entitlement = InstitutionEntitlement.objects.get(id=self.kwargs['entitlement_id'])
        entitlement.delete()

        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': self.kwargs['institution_id'], 'page': request.GET.get('page', 1)})
        return redirect('{}?{}'.format(base_url, query_string))
