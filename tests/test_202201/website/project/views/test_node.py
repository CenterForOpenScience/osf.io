#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views tests for the GakuNin RDM."""

from __future__ import absolute_import

import mock
import pytest
from framework.auth import Auth
from nose.tools import *  # noqa PEP8 asserts
from tests.base import (
    OsfTestCase,
)

pytestmark = pytest.mark.django_db

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
)


@pytest.mark.skip('Clone test case from tests/test_views.py for making coverage')
class TestComponentRemove(OsfTestCase):

    def setUp(self):
        super(TestComponentRemove, self).setUp()
        self.user1 = AuthUserFactory()
        self.user1.save()
        self.auth = self.user1.auth
        self.user2 = AuthUserFactory()

        # A project has 2 contributors
        self.project = ProjectFactory(
            title='Ham',
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()


    @mock.patch('website.util.quota.update_user_used_quota')
    def test_component_remove_with_node_is_project(self, mock_update_user_used_quota_method):
        url = self.project.api_url_for('component_remove')
        res = self.app.delete_json(url, {'node_id': self.project._id}, auth=self.auth)
        res_data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(res_data.get('url'), '/dashboard/')
        mock_update_user_used_quota_method.assert_called()

    @mock.patch('website.util.quota.update_user_used_quota')
    def test_component_remove_with_node_is_component(self, mock_update_user_used_quota_method):
        child_node = NodeFactory(parent=self.project, creator=self.user1)
        url = child_node.api_url_for('component_remove')
        res = self.app.delete_json(url, {'node_id': child_node._id}, auth=self.auth)
        res_data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(res_data.get('url'), child_node.parent_node.url)
        mock_update_user_used_quota_method.assert_not_called()
