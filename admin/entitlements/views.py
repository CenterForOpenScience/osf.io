from __future__ import unicode_literals

import logging
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, View

from admin.rdm.utils import RdmPermissionMixin
from osf.models import Institution
from osf.models import InstitutionEntitlement
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import Http404
from admin.base.utils import render_bad_request_response

logger = logging.getLogger(__name__)


class InstitutionEntitlementList(RdmPermissionMixin, UserPassesTestMixin, ListView):
    paginate_by = 25
    template_name = 'entitlements/list.html'
    raise_exception = True
    model = InstitutionEntitlement
    institution_id = None
    page = None

    def dispatch(self, request, *args, **kwargs):

        # login check
        if not self.is_authenticated:
            return self.handle_no_permission()
        try:
            self.institution_id = self.request.GET.get('institution_id')
            if self.institution_id:
                self.institution_id = int(self.institution_id)
            return super(InstitutionEntitlementList, self).dispatch(request, *args, **kwargs)
        except ValueError:
            return render_bad_request_response(request=request, error_msgs='institution_id must be a integer')

    def test_func(self):
        """check user permissions"""
        if not self.institution_id:
            # superuser or admin has an institution
            return self.is_super_admin or self.is_institutional_admin
        else:
            # institution not exist
            if not Institution.objects.filter(id=self.institution_id).exists():
                raise Http404(
                    'Institution with id "{}" not found.'.format(
                        self.institution_id
                    ))
            # superuser or institutional admin has permission
            return self.is_super_admin or \
                (self.is_admin and self.is_affiliated_institution(self.institution_id))

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

        institution_id = int(self.kwargs.get('institution_id', self.institution_id or selected_id))
        object_list = self.object_list.filter(institution_id=institution_id)

        page_size = self.get_paginate_by(object_list)
        paginator, page, query_set, is_paginated = self.paginate_queryset(object_list, page_size)

        kwargs.setdefault('institutions', institutions)
        kwargs.setdefault('institution_id', institution_id)
        kwargs.setdefault('selected_id', institution_id)
        kwargs.setdefault('entitlements', query_set)
        kwargs.setdefault('page', page)

        return super(InstitutionEntitlementList, self).get_context_data(**kwargs)


class BulkAddInstitutionEntitlement(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True
    institution_id = None

    def dispatch(self, request, *args, **kwargs):
        """Initialize attributes shared by all view methods."""
        # login check
        if not self.is_authenticated:
            return self.handle_no_permission()
        try:
            self.institution_id = self.request.POST.get('institution_id')
            if self.institution_id:
                self.institution_id = int(self.institution_id)
            else:
                return render_bad_request_response(request=request, error_msgs='institution_id is required')
            return super(BulkAddInstitutionEntitlement, self).dispatch(request, *args, **kwargs)
        except ValueError:
            return render_bad_request_response(request=request, error_msgs='institution_id must be a integer')

    def test_func(self):
        """check user permissions"""
        # institution not exist
        if not Institution.objects.filter(id=self.institution_id, is_deleted=False).exists():
            raise Http404(
                'Institution with id "{}" not found.'.format(
                    self.institution_id
                ))
        # superuser or institutional admin has permission
        return self.is_super_admin or \
            (self.is_admin and self.is_affiliated_institution(self.institution_id))

    def post(self, request):
        entitlements = request.POST.getlist('entitlements')
        login_availability_list = request.POST.getlist('login_availability')

        existing_set = InstitutionEntitlement.objects.filter(
            institution_id=self.institution_id, entitlement__in=entitlements)
        existing_list = existing_set.values_list('entitlement', flat=True)
        for idx, entitlement in enumerate(entitlements):
            if entitlement not in existing_list:
                InstitutionEntitlement.objects.create(institution_id=self.institution_id,
                                                    entitlement=entitlement,
                                                    login_availability=login_availability_list[idx] == 'on',
                                                    modifier=request.user)
        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': self.institution_id})
        return redirect('{}?{}'.format(base_url, query_string))


class ToggleInstitutionEntitlement(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True
    institution_id = None
    entitlement_id = None

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        self.institution_id = int(self.kwargs.get('institution_id'))
        self.entitlement_id = int(self.kwargs.get('entitlement_id'))

        # institution not exist
        if not Institution.objects.filter(id=self.institution_id, is_deleted=False).exists():
            raise Http404(
                'Institution with id "{}" not found.'.format(
                    self.institution_id
                ))

        # superuser or institutional admin has permission
        has_auth = self.is_super_admin or \
            (self.is_admin and self.is_affiliated_institution(self.institution_id))
        if not has_auth:
            return False

        entitlement = InstitutionEntitlement.objects.filter(id=self.entitlement_id).first()
        if not entitlement:
            raise Http404(
                'Entitlement with id "{}" not found.'.format(
                    self.entitlement_id
                ))
        else:
            # entitlement same institution of admin user
            return entitlement.institution_id == self.institution_id

    def post(self, request, *args, **kwargs):
        entitlement = InstitutionEntitlement.objects.get(id=self.entitlement_id)
        entitlement.login_availability = not entitlement.login_availability
        entitlement.modifier = request.user
        entitlement.save()

        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': self.institution_id, 'page': request.GET.get('page', 1)})
        return redirect('{}?{}'.format(base_url, query_string))


class DeleteInstitutionEntitlement(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True
    institution_id = None
    entitlement_id = None

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        self.institution_id = int(self.kwargs.get('institution_id'))
        self.entitlement_id = int(self.kwargs.get('entitlement_id'))

        # superuser and institution not exist
        if not Institution.objects.filter(id=self.institution_id, is_deleted=False).exists():
            raise Http404(
                'Institution with id "{}" not found.'.format(
                    self.institution_id
                ))

        # superuser or institutional admin has permission
        has_auth = self.is_super_admin or \
            (self.is_admin and self.is_affiliated_institution(self.institution_id))
        if not has_auth:
            return False

        entitlement = InstitutionEntitlement.objects.filter(id=self.entitlement_id).first()
        if not entitlement:
            raise Http404(
                'Entitlement with id "{}" not found.'.format(
                    self.entitlement_id
                ))
        else:
            # entitlement same institution of admin user
            return entitlement.institution_id == self.institution_id

    def post(self, request, *args, **kwargs):
        entitlement = InstitutionEntitlement.objects.get(id=self.kwargs['entitlement_id'])
        entitlement.delete()

        base_url = reverse('institutions:entitlements')
        query_string = urlencode({'institution_id': self.institution_id, 'page': request.GET.get('page', 1)})
        return redirect('{}?{}'.format(base_url, query_string))
