from nose.tools import *  # flake8: noqa

from framework.auth import core

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import ProjectFactory, AuthUserFactory, CommentFactory, RegistrationFactory


class TestCommentRepliesList(ApiTestCase):

    def setUp(self):
        super(TestCommentRepliesList, self).setUp()
        self.user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

    def _set_up_private_project_comment_reply(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.comment = CommentFactory(node=self.private_project, user=self.user)
        self.comment_reply = CommentFactory(node=self.private_project, target=self.comment, user=self.user)
        self.private_url = '/{}comments/{}/replies/'.format(API_BASE, self.comment._id)

    def _set_up_public_project_comment_reply(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        self.public_comment_reply = CommentFactory(node=self.public_project, target=self.public_comment, user=self.user)
        self.public_url = '/{}comments/{}/replies/'.format(API_BASE, self.public_comment._id)

    def _set_up_registration_comment_reply(self):
        self.registration = RegistrationFactory(creator=self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user)
        self.registration_comment_reply = CommentFactory(node=self.registration, target=self.registration_comment, user=self.user)
        self.registration_url = '/{}comments/{}/replies/'.format(API_BASE, self.registration_comment._id)

    def test_return_private_node_comment_replies_logged_out_user(self):
        self._set_up_private_project_comment_reply()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_return_private_node_comment_replies_logged_in_non_contributor(self):
        self._set_up_private_project_comment_reply()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_node_comment_replies_logged_in_contributor(self):
        self._set_up_private_project_comment_reply()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_out_user(self):
        self._set_up_public_project_comment_reply()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_in_non_contributor(self):
        self._set_up_public_project_comment_reply()
        res = self.app.get(self.public_url, auth=self.non_contributor)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_in_contributor(self):
        self._set_up_public_project_comment_reply()
        res = self.app.get(self.public_url, auth=self.user)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_registration_comment_replies_logged_in_contributor(self):
        self._set_up_registration_comment_reply()
        res = self.app.get(self.registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.registration_comment_reply._id, comment_ids)

    def test_return_both_deleted_and_undeleted_comment_replies(self):
        self._set_up_private_project_comment_reply()
        deleted_comment_reply = CommentFactory(project=self.private_project, target=self.comment, user=self.user, is_deleted=True)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_in(self.comment_reply._id, comment_ids)
        assert_in(deleted_comment_reply._id, comment_ids)


class TestCommentRepliesFiltering(ApiTestCase):

    def setUp(self):
        super(TestCommentRepliesFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.comment = CommentFactory(node=self.project, user=self.user)
        self.reply = CommentFactory(node=self.project, target=self.comment, user=self.user)
        self.deleted_reply = CommentFactory(node=self.project, target=self.comment, user=self.user, is_deleted=True)
        self.base_url = '/{}comments/{}/replies/'.format(API_BASE, self.comment._id)

        self.formatted_date_created = self.reply.date_created.strftime('%Y-%m-%dT%H:%M:%S.%f')
        self.reply.edit('Edited comment', auth=core.Auth(self.user), save=True)
        self.formatted_date_modified = self.reply.date_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def test_node_comments_replies_with_no_filter_returns_all(self):
        res = self.app.get(self.base_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)

    def test_filtering_for_deleted_comment_replies(self):
        url = self.base_url + '?filter[deleted]=True'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes']['deleted'])

    def test_filtering_for_non_deleted_comment_replies(self):
        url = self.base_url + '?filter[deleted]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_false(res.json['data'][0]['attributes']['deleted'])

    def test_filtering_comments_replies_created_before_date(self):
        url = self.base_url + '?filter[date_created][lt]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_comment_replies_created_on_datetime(self):
        url = self.base_url + '?filter[date_created][eq]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comment_replies_created_on_date(self):
        url = self.base_url + '?filter[date_created][eq]={}'.format(self.reply.date_created.strftime('%Y-%m-%d'))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)

    def test_filtering_comment_replies_created_after_date(self):
        url = self.base_url + '?filter[date_created][gt]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comment_replies_modified_before_date(self):
        url = self.base_url + '?filter[date_modified][lt]={}'.format(self.formatted_date_modified)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comment_replies_modified_on_date(self):
        url = self.base_url + '?filter[date_modified][eq]={}'.format(self.formatted_date_modified)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comment_replies_modified_after_date(self):
        url = self.base_url + '?filter[date_modified][gt]={}'.format(self.formatted_date_modified)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)