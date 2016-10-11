from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from api_tests.nodes.views.test_node_view_only_links_list import ViewOnlyLinkTestCase

from osf_tests.factories import NodeFactory


class TestViewOnlyLinksNodes(ViewOnlyLinkTestCase):

    def setUp(self):
        super(TestViewOnlyLinksNodes, self).setUp()
        self.url = '/{}view_only_links/{}/nodes/'.format(API_BASE, self.view_only_link._id)

    def test_admin_can_view_vol_nodes_detail(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_read_write_cannot_view_vol_detail(self):
        res = self.app.get(self.url, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_cannot_view_vol_detail(self):
        res = self.app.get(self.url, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_user_cannot_view_vol_detail(self):
        res = self.app.get(self.url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_view_vol_detail(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestViewOnlyLinkNodesSet(ViewOnlyLinkTestCase):

    def setUp(self):
        super(TestViewOnlyLinkNodesSet, self).setUp()
        self.component_one = NodeFactory(creator=self.user, parent=self.public_project, is_public=True)
        self.component_two = NodeFactory(creator=self.user, parent=self.public_project, is_public=False)

        self.project_two = NodeFactory(creator=self.user)

        self.first_level_component = NodeFactory(creator=self.user, parent=self.public_project)
        self.second_level_component = NodeFactory(creator=self.user, parent=self.first_level_component)

        self.component_one_payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': self.component_one._id
                }
            ]
        }

        self.url = '/{}view_only_links/{}/relationships/nodes/'.format(API_BASE, self.view_only_link._id)

    def test_admin_can_set_single_node(self):
        res = self.app.post_json_api(self.url, self.component_one_payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 201)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.component_one, self.view_only_link.nodes.all())

    def test_admin_can_set_multiple_nodes(self):
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': self.component_one._id
                }, {
                    'type': 'nodes',
                    'id': self.component_two._id
                }
            ]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 201)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.component_one, self.view_only_link.nodes.all())
        assert_in(self.component_two, self.view_only_link.nodes.all())

    def test_set_nodes_does_not_duplicate_nodes(self):
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': self.public_project._id
                }, {
                    'type': 'nodes',
                    'id': self.component_one._id
                }, {
                    'type': 'nodes',
                    'id': self.component_one._id
                }
            ]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 201)
        assert_equal(self.view_only_link.nodes.count(), 2)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.component_one, self.view_only_link.nodes.all())

    def test_set_node_not_component(self):
        """
        Project One (already associated with VOL)
            -> Level One Component (can be associated with VOL)

        Project Two (CANNOT be associated with this VOL)
        """
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': self.project_two._id
                },
            ]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'The node {0} cannot be affiliated with this View Only Link because the node you\'re trying to affiliate is not descended from the node that the View Only Link is attached to.'.format(self.project_two._id))

    def test_set_node_second_level_component_without_first_level_parent(self):
        """
        Parent Project (already associated with VOL)
            ->  First Level Component (NOT included)
                -> Second Level Component (included -- OK)
        """
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': self.second_level_component._id
                },
            ]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        self.view_only_link.reload()
        assert_equal(res.status_code, 201)
        assert_equal(len(res.json['data']), 2)
        assert_in(self.public_project, self.view_only_link.nodes.all())
        assert_in(self.second_level_component, self.view_only_link.nodes.all())

    def test_set_node_second_level_component_with_first_level_parent(self):
        """
        Parent Project (already associated with VOL)
            ->  First Level Component (included)
                -> Second Level Component (included -- OK)
        """
        payload = {
            'data': [
                {
                    'type': 'nodes',
                    'id': self.first_level_component._id
                },
                {
                    'type': 'nodes',
                    'id': self.second_level_component._id
                }
            ]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 201)
        assert_in(self.first_level_component, self.view_only_link.nodes.all())
        assert_in(self.second_level_component, self.view_only_link.nodes.all())

    def test_invalid_nodes_in_payload(self):
        payload = {
            'data': [{
                'type': 'nodes',
                'id': 'abcde'
            }]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_type_required_in_payload(self):
        payload = {
            'data': [{
                'id': self.component_one._id
            }]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_id_required_in_payload(self):
        payload = {
            'data': [{
                'type': 'nodes',
            }]
        }
        res = self.app.post_json_api(self.url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_read_write_contributor_cannot_set_nodes(self):
        res = self.app.post_json_api(self.url, self.component_one_payload, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_set_nodes(self):
        res = self.app.post_json_api(self.url, self.component_one_payload, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_user_cannot_set_nodes(self):
        res = self.app.post_json_api(self.url, self.component_one_payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_set_nodes(self):
        res = self.app.post_json_api(self.url, self.component_one_payload, expect_errors=True)
        assert_equal(res.status_code, 401)


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
