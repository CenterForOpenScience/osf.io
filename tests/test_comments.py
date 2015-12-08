from __future__ import absolute_import
import datetime as dt
import mock
from nose.tools import *  # noqa PEP8 asserts
from modularodm.exceptions import ValidationValueError, ValidationTypeError

from framework.auth import Auth
from framework.exceptions import PermissionsError
from website.addons.osfstorage import settings as osfstorage_settings
from website.project.model import Comment, NodeLog
from website.project.signals import comment_added
from website.project.views.node import _view_project


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
        self.consolidated_auth = Auth(user=self.project.creator)
        self.non_contributor = AuthUserFactory()
        self.user = AuthUserFactory()
        self.project.add_contributor(self.user)
        self.project.save()
        self.user.save()

    def _configure_project(self, project, comment_level):

        project.comment_level = comment_level
        project.save()

    def _add_comment(self, project, content=None, **kwargs):

        content = content if content is not None else 'hammer to fall'
        url = project.api_url + 'comment/'
        return self.app.post_json(
            url,
            {
                'content': content,
                'isPublic': 'public',
                'page': 'node',
                'target': project._id
            },
            **kwargs
        )

    @mock.patch('website.project.views.comment.get_root_target_title')
    def _add_comment_files(self, project, mock_get_title, content=None, path=None, provider='osfstorage', **kwargs):
        project.add_addon(provider, auth=Auth(self.user))
        path = path if path is not None else 'mudhouse_coffee.txt'
        addon = project.get_addon(provider)
        if provider == 'dropbox':
            addon.folder = '/'
        guid, _ = addon.find_or_create_file_guid('/' + path)
        content = content if content is not None else 'large hot mocha'
        url = project.api_url + 'comment/'
        mock_get_title.return_value = 'files'
        return self.app.post_json(
            url,
            {
                'content': content,
                'isPublic': 'public',
                'page': 'files',
                'target': guid._id
            },
            **kwargs
        )

    def test_view_comments_updates_user_comments_view_timestamp(self):
        CommentFactory(node=self.project, page='node')

        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page':'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[self.project._id]['node']
        view_timestamp = dt.datetime.utcnow()
        assert_datetime_equal(user_timestamp, view_timestamp)

    def test_confirm_non_contrib_viewers_dont_have_pid_in_comments_view_timestamp(self):
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page':'node',
            'rootId': self.project._id
        }, auth=self.user.auth)

        self.non_contributor.reload()
        assert_not_in(self.project._id, self.non_contributor.comments_viewed_timestamp)

    def test_view_comments_updates_user_comments_view_timestamp_files(self):
        path = 'skittles.txt'
        self._add_comment_files(self.project, content='Red orange yellow skittles', path=path, provider='osfstorage', auth=self.project.creator.auth)
        addon = self.project.get_addon('osfstorage')
        guid, _ = addon.find_or_create_file_guid('/' + path)

        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'files',
            'rootId': guid._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[self.project._id]['files'][guid._id]
        view_timestamp = dt.datetime.utcnow()
        assert_datetime_equal(user_timestamp, view_timestamp)

    def test_n_unread_comments_overview(self):
        self._add_comment(self.project, auth=self.project.creator.auth)
        self.project.reload()
        res = _view_project(self.project, auth=Auth(user=self.user))
        assert_equal(res['user']['unread_comments']['node'], 1)

    @mock.patch('website.project.views.node.check_file_exists')
    def test_n_unread_comments_files(self, mock_check_file_exists):
        mock_check_file_exists.return_value = True, 1
        self._add_comment_files(self.project, auth=self.project.creator.auth)
        self.project.reload()
        self._add_comment_files(
            self.project,
            content=None,
            path=None,
            provider='github',
            auth=self.project.creator.auth
        )
        self.project.reload()
        self._add_comment_files(
            self.project,
            content='I failed my test',
            path='transcript.pdf',
            provider='dropbox',
            auth=self.project.creator.auth
        )
        self.project.reload()
        res = _view_project(self.project, auth=Auth(user=self.user))
        assert_equal(res['user']['unread_comments']['files'], 3)

    @mock.patch('website.project.views.node.check_file_exists')
    def test_n_unread_comments_total(self, mock_check_file_exists):
        mock_check_file_exists.return_value = True, 1
        self._add_comment_files(self.project, auth=self.project.creator.auth)
        self.project.reload()
        self._add_comment(self.project, auth=self.project.creator.auth)
        self._add_comment_files(
            self.project,
            content=None,
            path=None,
            provider='github',
            auth=self.project.creator.auth
        )
        self.project.reload()

        self._add_comment_files(
            self.project,
            content='I failed my test',
            path='transcript.pdf',
            provider='dropbox',
            auth=self.project.creator.auth
        )
        self.project.reload()

        res = _view_project(self.project, auth=Auth(user=self.user))['user']['unread_comments']
        assert_equal(res['node'], 1)
        assert_equal(res['files'], 3)


