import collections
from unittest import mock

import pytest
from babel import dates, Locale
from schema import Schema, And, Use, Or
from django.utils import timezone

from framework.auth import Auth
from osf.models import Comment, NotificationDigest, NotificationSubscription, Guid, OSFUser

from website.notifications.tasks import get_users_emails, send_users_email, group_by_node, remove_notifications
from website.notifications.exceptions import InvalidSubscriptionError
from website.notifications import constants
from website.notifications import emails
from website.notifications import utils
from website import mails
from website.profile.utils import get_profile_image_url
from website.project.signals import contributor_removed, node_deleted
from website.reviews import listeners
from website.util import api_url_for
from website.util import web_url_for
from website import settings

from osf_tests import factories
from osf.utils import permissions
from tests.base import capture_signals
from tests.base import OsfTestCase, NotificationTestCase



class TestNotificationsModels(OsfTestCase):

    def setUp(self):
        super().setUp()
        # Create project with component
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.parent = factories.ProjectFactory(creator=self.user)
        self.node = factories.NodeFactory(creator=self.user, parent=self.parent)

    def test_has_permission_on_children(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=permissions.READ)
        parent.save()

        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.save()
        sub_component2 = factories.NodeFactory(parent=node)

        assert node.has_permission_on_children(non_admin_user, permissions.READ)

    def test_check_user_has_permission_excludes_deleted_components(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=permissions.READ)
        parent.save()

        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.is_deleted = True
        sub_component.save()
        sub_component2 = factories.NodeFactory(parent=node)

        assert not node.has_permission_on_children(non_admin_user, permissions.READ)

    def test_check_user_does_not_have_permission_on_private_node_child(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=permissions.READ)
        parent.save()
        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)

        assert not node.has_permission_on_children(non_admin_user,permissions.READ)

    def test_check_user_child_node_permissions_false_if_no_children(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=permissions.READ)
        parent.save()
        node = factories.NodeFactory(parent=parent, category='project')

        assert not node.has_permission_on_children(non_admin_user,permissions.READ)

    def test_check_admin_has_permissions_on_private_component(self):
        parent = factories.ProjectFactory()
        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)

        assert node.has_permission_on_children(parent.creator,permissions.READ)

    def test_check_user_private_node_child_permissions_excludes_pointers(self):
        user = factories.UserFactory()
        parent = factories.ProjectFactory()
        pointed = factories.ProjectFactory(creator=user)
        parent.add_pointer(pointed, Auth(parent.creator))
        parent.save()

        assert not parent.has_permission_on_children(user,permissions.READ)

    def test_new_project_creator_is_subscribed(self):
        user = factories.UserFactory()
        factories.ProjectFactory(creator=user)
        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        assert len(user_subscriptions) == 1  # subscribed to file_updated
        assert 'file_updated' in event_types

    def test_new_node_creator_is_not_subscribed(self):
        user = factories.UserFactory()
        factories.NodeFactory(creator=user)
        user_subscriptions = list(utils.get_all_user_subscriptions(user))

        assert len(user_subscriptions) == 0

    def test_new_project_creator_is_subscribed_with_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'none')

        node = factories.ProjectFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        file_updated_subscription = NotificationSubscription.objects.get(_id=node._id + '_file_updated')

        assert len(user_subscriptions) == 2  # subscribed to both node and user settings
        assert 'file_updated' in event_types
        assert 'global_file_updated' in event_types
        assert file_updated_subscription.none.count() == 1
        assert file_updated_subscription.email_transactional.count() == 0

    def test_new_node_creator_is_not_subscribed_with_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'none')

        node = factories.NodeFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        assert len(user_subscriptions) == 1  # subscribed to only user settings
        assert 'global_file_updated' in event_types

    def test_subscribe_user_to_global_notfiications(self):
        user = factories.UserFactory()
        utils.subscribe_user_to_global_notifications(user)
        subscription_event_names = list(user.notification_subscriptions.values_list('event_name', flat=True))
        for event_name in constants.USER_SUBSCRIPTIONS_AVAILABLE:
            assert event_name in subscription_event_names

    def test_subscribe_user_to_registration_notifications(self):
        registration = factories.RegistrationFactory()
        with pytest.raises(InvalidSubscriptionError):
            utils.subscribe_user_to_notifications(registration, self.user)

    def test_new_project_creator_is_subscribed_with_default_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'email_transactional')

        node = factories.ProjectFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        file_updated_subscription = NotificationSubscription.objects.get(_id=node._id + '_file_updated')

        assert len(user_subscriptions) == 2  # subscribed to both node and user settings
        assert 'file_updated' in event_types
        assert 'global_file_updated' in event_types
        assert file_updated_subscription.email_transactional.count() == 1

    def test_new_fork_creator_is_subscribed_with_default_global_settings(self):
        user = factories.UserFactory()
        project = factories.ProjectFactory(creator=user)

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'email_transactional')

        node = factories.ForkFactory(project=project)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        node_file_updated_subscription = NotificationSubscription.objects.get(_id=node._id + '_file_updated')
        project_file_updated_subscription = NotificationSubscription.objects.get(_id=project._id + '_file_updated')

        assert len(user_subscriptions) == 3  # subscribed to project, fork, and user settings
        assert 'file_updated' in event_types
        assert 'global_file_updated' in event_types
        assert node_file_updated_subscription.email_transactional.count() == 1
        assert project_file_updated_subscription.email_transactional.count() == 1

    def test_new_node_creator_is_not_subscribed_with_default_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'email_transactional')

        node = factories.NodeFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        assert len(user_subscriptions) == 1  # subscribed to only user settings
        assert 'global_file_updated' in event_types


    def test_contributor_subscribed_when_added_to_project(self):
        user = factories.UserFactory()
        contributor = factories.UserFactory()
        project = factories.ProjectFactory(creator=user)
        project.add_contributor(contributor=contributor)
        contributor_subscriptions = list(utils.get_all_user_subscriptions(contributor))
        event_types = [sub.event_name for sub in contributor_subscriptions]

        assert len(contributor_subscriptions) == 1
        assert 'file_updated' in event_types

    def test_contributor_subscribed_when_added_to_component(self):
        user = factories.UserFactory()
        contributor = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=contributor._id + '_' + 'global_file_updated',
            user=contributor,
            event_name='global_file_updated'
        ).add_user_to_subscription(contributor, 'email_transactional')

        node = factories.NodeFactory(creator=user)
        node.add_contributor(contributor=contributor)

        contributor_subscriptions = list(utils.get_all_user_subscriptions(contributor))
        event_types = [sub.event_name for sub in contributor_subscriptions]

        file_updated_subscription = NotificationSubscription.objects.get(_id=node._id + '_file_updated')

        assert len(contributor_subscriptions) == 2  # subscribed to both node and user settings
        assert 'file_updated' in event_types
        assert 'global_file_updated' in event_types
        assert file_updated_subscription.email_transactional.count() == 1

    def test_unregistered_contributor_not_subscribed_when_added_to_project(self):
        user = factories.AuthUserFactory()
        unregistered_contributor = factories.UnregUserFactory()
        project = factories.ProjectFactory(creator=user)
        project.add_unregistered_contributor(
            unregistered_contributor.fullname,
            unregistered_contributor.email,
            Auth(user),
            existing_user=unregistered_contributor
        )

        contributor_subscriptions = list(utils.get_all_user_subscriptions(unregistered_contributor))
        assert len(contributor_subscriptions) == 0


