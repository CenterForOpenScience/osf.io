# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.generic import ListView, View

from django.contrib.auth.mixins import UserPassesTestMixin

from django.core.urlresolvers import reverse

from admin.base import settings
from osf.models import Institution, OSFUser
from osf.models import RdmUserKey
from admin.rdm.utils import RdmPermissionMixin, get_dummy_institution

class InstitutionList(RdmPermissionMixin, UserPassesTestMixin, ListView):

    paginate_by = 25
    template_name = 'rdm_keymanagement/institutions.html'
    ordering = 'name'
    raise_exception = True
    model = Institution

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False
        # allowed by superuser, or institution administrator
        if self.is_super_admin or self.is_admin:
            return True
        return False

    def get(self, request, *args, **kwargs):
        """get contexts"""
        user = self.request.user
        # superuser:
        if self.is_super_admin:
            self.object_list = self.get_queryset()
            ctx = self.get_context_data()
            return self.render_to_response(ctx)
        # institution administraor:
        elif self.is_admin:
            institution = user.affiliated_institutions.first()
            if institution:
                return redirect(reverse('keymanagement:users', args=[institution.id]))
            else:
                institution = get_dummy_institution()
                return redirect(reverse('keymanagement:users', args=[institution.id]))

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

class RemoveUserKeyList(RdmPermissionMixin, UserPassesTestMixin, ListView):

    template_name = 'rdm_keymanagement/delete_user_list.html'
    raise_exception = True
    paginate_by = 25

    def test_func(self):
        """check user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get_queryset(self):
        inst = self.kwargs['institution_id']
        query = OSFUser.objects.filter(affiliated_institutions=inst,
                                       is_active=False, date_disabled__isnull=False)
        remove_key_users = []
        for user in query:
            if RdmUserKey.objects.filter(guid=user.id, delete_flag=0).exists():
                remove_key_users.append(user)

        return remove_key_users

    def get_context_data(self, **kwargs):
        query_set = self.get_queryset()
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('page', page)
        kwargs.setdefault('institution', Institution.objects.get(id=self.kwargs['institution_id']))
        kwargs.setdefault('remove_key_users', query_set)
        return super(RemoveUserKeyList, self).get_context_data(**kwargs)

class RemoveUserKey(RdmPermissionMixin, UserPassesTestMixin, View):

    raise_exception = True

    def test_func(self):
        """check user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get(self, request, *args, **kwargs):
        guid = kwargs['user_id']

        update_datas = RdmUserKey.objects.filter(guid=guid)
        for update_data in update_datas:
            update_data.delete_flag = 1
            update_data.save()

        return HttpResponse('')
