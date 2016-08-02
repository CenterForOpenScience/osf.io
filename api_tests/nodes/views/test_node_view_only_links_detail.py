from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from website.util import permissions

from test_node_view_only_links_list import ViewOnlyLinkTestCase

from tests.factories import NodeFactory, AuthUserFactory


class TestViewOnlyLinksDetail(ViewOnlyLinkTestCase):

    def setUp(self):
        super(TestViewOnlyLinksDetail, self).setUp()
        self.url = '/{}nodes/{}/view_only_links/{}/'.format(API_BASE, self.public_project._id, self.view_only_link._id)

    def test_admin_can_view_vol_detail(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'testlink')

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
        assert_equal(res.status_code, 401)

    def test_deleted_vol_not_returned(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'testlink')

        self.view_only_link.nodes.remove(self.public_project)
        self.view_only_link.save()

        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


class TestViewOnlyLinksUpdate(ViewOnlyLinkTestCase):

    def setUp(self):
        super(TestViewOnlyLinksUpdate, self).setUp()
        self.url = '/{}nodes/{}/view_only_links/{}/'.format(API_BASE, self.public_project._id, self.view_only_link._id)

        self.user_two = AuthUserFactory()
        self.public_project.add_contributor(self.user_two, permissions=[permissions.ADMIN])

        self.public_project_component = NodeFactory(is_public=True, creator=self.user, parent=self.public_project)
        self.public_project_component.save()

    def test_invalid_vol_name(self):
        payload = {
            'attributes': {
                'name': '<div>  </div>',
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid link name.')

    def test_invalid_nodes_in_payload(self):
        payload = {
            'attributes': {
                'nodes': [self.public_project._id, 'abcde'],
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Node with id "abcde" was not found')

    def test_admin_can_update_vol_name(self):
        assert_equal(self.view_only_link.name, 'testlink')
        assert_equal(self.view_only_link.anonymous, False)
        assert_equal(self.view_only_link.nodes, [self.public_project._id])

        payload = {
            'attributes': {
                'name': 'updated vol name'
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'updated vol name')
        assert_equal(res.json['data']['attributes']['anonymous'], False)
        assert_equal(res.json['data']['attributes']['nodes'], [self.public_project._id])

    def test_admin_can_update_vol_anonymous(self):
        assert_equal(self.view_only_link.name, 'testlink')
        assert_equal(self.view_only_link.anonymous, False)
        assert_equal(self.view_only_link.nodes, [self.public_project._id])

        payload = {
            'attributes': {
                'anonymous': True
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'testlink')
        assert_equal(res.json['data']['attributes']['anonymous'], True)
        assert_equal(res.json['data']['attributes']['nodes'], [self.public_project._id])

    def test_admin_can_update_vol_add_node(self):
        assert_equal(self.view_only_link.name, 'testlink')
        assert_equal(self.view_only_link.anonymous, False)
        assert_equal(self.view_only_link.nodes, [self.public_project._id])

        payload = {
            'attributes': {
                'nodes': [self.public_project._id, self.public_project_component._id]
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'testlink')
        assert_equal(res.json['data']['attributes']['anonymous'], False)
        assert_equal(res.json['data']['attributes']['nodes'], [self.public_project._id, self.public_project_component._id])

    def test_admin_can_update_vol_remove_node(self):
        self.view_only_link.nodes.append(self.public_project_component._id)
        assert_equal(self.view_only_link.name, 'testlink')
        assert_equal(self.view_only_link.anonymous, False)
        assert_equal(self.view_only_link.nodes, [self.public_project._id, self.public_project_component._id])

        payload = {
            'attributes': {
                'nodes': [self.public_project_component._id]
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'testlink')
        assert_equal(res.json['data']['attributes']['anonymous'], False)
        assert_equal(res.json['data']['attributes']['nodes'], [self.public_project_component._id])

    def test_non_admin_cannot_update_vol_nodes(self):
        self.view_only_link.nodes.append(self.public_project_component._id)
        assert_equal(self.view_only_link.nodes, [self.public_project._id, self.public_project_component._id])

        payload = {
            'attributes': {
                'nodes': [self.public_project_component._id]
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user_two.auth, expect_errors=True)

        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'User with id "{}" does not have permission to update VOL with id "{}" for node "{}"'.format(self.user_two._id, self.view_only_link._id, self.public_project_component._id))

    def test_read_write_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
                'nodes': [self.public_project._id, self.public_project_component._id]
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
                'nodes': [self.public_project._id, self.public_project_component._id]
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_user_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
                'nodes': [self.public_project._id, self.public_project_component._id]
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
                'nodes': [self.public_project._id, self.public_project_component._id]
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, expect_errors=True)
        assert_equal(res.status_code, 401)


class TestViewOnlyLinksDelete(ViewOnlyLinkTestCase):

    def test_id_required_in_payload(self):
        pass

    def test_invalid_vol_id(self):
        pass

    def test_invalid_nodes_in_payload(self):
        pass

    def test_admin_can_delete_vol(self):
        pass

    def test_read_write_cannot_delete_vol(self):
        pass

    def test_read_only_cannot_delete_vol(self):
        pass

    def test_logged_in_user_cannot_delete_vol(self):
        pass

    def test_unauthenticated_user_cannot_delete_vol(self):
        pass
