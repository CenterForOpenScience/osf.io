from __future__ import absolute_import
import datetime as dt
from collections import OrderedDict
from nose.tools import *  # noqa PEP8 asserts
from nose_parameterized import parameterized, param
from modularodm.exceptions import ValidationValueError, ValidationTypeError, ValidationError
from modularodm import Q

from framework.auth import Auth
from framework.exceptions import PermissionsError
from website.addons.osfstorage import settings as osfstorage_settings
from website.files.models import FileNode
from website.files.models.box import BoxFile
from website.files.models.dropbox import DropboxFile
from website.files.models.github import GithubFile
from website.files.models.googledrive import GoogleDriveFile
from website.files.models.osfstorage import OsfStorageFile
from website.files.models.s3 import S3File
from website.project.model import Comment, NodeLog
from website.project.signals import comment_added
from website.project.views.comment import update_comment_root_target_file
from website import settings

from tests.base import (
    OsfTestCase,
    assert_datetime_equal,
    capture_signals
)
from tests.factories import (
    UserFactory, ProjectFactory, AuthUserFactory, CommentFactory, NodeFactory
)

PROVIDERS = [('box', None), ('dropbox', '/file.txt'), ('github', '/file.txt'), ('googledrive', '/file.txt'), ('s3', '/file.txt'),]


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


