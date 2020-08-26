# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory

from addons.jupyterhub.tests.utils import JupyterhubAddonTestCase
from website.util import api_url_for


class TestJupyterhubViews(JupyterhubAddonTestCase, OsfTestCase):

    def test_jupyterhub_empty_services(self):
        self.node_settings.set_services([])
        self.node_settings.save()
        url = self.project.api_url_for('jupyterhub_get_services')
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(len(res.json['data']), 0)

    def test_jupyterhub_services(self):
        self.node_settings.set_services([('jh1', 'https://jh1.test/')])
        self.node_settings.save()
        url = self.project.api_url_for('jupyterhub_get_services')
        res = self.app.get(url, auth=self.user.auth)
        import_url = 'https://jh1.test/rcosrepo/import/' + \
                     self.node_settings.owner._id
        assert_equals(len(res.json['data']), 1)
        assert_equals(res.json['data'][0]['name'], 'jh1')
        assert_equals(res.json['data'][0]['base_url'], 'https://jh1.test/')
        assert_equals(res.json['data'][0]['import_url'], import_url)
