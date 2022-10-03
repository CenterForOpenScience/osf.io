import mock
import pytz
import pytest
import datetime
from django.utils import timezone
from collections import OrderedDict

from addons.box.models import BoxFile
from addons.dropbox.models import DropboxFile
from addons.github.models import GithubFile
from addons.googledrive.models import GoogleDriveFile
from addons.osfstorage.models import OsfStorageFile
from addons.s3.models import S3File
from website import settings
from addons.osfstorage import settings as osfstorage_settings
from website.project.views.comment import update_file_guid_referent
from website.project.signals import comment_added, mention_added
from framework.exceptions import PermissionsError
from tests.base import capture_signals
from osf.models import Comment, NodeLog, Guid, BaseFileNode
from osf.utils import permissions
from framework.auth.core import Auth
from .factories import (
    CommentFactory,
    ProjectFactory,
    NodeFactory,
    UserFactory,
    UnregUserFactory,
    AuthUserFactory,
    OSFGroupFactory,
)

# All tests will require a databse
pytestmark = pytest.mark.django_db


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def user_without_nodes():
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
def comment(user, project):
    return CommentFactory(user=user, target=project.guids.last(), node=project)


@pytest.fixture()
def unreg_contributor(project):
    unreg_user = UnregUserFactory()
    unreg_user.save()
    project.add_unregistered_contributor(unreg_user.fullname, unreg_user.email, Auth(project.creator),
                                         permissions=permissions.READ, save=True)
    return unreg_user


@pytest.fixture()
def contributor(project):
    user = UserFactory()
    project.add_contributor(user)
    return user


@pytest.fixture()
def component(user, project):
    return NodeFactory(parent=project, creator=user)


@pytest.fixture()
def project_with_contributor(user, contributor):
    project = ProjectFactory(creator=user)
    project.add_contributor(contributor)
    return project


@pytest.fixture()
def comment_self_mentioned(user):
    return 'This is a comment with a good mention [@Mentioned User](http://localhost:5000/{}/).'.format(user._id)


@pytest.fixture()
def comment_contributor_mentioned(contributor):
    return 'This is a comment with a good mention [@Mentioned User](http://localhost:5000/{}/).'.format(contributor._id)


@pytest.fixture()
def comment_invalid_user_mentioned():
    return 'This is a comment with a good mention [@Mentioned User](http://localhost:5000/qwerty/).'


@pytest.fixture()
def comment_too_long():
    return ''.join(['c' for _ in range(settings.COMMENT_MAXLENGTH + 3)])


@pytest.fixture()
def comment_too_long_with_mention(user):
    mention = '[@George Ant](http://localhost:5000/{}/)'.format(user._id)
    return ''.join(['c' for _ in range(settings.COMMENT_MAXLENGTH - 8)]) + mention


@pytest.fixture()
def comment_valid():
    return 'This is a good comment'


@pytest.fixture()
def comment_mention_valid(contributor):
    return 'This is a comment [@User](http://localhost:5000/{}/).'.format(contributor._id)


@pytest.fixture()
def comment_mention_project_with_contributor(contributor, project_with_contributor):
    return 'This is a comment [@User](http://localhost:5000/{}/).'.format(contributor._id)


@pytest.fixture()
def comment_mention_unreg_contributor(unreg_contributor):
    return 'This is a comment [@Unconfirmed User](http://localhost:5000/{}/).'.format(unreg_contributor._id)


@pytest.fixture()
def comment_mention_non_contributor(user_without_nodes):
    return 'This is a comment [@User](http://localhost:5000/{}/).'.format(user_without_nodes._id)


@pytest.fixture()
def comment_mention_edited_twice(comment, node):
    return 'This is a new comment [@User](http://localhost:5000/{}/).'.format(comment.user)


@pytest.fixture()
def comment_mentioned_with_contributors(user):
    return 'This is a new comment [@User](http://localhost:5000/{}/).'.format(user._id)

def test_comments_have_longer_guid():
    comment = CommentFactory()
    assert len(comment._id) == 12


def test_comments_are_queryable_by_root_target():
    root_target = ProjectFactory()
    comment = CommentFactory(node=root_target)
    assert Comment.objects.filter(root_target=root_target.guids.first()).first() == comment


def pytest_generate_tests(metafunc):
    # called once per each test function
    if not metafunc.cls:
        return
    if not hasattr(metafunc.cls, 'params'):
        return
    funcarglist = metafunc.cls.params.get(metafunc.function.__name__)
    if not funcarglist:
        return
    argnames = sorted(funcarglist[0])
    metafunc.parametrize(argnames, [[funcargs[name] for name in argnames] for funcargs in funcarglist])


