from __future__ import absolute_import
import datetime as dt
import unittest
from collections import OrderedDict
from nose.tools import *  # noqa PEP8 asserts
from nose_parameterized import parameterized
from modularodm.exceptions import ValidationValueError, ValidationError
from modularodm import Q

from framework.auth import Auth
from framework.exceptions import PermissionsError
from framework.guid.model import Guid
from website.addons.osfstorage import settings as osfstorage_settings
from website.files.models import FileNode
from website.files.models.box import BoxFile
from website.files.models.dropbox import DropboxFile
from website.files.models.github import GithubFile
from website.files.models.googledrive import GoogleDriveFile
from website.files.models.osfstorage import OsfStorageFile
from website.files.models.s3 import S3File
from website.project.model import Comment, NodeLog
from website.project.signals import comment_added, mention_added
from website.project.views.comment import update_file_guid_referent
from website.util import permissions
from website import settings


from tests.base import (
    OsfTestCase,
    assert_datetime_equal,
    capture_signals
)
from tests.factories import (
    UserFactory, ProjectFactory, AuthUserFactory, CommentFactory, NodeFactory
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

        user_timestamp = self.user.comments_viewed_timestamp[self.project._id]
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

        user_timestamp = self.user.comments_viewed_timestamp[test_file._id]
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
            content='This is a comment.',
            new_mentions=self.comment.new_mentions
        )

        assert_equal(comment.user, self.comment.user)
        assert_equal(comment.node, self.comment.node)
        assert_equal(comment.target, self.comment.target)
        assert_equal(len(comment.node.logs), 2)
        assert_equal(comment.node.logs[-1].action, NodeLog.COMMENT_ADDED)
        assert_equal([], self.comment.old_mentions)
        assert_equal(comment.new_mentions, self.comment.old_mentions)

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

    def test_create_sends_mention_added_signal_if_mentions(self):
        with capture_signals() as mock_signals:
            comment = Comment.create(
                auth=self.auth,
                user=self.comment.user,
                node=self.comment.node,
                target=self.comment.target,
                is_public=True,
                content='This is a comment.',
                new_mentions=[self.comment.user._id]
            )
        assert_equal(mock_signals.signals_sent(), set([comment_added, mention_added]))

    def test_create_does_not_send_mention_added_signal_if_noncontributor_mentions(self):
        with assert_raises(ValidationValueError) as error:
            with capture_signals() as mock_signals:
                comment = Comment.create(
                    auth=self.auth,
                    user=self.comment.user,
                    node=self.comment.node,
                    target=self.comment.target,
                    is_public=True,
                    content='This is a comment.',
                    new_mentions=['noncontributor']
                )
        assert_equal(mock_signals.signals_sent(), set([]))
        assert_equal(error.exception.message, 'User does not exist.')

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

    def test_edit_sends_mention_added_signal_if_mentions(self):
        with capture_signals() as mock_signals:
            self.comment.new_mentions=[self.comment.user._id]
            self.comment.edit(
                auth=self.auth,
                content='edited',
                save=True
            )
        assert_equal(mock_signals.signals_sent(), set([mention_added]))

    def test_edit_does_not_send_mention_added_signal_if_noncontributor_mentions(self):
        with assert_raises(ValidationValueError) as error:
            with capture_signals() as mock_signals:
                self.comment.new_mentions=['noncontributor']
                self.comment.edit(
                    auth=self.auth,
                    content='edited',
                    save=True
                )
        assert_equal(mock_signals.signals_sent(), set([]))
        assert_equal(error.exception.message, 'User does not exist.')

    def test_edit_does_not_send_mention_added_signal_if_already_mentioned(self):
        with capture_signals() as mock_signals:
            self.comment.old_mentions=[self.comment.user._id]
            self.comment.new_mentions=[self.comment.user._id]
            self.comment.edit(
                auth=self.auth,
                content='edited',
                save=True
            )
        assert_equal(mock_signals.signals_sent(), set([]))
        assert_equal(self.comment.new_mentions, [])

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

    def test_read_permission_contributor_can_comment(self):
        project = ProjectFactory()
        user = UserFactory()
        project.set_privacy('private')
        project.add_contributor(user, permissions=[permissions.READ])
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
        n_unread = Comment.find_n_unread(user=UserFactory(), node=ProjectFactory(), page='node')
        assert_equal(n_unread, 0)

    def test_find_unread_new_comments(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator)
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert_equal(n_unread, 1)

    def test_find_unread_includes_comment_replies(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=user)
        reply = CommentFactory(node=project, target=Guid.load(comment._id), user=project.creator)
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
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
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert_equal(n_unread, 0)

        # Edit previously read comment
        comment.edit(
            auth=Auth(project.creator),
            content='edited',
            save=True
        )
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert_equal(n_unread, 1)

    def test_find_unread_does_not_include_deleted_comments(self):
        project = ProjectFactory()
        user = AuthUserFactory()
        project.add_contributor(user)
        project.save()
        comment = CommentFactory(node=project, user=project.creator, is_deleted=True)
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert_equal(n_unread, 0)


