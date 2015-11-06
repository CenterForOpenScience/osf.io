# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
from urlparse import urlparse
from framework.auth.core import Auth

from website.models import NodeLog

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory
)
from tests.utils import assert_logs

node_url_for = lambda n_id: '/{}nodes/{}/'.format(API_BASE, n_id)


class TestNodeLinkDetail(ApiTestCase):

    def setUp(self):
        super(TestNodeLinkDetail, self).setUp()
        self.user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer = self.private_project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.private_project._id, self.pointer._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True)
        self.public_pointer_project = ProjectFactory(is_public=True)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, self.public_pointer._id)

    def test_returns_public_node_pointer_detail_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        expected_path = node_url_for(self.public_pointer_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_returns_public_node_pointer_detail_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_path = node_url_for(self.public_pointer_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_returns_private_node_pointer_detail_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_returns_private_node_pointer_detail_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_path = node_url_for(self.pointer_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_returns_private_node_pointer_detail_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_self_link_points_to_node_link_detail_url(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        url = res.json['data']['links']['self']
        assert_in(self.public_url, url)


class TestDeleteNodeLink(ApiTestCase):

    def setUp(self):
        super(TestDeleteNodeLink, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=True)
        self.pointer = self.project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.project._id, self.pointer._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, self.public_pointer._id)

    def test_delete_node_link_no_permissions_for_target_node(self):
        pointer_project = ProjectFactory(creator=self.user_two, is_public=False)
        pointer = self.public_project.add_pointer(pointer_project, auth=Auth(self.user), save=True)
        assert_in(pointer, self.public_project.nodes)
        url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, pointer._id)
        res = self.app.delete_json_api(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 204)

        self.public_project.reload()
        assert_not_in(pointer, self.public_project.nodes)

    def test_cannot_delete_if_registration(self):
        registration = RegistrationFactory(project=self.public_project)

        url = '/{}nodes/{}/node_links/'.format(
            API_BASE,
            registration._id,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        pointer_id = res.json['data'][0]['id']

        url = '/{}nodes/{}/node_links/{}/'.format(
            API_BASE,
            registration._id,
            pointer_id,
        )
        res = self.app.delete(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_deletes_public_node_pointer_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0].keys())

    def test_deletes_public_node_pointer_fails_if_bad_auth(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user_two.auth, expect_errors=True)
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])
        self.public_project.reload()
        assert_equal(node_count_before, len(self.public_project.nodes_pointer))

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    def test_deletes_public_node_pointer_succeeds_as_owner(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.public_project.nodes_pointer))

    def test_deletes_private_node_pointer_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_deletes_private_node_pointer_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)
        assert_equal(len(self.project.nodes_pointer), 0)

    def test_deletes_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    def test_return_deleted_public_node_pointer(self):
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload() # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        #check that deleted pointer can not be returned
        res = self.app.get(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_return_deleted_private_node_pointer(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        #check that deleted pointer can not be returned
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_delete_link_that_is_not_linked_to_correct_node(self):
        project = ProjectFactory(creator=self.user)
        # The node link belongs to a different project
        res = self.app.delete(
            '/{}nodes/{}/node_links/{}/'.format(API_BASE, project._id, self.public_pointer._id),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 404)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Node link does not belong to the requested node.')