class TestRemoveNodeSignal(OsfTestCase):

    def test_node_subscriptions_and_backrefs_removed_when_node_is_deleted(self):
        project = factories.ProjectFactory()
        component = factories.NodeFactory(parent=project, creator=project.creator)

        s = NotificationSubscription.objects.filter(email_transactional=project.creator)
        assert s.count() == 1

        s = NotificationSubscription.objects.filter(email_transactional=component.creator)
        assert s.count() == 1

        with capture_signals() as mock_signals:
            project.remove_node(auth=Auth(project.creator))
        project.reload()
        component.reload()

        assert project.is_deleted
        assert component.is_deleted
        assert mock_signals.signals_sent() == {node_deleted}

        s = NotificationSubscription.objects.filter(email_transactional=project.creator)
        assert s.count() == 0

        s = NotificationSubscription.objects.filter(email_transactional=component.creator)
        assert s.count() == 0

        with pytest.raises(NotificationSubscription.DoesNotExist):
            NotificationSubscription.objects.get(node=project)

        with pytest.raises(NotificationSubscription.DoesNotExist):
            NotificationSubscription.objects.get(node=component)


def list_or_dict(data):
    # Generator only returns lists or dicts from list or dict
    if isinstance(data, dict):
        for key in data:
            if isinstance(data[key], dict) or isinstance(data[key], list):
                yield data[key]
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) or isinstance(item, list):
                yield item


def has(data, sub_data):
    # Recursive approach to look for a subset of data in data.
    # WARNING: Don't use on huge structures
    # :param data: Data structure
    # :param sub_data: subset being checked for
    # :return: True or False
    try:
        next(item for item in data if item == sub_data)
        return True
    except StopIteration:
        lists_and_dicts = list_or_dict(data)
        for item in lists_and_dicts:
            if has(item, sub_data):
                return True
    return False


