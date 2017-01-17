import pytest
from collections import OrderedDict

from modularodm.exceptions import ValidationError


from addons.box.models import BoxFile
from addons.dropbox.models import DropboxFile
from addons.github.models import GithubFile
from addons.googledrive.models import GoogleDriveFile
from addons.osfstorage.models import OsfStorageFile
from addons.s3.models import S3File
from website import settings
from website.util import permissions
from addons.osfstorage import settings as osfstorage_settings
from website.project.views.comment import update_file_guid_referent
from website.project.signals import comment_added, mention_added, contributor_added
from framework.exceptions import PermissionsError
from tests.base import capture_signals
from osf.models import Comment, NodeLog, Guid, FileNode
from osf.modm_compat import Q
from osf.utils.auth import Auth
from .factories import (
    CommentFactory,
    ProjectFactory,
    NodeFactory,
    UserFactory,
    AuthUserFactory
)

# All tests will require a databse
pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)

@pytest.fixture()
def auth(user):
    return Auth(user)


@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def component(user, project):
    return NodeFactory(parent=project, creator=user)


def test_comments_have_longer_guid():
    comment = CommentFactory()
    assert len(comment._id) == 12

def test_comments_are_queryable_by_root_target():
    root_target = ProjectFactory()
    comment = CommentFactory(node=root_target)
    assert Comment.find(Q('root_target', 'eq', root_target.guids.first()))[0] == comment


