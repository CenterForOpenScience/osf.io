from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from api_tests.nodes.views.test_node_view_only_links_list import ViewOnlyLinkTestCase


class TestViewOnlyLinksDetail(ViewOnlyLinkTestCase):

    def setUp(self):
        super(TestViewOnlyLinksDetail, self).setUp()
        self.url = '/{}view_only_links/{}/'.format(API_BASE, self.view_only_link._id)

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
        assert_equal(res.status_code, 403)
