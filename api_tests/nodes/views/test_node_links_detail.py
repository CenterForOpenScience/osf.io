import pytest

from urlparse import urlparse

from framework.auth.core import Auth
from website.models import NodeLog
from api.base.settings.defaults import API_BASE
from tests.json_api_test_app import JSONAPITestApp
from tests.base import ApiTestCase
from tests.utils import assert_logs
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)

node_url_for = lambda n_id: '/{}nodes/{}/'.format(API_BASE, n_id)

@pytest.mark.django_db
class TestNodeLinkDetail:

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer = self.private_project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.private_project._id, self.pointer._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_pointer_project = ProjectFactory(is_public=True)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, self.public_pointer._id)

    def test_node_link_detail(self):

    #   test_returns_embedded_public_node_pointer_detail_logged_out
        res = self.app.get(self.public_url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == self.public_pointer_project._id

    #   test_returns_public_node_pointer_detail_logged_in
        res = self.app.get(self.public_url, auth=self.user.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == self.public_pointer_project._id

    #   test_returns_private_node_pointer_detail_logged_out
        res = self.app.get(self.private_url, expect_errors=True)
        assert res.status_code == 200
        target_node = res.json['data']['embeds']['target_node']
        assert 'errors' in target_node
        assert target_node['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    #   test_returns_private_node_pointer_detail_logged_in_contributor
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == self.pointer_project._id

    #   test_returns_private_node_pointer_detail_logged_in_non_contributor
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 200
        target_node = res.json['data']['embeds']['target_node']
        assert 'errors' in target_node
        assert target_node['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    #   test_self_link_points_to_node_link_detail_url
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert res.status_code == 200
        url = res.json['data']['links']['self']
        assert self.public_url in url

    #   test_node_links_bad_version
        url = '{}?version=2.1'.format(self.public_url)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This feature is deprecated as of version 2.1'

@pytest.mark.django_db
class TestDeleteNodeLink:

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
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
        assert pointer.child in self.public_project.nodes
        url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, pointer._id)
        res = self.app.delete_json_api(url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 204

        self.public_project.reload()
        assert pointer not in self.public_project.nodes

    def test_cannot_delete_if_registration(self):
        registration = RegistrationFactory(project=self.public_project)

        url = '/{}registrations/{}/node_links/'.format(
            API_BASE,
            registration._id,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
        pointer_id = res.json['data'][0]['id']

        url = '/{}registrations/{}/node_links/{}/'.format(
            API_BASE,
            registration._id,
            pointer_id,
        )
        res = self.app.delete(url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_deletes_public_node_pointer_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0].keys()

    def test_deletes_public_node_pointer_fails_if_bad_auth(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user_two.auth, expect_errors=True)
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]
        self.public_project.reload()
        assert node_count_before == len(self.public_project.nodes_pointer)

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    def test_deletes_public_node_pointer_succeeds_as_owner(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload()
        assert res.status_code == 204
        assert node_count_before - 1 == len(self.public_project.nodes_pointer)

    def test_deletes_private_node_pointer_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_deletes_private_node_pointer_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert res.status_code == 204
        assert len(self.project.nodes_pointer) == 0

    def test_deletes_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    def test_return_deleted_public_node_pointer(self):
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload() # Update the model to reflect changes made by post request
        assert res.status_code == 204

        #check that deleted pointer can not be returned
        res = self.app.get(self.public_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404

    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_return_deleted_private_node_pointer(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert res.status_code == 204

        #check that deleted pointer can not be returned
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_delete_link_that_is_not_linked_to_correct_node(self):
        project = ProjectFactory(creator=self.user)
        # The node link belongs to a different project
        res = self.app.delete(
            '/{}nodes/{}/node_links/{}/'.format(API_BASE, project._id, self.public_pointer._id),
            auth=self.user.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Not found.'

