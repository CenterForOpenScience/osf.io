# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.generic import ListView, View
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.urlresolvers import reverse
from admin.base import settings
from osf.models import Institution, Node, RdmTimestampGrantPattern
from admin.rdm.utils import RdmPermissionMixin, get_dummy_institution


class InstitutionList(RdmPermissionMixin, UserPassesTestMixin, ListView):
    paginate_by = 25
    template_name = 'rdm_timestampsettings/list.html'
    ordering = 'name'
    raise_exception = True
    model = Institution

    def test_func(self):
        '''権限等のチェック'''
        # ログインチェック
        if not self.is_authenticated:
            return False
        # 統合管理者または機関管理者なら許可
        if self.is_super_admin or self.is_admin:
            return True
        return False

    def get(self, request, *args, **kwargs):
        '''コンテキスト取得'''
        user = self.request.user
        # 統合管理者
        if self.is_super_admin:
            self.object_list = self.get_queryset()
            ctx = self.get_context_data()
            return self.render_to_response(ctx)
        # 機関管理者
        elif self.is_admin:
            institution = user.affiliated_institutions.first()
            if institution:
                return redirect(reverse('timestampsettings:nodes', args=[institution.id]))
            else:
                institution = get_dummy_institution()
                return redirect(reverse('timestampsettings:nodes', args=[institution.id]))

    def get_queryset(self):
        institutions = Institution.objects.all().order_by(self.ordering)
        result = []
        for institution in institutions:
            timestamp_pattern, _ = RdmTimestampGrantPattern.objects.get_or_create(
                institution_id=institution.id, node_guid__isnull=True
            )
            result.append(
                {
                    'institution': institution,
                    'timestamppattern': timestamp_pattern
                }
            )
        return result

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        kwargs.setdefault(
            'timestamppatterns',
            [
                {'name': 'Timestamp only', 'value': 1},
                {'name': 'Timestamp with digital signature', 'value': 2}
            ]
        )
        return super(InstitutionList, self).get_context_data(**kwargs)


class InstitutionNodeList(RdmPermissionMixin, UserPassesTestMixin, ListView):
    template_name = 'rdm_timestampsettings/node_list.html'
    paginate_by = 25
    ordering = '-modified'
    raise_exception = True
    model = Node

    def test_func(self):
        '''権限等のチェック'''
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get_queryset(self):
        inst = self.kwargs['institution_id']
        nodes = Node.objects.filter(affiliated_institutions=inst).order_by(self.ordering)
        result = []
        for data in nodes:
            timestamp_pattern, _ = RdmTimestampGrantPattern.objects.get_or_create(
                institution_id=inst, node_guid=data._id
            )
            result.append(
                {
                    'node': data,
                    'timestamppattern': timestamp_pattern
                }
            )
        return result

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('nodes', query_set)
        kwargs.setdefault('institution', Institution.objects.get(id=self.kwargs['institution_id']))
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        kwargs.setdefault(
            'timestamppatterns',
            [
                {'name': 'Timestamp only', 'value': 1},
                {'name': 'Timestamp with digital signature', 'value': 2}
            ]
        )
        return super(InstitutionNodeList, self).get_context_data(**kwargs)


class InstitutionTimeStampPatternForce(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True

    def test_func(self):
        '''権限等のチェック'''
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get(self, request, *args, **kwargs):
        institution_id = int(kwargs['institution_id'])
        timestamp_pattern_division = int(kwargs['timestamp_pattern_division'])
        is_forced = bool(int(kwargs['forced']))

        update_data, _ = RdmTimestampGrantPattern.objects.get_or_create(
            institution_id=institution_id, node_guid__isnull=True
        )
        update_data.timestamp_pattern_division = timestamp_pattern_division
        update_data.is_forced = is_forced
        update_data.save()

        return HttpResponse('')


class NodeTimeStampPatternChange(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True

    def test_func(self):
        '''権限等のチェック'''
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get(self, request, *args, **kwargs):
        institution_id = int(kwargs['institution_id'])
        guid = kwargs['guid']
        timestamp_pattern_division = int(kwargs['timestamp_pattern_division'])

        update_data, _ = RdmTimestampGrantPattern.objects.get_or_create(
            institution_id=institution_id, node_guid=guid
        )
        update_data.timestamp_pattern_division = timestamp_pattern_division
        update_data.save()

        return HttpResponse('')
