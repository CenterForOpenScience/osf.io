# -*- coding: utf-8 -*-
import httplib as http

from nose.tools import *  # noqa
from test_log_nodes_list import LogsTestCase


class TestLogContributors(LogsTestCase):

    def test_log_detail_private_logged_in_contributor_can_access_logs(self):
        res = self.app.get(self.private_log_contribs_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data[0]['id'], self.user._id)

    def test_log_detail_private_not_logged_in_cannot_access_logs(self):
        res = self.app.get(self.private_log_contribs_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_log_detail_private_non_contributor_cannot_access_logs(self):
        res = self.app.get(self.private_log_contribs_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_log_detail_public_not_logged_in_can_access_logs(self):
        res = self.app.get(self.public_log_contribs_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data[0]['id'], self.user._id)

    def test_log_detail_public_non_contributor_can_access_logs(self):
        res = self.app.get(self.public_log_contribs_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data[0]['id'], self.user._id)
