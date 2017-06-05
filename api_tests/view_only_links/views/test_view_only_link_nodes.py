import pytest
from nose.tools import *  # flake8: noqa

from website.util import permissions
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory,
    NodeFactory
)


@pytest.fixture(scope='function')
def user():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def read_only_user():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def read_write_user():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def non_contributor():
    return AuthUserFactory()

@pytest.fixture(scope='function')
def public_project(user, read_only_user, read_write_user):
    public_project = ProjectFactory(is_public=True, creator=user)
    public_project.add_contributor(read_only_user, permissions=[permissions.READ])
    public_project.add_contributor(read_write_user, permissions=[permissions.WRITE])
    public_project.save()
    return public_project

@pytest.fixture(scope='function')
def view_only_link(public_project):
    view_only_link = PrivateLinkFactory(name='testlink')
    view_only_link.nodes.add(public_project)
    view_only_link.save()
    return view_only_link

@pytest.mark.django_db
class TestViewOnlyLinksNodes:

    @pytest.fixture()
    def url(self, view_only_link):
        return '/{}view_only_links/{}/nodes/'.format(API_BASE, view_only_link._id)

    def test_view_only_links_nodes(self, app, user, read_only_user, read_write_user, non_contributor, url):

    #   test_admin_can_view_vol_nodes_detail
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

    #   test_read_write_cannot_view_vol_detail
        res = app.get(url, auth=read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_view_vol_detail
        res = app.get(url, auth=read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_view_vol_detail
        res = app.get(url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_vol_detail
        res = app.get(url, expect_errors=True)
        assert res.status_code == 403

@pytest.mark.django_db
class TestViewOnlyLinkNodesSet:

    @pytest.fixture()
    def component_one(self, user, public_project):
        return NodeFactory(creator=user, parent=public_project, is_public=True)

    @pytest.fixture()
    def component_two(self, user, public_project):
        return NodeFactory(creator=user, parent=public_project, is_public=False)

    @pytest.fixture()
    def project_two(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def first_level_component(self, user, public_project):
        return NodeFactory(creator=user, parent=public_project)

    @pytest.fixture()
    def second_level_component(self, user, first_level_component):
        return NodeFactory(creator=user, parent=first_level_component)

    @pytest.fixture()
    def component_one_payload(self, component_one):
        return {
            'data': [
                {
                    'type': 'nodes',
                    'id': component_one._id
                }
            ]
        }

    @pytest.fixture()
    def url(self, view_only_link):
        return '/{}view_only_links/{}/relationships/nodes/'.format(API_BASE, view_only_link._id)

    def test_admin_can_set_single_node(self, app, user, public_project, component_one, component_one_payload, view_only_link, url):
        res = app.post_json_api(url, component_one_payload, auth=user.auth)
        view_only_link.reload()
        assert res.status_code == 201
        assert public_project in view_only_link.nodes.all()
        assert component_one in view_only_link.nodes.all()

    def test_admin_can_set_multiple_nodes(self, app, user, public_project, component_one, component_two, view_only_link, url):
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': component_one._id
                }, {
                    'type': 'nodes',
                    'id': component_two._id
                }
            ]
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        view_only_link.reload()
        assert res.status_code == 201
        assert public_project in view_only_link.nodes.all()
        assert component_one in view_only_link.nodes.all()
        assert component_two in view_only_link.nodes.all()

    def test_set_nodes_does_not_duplicate_nodes(self, app, user, public_project, component_one, view_only_link, url):
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': public_project._id
                }, {
                    'type': 'nodes',
                    'id': component_one._id
                }, {
                    'type': 'nodes',
                    'id': component_one._id
                }
            ]
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        view_only_link.reload()
        assert res.status_code == 201
        assert view_only_link.nodes.count() == 2
        assert public_project in view_only_link.nodes.all()
        assert component_one in view_only_link.nodes.all()

    def test_set_node_not_component(self, app, user, project_two, url):
        """
        Project One (already associated with VOL)
            -> Level One Component (can be associated with VOL)

        Project Two (CANNOT be associated with this VOL)
        """
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': project_two._id
                },
            ]
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'The node {0} cannot be affiliated with this View Only Link because the node you\'re trying to affiliate is not descended from the node that the View Only Link is attached to.'.format(project_two._id)

    def test_set_node_second_level_component_without_first_level_parent(self, app, user, public_project, second_level_component, view_only_link, url):
        """
        Parent Project (already associated with VOL)
            ->  First Level Component (NOT included)
                -> Second Level Component (included -- OK)
        """
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': second_level_component._id
                },
            ]
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        view_only_link.reload()
        assert res.status_code == 201
        assert len(res.json['data']) == 2
        assert public_project in view_only_link.nodes.all()
        assert second_level_component in view_only_link.nodes.all()

    def test_set_node_second_level_component_with_first_level_parent(self, app, user, first_level_component, second_level_component, view_only_link, url):
        """
        Parent Project (already associated with VOL)
            ->  First Level Component (included)
                -> Second Level Component (included -- OK)
        """
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': first_level_component._id
                },
                {
                    'type': 'nodes',
                    'id': second_level_component._id
                }
            ]
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        view_only_link.reload()
        assert res.status_code == 201
        assert first_level_component in view_only_link.nodes.all()
        assert second_level_component in view_only_link.nodes.all()

    def test_view_only_link_nodes_set_errors(self, app, user, read_write_user, read_only_user, non_contributor, component_one_payload, component_one, url):

    #   test_invalid_nodes_in_payload
        payload = {
            'data': [{
                'type': 'nodes',
                'id': 'abcde'
            }]
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_type_required_in_payload
        payload = {
            'data': [{
                'id': component_one._id
            }]
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_id_required_in_payload
        payload = {
            'data': [{
                'type': 'nodes',
            }]
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_read_write_contributor_cannot_set_nodes
        res = app.post_json_api(url, component_one_payload, auth=read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_contributor_cannot_set_nodes
        res = app.post_json_api(url, component_one_payload, auth=read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_set_nodes
        res = app.post_json_api(url, component_one_payload, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_set_nodes
        res = app.post_json_api(url, component_one_payload, expect_errors=True)
        assert res.status_code == 401

class TestViewOnlyLinkNodesUpdate(TestViewOnlyLinkNodesSet):

    def setUp(self):
        super(TestViewOnlyLinkNodesUpdate, self).setUp()
        self.update_payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id
            }, {
                'type': 'nodes',
                'id': self.component_one._id
            }]
        }

    def test_admin_can_update_nodes_single_node_to_add(self):
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.component_one, self.view_only_link.nodes.all())

    def test_admin_can_update_nodes_multiple_nodes_to_add(self):
        self.update_payload['data'].append({
            'type': 'nodes',
            'id': self.component_two._id
        })
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 3)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.component_one, self.view_only_link.nodes.all())
        assert_in(self.component_two, self.view_only_link.nodes.all())

    def test_admin_can_update_nodes_single_node_to_remove(self):
        self.view_only_link.nodes.add(self.component_one)
        self.view_only_link.save()
        self.update_payload['data'].pop()
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_not_in(self.component_one, self.view_only_link.nodes.all())

    def test_admin_can_update_nodes_multiple_nodes_to_remove(self):
        self.view_only_link.nodes.add(self.component_one)
        self.view_only_link.nodes.add(self.component_two)
        self.view_only_link.save()
        self.update_payload['data'].pop()
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_not_in(self.component_one, self.view_only_link.nodes.all())
        assert_not_in(self.component_two, self.view_only_link.nodes.all())


    def test_admin_can_update_nodes_single_add_single_remove(self):
        self.view_only_link.nodes.add(self.component_two)
        self.view_only_link.save()
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.component_one, self.view_only_link.nodes.all())
        assert_not_in(self.component_two, self.view_only_link.nodes.all())


    def test_admin_can_update_nodes_multiple_add_multiple_remove(self):
        self.view_only_link.nodes.add(self.component_one)
        self.view_only_link.nodes.add(self.component_two)
        self.view_only_link.save()

        component_three = NodeFactory(creator=self.user, parent=self.public_project)
        component_four = NodeFactory(creator=self.user, parent=self.public_project)

        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id,
            }, {
                'type': 'nodes',
                'id': component_three._id
            }, {
                'type': 'nodes',
                'id': component_four._id
            }]
        }

        res = self.app.put_json_api(self.url, payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 3)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_not_in(self.component_one, self.view_only_link.nodes.all())
        assert_not_in(self.component_two, self.view_only_link.nodes.all())
        assert_in(component_three, self.view_only_link.nodes.all())
        assert_in(component_four, self.view_only_link.nodes.all())

    def test_update_nodes_no_changes(self):
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id,
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_in(self.public_project, self.view_only_link.nodes.all())

    def test_update_nodes_top_level_node_not_included(self):
        """
        Parent Project (NOT included)
            ->  First Level Component (included) -- NOT ALLOWED
        """
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.component_one._id
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'The node {0} cannot be affiliated with this View Only Link because the node you\'re trying to affiliate is not descended from the node that the View Only Link is attached to.'.format(self.component_one._id))

    def test_update_node_not_component(self):
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.project_two._id
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'The node {0} cannot be affiliated with this View Only Link because the node you\'re trying to affiliate is not descended from the node that the View Only Link is attached to.'.format(self.project_two._id))

    def test_update_node_second_level_component_without_first_level_parent(self):
        """
        Parent Project (included)
            ->  First Level Component (NOT included)
                -> Second Level Component (included) -- OK
        """
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id
            }, {
                'type': 'nodes',
                'id': self.second_level_component._id
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.second_level_component, self.view_only_link.nodes.all())

    def test_update_node_second_level_component_with_first_level_parent(self):
        """
        Parent Project (included)
            ->  First Level Component (included)
                -> Second Level Component (included) -- OK
        """
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id
            }, {
                'type': 'nodes',
                'id': self.first_level_component._id
            }, {
                'type': 'nodes',
                'id': self.second_level_component._id
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        self.view_only_link.reload()
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 3)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.first_level_component, self.view_only_link.nodes.all())
        assert_in(self.second_level_component, self.view_only_link.nodes.all())

    def test_invalid_nodes_in_payload(self):
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id
            }, {
                'type': 'nodes',
                'id': 'abcde'
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_type_required_in_payload(self):
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id
            }, {
                'id': self.component_one._id
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_id_required_in_payload(self):
        payload = {
            'data': [{
                'type': 'nodes',
                'id': self.public_project._id
            }, {
                'type': 'nodes'
            }]
        }
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_read_write_contributor_cannot_update_nodes(self):
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_update_nodes(self):
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_user_cannot_update_nodes(self):
        res = self.app.put_json_api(self.url, self.update_payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_update_nodes(self):
        res = self.app.put_json_api(self.url, self.update_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
