from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import ProjectFactory, AuthUserFactory, CommentFactory, RegistrationFactory


class TestCommentRepliesList(ApiTestCase):

    def setUp(self):
        super(TestCommentRepliesList, self).setUp()
        self.user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()
        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.registration = RegistrationFactory(creator=self.user)

        self.comment = CommentFactory(node=self.private_project, user=self.user)
        self.comment_reply = CommentFactory(node=self.private_project, target=self.comment, user=self.user)

        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        self.public_comment_reply = CommentFactory(node=self.public_project, target=self.public_comment, user=self.user)

        self.registration_comment = CommentFactory(node=self.registration, user=self.user)
        self.registration_comment_reply = CommentFactory(node=self.registration, target=self.registration_comment, user=self.user)

        self.private_url = '/{}comments/{}/replies/'.format(API_BASE, self.comment._id)
        self.public_url = '/{}comments/{}/replies/'.format(API_BASE, self.public_comment._id)
        self.registration_url = '/{}comments/{}/replies/'.format(API_BASE, self.registration_comment._id)

    def test_return_private_node_comment_replies_logged_out_user(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_return_private_node_comment_replies_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_node_comment_replies_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_out_user(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_in_non_contributor(self):
        res = self.app.get(self.public_url, auth=self.non_contributor)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_in_contributor(self):
        res = self.app.get(self.public_url, auth=self.user)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_registration_comment_replies_logged_in_contributor(self):
        res = self.app.get(self.registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.registration_comment_reply._id, comment_ids)


class TestCommentRepliesCreate(ApiTestCase):
    pass


class TestCommentDetailView(ApiTestCase):
    pass


class TestReportsView(ApiTestCase):
    pass


class TestReportDetailView(ApiTestCase):
    pass
