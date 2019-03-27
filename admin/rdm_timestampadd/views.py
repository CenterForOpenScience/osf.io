# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from admin.base import settings
from admin.rdm.utils import RdmPermissionMixin, get_dummy_institution
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import ListView, View, TemplateView
from osf.models import Institution, Node, AbstractNode, Guid
from website.util import timestamp
import json


class InstitutionList(RdmPermissionMixin, UserPassesTestMixin, ListView):
    paginate_by = 25
    template_name = 'rdm_timestampadd/list.html'
    ordering = 'name'
    raise_exception = True
    model = Institution

    def test_func(self):
        """validate user permissions"""
        if not self.is_authenticated:
            return False
        if self.is_super_admin or self.is_admin:
            return True
        return False

    def get(self, request, *args, **kwargs):
        """get contexts"""
        user = self.request.user
        if self.is_super_admin:
            self.object_list = self.get_queryset()
            ctx = self.get_context_data()
            return self.render_to_response(ctx)
        elif self.is_admin:
            institution = user.affiliated_institutions.first()
            if institution:
                return redirect(reverse('timestampadd:nodes', args=[institution.id]))
            else:
                institution = get_dummy_institution()
                return redirect(reverse('timestampadd:nodes', args=[institution.id]))

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

class InstitutionNodeList(RdmPermissionMixin, UserPassesTestMixin, ListView):
    template_name = 'rdm_timestampadd/node_list.html'
    paginate_by = 25
    ordering = '-modified'
    raise_exception = True
    model = Node

    def test_func(self):
        """valiate user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

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

class TimeStampAddList(RdmPermissionMixin, TemplateView):
    template_name = 'rdm_timestampadd/timestampadd.html'
    ordering = 'provider'

    def get_context_data(self, **kwargs):
        ctx = super(TimeStampAddList, self).get_context_data(**kwargs)
        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])

        ctx['init_project_timestamp_error_list'] = timestamp.get_error_list(absNodeData._id)
        ctx['project_title'] = absNodeData.title
        ctx['guid'] = self.kwargs['guid']
        ctx['institution_id'] = self.kwargs['institution_id']
        return ctx

class VerifyTimeStampAddList(RdmPermissionMixin, View):

    def post(self, request, *args, **kwargs):
        json_data = dict(self.request.POST.iterlists())
        ctx = {}
        for key in json_data.keys():
            ctx.update({key: json_data[key]})

        guid = Guid.objects.get(object_id=self.kwargs['guid'], content_type_id=ContentType.objects.get_for_model(AbstractNode).id)
        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])

        # Node Admin
        admin_osfuser_list = list(absNodeData.get_admin_contributors(absNodeData.contributors))
        source_user = self.request.user
        self.request.user = admin_osfuser_list[0]
        uid = self.request.user.id

        # Admin User
        self.request.user = source_user
        ctx['provider_list'] = timestamp.get_full_list(uid, guid._id, absNodeData)
        return HttpResponse(json.dumps(ctx), content_type='application/json')

class TimestampVerifyData(RdmPermissionMixin, View):

    def test_func(self):
        """validate user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def post(self, request, *args, **kwargs):
        json_data = dict(self.request.POST.iterlists())
        request_data = {}
        for key in json_data.keys():
            request_data.update({key: json_data[key]})
        data = {}
        for key in request_data.keys():
            data.update({key: request_data[key][0]})

        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])

        # Node Admin
        admin_osfuser_list = list(absNodeData.get_admin_contributors(absNodeData.contributors))
        source_user = self.request.user
        self.request.user = admin_osfuser_list[0]
        response = timestamp.check_file_timestamp(self.request.user.id, absNodeData, data)
        # Admin User
        self.request.user = source_user
        return HttpResponse(json.dumps(response), content_type='application/json')

class AddTimeStampResultList(RdmPermissionMixin, TemplateView):
    template_name = 'rdm_timestampadd/timestampadd.html'

    def test_func(self):
        """validate user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get_context_data(self, **kwargs):
        ctx = super(AddTimeStampResultList, self).get_context_data(**kwargs)
        guid = Guid.objects.get(object_id=self.kwargs['guid'], content_type_id=ContentType.objects.get_for_model(AbstractNode).id)
        ctx['provider_file_list'] = timestamp.get_error_list(guid._id)
        return ctx

class AddTimestampData(RdmPermissionMixin, View):

    def test_func(self):
        """validate user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def post(self, request, *args, **kwargs):
        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])

        request_data = dict(self.request.POST.iterlists())
        data = {}
        for key in request_data.keys():
            data.update({key: request_data[key][0]})

        # Change user Node-Admin
        admin_osfuser_list = list(absNodeData.get_admin_contributors(absNodeData.contributors))
        self.request.user = admin_osfuser_list[0]

        result = timestamp.add_token(self.request.user.id, absNodeData, data)

        return HttpResponse(
            json.dumps({'result': result}),
            content_type='application/json'
        )
