# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import json
import requests
import time
import os
import shutil
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.generic import ListView, View, TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from admin.base import settings
from osf.models import Institution, Node, OSFUser, AbstractNode, BaseFileNode, RdmFileTimestamptokenVerifyResult, Guid
from admin.rdm.utils import RdmPermissionMixin, get_dummy_institution
from api.base import settings as api_settings
from datetime import datetime
from api.timestamp.add_timestamp import AddTimestamp
from website.util import waterbutler_api_url_for


class InstitutionList(RdmPermissionMixin, UserPassesTestMixin, ListView):
    paginate_by = 25
    template_name = 'rdm_timestampadd/list.html'
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
        '''権限等のチェック'''
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
        data_list = RdmFileTimestamptokenVerifyResult.objects.filter(
            project_id=absNodeData._id
        ).order_by('provider', 'path')
        guid = Guid.objects.get(object_id=self.kwargs['guid'], content_type_id=ContentType.objects.get_for_model(AbstractNode).id)
        provider_error_list = []
        provider = None
        error_list = []
        for data in data_list:
            if data.inspection_result_status == api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS:
                continue

            if not provider:
                provider = data.provider
            elif provider != data.provider:
                provider_error_list.append({'provider': provider, 'error_list': error_list})
                provider = data.provider
                error_list = []

            if data.inspection_result_status == api_settings.TIME_STAMP_TOKEN_CHECK_NG:
                verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_NG_MSG  # 'NG'
            elif data.inspection_result_status == api_settings.TIME_STAMP_TOKEN_NO_DATA:
                verify_result_title = api_settings.TIME_STAMP_TOKEN_NO_DATA_MSG  # 'TST missing(Retrieving Failed)'
            elif data.inspection_result_status == api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND:
                verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG  # 'TST missing(Unverify)'
            elif data.inspection_result_status == api_settings.FILE_NOT_EXISTS:
                verify_result_title = api_settings.FILE_NOT_EXISTS_MSG  # 'FILE missing'
            else:
                verify_result_title = api_settings.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG  # 'FILE missing(Unverify)'

            if not data.update_user:
                operator_user = OSFUser.objects.get(id=data.create_user).fullname
                operator_date = data.create_date.strftime('%Y/%m/%d %H:%M:%S')
            else:
                operator_user = OSFUser.objects.get(id=data.update_user).fullname
                operator_date = data.update_date.strftime('%Y/%m/%d %H:%M:%S')

            if provider == 'osfstorage':
                base_file_data = BaseFileNode.objects.get(_id=data.file_id)
                error_info = {
                    'file_name': base_file_data.name,
                    'file_path': data.path,
                    'file_kind': 'file',
                    'project_id': data.project_id,
                    'file_id': data.file_id,
                    'version': base_file_data.current_version_number,
                    'operator_user': operator_user,
                    'operator_date': operator_date,
                    'verify_result_title': verify_result_title
                }
            else:
                file_name = os.path.basename(data.path)

                error_info = {
                    'file_name': file_name,
                    'file_path': data.path,
                    'file_kind': 'file',
                    'project_id': data.project_id,
                    'file_id': data.file_id,
                    'version': '',
                    'operator_user': operator_user,
                    'operator_date': operator_date,
                    'verify_result_title': verify_result_title
                }
            error_list.append(error_info)

        if error_list:
            provider_error_list.append({'provider': provider, 'error_list': error_list})

        ctx['init_project_timestamp_error_list'] = provider_error_list
        ctx['project_title'] = absNodeData.title
        ctx['guid'] = self.kwargs['guid']
        ctx['institution_id'] = self.kwargs['institution_id']
        ctx['web_api_url'] = self.web_api_url(guid._id)
        return ctx

    def web_api_url(self, node_id):
        return settings.osf_settings.DOMAIN + 'api/v1/project/' + node_id + '/'


class VerifyTimeStampAddList(RdmPermissionMixin, View):

    def post(self, request, *args, **kwargs):
        json_data = dict(self.request.POST.iterlists())
        ctx = {}
        for key in json_data.keys():
            ctx.update({key: json_data[key]})

        cookie = self.request.user.get_or_create_cookie()
        cookies = {settings.osf_settings.COOKIE_NAME: cookie}
        headers = {'content-type': 'application/json'}
        guid = Guid.objects.get(object_id=self.kwargs['guid'], content_type_id=ContentType.objects.get_for_model(AbstractNode).id)
        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])
        web_url = self.web_url_path(guid._id)

        # Node Admin
        admin_osfuser_list = list(absNodeData.get_admin_contributors(absNodeData.contributors))
        source_user = self.request.user
        self.request.user = admin_osfuser_list[0]
        cookie = self.request.user.get_or_create_cookie()
        cookies = {settings.osf_settings.COOKIE_NAME: cookie}

        web_response = requests.get(web_url, headers=headers, cookies=cookies)

        # Admin User
        self.request.user = source_user
        ctx['provider_file_list'] = web_response.json()['provider_list']
        ctx['guid'] = self.kwargs['guid']
        ctx['project_title'] = absNodeData.title
        ctx['institution_id'] = self.kwargs['institution_id']
        ctx['web_api_url'] = self.web_api_url(guid._id)
        return HttpResponse(json.dumps(ctx), content_type='application/json')

    def web_url_path(self, node_id):
        return settings.osf_settings.DOMAIN + node_id + '/timestamp/json/'

    def web_api_url(self, node_id):
        return settings.osf_settings.DOMAIN + 'api/v1/project/' + node_id + '/'


