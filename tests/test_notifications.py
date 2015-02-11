from modularodm import Q
from modularodm.exceptions import NoResultsFound
from tests.base import OsfTestCase
from nose.tools import *  # PEP8 asserts
from website.notifications.model import Subscription
from website.notifications.utils import get_all_user_subscriptions
from website.util import api_url_for
from website import settings
from tests.factories import NodeFactory, UserFactory, SubscriptionFactory


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

        #  check that subscription was created
        event_id = node._id + '_' + 'comments'
        s = Subscription.find_one(Q('_id', 'eq', event_id))

        #  check that user was added to notification_type field
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

        #  check that subscription was created
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
        self.node = NodeFactory()
        self.s = SubscriptionFactory(
            _id=self.node._id + '_' + 'comments'
        )
        self.s.save()
        self.s.email_transactional.append(self.user)
        self.s.save()

    def test_get_all_user_subscriptions(self):
        assert_equal(get_all_user_subscriptions(self.user), [self.s])

    def test_get_all_configured_projects(self):
        pass

    def test_get_parent_notification_type(self):
        pass

    def test_format_data_node_settings(self):
        pass

    def test_format_data_user_settings(self):
        pass


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