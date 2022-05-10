# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import json
import logging
from django.http import HttpResponse
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from admin.rdm.utils import RdmPermissionMixin
from . import erad


logger = logging.getLogger(__name__)


class ERadRecordDashboard(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    template_name = 'rdm_metadata/erad.html'

    def test_func(self):
        '''check user permissions'''
        # login check
        if not self.is_authenticated:
            return False
        # permitted if superuser only
        if self.is_super_admin:
            return True
        return False

    def get_context_data(self, **kwargs):
        return {}

class ERadRecords(RdmPermissionMixin, UserPassesTestMixin, View):
    def test_func(self):
        '''check user permissions'''
        # login check
        if not self.is_authenticated:
            return False
        # permitted if superuser only
        if self.is_super_admin:
            return True
        return False

    def post(self, request):
        files = json.loads(request.body)
        logger.info('Update Records: {} files'.format(len(files)))
        records = 0
        for file in files:
            logger.info('Updating... {}'.format(file['name']))
            try:
                records += erad.do_populate(file['name'], file['text'])
            except ValueError as e:
                return HttpResponse(
                    json.dumps({'status': 'error', 'message': str(e)}),
                    content_type='application/json',
                    status=400,
                )
        return HttpResponse(
            json.dumps({
                'status': 'OK',
                'records': records,
            }),
            content_type='application/json',
        )
