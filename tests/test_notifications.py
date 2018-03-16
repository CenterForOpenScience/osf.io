import collections
import mock
from babel import dates, Locale
from schema import Schema, And, Use, Or
from django.utils import timezone

from nose.tools import *  # noqa PEP8 asserts

from framework.auth import Auth
from osf.models import Comment, NotificationDigest, NotificationSubscription, Guid, OSFUser

from website.notifications.tasks import get_users_emails, send_users_email, group_by_node, remove_notifications
from website.notifications import constants
from website.notifications import emails
from website.notifications import utils
from website import mails, settings
from website.project.signals import contributor_removed, node_deleted
from website.reviews import listeners
from website.util import api_url_for
from website.util import web_url_for
from website import settings

from osf_tests import factories
from tests.base import capture_signals
from tests.base import OsfTestCase, NotificationTestCase



class TestNotificationsModels(OsfTestCase):

    def setUp(self):
        super(TestNotificationsModels, self).setUp()
        # Create project with component
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.parent = factories.ProjectFactory(creator=self.user)
        self.node = factories.NodeFactory(creator=self.user, parent=self.parent)

    def test_has_permission_on_children(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()

        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.save()
        sub_component2 = factories.NodeFactory(parent=node)

        assert_true(
            node.has_permission_on_children(non_admin_user, 'read')
        )

    def test_check_user_has_permission_excludes_deleted_components(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()

        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.is_deleted = True
        sub_component.save()
        sub_component2 = factories.NodeFactory(parent=node)

        assert_false(
            node.has_permission_on_children(non_admin_user,'read')
        )

    def test_check_user_does_not_have_permission_on_private_node_child(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()
        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)

        assert_false(
            node.has_permission_on_children(non_admin_user,'read')
        )

    def test_check_user_child_node_permissions_false_if_no_children(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()
        node = factories.NodeFactory(parent=parent, category='project')

        assert_false(
            node.has_permission_on_children(non_admin_user,'read')
        )

    def test_check_admin_has_permissions_on_private_component(self):
        parent = factories.ProjectFactory()
        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)

        assert_true(
            node.has_permission_on_children(parent.creator,'read')
        )

    def test_check_user_private_node_child_permissions_excludes_pointers(self):
        user = factories.UserFactory()
        parent = factories.ProjectFactory()
        pointed = factories.ProjectFactory(creator=user)
        parent.add_pointer(pointed, Auth(parent.creator))
        parent.save()

        assert_false(
            parent.has_permission_on_children(user,'read')
        )

    def test_new_project_creator_is_subscribed(self):
        user = factories.UserFactory()
        factories.ProjectFactory(creator=user)
        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        assert_equal(len(user_subscriptions), 2)  # subscribed to both file_updated and comments
        assert_in('file_updated', event_types)
        assert_in('comments', event_types)

    def test_new_node_creator_is_not_subscribed(self):
        user = factories.UserFactory()
        factories.NodeFactory(creator=user)
        user_subscriptions = list(utils.get_all_user_subscriptions(user))

        assert_equal(len(user_subscriptions), 0)

    def test_new_project_creator_is_subscribed_with_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comments',
            user=user,
            event_name='global_comments'
        ).add_user_to_subscription(user, 'email_digest')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'none')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_mentions',
            user=user,
            event_name='global_mentions'
        ).add_user_to_subscription(user, 'email_digest')

        node = factories.ProjectFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        file_updated_subscription = NotificationSubscription.objects.get(_id=node._id + '_file_updated')
        comments_subscription = NotificationSubscription.objects.get(_id=node._id + '_comments')

        assert_equal(len(user_subscriptions), 5)  # subscribed to both node and user settings
        assert_in('file_updated', event_types)
        assert_in('comments', event_types)
        assert_in('global_file_updated', event_types)
        assert_in('global_comments', event_types)
        assert_in('global_mentions', event_types)
        assert_equal(file_updated_subscription.none.count(), 1)
        assert_equal(file_updated_subscription.email_transactional.count(), 0)
        assert_equal(comments_subscription.email_digest.count(), 1)
        assert_equal(comments_subscription.email_transactional.count(), 0)

    def test_new_node_creator_is_not_subscribed_with_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comments',
            user=user,
            event_name='global_comments'
        ).add_user_to_subscription(user, 'email_digest')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'none')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comment_replies',
            user=user,
            event_name='global_comment_replies'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_mentions',
            user=user,
            event_name='global_mentions'
        ).add_user_to_subscription(user, 'email_transactional')

        node = factories.NodeFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        assert_equal(len(user_subscriptions), 4)  # subscribed to only user settings
        assert_in('global_file_updated', event_types)
        assert_in('global_comments', event_types)
        assert_in('global_comment_replies', event_types)
        assert_in('global_mentions', event_types)

    def test_subscribe_user_to_global_notfiications(self):
        user = factories.UserFactory()
        utils.subscribe_user_to_global_notifications(user)
        subscription_event_names = list(user.notification_subscriptions.values_list('event_name', flat=True))
        for event_name in constants.USER_SUBSCRIPTIONS_AVAILABLE:
            assert_in(event_name, subscription_event_names)

    def test_new_project_creator_is_subscribed_with_default_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comments',
            user=user,
            event_name='global_comments'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comment_replies',
            user=user,
            event_name='global_comment_replies'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_mentions',
            user=user,
            event_name='global_mentions'
        ).add_user_to_subscription(user, 'email_transactional')

        node = factories.ProjectFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        file_updated_subscription = NotificationSubscription.objects.get(_id=node._id + '_file_updated')
        comments_subscription = NotificationSubscription.objects.get(_id=node._id + '_comments')

        assert_equal(len(user_subscriptions), 6)  # subscribed to both node and user settings
        assert_in('file_updated', event_types)
        assert_in('comments', event_types)
        assert_in('global_file_updated', event_types)
        assert_in('global_comments', event_types)
        assert_in('global_comment_replies', event_types)
        assert_in('global_mentions', event_types)
        assert_equal(file_updated_subscription.email_transactional.count(), 1)
        assert_equal(comments_subscription.email_transactional.count(), 1)

    def test_new_fork_creator_is_subscribed_with_default_global_settings(self):
        user = factories.UserFactory()
        project = factories.ProjectFactory(creator=user)

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comments',
            user=user,
            event_name='global_comments'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_mentions',
            user=user,
            event_name='global_mentions'
        ).add_user_to_subscription(user, 'email_transactional')

        node = factories.ForkFactory(project=project)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        node_file_updated_subscription = NotificationSubscription.objects.get(_id=node._id + '_file_updated')
        node_comments_subscription = NotificationSubscription.objects.get(_id=node._id + '_comments')
        project_file_updated_subscription = NotificationSubscription.objects.get(_id=project._id + '_file_updated')
        project_comments_subscription = NotificationSubscription.objects.get(_id=project._id + '_comments')

        assert_equal(len(user_subscriptions), 7)  # subscribed to project, fork, and user settings
        assert_in('file_updated', event_types)
        assert_in('comments', event_types)
        assert_in('global_file_updated', event_types)
        assert_in('global_comments', event_types)
        assert_in('global_mentions', event_types)
        assert_equal(node_file_updated_subscription.email_transactional.count(), 1)
        assert_equal(node_comments_subscription.email_transactional.count(), 1)
        assert_equal(project_file_updated_subscription.email_transactional.count(), 1)
        assert_equal(project_comments_subscription.email_transactional.count(), 1)

    def test_new_node_creator_is_not_subscribed_with_default_global_settings(self):
        user = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comments',
            user=user,
            event_name='global_comments'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_file_updated',
            user=user,
            event_name='global_file_updated'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_comment_replies',
            user=user,
            event_name='global_comment_replies'
        ).add_user_to_subscription(user, 'email_transactional')

        factories.NotificationSubscriptionFactory(
            _id=user._id + '_' + 'global_mentions',
            user=user,
            event_name='global_mentions'
        ).add_user_to_subscription(user, 'email_transactional')

        node = factories.NodeFactory(creator=user)

        user_subscriptions = list(utils.get_all_user_subscriptions(user))
        event_types = [sub.event_name for sub in user_subscriptions]

        assert_equal(len(user_subscriptions), 4)  # subscribed to only user settings
        assert_in('global_file_updated', event_types)
        assert_in('global_comments', event_types)
        assert_in('global_comment_replies', event_types)
        assert_in('global_mentions', event_types)


    def test_contributor_subscribed_when_added_to_project(self):
        user = factories.UserFactory()
        contributor = factories.UserFactory()
        project = factories.ProjectFactory(creator=user)
        project.add_contributor(contributor=contributor)
        contributor_subscriptions = list(utils.get_all_user_subscriptions(contributor))
        event_types = [sub.event_name for sub in contributor_subscriptions]

        assert_equal(len(contributor_subscriptions), 2)
        assert_in('file_updated', event_types)
        assert_in('comments', event_types)

    def test_contributor_subscribed_when_added_to_component(self):
        user = factories.UserFactory()
        contributor = factories.UserFactory()

        factories.NotificationSubscriptionFactory(
            _id=contributor._id + '_' + 'global_comments',
            user=contributor,
            event_name='global_comments'
        ).add_user_to_subscription(contributor, 'email_transactional')

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
        comments_subscription = NotificationSubscription.objects.get(_id=node._id + '_comments')

        assert_equal(len(contributor_subscriptions), 4)  # subscribed to both node and user settings
        assert_in('file_updated', event_types)
        assert_in('comments', event_types)
        assert_in('global_file_updated', event_types)
        assert_in('global_comments', event_types)
        assert_equal(file_updated_subscription.email_transactional.count(), 1)
        assert_equal(comments_subscription.email_transactional.count(), 1)

    def test_unregistered_contributor_not_subscribed_when_added_to_project(self):
        user = factories.UserFactory()
        unregistered_contributor = factories.UnregUserFactory()
        project = factories.ProjectFactory(creator=user)
        project.add_contributor(contributor=unregistered_contributor)
        contributor_subscriptions = list(utils.get_all_user_subscriptions(unregistered_contributor))
        assert_equal(len(contributor_subscriptions), 0)


