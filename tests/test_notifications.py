from modularodm import Q
from modularodm.exceptions import NoResultsFound
from tests.base import OsfTestCase
from nose.tools import *  # PEP8 asserts
from website.notifications.model import Subscription
from website.notifications.utils import (get_all_user_subscriptions, get_configured_projects,
                                         get_parent_notification_type, format_data, format_user_subscriptions,
                                         format_user_and_project_subscriptions)
from website.util import api_url_for
from website import settings
from tests.factories import ProjectFactory, NodeFactory, UserFactory, SubscriptionFactory


class TestSubscriptionView(OsfTestCase):
    def test_create_new_subscription(self):
        node = NodeFactory()
        payload = {
            'id': node._id,
            'event': 'comments',
            'notification_type': 'email_transactional'
        }
        url = api_url_for('subscribe')
        self.app.post_json(url, payload, auth=node.creator.auth)

        # check that subscription was created
        event_id = node._id + '_' + 'comments'
        s = Subscription.find_one(Q('_id', 'eq', event_id))

        # check that user was added to notification_type field
        assert_equal(payload['id'], s.object_id)
        assert_equal(payload['event'], s.event_name)
        assert_in(node.creator, getattr(s, payload['notification_type']))

        # change subscription
        new_payload = {
            'id': node._id,
            'event': 'comments',
            'notification_type': 'email_digest'
        }
        url = api_url_for('subscribe')
        self.app.post_json(url, new_payload, auth=node.creator.auth)
        s.reload()
        assert_false(node.creator in getattr(s, payload['notification_type']))
        assert_in(node.creator, getattr(s, new_payload['notification_type']))

    def test_adopt_parent_subscription_default(self):
        node = NodeFactory()
        payload = {
            'id': node._id,
            'event': 'comments',
            'notification_type': 'adopt_parent'
        }
        url = api_url_for('subscribe')
        self.app.post_json(url, payload, auth=node.creator.auth)
        event_id = node._id + '_' + 'comments'
        # confirm subscription was not created
        with assert_raises(NoResultsFound):
            Subscription.find_one(Q('_id', 'eq', event_id))

    def test_change_subscription_to_adopt_parent_subscription_removes_user(self):
        node = NodeFactory()
        payload = {
            'id': node._id,
            'event': 'comments',
            'notification_type': 'email_transactional'
        }
        url = api_url_for('subscribe')
        self.app.post_json(url, payload, auth=node.creator.auth)

        # check that subscription was created
        event_id = node._id + '_' + 'comments'
        s = Subscription.find_one(Q('_id', 'eq', event_id))

        # change subscription to adopt_parent
        new_payload = {
            'id': node._id,
            'event': 'comments',
            'notification_type': 'adopt_parent'
        }
        url = api_url_for('subscribe')
        self.app.post_json(url, new_payload, auth=node.creator.auth)
        s.reload()

        # assert that user is removed from the subscription entirely
        for n in settings.NOTIFICATION_TYPES:
            assert_false(node.creator in getattr(s, n))


