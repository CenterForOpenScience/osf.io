from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from test_node_view_only_links_list import ViewOnlyLinkTestCase


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


class TestViewOnlyLinksCreate(ViewOnlyLinkTestCase):

    def test_id_reqired_in_payload(self):
        pass

    def test_invalid_vol_id(self):
        pass

    def test_invalid_vol_name(self):
        pass

    def test_nodes_required_in_payload(self):
        pass

    def test_invalid_nodes_in_payload(self):
        pass

    def test_admin_can_create_vol(self):
        pass

    def test_read_write_cannot_create_vol(self):
        pass

    def test_read_only_cannot_create_vol(self):
        pass

    def test_logged_in_user_cannot_create_vol(self):
        pass

    def test_unauthenticated_user_cannot_create_vol(self):
        pass


class TestViewOnlyLinksUpdate(ViewOnlyLinkTestCase):

    def test_id_reqired_in_payload(self):
        pass

    def test_invalid_vol_id(self):
        pass

    def test_invalid_vol_name(self):
        pass

    def test_nodes_required_in_payload(self):
        pass

    def test_invalid_nodes_in_payload(self):
        pass

    def test_admin_can_update_vol(self):
        pass

    def test_read_write_cannot_update_vol(self):
        pass

    def test_read_only_cannot_update_vol(self):
        pass

    def test_logged_in_user_cannot_update_vol(self):
        pass

    def test_unauthenticated_user_cannot_update_vol(self):
        pass


class TestViewOnlyLinksDelete(ViewOnlyLinkTestCase):

    def test_id_reqired_in_payload(self):
        pass

    def test_invalid_vol_id(self):
        pass

    def test_nodes_required_in_payload(self):
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