class TestSubscriptionView(OsfTestCase):

    def setUp(self):
        super(TestSubscriptionView, self).setUp()
        self.node = factories.NodeFactory()
        self.user = self.node.creator

    def test_create_new_subscription(self):
        payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'email_transactional'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, payload, auth=self.node.creator.auth)

        # check that subscription was created
        event_id = self.node._id + '_' + 'comments'
        s = NotificationSubscription.objects.get(_id=event_id)

        # check that user was added to notification_type field
        assert_equal(payload['id'], s.owner._id)
        assert_equal(payload['event'], s.event_name)
        assert_in(self.node.creator, getattr(s, payload['notification_type']).all())

        # change subscription
        new_payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'email_digest'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, new_payload, auth=self.node.creator.auth)
        s.reload()
        assert_false(self.node.creator in getattr(s, payload['notification_type']).all())
        assert_in(self.node.creator, getattr(s, new_payload['notification_type']).all())

    def test_adopt_parent_subscription_default(self):
        payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'adopt_parent'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, payload, auth=self.node.creator.auth)
        event_id = self.node._id + '_' + 'comments'
        # confirm subscription was created because parent had default subscription
        s = NotificationSubscription.objects.filter(_id=event_id).count()
        assert_equal(0, s)

    def test_change_subscription_to_adopt_parent_subscription_removes_user(self):
        payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'email_transactional'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, payload, auth=self.node.creator.auth)

        # check that subscription was created
        event_id = self.node._id + '_' + 'comments'
        s = NotificationSubscription.objects.get(_id=event_id)

        # change subscription to adopt_parent
        new_payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'adopt_parent'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, new_payload, auth=self.node.creator.auth)
        s.reload()

        # assert that user is removed from the subscription entirely
        for n in constants.NOTIFICATION_TYPES:
            assert_false(self.node.creator in getattr(s, n).all())

    def test_configure_subscription_adds_node_id_to_notifications_configured(self):
        project = factories.ProjectFactory(creator=self.user)
        assert_false(project._id in self.user.notifications_configured)
        payload = {
            'id': project._id,
            'event': 'comments',
            'notification_type': 'email_digest'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, payload, auth=project.creator.auth)

        self.user.reload()

        assert_true(project._id in self.user.notifications_configured)


