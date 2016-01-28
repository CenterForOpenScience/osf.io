from __future__ import absolute_import
import datetime as dt
from nose.tools import *  # noqa PEP8 asserts
from modularodm.exceptions import ValidationValueError, ValidationTypeError, ValidationError

from framework.auth import Auth
from framework.exceptions import PermissionsError
from website.addons.osfstorage import settings as osfstorage_settings
from website.project.model import Comment, NodeLog
from website.project.signals import comment_added
from website import settings

from tests.base import (
    OsfTestCase,
    assert_datetime_equal,
    capture_signals
)
from tests.factories import (
    UserFactory, ProjectFactory, AuthUserFactory, CommentFactory,
)


class TestCommentViews(OsfTestCase):

    def setUp(self):
        super(TestCommentViews, self).setUp()
        self.project = ProjectFactory(is_public=True)
        self.user = AuthUserFactory()
        self.project.add_contributor(self.user)
        self.project.save()
        self.user.save()

    def test_view_project_comments_updates_user_comments_view_timestamp(self):
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[self.project._id]['node']
        view_timestamp = dt.datetime.utcnow()
        assert_datetime_equal(user_timestamp, view_timestamp)

    def test_confirm_non_contrib_viewers_dont_have_pid_in_comments_view_timestamp(self):
        non_contributor = AuthUserFactory()
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)

        non_contributor.reload()
        assert_not_in(self.project._id, non_contributor.comments_viewed_timestamp)

    def test_view_comments_updates_user_comments_view_timestamp_files(self):
        osfstorage = self.project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        test_file = root_node.append_file('test_file')
        test_file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()

        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'files',
            'rootId': test_file._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[self.project._id]['files'][test_file._id]
        view_timestamp = dt.datetime.utcnow()
        assert_datetime_equal(user_timestamp, view_timestamp)


