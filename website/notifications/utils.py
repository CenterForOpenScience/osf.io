import collections

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.auth import signals
from website.models import Node
from website.notifications import constants
from website.notifications import model


class NotificationsDict(dict):
    def __init__(self):
        super(NotificationsDict, self).__init__()
        self.update(messages=[], children=collections.defaultdict(NotificationsDict))

    def add_message(self, keys, messages):
        """
        :param keys: ordered list of project ids from parent to node (e.g. ['parent._id', 'node._id'])
        :param messages: built email message for an event that occurred on the node
        :return: nested dict with project/component ids as the keys with the message at the appropriate level
        """
        d_to_use = self
        for key in keys:
            d_to_use = d_to_use['children'][key]
        if not isinstance(messages, list):
            messages = [messages]
        d_to_use['messages'].extend(messages)
        return True


def to_subscription_key(uid, event):
    """Build the Subscription primary key for the given guid and event"""
    return str(uid + '_' + event)


def from_subscription_key(key):
    parsed_key = key.split("_", 1)
    return {
        'uid': parsed_key[0],
        'event': parsed_key[1]
    }


@signals.contributor_removed.connect
def remove_contributor_from_subscriptions(contributor, node):
    """ Remove contributor from node subscriptions unless the user is an
        admin on any of node's parent projects.
    """
    if contributor._id not in node.admin_contributor_ids:
        node_subscriptions = get_all_node_subscriptions(contributor, node)
        for subscription in node_subscriptions:
            subscription.remove_user_from_subscription(contributor)

            # node = Node.load(subscription.object_id)

            parent = node.parent_node
            if parent and parent.child_node_subscriptions.get(contributor._id, None) and node._id in parent.child_node_subscriptions.get(contributor._id, None):
                if node._id in parent.child_node_subscriptions[contributor._id]:
                    parent.child_node_subscriptions[contributor._id].remove(node._id)
                    parent.save()


@signals.node_deleted.connect
def remove_subscription(node):
    model.Subscription.remove(Q('owner', 'eq', node))
    parent = node.parent_node

    if parent and parent.child_node_subscriptions:
        for user in parent.child_node_subscriptions.keys():
            if node._id in parent.child_node_subscriptions[user._id]:
                parent.child_node_subscriptions[user._id].remove(node._id)
        parent.save()


def get_configured_projects(user):
    """ Filter all user subscriptions for ones that are on parent projects and return the project ids
    :param user: modular odm User object
    :return: list of project ids for projects with no parent
    """
    configured_projects = []
    user_subscriptions = get_all_user_subscriptions(user)

    for subscription in user_subscriptions:
        # If the user has opted out of emails skip
        if user in subscription.none or not isinstance(subscription.owner, Node):
            continue

        node = subscription.owner

        while node.parent_id and not node.is_deleted:
            node = Node.load(node.parent_id)

        if not node.is_deleted:
            configured_projects.append(node._id)

    return configured_projects


def check_project_subscriptions_are_all_none(user, node):
    node_subscriptions = get_all_node_subscriptions(user, node)
    for s in node_subscriptions:
        if user not in s.none:
            return False
    return True


def get_all_user_subscriptions(user):
    """ Get all Subscription objects that the user is subscribed to"""
    user_subscriptions = []
    for notification_type in constants.NOTIFICATION_TYPES:
        if getattr(user, notification_type, []):
            for subscription in getattr(user, notification_type, []):
                if subscription:
                    user_subscriptions.append(subscription)

    return user_subscriptions


def get_all_node_subscriptions(user, node, user_subscriptions=None):
    """ Get all Subscription objects for a node that the user is subscribed to

    :param user: modular odm User object
    :param node: modular odm Node object
    :param user_subscriptions: all Subscription objects that the user is subscribed to
    :return: list of Subscription objects for a node that the user is subscribed to
    """
    if not user_subscriptions:
        user_subscriptions = get_all_user_subscriptions(user)
    node_subscriptions = []
    for s in user_subscriptions:
        if s.owner == node:
            node_subscriptions.append(s)

    return node_subscriptions


