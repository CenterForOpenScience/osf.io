from nose.tools import *  # flake8: noqa
from datetime import datetime

from api.base.settings.defaults import API_BASE
from api_tests import utils as test_utils
from tests.base import ApiTestCase
from tests.factories import ProjectFactory, AuthUserFactory, CommentFactory


class TestReportDetailView(ApiTestCase):

    def setUp(self):
        super(TestReportDetailView, self).setUp()
        self.user = AuthUserFactory()
        self.contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()
        self.payload = {
            'data': {
                'id': self.user._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }

    def _set_up_private_project_comment_reports(self):
        self.private_project = ProjectFactory.create(is_public=False, creator=self.user)
        self.private_project.add_contributor(contributor=self.contributor, save=True)
        self.comment = CommentFactory.build(node=self.private_project, user=self.contributor)
        self.comment.reports = {self.user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }}
        self.comment.save()
        self.private_url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.comment._id, self.user._id)

    def _set_up_public_project_comment_reports(self):
        self.public_project = ProjectFactory.create(is_public=True, creator=self.user)
        self.public_project.add_contributor(contributor=self.contributor, save=True)
        self.public_comment = CommentFactory.build(node=self.public_project, user=self.contributor)
        self.public_comment.reports = {self.user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }}
        self.public_comment.save()
        self.public_url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.user._id)

    def test_private_node_reporting_contributor_can_view_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_private_node_reported_contributor_cannot_view_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.get(self.private_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_view_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_view_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_view_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_public_node_reported_contributor_cannot_view_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.get(self.public_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_view_other_users_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_view_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_view_own_report_detail(self):
        self._set_up_public_project_comment_reports()
        self.public_comment.reports[self.non_contributor._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }
        self.public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.non_contributor._id)
        res = self.app.get(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_private_node_reporting_contributor_can_update_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)
        assert_equal(res.json['data']['attributes']['message'], self.payload['data']['attributes']['message'])

    def test_private_node_reported_contributor_cannot_update_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_update_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_update_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_update_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)
        assert_equal(res.json['data']['attributes']['message'], self.payload['data']['attributes']['message'])

    def test_public_node_reported_contributor_cannot_update_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_update_other_users_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_update_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_update_own_report_detail(self):
        self._set_up_public_project_comment_reports()
        self.public_comment.reports[self.non_contributor._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }
        self.public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.non_contributor._id)
        payload = {
            'data': {
                'id': self.non_contributor._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['message'], payload['data']['attributes']['message'])

    def test_private_node_reporting_contributor_can_delete_report_detail(self):
        self._set_up_private_project_comment_reports()
        comment = CommentFactory.build(node=self.private_project, user=self.contributor)
        comment.reports = {self.user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }}
        comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, comment._id, self.user._id)
        res = self.app.delete_json_api(url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_private_node_reported_contributor_cannot_delete_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.delete_json_api(self.private_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_delete_report_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.delete_json_api(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_delete_detail(self):
        self._set_up_private_project_comment_reports()
        res = self.app.delete_json_api(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_delete_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_public_node_reported_contributor_cannot_delete_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.delete_json_api(self.public_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_delete_other_users_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.delete_json_api(self.public_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_delete_report_detail(self):
        self._set_up_public_project_comment_reports()
        res = self.app.delete_json_api(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_delete_own_report_detail(self):
        self._set_up_public_project_comment_reports()
        self.public_comment.reports[self.non_contributor._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }
        self.public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.non_contributor._id)
        res = self.app.delete_json_api(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 204)


class TestFileCommentReportDetailView(ApiTestCase):

    def setUp(self):
        super(TestFileCommentReportDetailView, self).setUp()
        self.user = AuthUserFactory()
        self.contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()
        self.payload = {
            'data': {
                'id': self.user._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }

    def _set_up_private_project_file_comment_reports(self):
        self.private_project = ProjectFactory.create(is_public=False, creator=self.user)
        self.private_project.add_contributor(contributor=self.contributor, save=True)
        self.file = test_utils.create_test_file(self.private_project, self.user)
        self.comment = CommentFactory.build(node=self.private_project, target=self.file.get_guid(), user=self.contributor)
        self.comment.reports = {self.user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }}
        self.comment.save()
        self.private_url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.comment._id, self.user._id)

    def _set_up_public_project_file_comment_reports(self):
        self.public_project = ProjectFactory.create(is_public=True, creator=self.user)
        self.public_project.add_contributor(contributor=self.contributor, save=True)
        self.public_file = test_utils.create_test_file(self.public_project, self.user)
        self.public_comment = CommentFactory.build(node=self.public_project, target=self.public_file.get_guid(), user=self.contributor)
        self.public_comment.reports = {self.user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }}
        self.public_comment.save()
        self.public_url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.user._id)

    def test_private_node_reporting_contributor_can_view_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_private_node_reported_contributor_cannot_view_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.get(self.private_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_view_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_view_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_view_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_public_node_reported_contributor_cannot_view_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.get(self.public_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_view_other_users_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_view_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_view_own_file_comment_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        self.public_comment.reports[self.non_contributor._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }
        self.public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.non_contributor._id)
        res = self.app.get(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_private_node_reporting_contributor_can_update_file_comment_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)
        assert_equal(res.json['data']['attributes']['message'], self.payload['data']['attributes']['message'])

    def test_private_node_reported_contributor_cannot_update_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_update_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_update_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.put_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_update_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)
        assert_equal(res.json['data']['attributes']['message'], self.payload['data']['attributes']['message'])

    def test_public_node_reported_contributor_cannot_update_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_update_other_user_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_update_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.put_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_update_own_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        self.public_comment.reports[self.non_contributor._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }
        self.public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.non_contributor._id)
        payload = {
            'data': {
                'id': self.non_contributor._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['message'], payload['data']['attributes']['message'])

    def test_private_node_reporting_contributor_can_delete_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        comment = CommentFactory.build(node=self.private_project, target=self.file.get_guid(), user=self.contributor)
        comment.reports = {self.user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }}
        comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, comment._id, self.user._id)
        res = self.app.delete_json_api(url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_private_node_reported_contributor_cannot_delete_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.delete_json_api(self.private_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_delete_report_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.delete_json_api(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_delete_detail(self):
        self._set_up_private_project_file_comment_reports()
        res = self.app.delete_json_api(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_delete_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_public_node_reported_contributor_cannot_delete_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.delete_json_api(self.public_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_delete_other_users_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.delete_json_api(self.public_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_delete_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        res = self.app.delete_json_api(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_delete_own_report_detail(self):
        self._set_up_public_project_file_comment_reports()
        self.public_comment.reports[self.non_contributor._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': datetime.utcnow(),
            'retracted': False,
        }
        self.public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.non_contributor._id)
        res = self.app.delete_json_api(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 204)