class TestCommentModel(OsfTestCase):

    def setUp(self):
        super(TestCommentModel, self).setUp()
        self.comment = CommentFactory()
        self.auth = Auth(user=self.comment.user)

    def test_create(self):
        comment = Comment.create(
            auth=self.auth,
            user=self.comment.user,
            node=self.comment.node,
            target=self.comment.target,
            page='node',
            is_public=True,
            content='This is a comment.'
        )
        assert_equal(comment.user, self.comment.user)
        assert_equal(comment.node, self.comment.node)
        assert_equal(comment.target, self.comment.target)
        assert_equal(len(comment.node.logs), 2)
        assert_equal(comment.node.logs[-1].action, NodeLog.COMMENT_ADDED)

    def test_create_comment_content_cannot_exceed_max_length(self):
        with assert_raises(ValidationValueError):
            comment = Comment.create(
                auth=self.auth,
                user=self.comment.user,
                node=self.comment.node,
                target=self.comment.target,
                is_public=True,
                content=''.join(['c' for c in range(settings.COMMENT_MAXLENGTH + 1)])
            )

    def test_create_comment_content_cannot_be_none(self):
        with assert_raises(ValidationError) as error:
            comment = Comment.create(
                auth=self.auth,
                user=self.comment.user,
                node=self.comment.node,
                target=self.comment.target,
                is_public=True,
                content=None
        )
        assert_equal(error.exception.message, 'Value <content> is required.')

    def test_create_comment_content_cannot_be_empty(self):
        with assert_raises(ValidationValueError) as error:
            comment = Comment.create(
                auth=self.auth,
                user=self.comment.user,
                node=self.comment.node,
                target=self.comment.target,
                is_public=True,
                content=''
        )
        assert_equal(error.exception.message, 'Value must not be empty.')

    def test_create_comment_content_cannot_be_whitespace(self):
        with assert_raises(ValidationValueError) as error:
            comment = Comment.create(
                auth=self.auth,
                user=self.comment.user,
                node=self.comment.node,
                target=self.comment.target,
                is_public=True,
                content='    '
        )
        assert_equal(error.exception.message, 'Value must not be empty.')

    def test_create_sends_comment_added_signal(self):
        with capture_signals() as mock_signals:
            comment = Comment.create(
                auth=self.auth,
                user=self.comment.user,
                node=self.comment.node,
                target=self.comment.target,
                is_public=True,
                content='This is a comment.'
            )
        assert_equal(mock_signals.signals_sent(), set([comment_added]))

    def test_edit(self):
        self.comment.edit(
            auth=self.auth,
            content='edited',
            save=True
        )
        assert_equal(self.comment.content, 'edited')
        assert_true(self.comment.modified)
        assert_equal(len(self.comment.node.logs), 2)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_UPDATED)

    def test_delete(self):
        self.comment.delete(auth=self.auth, save=True)
        assert_equal(self.comment.is_deleted, True)
        assert_equal(len(self.comment.node.logs), 2)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_REMOVED)

    def test_undelete(self):
        self.comment.delete(auth=self.auth, save=True)
        self.comment.undelete(auth=self.auth, save=True)
        assert_equal(self.comment.is_deleted, False)
        assert_equal(len(self.comment.node.logs), 3)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_RESTORED)

    def test_report_abuse(self):
        user = UserFactory()
        self.comment.report_abuse(user, category='spam', text='ads', save=True)
        assert_in(user._id, self.comment.reports)
        assert_equal(
            self.comment.reports[user._id],
            {'category': 'spam', 'text': 'ads'}
        )

    def test_report_abuse_own_comment(self):
        with assert_raises(ValueError):
            self.comment.report_abuse(
                self.comment.user, category='spam', text='ads', save=True
            )

    def test_unreport_abuse(self):
        user = UserFactory()
        self.comment.report_abuse(user, category='spam', text='ads', save=True)
        self.comment.unreport_abuse(user, save=True)
        assert_not_in(user._id, self.comment.reports)

    def test_unreport_abuse_not_reporter(self):
        reporter = UserFactory()
        non_reporter = UserFactory()
        self.comment.report_abuse(reporter, category='spam', text='ads', save=True)
        with assert_raises(ValueError):
            self.comment.unreport_abuse(non_reporter, save=True)
        assert_in(reporter._id, self.comment.reports)

    def test_validate_reports_bad_key(self):
        self.comment.reports[None] = {'category': 'spam', 'text': 'ads'}
        with assert_raises(ValidationValueError):
            self.comment.save()

    def test_validate_reports_bad_type(self):
        self.comment.reports[self.comment.user._id] = 'not a dict'
        with assert_raises(ValidationTypeError):
            self.comment.save()

    def test_validate_reports_bad_value(self):
        self.comment.reports[self.comment.user._id] = {'foo': 'bar'}
        with assert_raises(ValidationValueError):
            self.comment.save()

    def test_read_permission_contributor_can_comment(self):
        project = ProjectFactory()
        user = UserFactory()
        project.set_privacy('private')
        project.add_contributor(user, 'read')
        project.save()

        assert_true(project.can_comment(Auth(user=user)))

    def test_get_content_for_not_deleted_comment(self):
        project = ProjectFactory(is_public=True)
        comment = CommentFactory(node=project)
        content = comment.get_content(auth=Auth(comment.user))
        assert_equal(content, comment.content)

    def test_get_content_returns_deleted_content_to_commenter(self):
        comment = CommentFactory(is_deleted=True)
        content = comment.get_content(auth=Auth(comment.user))
        assert_equal(content, comment.content)

    def test_get_content_does_not_return_deleted_content_to_non_commenter(self):
        user = AuthUserFactory()
        comment = CommentFactory(is_deleted=True)
        content = comment.get_content(auth=Auth(user))
        assert_is_none(content)

    def test_get_content_public_project_does_not_return_deleted_content_to_logged_out_user(self):
        project = ProjectFactory(is_public=True)
        comment = CommentFactory(node=project, is_deleted=True)
        content = comment.get_content(auth=None)
        assert_is_none(content)

    def test_get_content_private_project_throws_permissions_error_for_logged_out_users(self):
        project = ProjectFactory(is_public=False)
        comment = CommentFactory(node=project, is_deleted=True)
        with assert_raises(PermissionsError):
            comment.get_content(auth=None)

    def test_find_unread_is_zero_when_no_comments(self):
        n_unread = Comment.find_n_unread(user=UserFactory(), node=ProjectFactory())
        assert_equal(n_unread, 0)

    def test_find_unread_new_comments(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator)
        n_unread = Comment.find_n_unread(user=user, node=project)
        assert_equal(n_unread, 1)

    def test_find_unread_includes_comment_replies(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=user)
        reply = CommentFactory(node=project, target=comment, user=project.creator)
        n_unread = Comment.find_n_unread(user=user, node=project)
        assert_equal(n_unread, 1)

    # Regression test for https://openscience.atlassian.net/browse/OSF-5193
    def test_find_unread_includes_edited_comments(self):
        project = ProjectFactory()
        user = AuthUserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator)

        url = project.api_url_for('update_comments_timestamp')
        payload = {'page': 'node', 'rootId': project._id}
        res = self.app.put_json(url, payload, auth=user.auth)
        user.reload()
        n_unread = Comment.find_n_unread(user=user, node=project)
        assert_equal(n_unread, 0)

        # Edit previously read comment
        comment.edit(
            auth=Auth(project.creator),
            content='edited',
            save=True
        )
        n_unread = Comment.find_n_unread(user=user, node=project)
        assert_equal(n_unread, 1)

    def test_find_unread_does_not_include_deleted_comments(self):
        project = ProjectFactory()
        user = AuthUserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator, is_deleted=True)
        n_unread = Comment.find_n_unread(user=user, node=project)
        assert_equal(n_unread, 0)