def subscription_schema(project, structure, level=0):
    # builds a schema from a list of nodes and events
    # :param project: validation type
    # :param structure: list of nodes (another list) and events
    # :return: schema
    sub_list = []
    for item in list_or_dict(structure):
        sub_list.append(subscription_schema(project, item, level=level+1))
    sub_list.append(event_schema(level))

    node_schema = {
        'node': {
            'id': Use(type(project._id), error=f'node_id{level}'),
            'title': Use(type(project.title), error=f'node_title{level}'),
            'url': Use(type(project.url), error=f'node_{level}')
        },
        'kind': And(str, Use(lambda s: s in ('node', 'folder'),
                             error=f"kind didn't match node or folder {level}")),
        'nodeType': Use(lambda s: s in ('project', 'component'), error='nodeType not project or component'),
        'category': Use(lambda s: s in settings.NODE_CATEGORY_MAP, error='category not in settings.NODE_CATEGORY_MAP'),
        'permissions': {
            'view': Use(lambda s: s in (True, False), error='view permissions is not True/False')
        },
        'children': sub_list
    }
    if level == 0:
        return Schema([node_schema])
    return node_schema


def event_schema(level=None):
    return {
        'event': {
            'title': And(Use(str, error=f'event_title{level} not a string'),
                         Use(lambda s: s in constants.NOTIFICATION_TYPES,
                             error=f'event_title{level} not in list')),
            'description': And(Use(str, error=f'event_desc{level} not a string'),
                               Use(lambda s: s in constants.NODE_SUBSCRIPTIONS_AVAILABLE,
                                   error=f'event_desc{level} not in list')),
            'notificationType': And(str, Or('adopt_parent', lambda s: s in constants.NOTIFICATION_TYPES)),
            'parent_notification_type': Or(None, 'adopt_parent', lambda s: s in constants.NOTIFICATION_TYPES)
        },
        'kind': 'event',
        'children': And(list, lambda l: len(l) == 0)
    }


class TestNotificationUtils(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = factories.UserFactory()
        self.project = factories.ProjectFactory(creator=self.user)

        self.user.notifications_configured[self.project._id] = True
        self.user.save()

        self.node = factories.NodeFactory(parent=self.project, creator=self.user)

        self.user_subscription = [
        factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'global_file_updated',
            user=self.user,
            event_name='global_file_updated'
        )]

        for x in self.user_subscription:
            x.save()
        for x in self.user_subscription:
            x.email_transactional.add(self.user)
        for x in self.user_subscription:
            x.save()

    def test_to_subscription_key(self):
        key = utils.to_subscription_key('xyz', 'comments')
        assert key == 'xyz_comments'

    def test_from_subscription_key(self):
        parsed_key = utils.from_subscription_key('xyz_comment_replies')
        assert parsed_key == {
            'uid': 'xyz',
            'event': 'comment_replies'
        }

    def test_get_configured_project_ids_does_not_return_user_or_node_ids(self):
        configured_nodes = utils.get_configured_projects(self.user)
        configured_ids = [n._id for n in configured_nodes]
        # No duplicates!
        assert len(configured_nodes) == 1

        assert self.project._id in configured_ids
        assert self.node._id not in configured_ids
        assert self.user._id not in configured_ids

    def test_get_configured_project_ids_excludes_deleted_projects(self):
        project = factories.ProjectFactory()
        project.is_deleted = True
        project.save()
        assert project not in utils.get_configured_projects(self.user)

    def test_get_configured_project_ids_excludes_node_with_project_category(self):
        node = factories.NodeFactory(parent=self.project, category='project')
        assert node not in utils.get_configured_projects(self.user)

    def test_get_configured_project_ids_includes_top_level_private_projects_if_subscriptions_on_node(self):
        private_project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=private_project)
        node_comments_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_' + 'comments',
            node=node,
            event_name='comments'
        )
        node_comments_subscription.save()
        node_comments_subscription.email_transactional.add(node.creator)
        node_comments_subscription.save()

        node.creator.notifications_configured[node._id] = True
        node.creator.save()
        configured_project_nodes = utils.get_configured_projects(node.creator)
        assert private_project in configured_project_nodes

    def test_get_configured_project_ids_excludes_private_projects_if_no_subscriptions_on_node(self):
        user = factories.UserFactory()

        private_project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=private_project)
        node.add_contributor(user)

        utils.remove_contributor_from_subscriptions(node, user)

        configured_project_nodes = utils.get_configured_projects(user)
        assert private_project not in configured_project_nodes

    def test_format_user_subscriptions(self):
        data = utils.format_user_subscriptions(self.user)
        expected = [
            {
                'event': {
                    'title': 'global_file_updated',
                    'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['global_file_updated'],
                    'notificationType': 'email_transactional',
                    'parent_notification_type': None,
                },
                'kind': 'event',
                'children': []
            }, {
                'event': {
                    'title': 'global_reviews',
                    'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['global_reviews'],
                    'notificationType': 'email_transactional',
                    'parent_notification_type': None
                },
                'kind': 'event',
                'children': []
            }
        ]

        assert data == expected

    def test_format_data_user_settings(self):
        data = utils.format_user_and_project_subscriptions(self.user)
        expected = [
            {
                'node': {
                    'id': self.user._id,
                    'title': 'Default Notification Settings',
                    'help': 'These are default settings for new projects you create or are added to. Modifying these settings will not modify settings on existing projects.'
            },
                'kind': 'heading',
                'children': utils.format_user_subscriptions(self.user)
            },
            {
                'node': {
                    'help': 'These are settings for each of your projects. Modifying these settings will only modify the settings for the selected project.',
                    'id': '',
                    'title': 'Project Notifications'
                },
                'kind': 'heading',
                'children': utils.format_data(self.user, utils.get_configured_projects(self.user))
            }]
        assert data == expected