# copied from tests/test_comments.py
class TestCommentModel:

    def test_create(self):
        first_comment = CommentFactory()
        auth = Auth(user=first_comment.user)

        comment = Comment.create(
            auth=auth,
            user=first_comment.user,
            node=first_comment.node,
            target=first_comment.target,
            root_target=first_comment.root_target,
            page='node',
            content='This is a comment, and ya cant teach that.'
        )
        assert comment.user == first_comment.user
        assert comment.node == first_comment.node
        assert comment.target == first_comment.target
        assert comment.node.logs.count() == 2
        assert comment.node.logs.latest().action == NodeLog.COMMENT_ADDED
        assert [] == first_comment.ever_mentioned

    def test_create_comment_content_cannot_exceed_max_length_simple(self, node, user, auth):
        with pytest.raises(ValidationError):
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content=''.join(['c' for c in range(settings.COMMENT_MAXLENGTH + 3)])
            )

    def test_create_comment_content_cannot_exceed_max_length_complex(self, node, user, auth):
        with pytest.raises(ValidationError):
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content=''.join(['c' for c in range(settings.COMMENT_MAXLENGTH - 8)]) + '[@George Ant](http://localhost:5000/' + user._id + '/)'
            )

    def test_create_comment_content_does_not_exceed_max_length_complex(self, node, user, auth):
        Comment.create(
            auth=auth,
            user=user,
            node=node,
            target=node.guids.all()[0],
            content=''.join(['c' for c in range(settings.COMMENT_MAXLENGTH - 12)]) + '[@George Ant](http://localhost:5000/' + user._id + '/)'
        )

    def test_create_comment_content_cannot_be_none(self, node, user, auth):

        with pytest.raises(ValidationError) as error:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content=None
            )
        assert error.value.messages[0] == 'This field cannot be null.'

    def test_create_comment_content_cannot_be_empty(self, node, user, auth):
        with pytest.raises(ValidationError) as error:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content=''
            )
        assert error.value.messages[0] == 'This field cannot be blank.'

    def test_create_comment_content_cannot_be_whitespace(self, node, user, auth):
        with pytest.raises(ValidationError) as error:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content='    '
            )
        assert error.value.messages[0] == 'Value must not be empty.'

    def test_create_sends_comment_added_signal(self, node, user, auth):
        with capture_signals() as mock_signals:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content='This is a comment.'
            )
        assert mock_signals.signals_sent() == ({comment_added})

    def test_create_sends_mention_added_signal_if_mentions(self, node, user, auth):
        with capture_signals() as mock_signals:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content='This is a comment with a bad mention [@Unconfirmed User](http://localhost:5000/' + user._id + '/).'
            )
        assert mock_signals.signals_sent() == ({comment_added, mention_added})

    def test_create_does_not_send_mention_added_signal_if_unconfirmed_contributor_mentioned(self, node, user, auth):
        with pytest.raises(ValidationError) as error:
            with capture_signals() as mock_signals:
                user = UserFactory()
                user.is_registered = False
                user.is_claimed = False
                user.save()
                node.add_contributor(user, visible=False, permissions=[permissions.READ], save=True)

                Comment.create(
                    auth=auth,
                    user=user,
                    node=node,
                    target=node.guids.all()[0],
                    content='This is a comment with a bad mention [@Unconfirmed User](http://localhost:5000/' + user._id + '/).'
                )
        assert mock_signals.signals_sent() == ({contributor_added})
        assert error.value.message == 'User does not exist or is not active.'

    def test_create_does_not_send_mention_added_signal_if_noncontributor_mentioned(self, node, user, auth):
        with pytest.raises(ValidationError) as error:
            with capture_signals() as mock_signals:
                user = UserFactory()
                Comment.create(
                    auth=auth,
                    user=user,
                    node=node,
                    target=node.guids.all()[0],
                    content='This is a comment with a bad mention [@Non-contributor User](http://localhost:5000/' + user._id + '/).'
                )
        assert mock_signals.signals_sent() == set([])
        assert error.value.message == 'Mentioned user is not a contributor.'

    def test_create_does_not_send_mention_added_signal_if_nonuser_mentioned(self, node, user, auth):
        with pytest.raises(ValidationError) as error:
            with capture_signals() as mock_signals:
                Comment.create(
                    auth=auth,
                    user=user,
                    node=node,
                    target=node.guids.all()[0],
                    content='This is a comment with a bad mention [@Not a User](http://localhost:5000/qwert/).'
                )
        assert mock_signals.signals_sent() == set([])
        assert error.value.message == 'User does not exist or is not active.'

    def test_edit(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        comment.edit(
            auth=auth,
            content='edited',
            save=True
        )
        assert comment.content == 'edited'
        assert comment.modified
        assert comment.node.logs.count() == 2
        assert comment.node.logs.latest().action == NodeLog.COMMENT_UPDATED

    def test_edit_sends_mention_added_signal_if_mentions(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        with capture_signals() as mock_signals:
            comment.edit(
                auth=auth,
                content='This is a comment with a bad mention [@Mentioned User](http://localhost:5000/' + comment.user._id + '/).',
                save=True
            )
        assert mock_signals.signals_sent() == ({mention_added})

    def test_edit_does_not_send_mention_added_signal_if_nonuser_mentioned(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        with pytest.raises(ValidationError) as error:
            with capture_signals() as mock_signals:
                comment.edit(
                    auth=auth,
                    content='This is a comment with a bad mention [@Not a User](http://localhost:5000/qwert/).',
                    save=True
                )
        assert mock_signals.signals_sent() == set([])
        assert error.value.message == 'User does not exist or is not active.'

    def test_edit_does_not_send_mention_added_signal_if_noncontributor_mentioned(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        with pytest.raises(ValidationError) as error:
            with capture_signals() as mock_signals:
                user = UserFactory()
                comment.edit(
                    auth=auth,
                    content='This is a comment with a bad mention [@Non-contributor User](http://localhost:5000/' + user._id + '/).',
                    save=True
                )
        assert mock_signals.signals_sent() == set([])
        assert error.value.message == 'Mentioned user is not a contributor.'

    def test_edit_does_not_send_mention_added_signal_if_unconfirmed_contributor_mentioned(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        with pytest.raises(ValidationError) as error:
            with capture_signals() as mock_signals:
                user = UserFactory()
                user.is_registered = False
                user.is_claimed = False
                user.save()
                comment.node.add_contributor(user, visible=False, permissions=[permissions.READ])
                comment.node.save()

                comment.edit(
                    auth=auth,
                    content='This is a comment with a bad mention [@Unconfirmed User](http://localhost:5000/' + user._id + '/).',
                    save=True
                )
        assert mock_signals.signals_sent() == ({contributor_added})
        assert error.value.message == 'User does not exist or is not active.'

    def test_edit_does_not_send_mention_added_signal_if_already_mentioned(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        with capture_signals() as mock_signals:
            comment.ever_mentioned = [comment.user._id]
            comment.edit(
                auth=auth,
                content='This is a comment with a bad mention [@Already Mentioned User](http://localhost:5000/' + comment.user._id + '/).',
                save=True
            )
        assert mock_signals.signals_sent() == set([])

    def test_delete(self, node):
        comment = CommentFactory(node=node)
        auth = Auth(comment.user)

        comment.delete(auth=auth, save=True)
        assert comment.is_deleted, True
        assert comment.node.logs.count() == 2
        assert comment.node.logs.latest().action == NodeLog.COMMENT_REMOVED

    def test_undelete(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        comment.delete(auth=auth, save=True)
        comment.undelete(auth=auth, save=True)
        assert not comment.is_deleted
        assert comment.node.logs.count() == 3
        assert comment.node.logs.latest().action == NodeLog.COMMENT_RESTORED

    def test_read_permission_contributor_can_comment(self):
        project = ProjectFactory()
        user = UserFactory()
        project.set_privacy('private')
        project.add_contributor(user, permissions=[permissions.READ])
        project.save()

        assert project.can_comment(Auth(user=user))

    def test_get_content_for_not_deleted_comment(self):
        project = ProjectFactory(is_public=True)
        comment = CommentFactory(node=project)
        content = comment.get_content(auth=Auth(comment.user))
        assert content == comment.content

    def test_get_content_returns_deleted_content_to_commenter(self):
        comment = CommentFactory(is_deleted=True)
        content = comment.get_content(auth=Auth(comment.user))
        assert content == comment.content

    def test_get_content_does_not_return_deleted_content_to_non_commenter(self):
        user = AuthUserFactory()
        comment = CommentFactory(is_deleted=True)
        content = comment.get_content(auth=Auth(user))
        assert content is None

    def test_get_content_public_project_does_not_return_deleted_content_to_logged_out_user(self):
        project = ProjectFactory(is_public=True)
        comment = CommentFactory(node=project, is_deleted=True)
        content = comment.get_content(auth=None)
        assert content is None

    def test_get_content_private_project_throws_permissions_error_for_logged_out_users(self):
        project = ProjectFactory(is_public=False)
        comment = CommentFactory(node=project, is_deleted=True)
        with pytest.raises(PermissionsError):
            comment.get_content(auth=None)

    def test_find_unread_is_zero_when_no_comments(self):
        n_unread = Comment.find_n_unread(user=UserFactory(), node=ProjectFactory(), page='node')
        assert n_unread == 0

    def test_find_unread_new_comments(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user, save=True)
        CommentFactory(node=project, user=project.creator)
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert n_unread == 1

    def test_find_unread_includes_comment_replies(self):
        project = ProjectFactory()
        user = UserFactory()
        project.add_contributor(user, save=True)
        comment = CommentFactory(node=project, user=user)
        CommentFactory(node=project, target=Guid.load(comment._id), user=project.creator)
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert n_unread == 1


    def test_find_unread_does_not_include_deleted_comments(self):
        project = ProjectFactory()
        user = AuthUserFactory()
        project.add_contributor(user)
        project.save()
        CommentFactory(node=project, user=project.creator, is_deleted=True)
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert n_unread == 0


# copied from tests/test_comments.py
class FileCommentMoveRenameTestMixin(object):
    # TODO: Remove skip decorators when files are implemented
    # and when waterbutler payloads are consistently formatted
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

    def _create_file_with_comment(self, node, path, user):
        self.file = self.ProviderFile.create(
            is_file=True,
            node=node,
            path=path,
            name=path.strip('/'),
            materialized_path=path)
        self.guid = self.file.get_guid(create=True)
        self.file.save()
        self.comment = CommentFactory(user=user, node=node, target=self.guid)

    def test_comments_move_on_file_rename(self, project, user):
        source = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/file_renamed.txt',
            'node': project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()
        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_on_folder_rename(self, project, user):
        source = {
            'path': '/subfolder1/',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder2/',
            'node': project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_on_subfolder_file_when_parent_folder_is_renamed(self, project, user):
        source = {
            'path': '/subfolder1/',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder2/',
            'node': project,
            'provider': self.provider
        }
        file_path = 'sub-subfolder/file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_path), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_path), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_file_moved_to_subfolder(self, project, user):
        source = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/file.txt',
            'node': project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_file_moved_from_subfolder_to_root(self, project, user):
        source = {
            'path': '/subfolder/file.txt',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1


    def test_comments_move_when_file_moved_from_project_to_component(self, project, component, user):
        source = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': component,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.node._id == destination['node']._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1


    def test_comments_move_when_file_moved_from_component_to_project(self, project, component, user):
        source = {
            'path': '/file.txt',
            'node': component,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.node._id == destination['node']._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_folder_moved_to_subfolder(self, user, project):
        source = {
            'path': '/subfolder/',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder2/subfolder/',
            'node': project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_folder_moved_from_subfolder_to_root(self, project, user):
        source = {
            'path': '/subfolder2/subfolder/',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_folder_moved_from_project_to_component(self, project, component, user):
        source = {
            'path': '/subfolder/',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': component,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_folder_moved_from_component_to_project(self, project, component, user):
        source = {
            'path': '/subfolder/',
            'node': component,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_file_moved_to_osfstorage(self, project, user):
        osfstorage = project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        osf_file = root_node.append_file('file.txt')
        osf_file.create_version(user, {
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
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': osf_file.path,
            'node': project,
            'provider': 'osfstorage'
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id, destination_file_id=destination['path'].strip('/'))
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class('osfstorage', FileNode.FILE).get_or_create(destination['node'], destination['path'])
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_folder_moved_to_osfstorage(self, project, user):
        osfstorage = project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        osf_folder = root_node.append_folder('subfolder')
        osf_file = osf_folder.append_file('file.txt')
        osf_file.create_version(user, {
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
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': project,
            'provider': 'osfstorage',
            'children': [{
                'path': '/subfolder/file.txt',
                'node': project,
                'provider': 'osfstorage'
            }]
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id, destination_file_id=osf_file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class('osfstorage', FileNode.FILE).get_or_create(destination['node'], osf_file._id)
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    @pytest.mark.parametrize(
        ['destination_provider', 'destination_path'],
        [('box', '/1234567890'), ('dropbox', '/file.txt'), ('github', '/file.txt'), ('googledrive', '/file.txt'), ('s3', '/file.txt')]
    )
    def test_comments_move_when_file_moved_to_different_provider(self, destination_provider, destination_path, project, user):
        if self.provider == destination_provider:
            return True

        project.add_addon(destination_provider, auth=Auth(user))
        project.save()
        self.addon_settings = project.get_addon(destination_provider)
        self.addon_settings.folder = '/AddonFolder'
        self.addon_settings.save()

        source = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': destination_path,
            'node': project,
            'provider': destination_provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(destination_provider, FileNode.FILE).get_or_create(destination['node'], destination['path'])
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    @pytest.mark.parametrize(
        ['destination_provider', 'destination_path'],
        [('box', '/1234567890'), ('dropbox', '/subfolder/file.txt'), ('github', '/subfolder/file.txt'), ('googledrive', '/subfolder/file.txt'), ('s3', '/subfolder/file.txt'),]
    )
    def test_comments_move_when_folder_moved_to_different_provider(self, destination_provider, destination_path, project, user):
        if self.provider == destination_provider:
            return True

        project.add_addon(destination_provider, auth=Auth(user))
        project.save()
        self.addon_settings = project.get_addon(destination_provider)
        self.addon_settings.folder = '/AddonFolder'
        self.addon_settings.save()

        source = {
            'path': '/',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': project,
            'provider': destination_provider,
            'children': [{
                    'path': '/subfolder/file.txt',
                    'node': project,
                    'provider': destination_provider
            }]
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(destination_provider, FileNode.FILE).get_or_create(destination['node'], destination_path)
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1


# copied from tests/test_comments.py
class TestOsfstorageFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'osfstorage'
    ProviderFile = OsfStorageFile

    @classmethod
    def _format_path(cls, path, file_id=None):
        super(TestOsfstorageFileCommentMoveRename, cls)._format_path(path)
        return '/{}{}'.format(file_id, ('/' if path.endswith('/') else ''))

    def _create_file_with_comment(self, node, path, user):
        osfstorage = node.get_addon(self.provider)
        root_node = osfstorage.get_root()
        self.file = root_node.append_file('file.txt')
        self.file.create_version(user, {
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
        self.comment = CommentFactory(user=user, node=node, target=self.guid)

    def test_comments_move_when_file_moved_from_project_to_component(self, project, component, user):
        source = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': component,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.node._id == destination['node']._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_file_moved_from_component_to_project(self, project, component, user):
        source = {
            'path': '/file.txt',
            'node': component,
            'provider': self.provider
        }
        destination = {
            'path': '/file.txt',
            'node': project,
            'provider': self.provider
        }
        self._create_file_with_comment(node=source['node'], path=source['path'], user=user)
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.node._id == destination['node']._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_folder_moved_from_project_to_component(self, project, component, user):
        source = {
            'path': '/subfolder/',
            'node': project,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': component,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_folder_moved_from_component_to_project(self, project, component, user):
        source = {
            'path': '/subfolder/',
            'node': component,
            'provider': self.provider
        }
        destination = {
            'path': '/subfolder/',
            'node': project,
            'provider': self.provider
        }
        file_name = 'file.txt'
        self._create_file_with_comment(node=source['node'], path='{}{}'.format(source['path'], file_name), user=user)
        self.file.move_under(destination['node'].get_addon(self.provider).get_root())
        payload = self._create_payload('move', user, source, destination, self.file._id)
        update_file_guid_referent(self=None, node=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = FileNode.resolve_class(self.provider, FileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.find(Q('root_target', 'eq', self.guid.pk))
        assert file_comments.count() == 1

    def test_comments_move_when_file_moved_to_osfstorage(self):
        # Already in OSFStorage
        pass

    def test_comments_move_when_folder_moved_to_osfstorage(self):
        # Already in OSFStorage
        pass

# copied from tests/test_comments.py
class TestBoxFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'box'
    ProviderFile = BoxFile

    def _create_file_with_comment(self, node, path, user):
        self.file = self.ProviderFile.create(
            is_file=True,
            node=node,
            path=self._format_path(path),
            name=path.strip('/'),
            materialized_path=path)
        self.file.save()
        self.guid = self.file.get_guid(create=True)
        self.comment = CommentFactory(user=user, node=node, target=self.guid)

    @classmethod
    def _format_path(cls, path, file_id=None):
        super(TestBoxFileCommentMoveRename, cls)._format_path(path)
        return '/9876543210/' if path.endswith('/') else '/1234567890'


@pytest.mark.skip
class TestDropboxFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'dropbox'
    ProviderFile = DropboxFile

    def _create_file_with_comment(self, node, path, user):
        self.file = self.ProviderFile.create(
            is_file=True,
            node=node,
            path='{}{}'.format(node.get_addon(self.provider).folder, path),
            name=path.strip('/'),
            materialized_path=path)
        self.file.save()
        self.guid = self.file.get_guid(create=True)
        self.comment = CommentFactory(user=user, node=node, target=self.guid)


@pytest.mark.skip
class TestGoogleDriveFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'googledrive'
    ProviderFile = GoogleDriveFile

@pytest.mark.skip
class TestGithubFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'github'
    ProviderFile = GithubFile

@pytest.mark.skip
class TestS3FileCommentMoveRename(FileCommentMoveRenameTestMixin):

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