class TimestampVerifyData(RdmPermissionMixin, View):

    def test_func(self):
        '''権限等のチェック'''
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def post(self, request, *args, **kwargs):
        json_data = dict(self.request.POST.iterlists())
        request_data = {}
        for key in json_data.keys():
            request_data.update({key: json_data[key]})

        cookie = self.request.user.get_or_create_cookie()
        cookies = {settings.osf_settings.COOKIE_NAME: cookie}
        headers = {'content-type': 'application/json'}
        guid = Guid.objects.get(
            object_id=self.kwargs['guid'],
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id
        )
        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])
        web_url = self.web_api_url(guid._id)

        # Node Admin
        admin_osfuser_list = list(absNodeData.get_admin_contributors(absNodeData.contributors))
        source_user = self.request.user
        self.request.user = admin_osfuser_list[0]
        cookie = self.request.user.get_or_create_cookie()
        cookies = {settings.osf_settings.COOKIE_NAME: cookie}

        web_api_response = requests.post(
            web_url + 'timestamp/timestamp_error_data/',
            headers=headers, cookies=cookies,
            data=json.dumps(request_data)
        )

        # Admin User
        self.request.user = source_user

        response_json = web_api_response.json()
        web_api_response.close()
        response = response_json
        return HttpResponse(json.dumps(response), content_type='application/json')

    def web_api_url(self, node_id):
        return settings.osf_settings.DOMAIN + 'api/v1/project/' + node_id + '/'


class AddTimeStampResultList(RdmPermissionMixin, TemplateView):
    template_name = 'rdm_timestampadd/timestampadd.html'

    def test_func(self):
        '''権限等のチェック'''
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get_context_data(self, **kwargs):
        ctx = super(AddTimeStampResultList, self).get_context_data(**kwargs)
        cookie = self.request.user.get_or_create_cookie()
        cookies = {settings.osf_settings.COOKIE_NAME: cookie}
        headers = {'content-type': 'application/json'}
        guid = Guid.objects.get(
            object_id=self.kwargs['guid'],
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id
        )
        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])
        web_url = self.web_url_path(guid._id)

        web_response = requests.get(web_url, headers=headers, cookies=cookies)

        ctx['provider_file_list'] = web_response.json()['provider_list']
        ctx['guid'] = self.kwargs['guid']
        ctx['project_title'] = absNodeData.title
        ctx['institution_id'] = self.kwargs['institution_id']
        ctx['web_api_url'] = self.web_api_url(guid._id)
        return ctx

    def web_url_path(self, node_id):
        return settings.ADMIN_URL + '/timestampadd/' + self.kwargs['institution_id'] + '/nodes/' + self.kwargs['guid'] + '/'

    def web_api_url(self, node_id):
        return settings.osf_settings.DOMAIN + 'api/v1/project/' + node_id + '/'


class AddTimestampData(RdmPermissionMixin, View):

    def test_func(self):
        '''権限等のチェック'''
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def post(self, request, *args, **kwargs):
        json_data = dict(self.request.POST.iterlists())
        absNodeData = AbstractNode.objects.get(id=self.kwargs['guid'])
        request_data = {}
        for key in json_data.keys():
            request_data.update({key: json_data[key]})

        # Change user Node-Admin
        admin_osfuser_list = list(absNodeData.get_admin_contributors(absNodeData.contributors))
        source_user = self.request.user
        self.request.user = admin_osfuser_list[0]
        cookie = self.request.user.get_or_create_cookie()
        cookies = {settings.osf_settings.COOKIE_NAME: cookie}
        headers = {'content-type': 'application/json'}
        guid = Guid.objects.get(
            object_id=self.kwargs['guid'],
            content_type_id=ContentType.objects.get_for_model(AbstractNode).id
        )

        url = None
        tmp_dir = None
        data = RdmFileTimestamptokenVerifyResult.objects.get(file_id=request_data['file_id'][0])
        try:
            if request_data['provider'][0] == 'osfstorage':
                url = waterbutler_api_url_for(
                    data.project_id,
                    data.provider,
                    '/' + request_data['file_id'][0],
                    version=request_data['version'][0], action='download', direct=None
                )
            else:
                url = waterbutler_api_url_for(
                    data.project_id,
                    data.provider,
                    '/' + request_data['file_id'][0],
                    action='download', direct=None
                )
            res = requests.get(url, headers=headers, cookies=cookies)
            tmp_dir = 'tmp_{}'.format(self.request.user._id)
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            os.mkdir(tmp_dir)
            download_file_path = os.path.join(tmp_dir, request_data['file_name'][0])
            with open(download_file_path, 'wb') as fout:
                fout.write(res.content)
                res.close()

            addTimestamp = AddTimestamp()
            # Admin User
            self.request.user = source_user
            result = addTimestamp.add_timestamp(
                self.request.user._id, request_data['file_id'][0],
                guid._id, request_data['provider'][0], request_data['file_path'][0],
                download_file_path, tmp_dir
            )
            shutil.rmtree(tmp_dir)
        except Exception as err:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            raise ValueError('Exception:{}'.format(err))

        request_data.update({'result': result})
        return HttpResponse(json.dumps(request_data), content_type='application/json')

    def web_api_url(self, node_id):
        return settings.osf_settings.DOMAIN + 'api/v1/project/' + node_id + '/'


def waterbutler_meta_parameter(self):
    # get waterbutler api parameter value
    return {'meta=&_': int(time.mktime(datetime.now().timetuple()))}