class TestCompileSubscriptions(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.user_1 = factories.UserFactory()
        self.user_2 = factories.UserFactory()
        self.user_3 = factories.UserFactory()
        self.user_4 = factories.UserFactory()
        # Base project + 1 project shared with 3 + 1 project shared with 2
        self.base_project = factories.ProjectFactory(is_public=False, creator=self.user_1)
        self.shared_node = factories.NodeFactory(parent=self.base_project, is_public=False, creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.base_project, is_public=False, creator=self.user_1)
        # Adding contributors
        for node in [self.base_project, self.shared_node, self.private_node]:
            node.add_contributor(self.user_2, permissions=permissions.ADMIN)
        self.base_project.add_contributor(self.user_3, permissions=permissions.WRITE)
        self.shared_node.add_contributor(self.user_3, permissions=permissions.WRITE)
        # Setting basic subscriptions
        self.base_sub = factories.NotificationSubscriptionFactory(
            _id=self.base_project._id + '_file_updated',
            node=self.base_project,
            event_name='file_updated'
        )
        self.base_sub.save()
        self.shared_sub = factories.NotificationSubscriptionFactory(
            _id=self.shared_node._id + '_file_updated',
            node=self.shared_node,
            event_name='file_updated'
        )
        self.shared_sub.save()
        self.private_sub = factories.NotificationSubscriptionFactory(
            _id=self.private_node._id + '_file_updated',
            node=self.private_node,
            event_name='file_updated'
        )
        self.private_sub.save()

    def test_no_subscription(self):
        node = factories.NodeFactory()
        result = emails.compile_subscriptions(node, 'file_updated')
        assert {'email_transactional': [], 'none': [], 'email_digest': []} == result

    def test_no_subscribers(self):
        node = factories.NodeFactory()
        node_sub = factories.NotificationSubscriptionFactory(
            _id=node._id + '_file_updated',
            node=node,
            event_name='file_updated'
        )
        node_sub.save()
        result = emails.compile_subscriptions(node, 'file_updated')
        assert {'email_transactional': [], 'none': [], 'email_digest': []} == result

    def test_creator_subbed_parent(self):
        # Basic sub check
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.base_project, 'file_updated')
        assert {'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []} == result

    def test_creator_subbed_to_parent_from_child(self):
        # checks the parent sub is the one to appear without a child sub
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert {'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []} == result

    def test_creator_subbed_to_both_from_child(self):
        # checks that only one sub is in the list.
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        self.shared_sub.email_transactional.add(self.user_1)
        self.shared_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert {'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []} == result

    def test_creator_diff_subs_to_both_from_child(self):
        # Check that the child node sub overrides the parent node sub
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        self.shared_sub.none.add(self.user_1)
        self.shared_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert {'email_transactional': [], 'none': [self.user_1._id], 'email_digest': []} == result

    def test_user_wo_permission_on_child_node_not_listed(self):
        # Tests to see if a user without permission gets an Email about a node they cannot see.
        self.base_sub.email_transactional.add(self.user_3)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.private_node, 'file_updated')
        assert {'email_transactional': [], 'none': [], 'email_digest': []} == result

    def test_several_nodes_deep(self):
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        node2 = factories.NodeFactory(parent=self.shared_node)
        node3 = factories.NodeFactory(parent=node2)
        node4 = factories.NodeFactory(parent=node3)
        node5 = factories.NodeFactory(parent=node4)
        subs = emails.compile_subscriptions(node5, 'file_updated')
        assert subs == {'email_transactional': [self.user_1._id], 'email_digest': [], 'none': []}

    def test_several_nodes_deep_precedence(self):
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        node2 = factories.NodeFactory(parent=self.shared_node)
        node3 = factories.NodeFactory(parent=node2)
        node4 = factories.NodeFactory(parent=node3)
        node4_subscription = factories.NotificationSubscriptionFactory(
            _id=node4._id + '_file_updated',
            node=node4,
            event_name='file_updated'
        )
        node4_subscription.save()
        node4_subscription.email_digest.add(self.user_1)
        node4_subscription.save()
        node5 = factories.NodeFactory(parent=node4)
        subs = emails.compile_subscriptions(node5, 'file_updated')
        assert subs == {'email_transactional': [], 'email_digest': [self.user_1._id], 'none': []}


class TestMoveSubscription(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.blank = {key: [] for key in constants.NOTIFICATION_TYPES}  # For use where it is blank.
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.user_3 = factories.AuthUserFactory()
        self.user_4 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.project, is_public=False, creator=self.user_1)
        self.sub = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            node=self.project,
            event_name='file_updated'
        )
        self.sub.email_transactional.add(self.user_1)
        self.sub.save()
        self.file_sub = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_xyz42_file_updated',
            node=self.project,
            event_name='xyz42_file_updated'
        )
        self.file_sub.save()

    def test_separate_users(self):
        self.private_node.add_contributor(self.user_2, permissions=permissions.ADMIN, auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.private_node.save()
        subbed, removed = utils.separate_users(
            self.private_node, [self.user_2._id, self.user_3._id, self.user_4._id]
        )
        assert [self.user_2._id, self.user_3._id] == subbed
        assert [self.user_4._id] == removed

    def test_event_subs_same(self):
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=permissions.ADMIN, auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        assert {'email_transactional': [self.user_4._id], 'email_digest': [], 'none': []} == results

    def test_event_nodes_same(self):
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=permissions.ADMIN, auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.project)
        assert {'email_transactional': [], 'email_digest': [], 'none': []} == results

    def test_move_sub(self):
        # Tests old sub is replaced with new sub.
        utils.move_subscription(self.blank, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        self.file_sub.reload()
        assert 'abc42_file_updated' == self.file_sub.event_name
        assert self.private_node == self.file_sub.owner
        assert self.private_node._id + '_abc42_file_updated' == self.file_sub._id

    def test_move_sub_with_none(self):
        # Attempt to reproduce an error that is seen when moving files
        self.project.add_contributor(self.user_2, permissions=permissions.WRITE, auth=self.auth)
        self.project.save()
        self.file_sub.none.add(self.user_2)
        self.file_sub.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        assert {'email_transactional': [], 'email_digest': [], 'none': [self.user_2._id]} == results

    def test_remove_one_user(self):
        # One user doesn't have permissions on the node the sub is moved to. Should be listed.
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=permissions.ADMIN, auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        assert {'email_transactional': [self.user_4._id], 'email_digest': [], 'none': []} == results

    def test_remove_one_user_warn_another(self):
        # Two users do not have permissions on new node, but one has a project sub. Both should be listed.
        self.private_node.add_contributor(self.user_2, permissions=permissions.ADMIN, auth=self.auth)
        self.private_node.save()
        self.project.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.project.save()
        self.sub.email_digest.add(self.user_3)
        self.sub.save()
        self.file_sub.email_transactional.add(self.user_2, self.user_4)

        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        utils.move_subscription(results, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert {'email_transactional': [self.user_4._id], 'email_digest': [self.user_3._id], 'none': []} == results
        assert self.sub.email_digest.filter(id=self.user_3.id).exists()  # Is not removed from the project subscription.

    def test_warn_user(self):
        # One user with a project sub does not have permission on new node. User should be listed.
        self.private_node.add_contributor(self.user_2, permissions=permissions.ADMIN, auth=self.auth)
        self.private_node.save()
        self.project.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.project.save()
        self.sub.email_digest.add(self.user_3)
        self.sub.save()
        self.file_sub.email_transactional.add(self.user_2)
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        utils.move_subscription(results, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert {'email_transactional': [], 'email_digest': [self.user_3._id], 'none': []} == results
        assert self.user_3 in self.sub.email_digest.all() # Is not removed from the project subscription.

    def test_user_node_subbed_and_not_removed(self):
        self.project.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.project.save()
        self.private_node.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.private_node.save()
        self.sub.email_digest.add(self.user_3)
        self.sub.save()
        utils.move_subscription(self.blank, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert not self.file_sub.email_digest.filter().exists()

    # Regression test for commit ea15186
    def test_garrulous_event_name(self):
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=permissions.ADMIN, auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=permissions.WRITE, auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('complicated/path_to/some/file/ASDFASDF.txt_file_updated', self.project, self.private_node)
        assert {'email_transactional': [], 'email_digest': [], 'none': []} == results

class TestSendEmails(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.user = factories.AuthUserFactory()
        self.project = factories.ProjectFactory()
        self.node = factories.NodeFactory(parent=self.project)


    def test_get_settings_url_for_node(self):
        url = emails.get_settings_url(self.project._id, self.user)
        assert url == self.project.absolute_url + 'settings/'

    def test_get_settings_url_for_user(self):
        url = emails.get_settings_url(self.user._id, self.user)
        assert url == web_url_for('user_notifications', _absolute=True)

    def test_get_node_lineage(self):
        node_lineage = emails.get_node_lineage(self.node)
        assert node_lineage == [self.project._id, self.node._id]

    def test_fix_locale(self):
        assert emails.fix_locale('en') == 'en'
        assert emails.fix_locale('de_DE') == 'de_DE'
        assert emails.fix_locale('de_de') == 'de_DE'

    def test_localize_timestamp(self):
        timestamp = timezone.now()
        self.user.timezone = 'America/New_York'
        self.user.locale = 'en_US'
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = f'{formatted_time} on {formatted_date}'
        assert emails.localize_timestamp(timestamp, self.user) == formatted_datetime

    def test_localize_timestamp_empty_timezone(self):
        timestamp = timezone.now()
        self.user.timezone = ''
        self.user.locale = 'en_US'
        self.user.save()
        tz = dates.get_timezone('Etc/UTC')
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = f'{formatted_time} on {formatted_date}'
        assert emails.localize_timestamp(timestamp, self.user) == formatted_datetime

    def test_localize_timestamp_empty_locale(self):
        timestamp = timezone.now()
        self.user.timezone = 'America/New_York'
        self.user.locale = ''
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale('en')
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = f'{formatted_time} on {formatted_date}'
        assert emails.localize_timestamp(timestamp, self.user) == formatted_datetime

    def test_localize_timestamp_handles_unicode(self):
        timestamp = timezone.now()
        self.user.timezone = 'Europe/Moscow'
        self.user.locale = 'ru_RU'
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = f'{formatted_time} on {formatted_date}'
        assert emails.localize_timestamp(timestamp, self.user) == formatted_datetime


class TestSendDigest(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user_1 = factories.UserFactory()
        self.user_2 = factories.UserFactory()
        self.project = factories.ProjectFactory()
        self.timestamp = timezone.now()

    def test_group_notifications_by_user_transactional(self):
        send_type = 'email_transactional'
        d = factories.NotificationDigestFactory(
            user=self.user_1,
            send_type=send_type,
            timestamp=self.timestamp,
            message='Hello',
            node_lineage=[self.project._id]
        )
        d.save()
        d2 = factories.NotificationDigestFactory(
            user=self.user_2,
            send_type=send_type,
            timestamp=self.timestamp,
            message='Hello',
            node_lineage=[self.project._id]
        )
        d2.save()
        d3 = factories.NotificationDigestFactory(
            user=self.user_2,
            send_type='email_digest',
            timestamp=self.timestamp,
            message='Hello, but this should not appear (this is a digest)',
            node_lineage=[self.project._id]
        )
        d3.save()
        user_groups = list(get_users_emails(send_type))
        expected = [
            {
                'user_id': self.user_1._id,
                'info': [{
                    'message': 'Hello',
                    'node_lineage': [str(self.project._id)],
                    '_id': d._id
                }]
            },
            {
                'user_id': self.user_2._id,
                'info': [{
                    'message': 'Hello',
                    'node_lineage': [str(self.project._id)],
                    '_id': d2._id
                }]
            }
        ]

        assert len(user_groups) == 2
        assert user_groups == expected
        digest_ids = [d._id, d2._id, d3._id]
        remove_notifications(email_notification_ids=digest_ids)

    def test_group_notifications_by_user_digest(self):
        send_type = 'email_digest'
        d2 = factories.NotificationDigestFactory(
            user=self.user_2,
            send_type=send_type,
            timestamp=self.timestamp,
            message='Hello',
            node_lineage=[self.project._id]
        )
        d2.save()
        d3 = factories.NotificationDigestFactory(
            user=self.user_2,
            send_type='email_transactional',
            timestamp=self.timestamp,
            message='Hello, but this should not appear (this is transactional)',
            node_lineage=[self.project._id]
        )
        d3.save()
        user_groups = list(get_users_emails(send_type))
        expected = [
            {
                'user_id': str(self.user_2._id),
                'info': [{
                    'message': 'Hello',
                    'node_lineage': [str(self.project._id)],
                    '_id': str(d2._id)
                }]
            }
        ]

        assert len(user_groups) == 1
        assert user_groups == expected
        digest_ids = [d2._id, d3._id]
        remove_notifications(email_notification_ids=digest_ids)

    @mock.patch('website.mails.execute_email_send')
    def test_send_users_email_called_with_correct_args(self, mock_send_mail):
        send_type = 'email_transactional'
        d = factories.NotificationDigestFactory(
            send_type=send_type,
            event='comment_replies',
            timestamp=timezone.now(),
            message='Hello',
            node_lineage=[factories.ProjectFactory()._id]
        )
        d.save()
        user_groups = list(get_users_emails(send_type))
        send_users_email(send_type)
        assert mock_send_mail.called
        assert mock_send_mail.call_count == len(user_groups)

        last_user_index = len(user_groups) - 1
        user = OSFUser.load(user_groups[last_user_index]['user_id'])

        args, kwargs = mock_send_mail.call_args

        assert kwargs['to_addr'] == user.username
        assert kwargs['mail'] == mails.DIGEST
        assert kwargs['name'] == user.fullname
        assert kwargs['can_change_node_preferences'] == True
        message = group_by_node(user_groups[last_user_index]['info'])
        assert kwargs['message'] == message

    @mock.patch('website.mails.execute_email_send')
    def test_send_users_email_ignores_disabled_users(self, mock_send_mail):
        send_type = 'email_transactional'
        d = factories.NotificationDigestFactory(
            send_type=send_type,
            event='comment_replies',
            timestamp=timezone.now(),
            message='Hello',
            node_lineage=[factories.ProjectFactory()._id]
        )
        d.save()

        user_groups = list(get_users_emails(send_type))
        last_user_index = len(user_groups) - 1

        user = OSFUser.load(user_groups[last_user_index]['user_id'])
        user.is_disabled = True
        user.save()

        send_users_email(send_type)
        assert not mock_send_mail.called

    def test_remove_sent_digest_notifications(self):
        d = factories.NotificationDigestFactory(
            event='comment_replies',
            timestamp=timezone.now(),
            message='Hello',
            node_lineage=[factories.ProjectFactory()._id]
        )
        digest_id = d._id
        remove_notifications(email_notification_ids=[digest_id])
        with pytest.raises(NotificationDigest.DoesNotExist):
            NotificationDigest.objects.get(_id=digest_id)

class TestNotificationsReviews(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.provider = factories.PreprintProviderFactory(_id='engrxiv')
        self.preprint = factories.PreprintFactory(provider=self.provider)
        self.user = factories.UserFactory()
        self.sender = factories.UserFactory()
        self.context_info = {
            'email_sender': self.sender,
            'domain': 'osf.io',
            'reviewable': self.preprint,
            'workflow': 'pre-moderation',
            'provider_contact_email': settings.OSF_CONTACT_EMAIL,
            'provider_support_email': settings.OSF_SUPPORT_EMAIL,
        }
        self.action = factories.ReviewActionFactory()
        factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'global_comments',
            user=self.user,
            event_name='global_comments'
        ).add_user_to_subscription(self.user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'global_file_updated',
            user=self.user,
            event_name='global_file_updated'
        ).add_user_to_subscription(self.user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'global_reviews',
            user=self.user,
            event_name='global_reviews'
        ).add_user_to_subscription(self.user, 'email_transactional')

    def test_reviews_base_notification(self):
        contributor_subscriptions = list(utils.get_all_user_subscriptions(self.user))
        event_types = [sub.event_name for sub in contributor_subscriptions]
        assert 'global_reviews' in event_types

    @mock.patch('website.mails.mails.execute_email_send')
    def test_reviews_submit_notification(self, mock_send_email):
        listeners.reviews_submit_notification(self, context=self.context_info, recipients=[self.sender, self.user])
        assert mock_send_email.called

    @mock.patch('website.notifications.emails.notify_global_event')
    def test_reviews_notification(self, mock_notify):
        listeners.reviews_notification(self, creator=self.sender, context=self.context_info, action=self.action, template='test.html.mako')
        assert mock_notify.called


class QuerySetMatcher:
    def __init__(self, some_obj):
        self.some_obj = some_obj

    def __eq__(self, other):
        return list(self.some_obj) == list(other)


class TestNotificationsReviewsModerator(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.provider = factories.PreprintProviderFactory(_id='engrxiv')
        self.preprint = factories.PreprintFactory(provider=self.provider)
        self.submitter = factories.UserFactory()
        self.moderator_transacitonal = factories.UserFactory()
        self.moderator_digest= factories.UserFactory()

        self.context_info_submission = {
            'referrer': self.submitter,
            'domain': 'osf.io',
            'reviewable': self.preprint,
            'workflow': 'pre-moderation',
            'provider_contact_email': settings.OSF_CONTACT_EMAIL,
            'provider_support_email': settings.OSF_SUPPORT_EMAIL,
        }

        self.context_info_request = {
            'requester': self.submitter,
            'domain': 'osf.io',
            'reviewable': self.preprint,
            'workflow': 'pre-moderation',
            'provider_contact_email': settings.OSF_CONTACT_EMAIL,
            'provider_support_email': settings.OSF_SUPPORT_EMAIL,
        }

        self.action = factories.ReviewActionFactory()
        self.subscription = NotificationSubscription.load(self.provider._id+'_new_pending_submissions')
        self.subscription.add_user_to_subscription(self.moderator_transacitonal, 'email_transactional')
        self.subscription.add_user_to_subscription(self.moderator_digest, 'email_digest')

    @mock.patch('website.notifications.emails.store_emails')
    def test_reviews_submit_notification(self, mock_store):
        time_now = timezone.now()

        preprint = self.context_info_submission['reviewable']
        provider = preprint.provider

        self.context_info_submission['message'] = f'submitted {preprint.title}.'
        self.context_info_submission['profile_image_url'] = get_profile_image_url(self.context_info_submission['referrer'])
        self.context_info_submission['reviews_submission_url'] = f'{settings.DOMAIN}reviews/preprints/{provider._id}/{preprint._id}'
        listeners.reviews_submit_notification_moderators(self, time_now, self.context_info_submission)
        subscription = NotificationSubscription.load(self.provider._id + '_new_pending_submissions')
        digest_subscriber_ids = list(subscription.email_digest.all().values_list('guids___id', flat=True))
        instant_subscriber_ids = list(subscription.email_transactional.all().values_list('guids___id', flat=True))

        mock_store.assert_any_call(
            digest_subscriber_ids,
            'email_digest',
            'new_pending_submissions',
            self.context_info_submission['referrer'],
            self.context_info_submission['reviewable'],
            time_now,
            abstract_provider=self.context_info_submission['reviewable'].provider,
            **self.context_info_submission
        )

        mock_store.assert_any_call(
            instant_subscriber_ids,
            'email_transactional',
            'new_pending_submissions',
            self.context_info_submission['referrer'],
            self.context_info_submission['reviewable'],
            time_now,
            abstract_provider=self.context_info_request['reviewable'].provider,
            **self.context_info_submission
        )

    @mock.patch('website.notifications.emails.store_emails')
    def test_reviews_request_notification(self, mock_store):
        time_now = timezone.now()
        self.context_info_request['message'] = 'has requested withdrawal of {} "{}".'.format(self.context_info_request['reviewable'].provider.preprint_word,
                                                                                                 self.context_info_request['reviewable'].title)
        self.context_info_request['profile_image_url'] = get_profile_image_url(self.context_info_request['requester'])
        self.context_info_request['reviews_submission_url'] = '{}reviews/preprints/{}/{}'.format(settings.DOMAIN,
                                                                                         self.context_info_request[
                                                                                             'reviewable'].provider._id,
                                                                                         self.context_info_request[
                                                                                             'reviewable']._id)
        listeners.reviews_withdrawal_requests_notification(self, time_now, self.context_info_request)
        subscription = NotificationSubscription.load(self.provider._id + '_new_pending_submissions')
        digest_subscriber_ids = subscription.email_digest.all().values_list('guids___id', flat=True)
        instant_subscriber_ids = subscription.email_transactional.all().values_list('guids___id', flat=True)
        mock_store.assert_any_call(QuerySetMatcher(digest_subscriber_ids),
                                      'email_digest',
                                      'new_pending_submissions',
                                      self.context_info_request['requester'],
                                      self.context_info_request['reviewable'],
                                      time_now,
                                      abstract_provider=self.context_info_request['reviewable'].provider,
                                      **self.context_info_request)

        mock_store.assert_any_call(QuerySetMatcher(instant_subscriber_ids),
                                   'email_transactional',
                                   'new_pending_submissions',
                                   self.context_info_request['requester'],
                                   self.context_info_request['reviewable'],
                                   time_now,
                                   abstract_provider=self.context_info_request['reviewable'].provider,
                                   **self.context_info_request)