class FileCommentMoveRenameTestMixin(OsfTestCase):

    path_is_file_id = False
    id_based_providers = ['osfstorage']
    destination_providers = []

    @property
    def provider(self):
        raise NotImplementedError

    @property
    def ProviderFile(self):
        raise NotImplementedError

    @property
    def _path(self):
        return self.file.stored_object.path

    def _format_path(self, path, folder=None, is_id=path_is_file_id):
        return path

    @property
    def destination_providers(self):
        raise NotImplementedError

    def setUp(self):
        super(FileCommentMoveRenameTestMixin, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon(self.provider, auth=Auth(self.user))
        self.project.save()
        self.project_settings = self.project.get_addon(self.provider)
        self.project_settings.folder = '/Folder1'
        self.project_settings.save()

        self.component = NodeFactory(parent=self.project, creator=self.user)
        self.component.add_addon(self.provider, auth=Auth(self.user))
        self.component.save()
        self.component_settings = self.component.get_addon(self.provider)
        self.component_settings.folder = '/Folder2'
        self.component_settings.save()

    def _create_source_payload(self, path, node, provider):
        return OrderedDict([('materialized', path.strip('/')),
                            ('name', path.split('/')[-1]),
                            ('nid', node._id),
                            ('path', path),
                            ('provider', provider),
                            ('url', '/project/{}/files/{}/{}/'.format(node._id, provider, path.strip('/'))),
                            ('node', {'url': '/{}/'.format(node._id), '_id': node._id, 'title': node.title}),
                            ('addon', provider)])

    def _create_destination_payload(self, path, node, provider):
        return OrderedDict([('contentType', ''),
                            ('etag', 'abcdefghijklmnop'),
                            ('extra', OrderedDict([('revisionId', '12345678910')])),
                            ('kind', 'file'),
                            ('materialized', path.strip('/')),
                            ('modified', 'Tue, 02 Feb 2016 17:55:48 +0000'),
                            ('name', path.split('/')[-1]),
                            ('nid', node._id),
                            ('path', path),
                            ('provider', provider),
                            ('size', 1000),
                            ('url', '/project/{}/files/{}/{}/'.format(node._id, provider, path.strip('/'))),
                            ('node', {'url': '/{}/'.format(node._id), '_id': node._id, 'title': node.title}),
                            ('addon', provider)])

    def _create_payload(self, action, user, source, destination, file_id, destination_file_id=None):
        source_path = file_id if source['provider'] in self.id_based_providers else self._format_path(source['path'])
        destination_path = destination_file_id or (file_id if destination['provider'] in self.id_based_providers else self._format_path(destination['path']))

        return OrderedDict([('action', action),
                            ('auth', OrderedDict([('email', user.username), ('id', user._id), ('name', user.fullname)])),
                            ('destination', self._create_destination_payload(destination_path, destination['node'], destination['provider'])),
                            ('source', self._create_source_payload(source_path, source['node'], source['provider'])),
                            ('time', 100000000),
                            ('node', source['node']),
                            ('project', None)])

    def _create_file_with_comment(self, node, path, folder=None):
        self.file = self.ProviderFile.create(
            is_file=True,
            node=node,
            path=self._format_path(path, folder, is_id=self.path_is_file_id),
            name=path.strip('/'),
            materialized_path=path.strip('/'))
        self.file.save()
        self.comment = CommentFactory(user=self.user, node=node, target=self.file)

    def test_comments_move_on_file_rename(self):
        source = {
            'path': '/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/file_renamed.txt',
            'node': self.project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path(destination.get('path'), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_on_folder_rename(self):
        source = {
            'path': '/subfolder1/',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder2/',
            'node': self.project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path('{}{}'.format(destination['path'], file_name), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_on_subfolder_file_when_parent_folder_is_renamed(self):
        source = {
            'path': '/subfolder1/',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder2/',
            'node': self.project,
            'provider': self.provider
        }
        file_path = 'sub-subfolder/file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_path), folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path('{}{}'.format(destination['path'], file_path), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_file_moved_to_subfolder(self):
        source = {
            'path': '/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path(destination.get('path'), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_file_moved_from_subfolder_to_root(self):
        source = {
            'path': '/subfolder/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path(destination.get('path'), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_file_moved_from_project_to_component(self):
        source = {
            'path': '/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': self.component,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path(destination.get('path'), self.component_settings.folder))
        assert_equal(self.file.node._id, destination.get('node')._id)

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_file_moved_from_component_to_project(self):
        source = {
            'path': '/file.txt',
            'node': self.component,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.component_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path(destination.get('path'), self.project_settings.folder))
        assert_equal(self.file.stored_object.node._id, destination.get('node')._id)

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_folder_moved_to_subfolder(self):
        source = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder2/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path('{}{}'.format(destination['path'], file_name), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_folder_moved_from_subfolder_to_root(self):
        source = {
            'path': '/subfolder2/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path('{}{}'.format(destination['path'], file_name), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_folder_moved_from_project_to_component(self):
        source = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': self.component,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path('{}{}'.format(destination['path'], file_name), self.component_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_folder_moved_from_component_to_project(self):
        source = {
            'path': '/subfolder/',
            'node': self.component,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), folder=self.component_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        assert_equal(self._path, self._format_path('{}{}'.format(destination['path'], file_name), self.project_settings.folder))
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self.file.path)
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    @parameterized.expand([('box', None), ('dropbox', '/file.txt'), ('github', '/file.txt'), ('googledrive', '/file.txt'), ('s3', '/file.txt'),])
    def test_comments_move_when_file_moved_to_different_provider(self, destination_provider, expected_path):
        self.project.add_addon(destination_provider, auth=Auth(self.user))
        self.project.save()
        self.addon_settings = self.project.get_addon(destination_provider)
        self.addon_settings.folder = '/AddonFolder'
        self.addon_settings.save()

        source = {
            'path': '/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': self.project,
            'provider': destination_provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        file_node = FileNode.resolve_class(destination_provider, FileNode.FILE).get_or_create(destination['node'], (expected_path or self.file.path))
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_file_moved_to_osfstorage(self):
        osfstorage = self.project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        osf_file = root_node.append_file('file.txt')
        osf_file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png',
            'etag': 'abcdefghijklmnop'
        }).save()

        source = {
            'path': '/file.txt',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': osf_file.path,
            'node': self.project,
            'provider': 'osfstorage'
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id, destination_file_id=destination['path'].strip('/'))
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        file_node = FileNode.resolve_class('osfstorage', FileNode.FILE).get_or_create(destination['node'], destination['path'].strip('/'))
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(file_comments.count(), 1)


class TestOsfstorageFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    path_is_file_id = True
    provider = 'osfstorage'
    ProviderFile = OsfStorageFile
    destination_providers = ['box', 'dropbox', 'github', 'googledrive', 's3']

    @property
    def _path(self):
        return self.file.path

    def _format_path(self, path, folder=None, is_id=path_is_file_id):
        super(TestOsfstorageFileCommentMoveRename, self)._format_path(path, is_id=self.path_is_file_id)
        return '/{}'.format(self.file._id)

    def _create_file_with_comment(self, node, path, folder=None):
        osfstorage = self.project.get_addon(self.provider)
        root_node = osfstorage.get_root()
        self.file = root_node.append_file('test_file')
        self.file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png',
            'etag': 'abcdefghijklmnop'
        }).save()
        self.comment = CommentFactory(user=self.user, node=node, target=self.file)

    def test_comments_move_when_file_moved_to_osfstorage(self):
        pass


class TestBoxFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'box'
    ProviderFile = BoxFile
    destination_providers = ['osfstorage', 'dropbox', 'github', 'googledrive', 's3']

    def _format_path(self, path, folder=None, is_id=False):
        super(TestBoxFileCommentMoveRename, self)._format_path(path)
        return '/1234567890'

    @parameterized.expand([('box', None), ('dropbox', '/file.txt'), ('github', '/file.txt'), ('googledrive', '/file.txt'), ('s3', '/file.txt'),])
    def test_comments_move_when_file_moved_to_different_provider(self, destination_provider, expected_path):
        self.project.add_addon(destination_provider, auth=Auth(self.user))
        self.project.save()
        self.addon_settings = self.project.get_addon(destination_provider)
        self.addon_settings.folder = '/AddonFolder'
        self.addon_settings.save()

        source = {
            'path': '/1234567890',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': self.project,
            'provider': destination_provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], folder=self.project_settings.folder)
        payload = self._create_payload('move', self.user, source, destination, self.file._id, destination_file_id=destination['path'])
        update_comment_root_target_file(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.file.reload()

        file_node = FileNode.resolve_class(destination_provider, FileNode.FILE).get_or_create(destination['node'], destination['path'].strip('/'))
        file_comments = Comment.find(Q('root_target', 'eq', file_node._id))
        assert_equal(self.file._id, file_node._id)
        assert_equal(file_comments.count(), 1)

class TestDropboxFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'dropbox'
    ProviderFile = DropboxFile
    destination_providers = ['osfstorage', 'box', 'github', 'googledrive', 's3']

    def _format_path(self, path, folder=None, is_id=False):
        super(TestDropboxFileCommentMoveRename, self)._format_path(path, folder)
        if not folder:
            return path
        return '{}{}'.format(folder, path)


class TestGoogleDriveFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'googledrive'
    ProviderFile = GoogleDriveFile
    destination_providers = ['osfstorage', 'box', 'dropbox', 'github', 's3']


class TestGithubFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'github'
    ProviderFile = GithubFile
    destination_providers = ['osfstorage', 'box', 'dropbox', 'googledrive', 's3']


class TestS3FileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 's3'
    ProviderFile = S3File
    destination_providers = ['osfstorage', 'box', 'dropbox', 'googledrive', 'github']