class TestCommentModel(OsfTestCase):

    def setUp(self):
        super(TestCommentModel, self).setUp()
        self.comment = CommentFactory()
        self.consolidated_auth = Auth(user=self.comment.user)

    def test_create(self):
        comment = Comment.create(
            auth=self.consolidated_auth,
            user=self.comment.user,
            node=self.comment.node,
            target=self.comment.target,
            page='node',
            is_public=True,
        )
        assert_equal(comment.user, self.comment.user)
        assert_equal(comment.node, self.comment.node)
        assert_equal(comment.target, self.comment.target)
        assert_equal(len(comment.node.logs), 2)
        assert_equal(comment.node.logs[-1].action, NodeLog.COMMENT_ADDED)

    def test_create_sends_comment_added_signal(self):
        with capture_signals() as mock_signals:
            comment = Comment.create(
                auth=self.auth,
                user=self.comment.user,
                node=self.comment.node,
                target=self.comment.target,
                is_public=True,
            )
        assert_equal(mock_signals.signals_sent(), set([comment_added]))

    def test_edit(self):
        self.comment.edit(
            auth=self.consolidated_auth,
            content='edited'
        )
        assert_equal(self.comment.content, 'edited')
        assert_true(self.comment.modified)
        assert_equal(len(self.comment.node.logs), 2)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_UPDATED)

    def test_delete(self):
        self.comment.delete(auth=self.consolidated_auth)
        assert_equal(self.comment.is_deleted, True)
        assert_equal(len(self.comment.node.logs), 2)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_REMOVED)

    def test_undelete(self):
        self.comment.delete(auth=self.consolidated_auth)
        self.comment.undelete(auth=self.consolidated_auth)
        assert_equal(self.comment.is_deleted, False)
        assert_equal(len(self.comment.node.logs), 3)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_ADDED)

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
        n_unread = Comment.find_unread(user=UserFactory(), node=ProjectFactory())
        assert_equal(n_unread, 0)

    def test_find_unread_new_comments(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator)
        n_unread = Comment.find_unread(user=user, node=project)
        assert_equal(n_unread, 1)

    def test_find_unread_includes_comment_replies(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=user)
        reply = CommentFactory(node=project, target=comment, user=project.creator)
        n_unread = Comment.find_unread(user=user, node=project)
        assert_equal(n_unread, 1)

    # Regression test for https://openscience.atlassian.net/browse/OSF-5193
    def test_find_unread_includes_edited_comments(self):
        project = ProjectFactory()
        user = AuthUserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator)

        url = project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, auth=user.auth)
        user.reload()
        n_unread = Comment.find_unread(user=user, node=project)
        assert_equal(n_unread, 0)

        # Edit previously read comment
        comment.edit(
            auth=Auth(project.creator),
            content='edited',
            save=True
        )
        n_unread = Comment.find_unread(user=user, node=project)
        assert_equal(n_unread, 1)

    def test_find_unread_does_not_include_deleted_comments(self):
        project = ProjectFactory()
        user = AuthUserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator, is_deleted=True)
        n_unread = Comment.find_unread(user=user, node=project)
        assert_equal(n_unread, 0)