class FileCommentMoveRenameTestMixin(object):
    # TODO: Remove skip decorators when waterbutler returns a consistently formatted payload
    # for intra-provider folder moves and renames.

    id_based_providers = ['osfstorage']

    @property
    def provider(self):
        raise NotImplementedError

    @property
    def ProviderFile(self):
        raise NotImplementedError

    @classmethod
    def _format_path(cls, path, file_id=None):
        return path

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

    def _create_source_payload(self, path, node, provider, file_id=None):
        return OrderedDict([('materialized', path),
                            ('name', path.split('/')[-1]),
                            ('nid', node._id),
                            ('path', self._format_path(path, file_id)),
                            ('provider', provider),
                            ('url', '/project/{}/files/{}/{}/'.format(node._id, provider, path.strip('/'))),
                            ('node', {'url': '/{}/'.format(node._id), '_id': node._id, 'title': node.title}),
                            ('addon', provider)])

    def _create_destination_payload(self, path, node, provider, file_id, children=None):
        destination_path = PROVIDER_CLASS.get(provider)._format_path(path=path, file_id=file_id)
        destination = OrderedDict([('contentType', ''),
                            ('etag', 'abcdefghijklmnop'),
                            ('extra', OrderedDict([('revisionId', '12345678910')])),
                            ('kind', 'file'),
                            ('materialized', path),
                            ('modified', 'Tue, 02 Feb 2016 17:55:48 +0000'),
                            ('name', path.split('/')[-1]),
                            ('nid', node._id),
                            ('path', destination_path),
                            ('provider', provider),
                            ('size', 1000),
                            ('url', '/project/{}/files/{}/{}/'.format(node._id, provider, path.strip('/'))),
                            ('node', {'url': '/{}/'.format(node._id), '_id': node._id, 'title': node.title}),
                            ('addon', provider)])
        if children:
            destination_children = [self._create_destination_payload(child['path'], child['node'], child['provider'], file_id) for child in children]
            destination.update({'children': destination_children})
        return destination

    def _create_payload(self, action, user, source, destination, file_id, destination_file_id=None):
        return OrderedDict([
            ('action', action),
            ('auth', OrderedDict([('email', user.username), ('id', user._id), ('name', user.fullname)])),
            ('destination', self._create_destination_payload(path=destination['path'],
                                                             node=destination['node'],
                                                             provider=destination['provider'],
                                                             file_id=destination_file_id or file_id,
                                                             children=destination.get('children', []))),
            ('source', self._create_source_payload(source['path'], source['node'], source['provider'], file_id=file_id)),
            ('time', 100000000),
            ('node', source['node']),
            ('project', None)
        ])

    def _create_file_with_comment(self, node, path):
        self.file = self.ProviderFile.create(
            is_file=True,
            node=node,
            path=path,
            name=path.strip('/'),
            materialized_path=path)
        self.guid = self.file.get_guid(create=True)
        self.file.save()
        self.comment = CommentFactory(user=self.user, node=node, target=self.guid)

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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @unittest.skip
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @unittest.skip
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_path))
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_path), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        assert_equal(self.guid.referent.node._id, destination['node']._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        assert_equal(self.guid.referent.node._id, destination['node']._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @unittest.skip
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @unittest.skip
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @unittest.skip
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @unittest.skip
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        payload = self._create_payload('move', self.user, source, destination, self.file._id, destination_file_id=destination['path'].strip('/'))
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class('osfstorage', FileNode.FILE).get_or_create(destination['node'], destination['path'])
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    def test_comments_move_when_folder_moved_to_osfstorage(self):
        osfstorage = self.project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        osf_folder = root_node.append_folder('subfolder')
        osf_file = osf_folder.append_file('file.txt')
        osf_file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png',
            'etag': '1234567890abcde'
        }).save()

        source = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': 'osfstorage',
            'children': [{
                'path': '/subfolder/file.txt',
                'node': self.project,
                'provider': 'osfstorage'
            }]
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        payload = self._create_payload('move', self.user, source, destination, self.file._id, destination_file_id=osf_file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class('osfstorage', FileNode.FILE).get_or_create(destination['node'], osf_file._id)
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @parameterized.expand([('box', '/1234567890'), ('dropbox', '/file.txt'), ('github', '/file.txt'), ('googledrive', '/file.txt'), ('s3', '/file.txt'),])
    def test_comments_move_when_file_moved_to_different_provider(self, destination_provider, destination_path):
        if self.provider == destination_provider:
            return True

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
            'path': destination_path,
            'node': self.project,
            'provider': destination_provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'])
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(destination_provider, FileNode.FILE).get_or_create(destination['node'], destination['path'])
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @parameterized.expand([('box', '/1234567890'), ('dropbox', '/subfolder/file.txt'), ('github', '/subfolder/file.txt'), ('googledrive', '/subfolder/file.txt'), ('s3', '/subfolder/file.txt'),])
    def test_comments_move_when_folder_moved_to_different_provider(self, destination_provider, destination_path):
        if self.provider == destination_provider:
            return True

        self.project.add_addon(destination_provider, auth=Auth(self.user))
        self.project.save()
        self.addon_settings = self.project.get_addon(destination_provider)
        self.addon_settings.folder = '/AddonFolder'
        self.addon_settings.save()

        source = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': self.project,
            'provider': destination_provider,
            'children': [{
                    'path': '/subfolder/file.txt',
                    'node': self.project,
                    'provider': destination_provider
            }]
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(destination_provider, FileNode.FILE).get_or_create(destination['node'], destination_path)
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)


