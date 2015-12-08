from __future__ import absolute_import
import datetime as dt
import mock
import httplib as http
from nose.tools import *  # noqa PEP8 asserts
from modularodm.exceptions import ValidationValueError, ValidationTypeError
from dateutil.parser import parse as parse_date

from framework.auth import Auth
from website.project.model import Comment, NodeLog
from website.project.views.node import _view_project
from website.project.views.comment import serialize_comment

from tests.base import (
    OsfTestCase,
    assert_datetime_equal,
)
from tests.factories import (
    UserFactory, ProjectFactory, AuthUserFactory, CommentFactory,
    PrivateLinkFactory
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

    def test_add_comment_public_contributor(self):

        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        self.project.reload()

        res_comment = res.json['comment']
        date_created = parse_date(str(res_comment.pop('dateCreated')))
        date_modified = parse_date(str(res_comment.pop('dateModified')))

        serialized_comment = serialize_comment(self.project.commented[0], self.consolidated_auth)
        date_created2 = parse_date(serialized_comment.pop('dateCreated'))
        date_modified2 = parse_date(serialized_comment.pop('dateModified'))

        assert_datetime_equal(date_created, date_created2)
        assert_datetime_equal(date_modified, date_modified2)

        assert_equal(len(self.project.commented), 1)
        assert_equal(res_comment, serialized_comment)

    def test_add_comment_public_non_contributor(self):

        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, auth=self.non_contributor.auth,
        )

        self.project.reload()

        res_comment = res.json['comment']
        date_created = parse_date(res_comment.pop('dateCreated'))
        date_modified = parse_date(res_comment.pop('dateModified'))

        serialized_comment = serialize_comment(self.project.commented[0], Auth(user=self.non_contributor))
        date_created2 = parse_date(serialized_comment.pop('dateCreated'))
        date_modified2 = parse_date(serialized_comment.pop('dateModified'))

        assert_datetime_equal(date_created, date_created2)
        assert_datetime_equal(date_modified, date_modified2)

        assert_equal(len(self.project.commented), 1)
        assert_equal(res_comment, serialized_comment)

    def test_add_comment_private_contributor(self):

        self._configure_project(self.project, 'private')
        res = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        self.project.reload()

        res_comment = res.json['comment']
        date_created = parse_date(str(res_comment.pop('dateCreated')))
        date_modified = parse_date(str(res_comment.pop('dateModified')))

        serialized_comment = serialize_comment(self.project.commented[0], self.consolidated_auth)
        date_created2 = parse_date(serialized_comment.pop('dateCreated'))
        date_modified2 = parse_date(serialized_comment.pop('dateModified'))

        assert_datetime_equal(date_created, date_created2)
        assert_datetime_equal(date_modified, date_modified2)

        assert_equal(len(self.project.commented), 1)
        assert_equal(res_comment, serialized_comment)


    def test_add_comment_private_non_contributor(self):

        self._configure_project(self.project, 'private')
        res = self._add_comment(
            self.project, auth=self.non_contributor.auth, expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

    def test_add_comment_logged_out(self):

        self._configure_project(self.project, 'public')
        res = self._add_comment(self.project)

        assert_equal(res.status_code, 302)
        assert_in('login?', res.headers.get('location'))

    def test_add_comment_off(self):

        self._configure_project(self.project, None)
        res = self._add_comment(
            self.project, auth=self.project.creator.auth, expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_add_comment_empty(self):
        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, content='',
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_false(getattr(self.project, 'commented', []))

    def test_add_comment_toolong(self):
        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, content='toolong' * 500,
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_false(getattr(self.project, 'commented', []))

    def test_add_comment_whitespace(self):
        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, content='  ',
            auth=self.project.creator.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_false(getattr(self.project, 'commented', []))

    def test_edit_comment(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, page='node')

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'edited',
                'isPublic': 'private',
            },
            auth=self.project.creator.auth,
        )

        comment.reload()

        assert_equal(res.json['content'], 'edited')

        assert_equal(comment.content, 'edited')

    def test_edit_comment_short(self):
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, content='short', page='node')
        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': '',
                'isPublic': 'private',
            },
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        comment.reload()
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(comment.content, 'short')

    def test_edit_comment_toolong(self):
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, content='short', page='node')
        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'toolong' * 500,
                'isPublic': 'private',
            },
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        comment.reload()
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(comment.content, 'short')

    def test_edit_comment_non_author(self):
        "Contributors who are not the comment author cannot edit."
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, page='node')
        non_author = AuthUserFactory()
        self.project.add_contributor(non_author, auth=self.consolidated_auth)

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'edited',
                'isPublic': 'private',
            },
            auth=non_author.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

    def test_edit_comment_non_contributor(self):
        "Non-contributors who are not the comment author cannot edit."
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, page='node')

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'edited',
                'isPublic': 'private',
            },
            auth=self.non_contributor.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

    def test_delete_comment_author(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, page='node')

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        self.app.delete_json(
            url,
            auth=self.project.creator.auth,
        )

        comment.reload()

        assert_true(comment.is_deleted)

    def test_delete_comment_non_author(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, page='node')

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.delete_json(
            url,
            auth=self.non_contributor.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

        comment.reload()

        assert_false(comment.is_deleted)

    def test_report_abuse(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, page='node')
        reporter = AuthUserFactory()

        url = self.project.api_url + 'comment/{0}/report/'.format(comment._id)

        self.app.post_json(
            url,
            {
                'category': 'spam',
                'text': 'ads',
            },
            auth=reporter.auth,
        )

        comment.reload()
        assert_in(reporter._id, comment.reports)
        assert_equal(
            comment.reports[reporter._id],
            {'category': 'spam', 'text': 'ads'}
        )

    def test_can_view_private_comments_if_contributor(self):

        self._configure_project(self.project, 'public')
        CommentFactory(node=self.project, user=self.project.creator, is_public=False, page='node')

        url = self.project.api_url + 'comments/'
        res = self.app.get(url, {
            "page": 'node',
            "target": self.project._primary_key
        }, auth=self.project.creator.auth)

        assert_equal(len(res.json['comments']), 1)

    def test_view_comments_with_anonymous_link(self):
        self.project.set_privacy('private')
        self.project.save()
        self.project.reload()
        user = AuthUserFactory()
        link = PrivateLinkFactory(anonymous=True)
        link.nodes.append(self.project)
        link.save()

        CommentFactory(node=self.project, user=self.project.creator, is_public=False, page='node')

        url = self.project.api_url + 'comments/'
        res = self.app.get(url, {
            "view_only": link.key,
            "page": 'node',
            "target": self.project._primary_key
        }, auth=user.auth)
        comment = res.json['comments'][0]
        author = comment['author']
        assert_in('A user', author['fullname'])
        assert_false(author['gravatar_url'])
        assert_false(author['url'])
        assert_false(author['id'])

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

    def test_n_unread_comments_updates_when_comment_is_added(self):
        self._add_comment(self.project, auth=self.project.creator.auth)
        self.project.reload()

        url = self.project.api_url_for('list_comments')
        res = self.app.get(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        assert_equal(res.json.get('nUnread'), 1)

        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        self.user.reload()

        url = self.project.api_url_for('list_comments')
        res = self.app.get(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        assert_equal(res.json.get('nUnread'), 0)

    def test_n_unread_comments_updates_when_comment_is_added_files(self):
        path = 'gingertea.txt'
        self._add_comment_files(
            self.project,
            content='Ginger tea rocks',
            path=path,
            provider='osfstorage',
            auth=self.project.creator.auth
        )
        self.project.reload()

        addon = self.project.get_addon('osfstorage')
        guid, _ = addon.find_or_create_file_guid('/' + path)

        url = self.project.api_url_for('list_comments')
        res = self.app.get(url, {
            'page': 'files',
            'rootId': guid._id
        }, auth=self.user.auth)
        assert_equal(res.json.get('nUnread'), 1)

        url_timestamp = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url_timestamp, {
            'page': 'files',
            'rootId': guid._id
        }, auth=self.user.auth)
        self.user.reload()

        res = self.app.get(url, {
            'page': 'node',
            'rootId': guid._id
        }, auth=self.user.auth)
        assert_equal(res.json.get('nUnread'), 0)

    def test_n_unread_comments_updates_when_comment_reply(self):
        comment = CommentFactory(node=self.project, user=self.project.creator, page='node')
        reply = CommentFactory(node=self.project, user=self.user, target=comment, page='node')
        self.project.reload()

        url = self.project.api_url_for('list_comments')
        res = self.app.get(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.project.creator.auth)
        assert_equal(res.json.get('nUnread'), 1)


    def test_n_unread_comments_updates_when_comment_is_edited(self):
        self.test_edit_comment()
        self.project.reload()

        url = self.project.api_url_for('list_comments')
        res = self.app.get(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        assert_equal(res.json.get('nUnread'), 1)

    def test_n_unread_comments_is_zero_when_no_comments(self):
        url = self.project.api_url_for('list_comments')
        res = self.app.get(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.project.creator.auth)
        assert_equal(res.json.get('nUnread'), 0)

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