class TestRemoveContributor(OsfTestCase):

    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.project = factories.ProjectFactory()
        self.contributor = factories.UserFactory()
        self.project.add_contributor(contributor=self.contributor, permissions=['read'])
        self.project.save()

        self.subscription = NotificationSubscription.objects.get(
            node=self.project,
            _id=self.project._id + '_comments'
        )

        self.node = factories.NodeFactory(parent=self.project)
        self.node.add_contributor(contributor=self.project.creator, permissions=['read', 'write', 'admin'])
        self.node.save()

        self.node_subscription = NotificationSubscription.objects.get(
            _id=self.node._id + '_comments',
            node=self.node
        )
        self.node_subscription.add_user_to_subscription(self.node.creator, 'email_transactional')

    def test_removed_non_admin_contributor_is_removed_from_subscriptions(self):
        assert_in(self.contributor, self.subscription.email_transactional.all())
        self.project.remove_contributor(self.contributor, auth=Auth(self.project.creator))
        assert_not_in(self.contributor, self.project.contributors.all())
        self.subscription.reload()
        assert_not_in(self.contributor, self.subscription.email_transactional.all())

    def test_removed_non_parent_admin_contributor_is_removed_from_subscriptions(self):
        assert_in(self.node.creator, self.node_subscription.email_transactional.all())
        self.node.remove_contributor(self.node.creator, auth=Auth(self.node.creator))
        assert_not_in(self.node.creator, self.node.contributors.all())
        self.node_subscription.reload()
        assert_not_in(self.node.creator, self.node_subscription.email_transactional.all())

    def test_removed_contributor_admin_on_parent_not_removed_from_node_subscription(self):
        # Admin on parent project is removed as a contributor on a component. Check
        #     that admin is not removed from component subscriptions, as the admin
        #     now has read-only access.
        assert_in(self.project.creator, self.node_subscription.email_transactional.all())
        self.node.remove_contributor(self.project.creator, auth=Auth(self.project.creator))
        assert_not_in(self.project.creator, self.node.contributors.all())
        assert_in(self.project.creator, self.node_subscription.email_transactional.all())

    def test_remove_contributor_signal_called_when_contributor_is_removed(self):
        with capture_signals() as mock_signals:
            self.project.remove_contributor(self.contributor, auth=Auth(self.project.creator))
        assert_equal(mock_signals.signals_sent(), set([contributor_removed]))


class TestRemoveNodeSignal(OsfTestCase):

    def test_node_subscriptions_and_backrefs_removed_when_node_is_deleted(self):
        project = factories.ProjectFactory()

        s = NotificationSubscription.objects.filter(email_transactional=project.creator)
        assert_equal(s.count(), 2)

        with capture_signals() as mock_signals:
            project.remove_node(auth=Auth(project.creator))
        assert_true(project.is_deleted)
        assert_equal(mock_signals.signals_sent(), set([node_deleted]))

        s = NotificationSubscription.objects.filter(email_transactional=project.creator)
        assert_equal(s.count(), 0)

        with assert_raises(NotificationSubscription.DoesNotExist):
            NotificationSubscription.objects.get(node=project)


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
        (item for item in data if item == sub_data).next()
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
            'id': Use(type(project._id), error="node_id{}".format(level)),
            'title': Use(type(project.title), error="node_title{}".format(level)),
            'url': Use(type(project.url), error="node_{}".format(level))
        },
        'kind': And(str, Use(lambda s: s in ('node', 'folder'),
                             error="kind didn't match node or folder {}".format(level))),
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
            'title': And(Use(str, error="event_title{} not a string".format(level)),
                         Use(lambda s: s in constants.NOTIFICATION_TYPES,
                             error="event_title{} not in list".format(level))),
            'description': And(Use(str, error="event_desc{} not a string".format(level)),
                               Use(lambda s: s in constants.NODE_SUBSCRIPTIONS_AVAILABLE,
                                   error="event_desc{} not in list".format(level))),
            'notificationType': And(str, Or('adopt_parent', lambda s: s in constants.NOTIFICATION_TYPES)),
            'parent_notification_type': Or(None, 'adopt_parent', lambda s: s in constants.NOTIFICATION_TYPES)
        },
        'kind': 'event',
        'children': And(list, lambda l: len(l) == 0)
    }