class TestNotificationUtils(OsfTestCase):
    def setUp(self):
        super(TestNotificationUtils, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project_subscription = SubscriptionFactory(
            _id=self.project._id + '_' + 'comments',
            object_id=self.project._id,
            event_name='comments'
        )
        self.project_subscription.save()
        self.project_subscription.email_transactional.append(self.user)
        self.project_subscription.save()

        self.node = NodeFactory(project=self.project, creator=self.user)
        self.node_subscription = SubscriptionFactory(
            _id=self.node._id + '_' + 'comments',
            object_id=self.node._id,
            event_name='comments'
        )
        self.node_subscription.save()
        self.node_subscription.email_transactional.append(self.user)
        self.node_subscription.save()

        self.user_subscription = SubscriptionFactory(
            _id=self.user._id + '_' + 'comment_replies',
            object_id=self.user._id,
            event_name='comment_replies'
        )
        self.user_subscription.save()
        self.user_subscription.email_transactional.append(self.user)
        self.user_subscription.save()

    def test_get_all_user_subscriptions(self):
        user_subscriptions = get_all_user_subscriptions(self.user)
        assert_in(self.project_subscription, user_subscriptions)
        assert_in(self.node_subscription, user_subscriptions)
        assert_in(self.user_subscription, user_subscriptions)
        assert_equal(len(get_all_user_subscriptions(self.user)), 3)

    def test_get_configured_project_ids_does_not_return_user_or_node_ids(self):
        assert_in(self.project._id, get_configured_projects(self.user))
        assert_not_in(self.node._id, get_configured_projects(self.user))
        assert_not_in(self.user._id, get_configured_projects(self.user))

    def test_get_configured_project_ids_excludes_deleted_projects(self):
        project = ProjectFactory()
        subscription = SubscriptionFactory(
            _id=project._id + '_' + 'comments',
            object_id=project._id
        )
        subscription.email_transactional.append(self.user)
        subscription.save()
        subscription.save()
        project.is_deleted = True
        project.save()
        assert_not_in(self.node._id, get_configured_projects(self.user))

    def test_get_parent_notification_type(self):
        nt = get_parent_notification_type(self.node._id, 'comments', self.user)
        assert_equal(nt, 'email_transactional')

    def test_get_parent_notification_type_no_parent_subscriptions(self):
        node = NodeFactory()
        nt = get_parent_notification_type(node._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_get_parent_notification_type_no_parent(self):
        project = ProjectFactory()
        nt = get_parent_notification_type(project._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_get_parent_notification_type_handles_user_id(self):
        nt = get_parent_notification_type(self.user._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_format_data_project_settings(self):
        data = format_data(self.user, [self.project._id], [])
        expected = [
            {
                'node_id': self.project._id,
                'title': self.project.title,
                'kind': 'folder' if not self.project.node__parent else 'node',
                'nodeUrl': self.project.url,
                'children': [
                    {
                        'title': 'comments',
                        'description': settings.SUBSCRIPTIONS_AVAILABLE['comments'],
                        'kind': 'event',
                        'notificationType': 'email_transactional',
                        'children': [],
                        'parent_notification_type': None
                    },
                    {
                        'node_id': self.node._id,
                        'title': self.node.title,
                        'kind': 'folder' if not self.node.node__parent else 'node',
                        'nodeUrl': self.node.url,
                        'children': [
                            {
                                'title': 'comments',
                                'description': settings.SUBSCRIPTIONS_AVAILABLE['comments'],
                                'kind': 'event',
                                'notificationType': 'email_transactional',
                                'children': [],
                                'parent_notification_type': None
                            }
                        ]
                    }
                ]
            }
        ]
        assert_equal(data, expected)

    def test_format_data_node_settings(self):
        data = format_data(self.user, [self.node._id], [])
        expected = [{
                        'node_id': self.node._id,
                        'title': self.node.title,
                        'kind': 'folder' if not self.node.node__parent else 'node',
                        'nodeUrl': self.node.url,
                        'children': [
                            {
                                'title': 'comments',
                                'description': settings.SUBSCRIPTIONS_AVAILABLE['comments'],
                                'kind': 'event',
                                'notificationType': 'email_transactional',
                                'children': [],
                                'parent_notification_type': None
                            }
                        ]
                    }]
        assert_equal(data, expected)

    def test_format_user_subscriptions(self):
        data = format_user_subscriptions(self.user, [])
        expected = [{
                        'title': 'comment_replies',
                        'description': settings.USER_SUBSCRIPTIONS_AVAILABLE['comment_replies'],
                        'kind': 'event',
                        'notificationType': 'email_transactional',
                        'children': []
                    }]
        assert_equal(data, expected)

    def test_format_data_user_settings(self):
        data = format_user_and_project_subscriptions(self.user)
        expected = [
            {
                'title': 'User Notifications',
                'node_id': self.user._id,
                'kind': 'heading',
                'children': format_user_subscriptions(self.user, [])
            },
            {
                'title': 'Project Notifications',
                'node_id': '',
                'kind': 'heading',
                'children': format_data(self.user, get_configured_projects(self.user), [])
            }]

        assert_equal(data, expected)


class TestNotificationsDict(OsfTestCase):
    def test_notifications_dict_returns_proper_format(self):
        pass


class TestSendEmails(OsfTestCase):
    def test_notify(self):
        pass

    def test_check_parent(self):
        pass

    def test_send_email_transactional(self):
        pass

    def test_send_email_digest_creates_digest_notification(self):
        pass