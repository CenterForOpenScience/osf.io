from unittest import mock
import pytz
import pytest
import datetime
from django.utils import timezone
from website import settings
from framework.exceptions import PermissionsError
from tests.base import capture_signals
from osf.models import Comment, NodeLog, Guid
from osf.utils import permissions
from framework.auth.core import Auth
from .factories import (
    CommentFactory,
    ProjectFactory,
    NodeFactory,
    UserFactory,
    UnregUserFactory,
    AuthUserFactory,
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
    project.add_unregistered_contributor(
        unreg_user.fullname,
        unreg_user.email,
        Auth(project.creator),
        permissions=permissions.READ
    )
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
    return f'This is a comment with a good mention [@Mentioned User](http://localhost:5000/{user._id}/).'


@pytest.fixture()
def comment_contributor_mentioned(contributor):
    return f'This is a comment with a good mention [@Mentioned User](http://localhost:5000/{contributor._id}/).'


@pytest.fixture()
def comment_invalid_user_mentioned():
    return 'This is a comment with a good mention [@Mentioned User](http://localhost:5000/qwerty/).'


@pytest.fixture()
def comment_too_long():
    return ''.join(['c' for _ in range(settings.COMMENT_MAXLENGTH + 3)])


@pytest.fixture()
def comment_too_long_with_mention(user):
    mention = f'[@George Ant](http://localhost:5000/{user._id}/)'
    return ''.join(['c' for _ in range(settings.COMMENT_MAXLENGTH - 8)]) + mention


@pytest.fixture()
def comment_valid():
    return 'This is a good comment'


@pytest.fixture()
def comment_mention_valid(contributor):
    return f'This is a comment [@User](http://localhost:5000/{contributor._id}/).'


@pytest.fixture()
def comment_mention_project_with_contributor(contributor, project_with_contributor):
    return f'This is a comment [@User](http://localhost:5000/{contributor._id}/).'


@pytest.fixture()
def comment_mention_unreg_contributor(unreg_contributor):
    return f'This is a comment [@Unconfirmed User](http://localhost:5000/{unreg_contributor._id}/).'


@pytest.fixture()
def comment_mention_non_contributor(user_without_nodes):
    return f'This is a comment [@User](http://localhost:5000/{user_without_nodes._id}/).'


@pytest.fixture()
def comment_mention_edited_twice(comment, node):
    return f'This is a new comment [@User](http://localhost:5000/{comment.user}/).'


@pytest.fixture()
def comment_mentioned_with_contributors(user):
    return f'This is a new comment [@User](http://localhost:5000/{user._id}/).'

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
        # Make sure comments aren't NoneType
        {
            'comment_content': None,
            'expected_signals': set(),
            'expected_error_msg': "{'content': ['This field cannot be null.']}",
        },
        # Prevent user from entering a comment that's too long with a mention
        {
            'comment_content': comment_too_long_with_mention,
            'expected_signals': set(),
            'expected_error_msg': "{'content': ['Ensure this field has no more than 1000 characters.']}",
        },
    ]
    edit_cases = [
        # User edits valid comment
        {
            'comment_content': comment_valid,
            'expected_signals': set(),
            'expected_error_msg': None,
        },
        # Don't send mention if already mentioned
        {
            'comment_content': comment_mention_edited_twice,
            'expected_signals': set(),
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
