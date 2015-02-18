import collections
from framework.auth.signals import contributor_removed, node_deleted
from website.models import Node
from website.notifications.model import Subscription
from website.notifications.constants import SUBSCRIPTIONS_AVAILABLE, NOTIFICATION_TYPES, USER_SUBSCRIPTIONS_AVAILABLE
from modularodm import Q
from modularodm.exceptions import NoResultsFound


class NotificationsDict(dict):
    def __init__(self):
        super(NotificationsDict, self).__init__()
        self.update(messages=[], children=collections.defaultdict(NotificationsDict))

    def add_message(self, keys, messages):
        d_to_use = self
        for key in keys:
            d_to_use = d_to_use['children'][key]
        if not isinstance(messages, list):
            messages = [messages]
        d_to_use['messages'].extend(messages)
        return True


def to_subscription_key(uid, event):
    return str(uid + '_' + event)


def from_subscription_key(key):
    parsed_key = key.split("_", 1)
    return {
        'uid': parsed_key[0],
        'event': parsed_key[1]
    }


@contributor_removed.connect
def remove_contributor_from_subscriptions(contributor, node):
    node_subscriptions = get_all_node_subscriptions(contributor, node)
    for subscription in node_subscriptions:
        subscription.remove_user_from_subscription(contributor)


@node_deleted.connect
def remove_subscription(node):
    Subscription.remove(Q('object_id', 'eq', node._id))


def get_configured_projects(user):
    configured_project_ids = []
    user_subscriptions = get_all_user_subscriptions(user)
    for subscription in user_subscriptions:
        node = Node.load(subscription.object_id)
        if node and node.project_or_component == 'project' and not node.is_deleted and subscription.object_id not in configured_project_ids:
            configured_project_ids.append(subscription.object_id)

    return configured_project_ids


def get_all_user_subscriptions(user):
    user_subscriptions = []
    for notification_type in NOTIFICATION_TYPES:
        if getattr(user, notification_type, []):
            for subscription in getattr(user, notification_type, []):
                if subscription:
                    user_subscriptions.append(subscription)

    return user_subscriptions


def get_all_node_subscriptions(user, node, user_subscriptions=None):
    if not user_subscriptions:
        user_subscriptions = get_all_user_subscriptions(user)
    node_subscriptions = []
    for s in user_subscriptions:
        if s.object_id == node._id:
            node_subscriptions.append(s)

    return node_subscriptions


def format_data(user, node_ids, data, subscriptions_available=SUBSCRIPTIONS_AVAILABLE):
    user_subscriptions = get_all_user_subscriptions(user)
    for idx, node_id in enumerate(node_ids):
        node = Node.load(node_id)
        index = len(data)
        data.append({
            'node': {
                    'id': node_id,
                    'url': node.url,
                    'title': node.title,
                    },
            'kind': 'folder' if not node.node__parent else 'node',
            'children': []
        })

        node_subscriptions = get_all_node_subscriptions(user, node, user_subscriptions=user_subscriptions)
        for subscription in subscriptions_available:
            event = serialize_event(user, subscription, subscriptions_available, node_subscriptions, node)
            data[index]['children'].append(event)

        if node.nodes:
            authorized_nodes = [n for n in node.nodes if user in n.contributors and not n.is_deleted]
            format_data(user, [n._id for n in authorized_nodes], data[index]['children'])

    return data


def format_user_subscriptions(user, data):
    user_subscriptions = [s for s in Subscription.find(Q('object_id', 'eq', user._id))]
    for subscription in USER_SUBSCRIPTIONS_AVAILABLE:
        event = serialize_event(user, subscription, USER_SUBSCRIPTIONS_AVAILABLE, user_subscriptions)
        data.append(event)

    return data


def serialize_event(user, subscription, subscriptions_available, user_subscriptions, node=None):
    event = {
        'event': {
            'title': subscription,
            'description': subscriptions_available[subscription],
            'notificationType': 'adopt_parent' if node and node.node__parent else 'none',
        },
        'kind': 'event',
        'children': []
    }
    for s in user_subscriptions:
        if s.event_name == subscription:
            for notification_type in NOTIFICATION_TYPES:
                if user in getattr(s, notification_type):
                    event['event']['notificationType'] = notification_type

    if node:
        if event['event']['notificationType'] == 'adopt_parent':
            parent_nt = get_parent_notification_type(node._id, subscription, user)
            event['event']['parent_notification_type'] = parent_nt if parent_nt else 'none'
        else:
            event['event']['parent_notification_type'] = None  # only get nt if node = adopt_parent for display purposes

    return event


def get_parent_notification_type(uid, event, user):
    node = Node.load(uid)
    if node and node.node__parent:
        for p in node.node__parent:
            key = to_subscription_key(p._id, event)
            try:
                subscription = Subscription.find_one(Q('_id', 'eq', key))
            except NoResultsFound:
                return get_parent_notification_type(p._id, event, user)

            for notification_type in NOTIFICATION_TYPES:
                if user in getattr(subscription, notification_type):
                    return notification_type
            else:
                return get_parent_notification_type(p._id, event, user)


def format_user_and_project_subscriptions(user):
    return [
        {
            'node': {
                'id': user._id,
                'title': 'User Notifications',
            },
            'kind': 'heading',
            'children': format_user_subscriptions(user, [])
        },
        {
            'node': {
                'id': '',
                'title': 'Project Notifications',
            },
            'kind': 'heading',
            'children': format_data(user, get_configured_projects(user), [])
        }]