# copied from tests/test_comments.py
@pytest.mark.enable_implicit_clean
class TestCommentModel:

    create_and_edit_cases = [
        # Make sure comments aren't empty
        {
            'comment_content': '',
            'expected_signals': set(),
            'expected_error_msg': "{'content': ['This field cannot be blank.']}",
        },
        # Make sure comments aren't whitespace
        {
            'comment_content': '       ',
            'expected_signals': set(),
            'expected_error_msg': "{'content': ['Value must not be empty.']}",
        },
        # Make sure unreg contributors don't send mentions
        {
            'comment_content': comment_mention_unreg_contributor,
            'expected_signals': set(),
            'expected_error_msg': "['User does not exist or is not active.']",
        },
        # Make sure non-contributors don't send mentions
        {
            'comment_content': comment_mention_non_contributor,
            'expected_signals': set(),
            'expected_error_msg': "['Mentioned user is not a contributor or group member.']",
        },
        # Make sure mentions with invalid guids don't send signals
        {
            'comment_content': comment_invalid_user_mentioned,
            'expected_signals': set(),
            'expected_error_msg': "['User does not exist or is not active.']",
        },
        # Test to prevent user from entering a comment that's too long
        {
            'comment_content': comment_too_long,
            'expected_signals': set(),
            'expected_error_msg': "{'content': ['Ensure this field has no more than 1000 characters.']}",
        },

    ]
    create_cases = [
        # Make sure valid mentions send signals
        {
            'comment_content': comment_mention_valid,
            'expected_signals': {comment_added, mention_added},
            'expected_error_msg': None,
        },
        #  User mentions a contributor
        {
            'comment_content': comment_contributor_mentioned,
            'expected_signals': {comment_added, mention_added},
            'expected_error_msg': None,
        },
        # Make sure comments aren't NoneType
        {
            'comment_content': None,
            'expected_signals': set(),
            'expected_error_msg': "{'content': ['This field cannot be null.']}",
        },
        # User makes valid comment
        {
            'comment_content': comment_valid,
            'expected_signals': {comment_added},
            'expected_error_msg': None,
        },
        #  User mentions themselves
        {
            'comment_content': comment_self_mentioned,
            'expected_signals': {comment_added, mention_added},
            'expected_error_msg': None,
        },
        # Prevent user from entering a comment that's too long with a mention
        {
            'comment_content': comment_too_long_with_mention,
            'expected_signals': set(),
            'expected_error_msg': "{'content': ['Ensure this field has no more than 1000 characters.']}",
        },
    ]
    edit_cases = [
        # Send if mention is valid
        {
            'comment_content': comment_mention_valid,
            'expected_signals': {mention_added},
            'expected_error_msg': None,
        },
        #  User mentions a contributor
        {
            'comment_content': comment_contributor_mentioned,
            'expected_signals': {mention_added},
            'expected_error_msg': None,
        },
        # User edits valid comment
        {
            'comment_content': comment_valid,
            'expected_signals': set(),
            'expected_error_msg': None,
        },
        #  User mentions themselves
        {
            'comment_content': comment_self_mentioned,
            'expected_signals': {mention_added},
            'expected_error_msg': None,
        },
        # Don't send mention if already mentioned
        {
            'comment_content': comment_mention_edited_twice,
            'expected_signals': set(),
            'expected_error_msg': None,
        },
        # Send mention if already mentioned
        {
            'comment_content': comment_mention_project_with_contributor,
            'expected_signals': {mention_added},
            'expected_error_msg': None,
        }
    ]
    params = {
        'test_create_comment': create_and_edit_cases + create_cases,
        'test_edit_comment': create_and_edit_cases + edit_cases
    }

    def test_create_comment(self, request, user, project, comment_content, expected_signals, expected_error_msg):
        if hasattr(comment_content, '_pytestfixturefunction'):
            comment_content = request.getfixturevalue(comment_content.__name__)

        auth = Auth(user)
        error_msg = None
        with capture_signals() as mock_signals:
            try:
                Comment.create(
                    auth=auth,
                    user=user,
                    node=project,
                    target=project.guids.all()[0],
                    content=comment_content
                )
            except Exception as e:
                error_msg = str(e)

        assert expected_signals == mock_signals.signals_sent()
        assert error_msg == expected_error_msg

    def test_edit_comment(self, request, comment, comment_content, expected_signals, expected_error_msg):
        if hasattr(comment_content, '_pytestfixturefunction'):
            comment_content = request.getfixturevalue(comment_content.__name__)

        error_msg = None
        auth = Auth(comment.user)
        with capture_signals() as mock_signals:
            try:
                comment.edit(
                    auth=auth,
                    content=comment_content,
                    save=True,
                )
            except Exception as e:
                error_msg = str(e)

        assert expected_signals == mock_signals.signals_sent()
        assert error_msg == expected_error_msg

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

    def test_create_sends_mention_added_signal_if_group_member_mentions(self, node, user, auth):
        manager = AuthUserFactory()
        group = OSFGroupFactory(creator=manager)
        node.add_osf_group(group)
        assert node.is_contributor_or_group_member(manager) is True
        with capture_signals() as mock_signals:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guids.all()[0],
                content='This is a comment with a group member mention [@Group Member](http://localhost:5000/' + manager._id + '/).'
            )
        assert mock_signals.signals_sent() == ({comment_added, mention_added})

    def test_delete(self, node):
        comment = CommentFactory(node=node)
        auth = Auth(comment.user)
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            comment.delete(auth=auth, save=True)
        assert comment.is_deleted, True
        assert comment.deleted == mock_now
        assert comment.node.logs.count() == 2
        assert comment.node.logs.latest().action == NodeLog.COMMENT_REMOVED

    def test_undelete(self):
        comment = CommentFactory()
        auth = Auth(comment.user)
        comment.delete(auth=auth, save=True)
        comment.undelete(auth=auth, save=True)
        assert not comment.is_deleted
        assert not comment.deleted
        assert comment.node.logs.count() == 3
        assert comment.node.logs.latest().action == NodeLog.COMMENT_RESTORED

    def test_read_permission_contributor_can_comment(self):
        project = ProjectFactory()
        user = UserFactory()
        project.set_privacy('private')
        project.add_contributor(user, permissions=permissions.READ)
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
    id_based_providers = ['osfstorage']

    @pytest.fixture()
    def project(self, user):
        p = ProjectFactory(creator=user)
        p_settings = p.get_or_add_addon(self.provider, Auth(user))
        p_settings.folder = '/Folder1'
        p_settings.save()
        p.save()
        return p

    @pytest.fixture()
    def component(self, user, project):
        c = NodeFactory(parent=project, creator=user)
        c_settings = c.get_or_add_addon(self.provider, Auth(user))
        c_settings.folder = '/Folder2'
        c_settings.save()
        c.save()
        return c

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
            target=node,
            path=path,
            name=path.strip('/'),
            materialized_path=path)
        self.file.save()
        self.guid = self.file.get_guid(create=True)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()
        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_renamed', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_path), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.target._id == destination['node']._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.target._id == destination['node']._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class('osfstorage', BaseFileNode.FILE).get_or_create(destination['node'], destination['path'])
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class('osfstorage', BaseFileNode.FILE).get_or_create(destination['node'], osf_file._id)
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(destination_provider, BaseFileNode.FILE).get_or_create(destination['node'], destination['path'])
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
        assert file_comments.count() == 1

    @pytest.mark.parametrize(
        ['destination_provider', 'destination_path'],
        [('box', '/1234567890'), ('dropbox', '/subfolder/file.txt'), ('github', '/subfolder/file.txt'), ('googledrive', '/subfolder/file.txt'), ('s3', '/subfolder/file.txt'), ]
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(destination_provider, BaseFileNode.FILE).get_or_create(destination['node'], destination_path)
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.target._id == destination['node']._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path(destination['path'], file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        assert self.guid.referent.target._id == destination['node']._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
        update_file_guid_referent(self=None, target=destination['node'], event_type='addon_file_moved', payload=payload)
        self.guid.reload()

        file_node = BaseFileNode.resolve_class(self.provider, BaseFileNode.FILE).get_or_create(destination['node'], self._format_path('{}{}'.format(destination['path'], file_name), file_id=self.file._id))
        assert self.guid._id == file_node.get_guid()._id
        file_comments = Comment.objects.filter(root_target=self.guid.pk)
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
            target=node,
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


class TestDropboxFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'dropbox'
    ProviderFile = DropboxFile

    def _create_file_with_comment(self, node, path, user):
        self.file = self.ProviderFile.create(
            target=node,
            path='{}{}'.format(node.get_addon(self.provider).folder, path),
            name=path.strip('/'),
            materialized_path=path)
        self.file.save()
        self.guid = self.file.get_guid(create=True)
        self.comment = CommentFactory(user=user, node=node, target=self.guid)


class TestGoogleDriveFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'googledrive'
    ProviderFile = GoogleDriveFile

class TestGithubFileCommentMoveRename(FileCommentMoveRenameTestMixin):

    provider = 'github'
    ProviderFile = GithubFile

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
