import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import NodeLog
from osf_tests.factories import (
    ProjectFactory,
    OSFGroupFactory,
    RegistrationFactory,
    AuthUserFactory,
)
from osf.utils.permissions import WRITE, READ
from rest_framework import exceptions
from tests.utils import assert_latest_log


def node_url_for(n_id):
    return '/{}nodes/{}/'.format(API_BASE, n_id)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeLinkDetail:

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(creator=user, is_public=False)

    @pytest.fixture()
    def private_pointer_project(self, user):
        return ProjectFactory(creator=user, is_public=False)

    @pytest.fixture()
    def private_pointer(self, user, private_project, private_pointer_project):
        return private_project.add_pointer(
            private_pointer_project, auth=Auth(user), save=True)

    @pytest.fixture()
    def private_url(self, private_project, private_pointer):
        return '/{}nodes/{}/node_links/{}/'.format(
            API_BASE, private_project._id, private_pointer._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def public_pointer_project(self):
        return ProjectFactory(is_public=True)

    @pytest.fixture()
    def public_pointer(self, user, public_project, public_pointer_project):
        return public_project.add_pointer(
            public_pointer_project, auth=Auth(user), save=True)

    @pytest.fixture()
    def public_url(self, public_project, public_pointer):
        return '/{}nodes/{}/node_links/{}/'.format(
            API_BASE, public_project._id, public_pointer._id)

    def test_node_link_detail(
            self, app, user, non_contrib, private_project,
            private_pointer_project, public_pointer_project,
            public_url, private_url):

        #   test_returns_embedded_public_node_pointer_detail_logged_out
        res = app.get(public_url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == public_pointer_project._id

    #   test_returns_public_node_pointer_detail_logged_in
        res = app.get(public_url, auth=user.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == public_pointer_project._id

    #   test_returns_private_node_pointer_detail_logged_out
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 200
        target_node = res.json['data']['embeds']['target_node']
        assert 'errors' in target_node
        assert target_node['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_returns_private_node_pointer_detail_logged_in_contributor
        res = app.get(private_url, auth=user.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == private_pointer_project._id

    #   test_returns_private_node_pointer_detail_logged_in_non_contrib
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        target_node = res.json['data']['embeds']['target_node']
        assert 'errors' in target_node
        assert target_node['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_returns_private_node_pointer_detail_logged_in_group_mem
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        private_project.add_osf_group(group, READ)
        res = app.get(private_url, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 200

    #   test_self_link_points_to_node_link_detail_url
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        url = res.json['data']['links']['self']
        assert public_url in url

    #   test_node_links_bad_version
        url = '{}?version=2.1'.format(public_url)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This feature is deprecated as of version 2.1'


@pytest.mark.django_db
class TestDeleteNodeLink:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(creator=user, is_public=False)

    @pytest.fixture()
    def private_pointer_project(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def private_pointer(self, user, private_project, private_pointer_project):
        return private_project.add_pointer(
            private_pointer_project, auth=Auth(user), save=True)

    @pytest.fixture()
    def private_url(self, private_project, private_pointer):
        return '/{}nodes/{}/node_links/{}/'.format(
            API_BASE, private_project._id, private_pointer._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_pointer_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_pointer(self, user, public_project, public_pointer_project):
        return public_project.add_pointer(
            public_pointer_project, auth=Auth(user), save=True)

    @pytest.fixture()
    def public_url(self, public_project, public_pointer):
        return '/{}nodes/{}/node_links/{}/'.format(
            API_BASE, public_project._id, public_pointer._id)

    def test_delete_node_link_no_permissions_for_target_node(
            self, app, public_project, user_two, user):
        pointer_project = ProjectFactory(creator=user_two, is_public=False)
        pointer = public_project.add_pointer(
            pointer_project, auth=Auth(user), save=True)
        assert pointer.child in public_project.nodes
        url = '/{}nodes/{}/node_links/{}/'.format(
            API_BASE, public_project._id, pointer._id)
        res = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 204

        public_project.reload()
        assert pointer.child not in public_project.nodes

    def test_cannot_delete_if_registration(
            self, app, user, public_project, user_two, public_pointer):
        registration = RegistrationFactory(project=public_project)

        url = '/{}registrations/{}/node_links/'.format(
            API_BASE,
            registration._id,
        )
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        pointer_id = res.json['data'][0]['id']

        # registration delete nodelink to a project
        url = '/{}registrations/{}/node_links/{}/'.format(
            API_BASE,
            registration._id,
            pointer_id,
        )
        res = app.delete(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # registration delete nodelink to a registration
        project_user_two = ProjectFactory(creator=user_two, is_public=False)
        pointer = project_user_two.add_pointer(
            registration, auth=Auth(user_two), save=True)
        registration_user_two = RegistrationFactory(
            project=project_user_two, creator=user_two)

        url = '/{}registrations/{}/node_links/{}/'.format(
            API_BASE,
            registration_user_two._id,
            pointer._id,
        )
        res = app.delete(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 405

    def test_can_delete_node_link_target_node_is_public_registration(
            self, app, public_project, user_two, user):
        public_registration = RegistrationFactory(
            creator=user, project=public_project, is_public=True)
        project_user_two = ProjectFactory(creator=user_two, is_public=False)
        pointer = project_user_two.add_pointer(
            public_registration, auth=Auth(user_two), save=True)

        url = '/{}nodes/{}/node_links/{}/'.format(
            API_BASE, project_user_two._id, pointer._id)
        assert pointer.child in project_user_two.nodes
        res = app.delete_json_api(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 204
        project_user_two.reload()
        assert pointer.child not in project_user_two.nodes

    def test_can_delete_node_link_target_node_is_private_registration(
            self, app, public_project, user_two, user):
        private_registration = RegistrationFactory(
            creator=user, project=public_project, is_public=False)
        project_user_two = ProjectFactory(creator=user_two, is_public=False)
        pointer = project_user_two.add_pointer(
            private_registration, auth=Auth(user_two), save=True)

        url = '/{}nodes/{}/node_links/{}/'.format(
            API_BASE, project_user_two._id, pointer._id)
        assert pointer.child in project_user_two.nodes
        res = app.delete_json_api(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 204
        project_user_two.reload()
        assert pointer.child not in project_user_two.nodes

    def test_deletes_public_node_pointer_logged_out(self, app, public_url):
        res = app.delete(public_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0].keys()

    def test_deletes_public_node_pointer_fails_if_bad_auth(
            self, app, user_two, public_project, public_url):
        node_count_before = len(public_project.nodes_pointer)
        res = app.delete(public_url, auth=user_two.auth, expect_errors=True)
        # This is could arguably be a 405, but we don't need to go crazy with
        # status codes
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]
        public_project.reload()
        assert node_count_before == len(public_project.nodes_pointer)

    def test_deletes_public_node_pointer_succeeds_as_owner(
            self, app, user, public_project, public_pointer, public_url):
        with assert_latest_log(NodeLog.POINTER_REMOVED, public_project):
            node_count_before = len(public_project.nodes_pointer)
            res = app.delete(public_url, auth=user.auth)
            public_project.reload()
            assert res.status_code == 204
            assert node_count_before - 1 == len(public_project.nodes_pointer)

    def test_deletes_private_node_pointer_logged_out(self, app, private_url):
        res = app.delete(private_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_pointer_logged_in_contributor(
            self, app, user, private_project, private_url):
        with assert_latest_log(NodeLog.POINTER_REMOVED, private_project):
            res = app.delete(private_url, auth=user.auth)
            private_project.reload()  # Update the model to reflect changes made by post request
            assert res.status_code == 204
            assert len(private_project.nodes_pointer) == 0

    def test_deletes_private_node_pointer_logged_in_non_contrib(
            self, app, user_two, private_url):
        res = app.delete(private_url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_pointer_logged_in_read_group_mem(
            self, app, user_two, private_url, private_project):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        private_project.add_osf_group(group, READ)
        res = app.delete(private_url, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 403
        private_project.update_osf_group(group, WRITE)
        res = app.delete(private_url, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 204

    def test_return_deleted_public_node_pointer(
            self, app, user, public_project, public_url):
        with assert_latest_log(NodeLog.POINTER_REMOVED, public_project):
            res = app.delete(public_url, auth=user.auth)
            public_project.reload()  # Update the model to reflect changes made by post request
            assert res.status_code == 204

        # check that deleted pointer can not be returned
        res = app.get(public_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_return_deleted_private_node_pointer(
            self, app, user, private_project, private_url):
        with assert_latest_log(NodeLog.POINTER_REMOVED, private_project):
            res = app.delete(private_url, auth=user.auth)
            private_project.reload()  # Update the model to reflect changes made by post request
            assert res.status_code == 204

        # check that deleted pointer can not be returned
        res = app.get(private_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_delete_link_that_is_not_linked_to_correct_node(
            self, app, user, public_pointer):
        project = ProjectFactory(creator=user)
        # The node link belongs to a different project
        res = app.delete(
            '/{}nodes/{}/node_links/{}/'.format(API_BASE, project._id, public_pointer._id),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == exceptions.NotFound.default_detail
