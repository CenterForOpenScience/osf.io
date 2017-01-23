from __future__ import absolute_import

from collections import OrderedDict
import unittest

from framework.auth import Auth
from framework.exceptions import PermissionsError
from framework.guid.model import Guid
from modularodm import Q
from modularodm.exceptions import ValidationError, ValidationValueError
from nose.tools import *  # noqa PEP8 asserts
from nose_parameterized import parameterized
from tests.base import OsfTestCase, capture_signals
from osf_tests.factories import (AuthUserFactory, CommentFactory, NodeFactory,
                             ProjectFactory, UserFactory)
from website import settings
from addons.osfstorage import settings as osfstorage_settings
from website.files.models import FileNode
from website.files.models.box import BoxFile
from website.files.models.dropbox import DropboxFile
from website.files.models.github import GithubFile
from website.files.models.googledrive import GoogleDriveFile
from website.files.models.osfstorage import OsfStorageFile
from website.files.models.s3 import S3File
from website.project.model import Comment, NodeLog
from website.project.signals import (comment_added, contributor_added,
                                     mention_added)
from website.project.views.comment import update_file_guid_referent
from website.util import permissions


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
