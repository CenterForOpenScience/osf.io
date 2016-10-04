import pytest

from modularodm.exceptions import ValidationError

from website import settings
from website.util import permissions
from website.project.signals import comment_added, mention_added, contributor_added
from framework.exceptions import PermissionsError
from tests.base import capture_signals
from osf_models.models import Comment, NodeLog, Guid
from osf_models.modm_compat import Q
from osf_models.utils.auth import Auth
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

def test_comments_have_longer_guid():
    comment = CommentFactory()
    assert len(comment._id) == 12

def test_comments_are_queryable_by_root_target():
    root_target = ProjectFactory()
    comment = CommentFactory(node=root_target)
    assert Comment.find(Q('root_target', 'eq', root_target._id))[0] == comment


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
                target=node.guid,
                content=''.join(['c' for c in range(settings.COMMENT_MAXLENGTH + 3)])
            )

    def test_create_comment_content_cannot_exceed_max_length_complex(self, node, user, auth):
        with pytest.raises(ValidationError):
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guid,
                content=''.join(['c' for c in range(settings.COMMENT_MAXLENGTH - 8)]) + '[@George Ant](http://localhost:5000/' + user._id + '/)'
            )

    def test_create_comment_content_does_not_exceed_max_length_complex(self, node, user, auth):
        Comment.create(
            auth=auth,
            user=user,
            node=node,
            target=node.guid,
            content=''.join(['c' for c in range(settings.COMMENT_MAXLENGTH - 12)]) + '[@George Ant](http://localhost:5000/' + user._id + '/)'
        )

    def test_create_comment_content_cannot_be_none(self, node, user, auth):

        with pytest.raises(ValidationError) as error:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guid,
                content=None
            )
        assert error.value.messages[0] == 'This field cannot be null.'

    def test_create_comment_content_cannot_be_empty(self, node, user, auth):
        with pytest.raises(ValidationError) as error:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guid,
                content=''
            )
        assert error.value.messages[0] == 'This field cannot be blank.'

    def test_create_comment_content_cannot_be_whitespace(self, node, user, auth):
        with pytest.raises(ValidationError) as error:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guid,
                content='    '
            )
        assert error.value.messages[0] == 'Value must not be empty.'

    def test_create_sends_comment_added_signal(self, node, user, auth):
        with capture_signals() as mock_signals:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guid,
                content='This is a comment.'
            )
        assert mock_signals.signals_sent() == ({comment_added})

    def test_create_sends_mention_added_signal_if_mentions(self, node, user, auth):
        with capture_signals() as mock_signals:
            Comment.create(
                auth=auth,
                user=user,
                node=node,
                target=node.guid,
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
                node.add_contributor(user, visible=False,permissions=[permissions.READ], save=True)

                Comment.create(
                    auth=auth,
                    user=user,
                    node=node,
                    target=node.guid,
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
                    target=node.guid,
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
                    target=node.guid,
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
            comment.ever_mentioned=[comment.user._id]
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