def format_data(user, node_ids):
    """ Format subscriptions data for project settings page
    :param user: modular odm User object
    :param node_ids: list of parent project ids
    :param data: the formatted data
    :return: treebeard-formatted data
    """
    items = []
    user_subscriptions = get_all_user_subscriptions(user)
    for node_id in node_ids:
        children = []
        node = Node.load(node_id)
        can_read = node.has_permission(user, 'read')
        can_read_children = node.can_read_children(user)
        assert node, '{} is not a valid Node.'.format(node_id)

        if not can_read and not can_read_children:
            continue

        # List project/node if user has at least 'read' permissions (contributor or admin viewer) or if
        # user is contributor on a component of the project/node

        if can_read:
            node_subscriptions = get_all_node_subscriptions(user, node, user_subscriptions=user_subscriptions)
            for subscription in constants.NODE_SUBSCRIPTIONS_AVAILABLE:
                children.append(serialize_event(user, subscription, constants.NODE_SUBSCRIPTIONS_AVAILABLE, node_subscriptions, node))

        children.extend(format_data(
            user,
            [
                n._id
                for n in node.nodes
                if n.primary and
                not n.is_deleted
            ]
        ))

        item = {
            'node': {
                'id': node_id,
                'url': node.url if can_read else '',
                'title': node.title if can_read else 'Private Project',
            },
            'children': children,
            'kind': 'folder' if not node.node__parent or not node.parent_node.has_permission(user, 'read') else 'node',
        }

        items.append(item)

    return items


def format_user_subscriptions(user, data):
    """ Format user-level subscriptions (e.g. comment replies across the OSF) for user settings page"""
    user_subscriptions = [s for s in model.Subscription.find(Q('owner', 'eq', user))]
    for subscription in constants.USER_SUBSCRIPTIONS_AVAILABLE:
        event = serialize_event(user, subscription, constants.USER_SUBSCRIPTIONS_AVAILABLE, user_subscriptions)
        data.append(event)

    return data


def serialize_event(user, subscription, subscriptions_available, user_subscriptions, node=None):
    """
    :param user: modular odm User object
    :param subscription: modular odm Subscription object
    :param subscriptions_available: dict of available notification events for a project or user
    :param user_subscriptions: all user subscriptions
    :param node: modular odm Node object
    :return: treebeard-formatted subscription events
    """
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
            for notification_type in constants.NOTIFICATION_TYPES:
                if user in getattr(s, notification_type):
                    event['event']['notificationType'] = notification_type

    if node and node.parent_node and node.parent_node.has_permission(user, 'read'):
        parent_nt = get_parent_notification_type(node._id, subscription, user)
        event['event']['parent_notification_type'] = parent_nt if parent_nt else 'none'
    else:
        event['event']['parent_notification_type'] = None

    return event


def get_parent_notification_type(uid, event, user):
    """
    Given an event on a node (e.g. comment on node 'xyz'), find the user's notification
    type on the parent project for the same event.
    :param str uid: id of event owner (Node or User object)
    :param str event: notification event (e.g. 'comment_replies')
    :param obj user: modular odm User object
    :return: str notification type (e.g. 'email_transactional')
    """
    node = Node.load(uid)
    if node and node.node__parent:
        for p in node.node__parent:
            key = to_subscription_key(p._id, event)
            try:
                subscription = model.Subscription.find_one(Q('_id', 'eq', key))
            except NoResultsFound:
                return get_parent_notification_type(p._id, event, user)

            for notification_type in constants.NOTIFICATION_TYPES:
                if user in getattr(subscription, notification_type):
                    return notification_type
            else:
                return get_parent_notification_type(p._id, event, user)


def format_user_and_project_subscriptions(user):
    """ Format subscriptions data for user settings page. """
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
            'children': format_data(user, get_configured_projects(user))
        }]