class TestOsfstorageFileCommentMoveRename(FileCommentMoveRenameTestMixin, OsfTestCase):

    provider = 'osfstorage'
    ProviderFile = OsfStorageFile

    @classmethod
    def _format_path(cls, path, file_id=None):
        super(TestOsfstorageFileCommentMoveRename, cls)._format_path(path)
        return '/{}{}'.format(file_id, ('/' if path.endswith('/') else ''))

    def _create_file_with_comment(self, node, path):
        osfstorage = node.get_addon(self.provider)
        root_node = osfstorage.get_root()
        self.file = root_node.append_file('file.txt')
        self.file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png',
            'etag': 'abcdefghijklmnop'
        }).save()
        self.file.materialized_path = path
        self.guid = self.file.get_guid(create=True)
        self.comment = CommentFactory(user=self.user, node=node, target=self.guid)

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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        assert_equal(self.guid.referent.node._id, destination['node']._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path=source['path'])
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        assert_equal(self.guid.referent.node._id, destination['node']._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
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
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name))
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', self.user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert_equal(self.guid._id, file_node.get_guid()._id)
        file_comments = Comment.find(Q('root_target', 'eq', self.guid._id))
        assert_equal(file_comments.count(), 1)

    @unittest.skip
    def test_comments_move_when_file_moved_to_osfstorage(self):
        super(TestOsfstorageFileCommentMoveRename, self).test_comments_move_when_file_moved_to_osfstorage()

    @unittest.skip
    def test_comments_move_when_folder_moved_to_osfstorage(self):
        super(TestOsfstorageFileCommentMoveRename, self).test_comments_move_when_folder_moved_to_osfstorage()


class TestBoxFileCommentMoveRename(FileCommentMoveRenameTestMixin, OsfTestCase):

    provider = 'box'
    ProviderFile = BoxFile

    def _create_file_with_comment(self, node, path):
        self.file = self.ProviderFile.create(
            is_file=True,
            node=node,
            path=self._format_path(path),
            name=path.strip('/'),
            materialized_path=path)
        self.guid = self.file.get_guid(create=True)
        self.file.save()
        self.comment = CommentFactory(user=self.user, node=node, target=self.guid)

    @classmethod
    def _format_path(cls, path, file_id=None):
        super(TestBoxFileCommentMoveRename, cls)._format_path(path)
        return '/9876543210/' if path.endswith('/') else '/1234567890'


class TestDropboxFileCommentMoveRename(FileCommentMoveRenameTestMixin, OsfTestCase):

    provider = 'dropbox'
    ProviderFile = DropboxFile

    def _create_file_with_comment(self, node, path):
        self.file = self.ProviderFile.create(
            is_file=True,
            node=node,
            path='{}{}'.format(node.get_addon(self.provider).folder, path),
            name=path.strip('/'),
            materialized_path=path)
        self.guid = self.file.get_guid(create=True)
        self.file.save()
        self.comment = CommentFactory(user=self.user, node=node, target=self.guid)


class TestGoogleDriveFileCommentMoveRename(FileCommentMoveRenameTestMixin, OsfTestCase):

    provider = 'googledrive'
    ProviderFile = GoogleDriveFile


class TestGithubFileCommentMoveRename(FileCommentMoveRenameTestMixin, OsfTestCase):

    provider = 'github'
    ProviderFile = GithubFile


class TestS3FileCommentMoveRename(FileCommentMoveRenameTestMixin, OsfTestCase):

    provider = 's3'
    ProviderFile = S3File


PROVIDER_CLASS = {
    'osfstorage': TestOsfstorageFileCommentMoveRename,
    'box': TestBoxFileCommentMoveRename,
    'dropbox': TestDropboxFileCommentMoveRename,
    'github': TestGithubFileCommentMoveRename,
    'googledrive': TestGoogleDriveFileCommentMoveRename,
    's3': TestS3FileCommentMoveRename

}