class TestNotificationUtils(OsfTestCase):

    def setUp(self):
        super(TestNotificationUtils, self).setUp()
        self.user = factories.UserFactory()
        self.project = factories.ProjectFactory(creator=self.user)

        self.project_subscription = NotificationSubscription.objects.get(
            node=self.project,
            _id=self.project._id + '_comments',
            event_name='comments'
        )

        self.user.notifications_configured[self.project._id] = True
        self.user.save()

        self.node = factories.NodeFactory(parent=self.project, creator=self.user)

        self.node_comments_subscription = factories.NotificationSubscriptionFactory(
            _id=self.node._id + '_' + 'comments',
            node=self.node,
            event_name='comments'
        )
        self.node_comments_subscription.save()
        self.node_comments_subscription.email_transactional.add(self.user)
        self.node_comments_subscription.save()

        self.node_subscription = list(NotificationSubscription.objects.filter(node=self.node))

        self.user_subscription = [factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'comment_replies',
            user=self.user,
            event_name='comment_replies'
        ),
        factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'global_comment',
            user=self.user,
            event_name='global_comment'
        ),
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
        assert_equal(key, 'xyz_comments')

    def test_from_subscription_key(self):
        parsed_key = utils.from_subscription_key('xyz_comment_replies')
        assert_equal(parsed_key, {
            'uid': 'xyz',
            'event': 'comment_replies'
        })

    def test_get_all_user_subscriptions(self):
        user_subscriptions = list(utils.get_all_user_subscriptions(self.user))
        assert_in(self.project_subscription, user_subscriptions)
        assert_in(self.node_comments_subscription, user_subscriptions)
        for x in self.user_subscription:
            assert_in(x, user_subscriptions)
        assert_equal(len(user_subscriptions), 6)

    def test_get_all_node_subscriptions_given_user_subscriptions(self):
        user_subscriptions = utils.get_all_user_subscriptions(self.user)
        node_subscription_ids = [x._id for x in utils.get_all_node_subscriptions(self.user, self.node,
                                                                          user_subscriptions=user_subscriptions)]
        expected_node_subscription_ids = [x._id for x in self.node_subscription]
        assert_items_equal(node_subscription_ids, expected_node_subscription_ids)

    def test_get_all_node_subscriptions_given_user_and_node(self):
        node_subscription_ids = [x._id for x in utils.get_all_node_subscriptions(self.user, self.node)]
        expected_node_subscription_ids = [x._id for x in self.node_subscription]
        assert_items_equal(node_subscription_ids, expected_node_subscription_ids)

    def test_get_configured_project_ids_does_not_return_user_or_node_ids(self):
        configured_nodes = utils.get_configured_projects(self.user)
        configured_ids = [n._id for n in configured_nodes]
        # No duplicates!
        assert_equal(len(configured_nodes), 1)

        assert_in(self.project._id, configured_ids)
        assert_not_in(self.node._id, configured_ids)
        assert_not_in(self.user._id, configured_ids)

    def test_get_configured_project_ids_excludes_deleted_projects(self):
        project = factories.ProjectFactory()
        project.is_deleted = True
        project.save()
        assert_not_in(project, utils.get_configured_projects(self.user))

    def test_get_configured_project_ids_excludes_node_with_project_category(self):
        node = factories.NodeFactory(parent=self.project, category='project')
        assert_not_in(node, utils.get_configured_projects(self.user))

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
        assert_in(private_project, configured_project_nodes)

    def test_get_configured_project_ids_excludes_private_projects_if_no_subscriptions_on_node(self):
        user = factories.UserFactory()

        private_project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=private_project)
        node.add_contributor(user)

        utils.remove_contributor_from_subscriptions(node, user)

        configured_project_nodes = utils.get_configured_projects(user)
        assert_not_in(private_project, configured_project_nodes)

    def test_get_parent_notification_type(self):
        nt = utils.get_parent_notification_type(self.node, 'comments', self.user)
        assert_equal(nt, 'email_transactional')

    def test_get_parent_notification_type_no_parent_subscriptions(self):
        node = factories.NodeFactory()
        nt = utils.get_parent_notification_type(node._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_get_parent_notification_type_no_parent(self):
        project = factories.ProjectFactory()
        nt = utils.get_parent_notification_type(project._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_get_parent_notification_type_handles_user_id(self):
        nt = utils.get_parent_notification_type(self.user._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_format_data_project_settings(self):
        data = utils.format_data(self.user, [self.project])
        parent_event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': []
        }
        child_event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': []
        }
        expected_new = [['event'], 'event']
        schema = subscription_schema(self.project, expected_new)
        assert schema.validate(data)
        assert has(data, parent_event)
        assert has(data, child_event)

    def test_format_data_node_settings(self):
        data = utils.format_data(self.user, [self.node])
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': []
        }
        schema = subscription_schema(self.project, ['event'])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_includes_admin_view_only_component_subscriptions(self):
        # Test private components in which parent project admins are not contributors still appear in their
        # notifications settings.
        node = factories.NodeFactory(parent=self.project)
        data = utils.format_data(self.user, [self.project])
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'adopt_parent',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': [],
        }
        schema = subscription_schema(self.project, ['event', ['event'], ['event']])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_data_excludes_pointers(self):
        project = factories.ProjectFactory()
        pointed = factories.ProjectFactory()
        project.add_pointer(pointed, Auth(project.creator))
        project.creator.notifications_configured[project._id] = True
        project.creator.save()
        configured_project_nodes = utils.get_configured_projects(project.creator)
        data = utils.format_data(project.creator, configured_project_nodes)
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': [],
        }
        schema = subscription_schema(self.project, ['event'])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_data_user_subscriptions_includes_private_parent_if_configured_children(self):
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
        data = utils.format_data(node.creator, configured_project_nodes)
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': [],
        }
        schema = subscription_schema(self.project, ['event', ['event']])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_data_user_subscriptions_if_children_points_to_parent(self):
        private_project = factories.ProjectFactory(creator=self.user)
        node = factories.NodeFactory(parent=private_project, creator=self.user)
        node.add_pointer(private_project, Auth(self.user))
        node.save()
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
        data = utils.format_data(node.creator, configured_project_nodes)
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': [],
        }
        schema = subscription_schema(self.project, ['event', ['event']])
        assert schema.validate(data)
        assert has(data, event)

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
                    'title': 'global_comment_replies',
                    'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['global_comment_replies'],
                    'notificationType': 'email_transactional',
                    'parent_notification_type': None
                },
                'kind': 'event',
                'children': []
            }, {
                'event': {
                    'title': 'global_mentions',
                    'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['global_mentions'],
                    'notificationType': 'email_transactional',
                    'parent_notification_type': None
                },
                'kind': 'event',
                'children': []
            }, {
                'event': {
                    'title': 'global_comments',
                    'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['global_comments'],
                    'notificationType': 'email_transactional',
                    'parent_notification_type': None
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
        assert_items_equal(data, expected)

    def test_get_global_notification_type(self):
        notification_type = utils.get_global_notification_type(self.user_subscription[1] ,self.user)
        assert_equal('email_transactional', notification_type)

    def test_check_if_all_global_subscriptions_are_none_false(self):
        all_global_subscriptions_none = utils.check_if_all_global_subscriptions_are_none(self.user)
        assert_false(all_global_subscriptions_none)

    def test_check_if_all_global_subscriptions_are_none_true(self):
        for x in self.user_subscription:
            x.none.add(self.user)
            x.email_transactional.remove(self.user)
        for x in self.user_subscription:
            x.save()
        all_global_subscriptions_none = utils.check_if_all_global_subscriptions_are_none(self.user)
        assert_true(all_global_subscriptions_none)

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
        assert_equal(data, expected)

    def test_serialize_user_level_event(self):
        user_subscriptions = [x for x in utils.get_all_user_subscriptions(self.user)]
        user_subscription = None
        for subscription in user_subscriptions:
            if 'global_comment_replies' in getattr(subscription, 'event_name'):
                user_subscription = subscription
        data = utils.serialize_event(self.user, event_description='global_comment_replies',
                                     subscription=user_subscription)
        expected = {
            'event': {
                'title': 'global_comment_replies',
                'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['global_comment_replies'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': []
        }
        assert_equal(data, expected)

    def test_serialize_node_level_event(self):
        node_subscriptions = [x for x in utils.get_all_node_subscriptions(self.user, self.node)]
        data = utils.serialize_event(user=self.user, event_description='comments',
                                     subscription=node_subscriptions[0], node=self.node)
        expected = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': [],
        }
        assert_equal(data, expected)

    def test_serialize_node_level_event_that_adopts_parent_settings(self):
        user = factories.UserFactory()
        self.project.add_contributor(contributor=user, permissions=['read'])
        self.project.save()
        self.node.add_contributor(contributor=user, permissions=['read'])
        self.node.save()

        # set up how it was in original test - remove existing subscriptions
        utils.remove_contributor_from_subscriptions(self.node, user)

        node_subscriptions = utils.get_all_node_subscriptions(user, self.node)
        data = utils.serialize_event(user=user, event_description='comments',
                                     subscription=node_subscriptions, node=self.node)
        expected = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'adopt_parent',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': [],
        }
        assert_equal(data, expected)


class TestNotificationsDict(OsfTestCase):
    def test_notifications_dict_add_message_returns_proper_format(self):
        d = utils.NotificationsDict()
        message = {
            'message': 'Freddie commented on your project',
            'timestamp': timezone.now()
        }
        message2 = {
            'message': 'Mercury commented on your component',
            'timestamp': timezone.now()
        }

        d.add_message(['project'], message)
        d.add_message(['project', 'node'], message2)

        expected = {
            'messages': [],
            'children': collections.defaultdict(
                utils.NotificationsDict, {
                    'project': {
                        'messages': [message],
                        'children': collections.defaultdict(utils.NotificationsDict, {
                            'node': {
                                'messages': [message2],
                                'children': collections.defaultdict(utils.NotificationsDict, {})
                            }
                        })
                    }
                }
            )}
        assert_equal(d, expected)


class TestCompileSubscriptions(NotificationTestCase):
    def setUp(self):
        super(TestCompileSubscriptions, self).setUp()
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
            node.add_contributor(self.user_2, permissions='admin')
        self.base_project.add_contributor(self.user_3, permissions='write')
        self.shared_node.add_contributor(self.user_3, permissions='write')
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
        assert_equal({'email_transactional': [], 'none': [], 'email_digest': []}, result)

    def test_no_subscribers(self):
        node = factories.NodeFactory()
        node_sub = factories.NotificationSubscriptionFactory(
            _id=node._id + '_file_updated',
            node=node,
            event_name='file_updated'
        )
        node_sub.save()
        result = emails.compile_subscriptions(node, 'file_updated')
        assert_equal({'email_transactional': [], 'none': [], 'email_digest': []}, result)

    def test_creator_subbed_parent(self):
        # Basic sub check
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.base_project, 'file_updated')
        assert_equal({'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []}, result)

    def test_creator_subbed_to_parent_from_child(self):
        # checks the parent sub is the one to appear without a child sub
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert_equal({'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []}, result)

    def test_creator_subbed_to_both_from_child(self):
        # checks that only one sub is in the list.
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        self.shared_sub.email_transactional.add(self.user_1)
        self.shared_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert_equal({'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []}, result)

    def test_creator_diff_subs_to_both_from_child(self):
        # Check that the child node sub overrides the parent node sub
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        self.shared_sub.none.add(self.user_1)
        self.shared_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert_equal({'email_transactional': [], 'none': [self.user_1._id], 'email_digest': []}, result)

    def test_user_wo_permission_on_child_node_not_listed(self):
        # Tests to see if a user without permission gets an Email about a node they cannot see.
        self.base_sub.email_transactional.add(self.user_3)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.private_node, 'file_updated')
        assert_equal({'email_transactional': [], 'none': [], 'email_digest': []}, result)

    def test_several_nodes_deep(self):
        self.base_sub.email_transactional.add(self.user_1)
        self.base_sub.save()
        node2 = factories.NodeFactory(parent=self.shared_node)
        node3 = factories.NodeFactory(parent=node2)
        node4 = factories.NodeFactory(parent=node3)
        node5 = factories.NodeFactory(parent=node4)
        subs = emails.compile_subscriptions(node5, 'file_updated')
        assert_equal(subs, {'email_transactional': [self.user_1._id], 'email_digest': [], 'none': []})

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
        assert_equal(subs, {'email_transactional': [], 'email_digest': [self.user_1._id], 'none': []})


class TestMoveSubscription(NotificationTestCase):
    def setUp(self):
        super(TestMoveSubscription, self).setUp()
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
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        subbed, removed = utils.separate_users(
            self.private_node, [self.user_2._id, self.user_3._id, self.user_4._id]
        )
        assert_equal([self.user_2._id, self.user_3._id], subbed)
        assert_equal([self.user_4._id], removed)

    def test_event_subs_same(self):
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        assert_equal({'email_transactional': [self.user_4._id], 'email_digest': [], 'none': []}, results)

    def test_event_nodes_same(self):
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.project)
        assert_equal({'email_transactional': [], 'email_digest': [], 'none': []}, results)

    def test_move_sub(self):
        # Tests old sub is replaced with new sub.
        utils.move_subscription(self.blank, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        self.file_sub.reload()
        assert_equal('abc42_file_updated', self.file_sub.event_name)
        assert_equal(self.private_node, self.file_sub.owner)
        assert_equal(self.private_node._id + '_abc42_file_updated', self.file_sub._id)

    def test_move_sub_with_none(self):
        # Attempt to reproduce an error that is seen when moving files
        self.project.add_contributor(self.user_2, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.file_sub.none.add(self.user_2)
        self.file_sub.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        assert_equal({'email_transactional': [], 'email_digest': [], 'none': [self.user_2._id]}, results)

    def test_remove_one_user(self):
        # One user doesn't have permissions on the node the sub is moved to. Should be listed.
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        assert_equal({'email_transactional': [self.user_4._id], 'email_digest': [], 'none': []}, results)

    def test_remove_one_user_warn_another(self):
        # Two users do not have permissions on new node, but one has a project sub. Both should be listed.
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.save()
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.sub.email_digest.add(self.user_3)
        self.sub.save()
        self.file_sub.email_transactional.add(self.user_2, self.user_4)

        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        utils.move_subscription(results, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert_equal({'email_transactional': [self.user_4._id], 'email_digest': [self.user_3._id], 'none': []}, results)
        assert_true(self.sub.email_digest.filter(id=self.user_3.id).exists())  # Is not removed from the project subscription.

    def test_warn_user(self):
        # One user with a project sub does not have permission on new node. User should be listed.
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.save()
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.sub.email_digest.add(self.user_3)
        self.sub.save()
        self.file_sub.email_transactional.add(self.user_2)
        results = utils.users_to_remove('xyz42_file_updated', self.project, self.private_node)
        utils.move_subscription(results, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert_equal({'email_transactional': [], 'email_digest': [self.user_3._id], 'none': []}, results)
        assert_in(self.user_3, self.sub.email_digest.all())  # Is not removed from the project subscription.

    def test_user_node_subbed_and_not_removed(self):
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        self.sub.email_digest.add(self.user_3)
        self.sub.save()
        utils.move_subscription(self.blank, 'xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert_false(self.file_sub.email_digest.filter().exists())

    # Regression test for commit ea15186
    def test_garrulous_event_name(self):
        self.file_sub.email_transactional.add(self.user_2, self.user_3, self.user_4)
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        results = utils.users_to_remove('complicated/path_to/some/file/ASDFASDF.txt_file_updated', self.project, self.private_node)
        assert_equal({'email_transactional': [], 'email_digest': [], 'none': []}, results)

class TestSendEmails(NotificationTestCase):
    def setUp(self):
        super(TestSendEmails, self).setUp()
        self.user = factories.AuthUserFactory()
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_' + 'comments',
            node=self.project,
            event_name='comments'
        )
        self.project_subscription.save()
        self.project_subscription.email_transactional.add(self.project.creator)
        self.project_subscription.save()

        self.node = factories.NodeFactory(parent=self.project)
        self.node_subscription = factories.NotificationSubscriptionFactory(
            _id=self.node._id + '_comments',
            node=self.node,
            event_name='comments'
        )
        self.node_subscription.save()
        self.user_subscription = factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'global_comment_replies',
            node=self.node,
            event_name='global_comment_replies'
        )
        self.user_subscription.email_transactional.add(self.user)
        self.user_subscription.save()

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_no_subscription(self, mock_store):
        node = factories.ProjectFactory()
        user = factories.AuthUserFactory()
        emails.notify('comments', user=user, node=node, timestamp=timezone.now())
        assert_false(mock_store.called)

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_no_subscribers(self, mock_store):
        node = factories.NodeFactory()
        node_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_comments',
            node=node,
            event_name='comments'
        )
        node_subscription.save()
        emails.notify('comments', user=self.user, node=node, timestamp=timezone.now())
        assert_false(mock_store.called)

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_sends_with_correct_args(self, mock_store):
        time_now = timezone.now()
        emails.notify('comments', user=self.user, node=self.node, timestamp=time_now)
        assert_true(mock_store.called)
        mock_store.assert_called_with([self.project.creator._id], 'email_transactional', 'comments', self.user,
                                      self.node, time_now)

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_does_not_send_to_exclude(self, mock_store):
        time_now = timezone.now()
        context = {'exclude':[self.project.creator._id]}
        emails.notify('comments', user=self.user, node=self.node, timestamp=time_now, **context)
        assert_equal(mock_store.call_count, 0)

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_does_not_send_to_users_subscribed_to_none(self, mock_store):
        node = factories.NodeFactory()
        user = factories.UserFactory()
        node_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_comments',
            node=node,
            event_name='comments'
        )
        node_subscription.save()
        node_subscription.none.add(user)
        node_subscription.save()
        sent = emails.notify('comments', user=user, node=node, timestamp=timezone.now())
        assert_false(mock_store.called)
        assert_equal(sent, [])

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_mentions_does_not_send_to_mentioned_users_subscribed_to_none(self, mock_store):
        node = factories.NodeFactory()
        user = factories.UserFactory()
        factories.NotificationSubscriptionFactory(
            _id=user._id + '_global_mentions',
            node=self.node,
            event_name='global_mentions'
        ).add_user_to_subscription(user, 'none')
        time_now = timezone.now()
        sent = emails.notify_mentions('global_mentions', user=user, node=node, timestamp=time_now, new_mentions=[user._id])
        assert_false(mock_store.called)
        assert_equal(sent, [])

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_mentions_does_send_to_mentioned_users(self, mock_store):
        user = factories.UserFactory()
        factories.NotificationSubscriptionFactory(
            _id=user._id + '_global_mentions',
            node=self.node,
            event_name='global_mentions'
        ).add_user_to_subscription(user, 'email_transactional')
        node = factories.ProjectFactory(creator=user)
        time_now = timezone.now()
        emails.notify_mentions('global_mentions', user=user, node=node, timestamp=time_now, new_mentions=[user._id])
        assert_true(mock_store.called)
        mock_store.assert_called_with([node.creator._id], 'email_transactional', 'global_mentions', user,
                                      node, time_now, None, new_mentions=[node.creator._id])

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_sends_comment_reply_event_if_comment_is_direct_reply(self, mock_store):
        time_now = timezone.now()
        emails.notify('comments', user=self.user, node=self.node, timestamp=time_now, target_user=self.project.creator)
        mock_store.assert_called_with([self.project.creator._id], 'email_transactional', 'comment_replies',
                                      self.user, self.node, time_now, target_user=self.project.creator)

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_sends_comment_reply_when_target_user_is_subscribed_via_user_settings(self, mock_store):
        time_now = timezone.now()
        emails.notify('global_comment_replies', user=self.project.creator, node=self.node, timestamp=time_now, target_user=self.user)
        mock_store.assert_called_with([self.user._id], 'email_transactional', 'comment_replies',
                                      self.project.creator, self.node, time_now, target_user=self.user)

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_sends_comment_event_if_comment_reply_is_not_direct_reply(self, mock_store):
        user = factories.UserFactory()
        time_now = timezone.now()
        emails.notify('comments', user=user, node=self.node, timestamp=time_now, target_user=user)
        mock_store.assert_called_with([self.project.creator._id], 'email_transactional', 'comments', user,
                                      self.node, time_now, target_user=user)

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_does_not_send_comment_if_they_reply_to_their_own_comment(self, mock_store, mock_send_mail):
        time_now = timezone.now()
        emails.notify('comments', user=self.project.creator, node=self.project, timestamp=time_now,
                      target_user=self.project.creator)
        assert_false(mock_store.called)
        assert_false(mock_send_mail.called)

    @mock.patch('website.notifications.emails.store_emails')
    def test_notify_sends_comment_event_if_comment_reply_is_not_direct_reply_on_component(self, mock_store):
        # Test that comment replies on components that are not direct replies to the subscriber use the
        # "comments" email template.
        user = factories.UserFactory()
        time_now = timezone.now()
        emails.notify('comments', user, self.node, time_now, target_user=user)
        mock_store.assert_called_with([self.project.creator._id], 'email_transactional', 'comments', user,
                                      self.node, time_now, target_user=user)

    def test_check_node_node_none(self):
        subs = emails.check_node(None, 'comments')
        assert_equal(subs, {'email_transactional': [], 'email_digest': [], 'none': []})

    def test_check_node_one(self):
        subs = emails.check_node(self.project, 'comments')
        assert_equal(subs, {'email_transactional': [self.project.creator._id], 'email_digest': [], 'none': []})

    @mock.patch('website.project.views.comment.notify')
    def test_check_user_comment_reply_subscription_if_email_not_sent_to_target_user(self, mock_notify):
        # user subscribed to comment replies
        user = factories.UserFactory()
        user_subscription = factories.NotificationSubscriptionFactory(
            _id=user._id + '_comments',
            user=user,
            event_name='comment_replies'
        )
        user_subscription.email_transactional.add(user)
        user_subscription.save()

        # user is not subscribed to project comment notifications
        project = factories.ProjectFactory()

        # user comments on project
        target = factories.CommentFactory(node=project, user=user)
        content = 'hammer to fall'

        # reply to user (note: notify is called from Comment.create)
        reply = Comment.create(
            auth=Auth(project.creator),
            user=project.creator,
            node=project,
            content=content,
            target=Guid.load(target._id),
            root_target=Guid.load(project._id),
        )
        assert_true(mock_notify.called)
        assert_equal(mock_notify.call_count, 2)

    @mock.patch('website.project.views.comment.notify')
    def test_check_user_comment_reply_only_calls_once(self, mock_notify):
        # user subscribed to comment replies
        user = factories.UserFactory()
        user_subscription = factories.NotificationSubscriptionFactory(
            _id=user._id + '_comments',
            user=user,
            event_name='comment_replies'
        )
        user_subscription.email_transactional.add(user)
        user_subscription.save()

        project = factories.ProjectFactory()

        # user comments on project
        target = factories.CommentFactory(node=project, user=user)
        content = 'P-Hacking: A user guide'

        mock_notify.return_value = [user._id]
        # reply to user (note: notify is called from Comment.create)
        reply = Comment.create(
            auth=Auth(project.creator),
            user=project.creator,
            node=project,
            content=content,
            target=Guid.load(target._id),
            root_target=Guid.load(project._id),
        )
        assert_true(mock_notify.called)
        assert_equal(mock_notify.call_count, 1)

    def test_get_settings_url_for_node(self):
        url = emails.get_settings_url(self.project._id, self.user)
        assert_equal(url, self.project.absolute_url + 'settings/')

    def test_get_settings_url_for_user(self):
        url = emails.get_settings_url(self.user._id, self.user)
        assert_equal(url, web_url_for('user_notifications', _absolute=True))

    def test_get_node_lineage(self):
        node_lineage = emails.get_node_lineage(self.node)
        assert_equal(node_lineage, [self.project._id, self.node._id])

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
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)

    def test_localize_timestamp_empty_timezone(self):
        timestamp = timezone.now()
        self.user.timezone = ''
        self.user.locale = 'en_US'
        self.user.save()
        tz = dates.get_timezone('Etc/UTC')
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)

    def test_localize_timestamp_empty_locale(self):
        timestamp = timezone.now()
        self.user.timezone = 'America/New_York'
        self.user.locale = ''
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale('en')
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)

    def test_localize_timestamp_handles_unicode(self):
        timestamp = timezone.now()
        self.user.timezone = 'Europe/Moscow'
        self.user.locale = 'ru_RU'
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)


class TestSendDigest(OsfTestCase):
    def setUp(self):
        super(TestSendDigest, self).setUp()
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
                u'user_id': self.user_1._id,
                u'info': [{
                    u'message': u'Hello',
                    u'node_lineage': [unicode(self.project._id)],
                    u'_id': d._id
                }]
            },
            {
                u'user_id': self.user_2._id,
                u'info': [{
                    u'message': u'Hello',
                    u'node_lineage': [unicode(self.project._id)],
                    u'_id': d2._id
                }]
            }
        ]

        assert_equal(len(user_groups), 2)
        assert_equal(user_groups, expected)
        digest_ids = [d._id, d2._id, d3._id]
        remove_notifications(email_notification_ids=digest_ids)

    def test_group_notifications_by_user_digest(self):
        send_type = 'email_digest'
        d = factories.NotificationDigestFactory(
            user=self.user_1,
            send_type=send_type,
            event='comment_replies',
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
            send_type='email_transactional',
            timestamp=self.timestamp,
            message='Hello, but this should not appear (this is transactional)',
            node_lineage=[self.project._id]
        )
        d3.save()
        user_groups = list(get_users_emails(send_type))
        expected = [
            {
                u'user_id': unicode(self.user_1._id),
                u'info': [{
                    u'message': u'Hello',
                    u'node_lineage': [unicode(self.project._id)],
                    u'_id': unicode(d._id)
                }]
            },
            {
                u'user_id': unicode(self.user_2._id),
                u'info': [{
                    u'message': u'Hello',
                    u'node_lineage': [unicode(self.project._id)],
                    u'_id': unicode(d2._id)
                }]
            }
        ]

        assert_equal(len(user_groups), 2)
        assert_equal(user_groups, expected)
        digest_ids = [d._id, d2._id, d3._id]
        remove_notifications(email_notification_ids=digest_ids)

    @mock.patch('website.mails.send_mail')
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
        assert_true(mock_send_mail.called)
        assert_equals(mock_send_mail.call_count, len(user_groups))

        last_user_index = len(user_groups) - 1
        user = OSFUser.load(user_groups[last_user_index]['user_id'])

        args, kwargs = mock_send_mail.call_args

        assert_equal(kwargs['to_addr'], user.username)
        assert_equal(kwargs['mimetype'], 'html')
        assert_equal(kwargs['mail'], mails.DIGEST)
        assert_equal(kwargs['name'], user.fullname)
        assert_equal(kwargs['can_change_node_preferences'], True)
        message = group_by_node(user_groups[last_user_index]['info'])
        assert_equal(kwargs['message'], message)

    @mock.patch('website.mails.send_mail')
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
        assert_false(mock_send_mail.called)

    def test_remove_sent_digest_notifications(self):
        d = factories.NotificationDigestFactory(
            event='comment_replies',
            timestamp=timezone.now(),
            message='Hello',
            node_lineage=[factories.ProjectFactory()._id]
        )
        digest_id = d._id
        remove_notifications(email_notification_ids=[digest_id])
        with assert_raises(NotificationDigest.DoesNotExist):
            NotificationDigest.objects.get(_id=digest_id)

class TestNotificationsReviews(OsfTestCase):
    def setUp(self):
        super(TestNotificationsReviews, self).setUp()
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
        assert_in('global_reviews', event_types)

    @mock.patch('website.mails.mails.send_mail')
    def test_reviews_submit_notification(self, mock_send_email):
        listeners.reviews_submit_notification(self, context=self.context_info, recipients=[self.sender, self.user])
        assert_true(mock_send_email.called)

    @mock.patch('website.notifications.emails.notify_global_event')
    def test_reviews_notification(self, mock_notify):
        listeners.reviews_notification(self, creator=self.sender, context=self.context_info, action=self.action, template='test.html.mako')
        assert_true(mock_notify.called)
