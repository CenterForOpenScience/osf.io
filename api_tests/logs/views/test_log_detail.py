# -*- coding: utf-8 -*-
from nose.tools import *  # noqa
from test_log_nodes_list import LogsTestCase


class TestLogDetail(LogsTestCase):

    def test_log_detail_returns_data(self):
        res = self.app.get(self.private_log_detail, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data['id'], self.log._id)

    def test_log_detail_private_not_logged_in_cannot_access_logs(self):
        res = self.app.get(self.private_log_detail, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_log_detail_private_non_contributor_cannot_access_logs(self):
        res = self.app.get(self.private_log_detail, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_log_detail_public_not_logged_in_can_access_logs(self):
        res = self.app.get(self.public_log_detail, expect_errors=True)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data['id'], self.public_log._id)

    def test_log_detail_public_non_contributor_can_access_logs(self):
        res = self.app.get(self.public_log_detail, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data['id'], self.public_log._id)

    def test_log_detail_data_format_api(self):
        res = self.app.get(self.public_log_detail + '?format=api', auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in(self.public_log._id, res.body)

