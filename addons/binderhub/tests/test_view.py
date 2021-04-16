# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory

from .. import SHORT_NAME
from .. import settings
from .utils import BaseAddonTestCase
from website.util import api_url_for


class TestViews(BaseAddonTestCase, OsfTestCase):

    def test_empty_binder_url(self):
        self.node_settings.set_binder_url('')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['binder_url'], settings.DEFAULT_BINDER_URL)

    def test_binder_url(self):
        self.node_settings.set_binder_url('URL_1')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['binder_url'], 'URL_1')

    def test_ember_empty_binder_url(self):
        self.node_settings.set_binder_url('')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.project._id)
        assert_equals(res.json['data']['type'], 'binderhub-config')
        assert_equals(res.json['data']['attributes']['binderhub']['url'], settings.DEFAULT_BINDER_URL)

    def test_ember_binder_url(self):
        self.node_settings.set_binder_url('URL_1')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.project._id)
        assert_equals(res.json['data']['type'], 'binderhub-config')
        assert_equals(res.json['data']['attributes']['binderhub']['url'], 'URL_1')
