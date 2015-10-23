# -*- coding: utf-8 -*-
import json
import base64
from urlparse import urlparse

import mock
from nose.tools import *  # flake8: noqa
import httpretty

from framework.auth.core import Auth

from website.addons.github import model
from website.models import Node, NodeLog
from website.views import find_dashboard
from website.util import permissions, waterbutler_api_url_for
from website.util.sanitize import strip_html
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase, fake
from tests.factories import (
    DashboardFactory,
    FolderFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
    AuthUserFactory
)
from tests.utils import assert_logs, assert_not_logs










class NodeCRUDTestCase(ApiTestCase):

    def setUp(self):
        super(NodeCRUDTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'
        self.new_category = 'project'

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.fake_url = '/{}nodes/{}/'.format(API_BASE, '12345')

def make_node_payload(node, attributes):
    return {
        'data': {
            'id': node._id,
            'type': 'nodes',
            'attributes': attributes,
        }
    }













node_url_for = lambda n_id: '/{}nodes/{}/'.format(API_BASE, n_id)







def prepare_mock_wb_response(
        node=None,
        provider='github',
        files=None,
        folder=True,
        path='/',
        method=httpretty.GET,
        status_code=200
    ):
    """Prepare a mock Waterbutler response with httpretty.

    :param Node node: Target node.
    :param str provider: Addon provider
    :param list files: Optional list of files. You can specify partial data; missing values
        will have defaults.
    :param folder: True if mocking out a folder response, False if a file response.
    :param path: Waterbutler path, passed to waterbutler_api_url_for.
    :param str method: HTTP method.
    :param int status_code: HTTP status.
    """
    node = node
    files = files or []
    wb_url = waterbutler_api_url_for(node._id, provider=provider, path=path, meta=True)

    default_file = {
        u'contentType': None,
        u'extra': {u'downloads': 0, u'version': 1},
        u'kind': u'file',
        u'modified': None,
        u'name': u'NewFile',
        u'path': u'/NewFile',
        u'provider': provider,
        u'size': None,
        u'materialized': '/',
    }

    if len(files):
        data = [dict(default_file, **each) for each in files]
    else:
        data = [default_file]

    jsonapi_data = []
    for datum in data:
        jsonapi_data.append({'attributes': datum})

    if not folder:
        jsonapi_data = jsonapi_data[0]

    body = json.dumps({
        u'data': jsonapi_data
    })
    httpretty.register_uri(
        method,
        wb_url,
        body=body,
        status=status_code,
        content_type='application/json'
    )







