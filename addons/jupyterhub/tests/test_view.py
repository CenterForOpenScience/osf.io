# -*- coding: utf-8 -*-
import httplib as http

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
