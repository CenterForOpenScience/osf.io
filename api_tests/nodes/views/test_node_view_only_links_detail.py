from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from website.util import permissions

from test_node_view_only_links_list import ViewOnlyLinkTestCase

from osf_tests.factories import NodeFactory, AuthUserFactory


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

    def test_admin_can_update_vol_name(self):
        assert_equal(self.view_only_link.name, 'testlink')
        assert_equal(self.view_only_link.anonymous, False)

        payload = {
            'attributes': {
                'name': 'updated vol name'
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'updated vol name')
        assert_equal(res.json['data']['attributes']['anonymous'], False)

    def test_admin_can_update_vol_anonymous(self):
        assert_equal(self.view_only_link.name, 'testlink')
        assert_equal(self.view_only_link.anonymous, False)

        payload = {
            'attributes': {
                'anonymous': True
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'testlink')
        assert_equal(res.json['data']['attributes']['anonymous'], True)

    def test_read_write_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_user_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_update_vol(self):
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = self.app.put_json_api(self.url, {'data': payload}, expect_errors=True)
        assert_equal(res.status_code, 401)


class TestViewOnlyLinksDelete(ViewOnlyLinkTestCase):

    def setUp(self):
        super(TestViewOnlyLinksDelete, self).setUp()
        self.url = '/{}nodes/{}/view_only_links/{}/'.format(API_BASE, self.public_project._id, self.view_only_link._id)

    def test_admin_can_delete_vol(self):
        res = self.app.delete(self.url, auth=self.user.auth)
        self.view_only_link.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.view_only_link.is_deleted, True)

    def test_read_write_cannot_delete_vol(self):
        res = self.app.delete(self.url, auth=self.read_write_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_read_only_cannot_delete_vol(self):
        res = self.app.delete(self.url, auth=self.read_only_user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_logged_in_user_cannot_delete_vol(self):
        res = self.app.delete(self.url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_unauthenticated_user_cannot_delete_vol(self):
        res = self.app.delete(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)
