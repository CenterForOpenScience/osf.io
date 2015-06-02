import collections

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.auth import signals
from website.models import Node
from website.notifications import constants
from website.notifications import model
from website.notifications.model import NotificationSubscription


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


@signals.node_deleted.connect
def remove_subscription(node):
    model.NotificationSubscription.remove(Q('owner', 'eq', node))
    parent = node.parent_node

    if parent and parent.child_node_subscriptions:
        for user_id in parent.child_node_subscriptions:
            if node._id in parent.child_node_subscriptions[user_id]:
                parent.child_node_subscriptions[user_id].remove(node._id)
        parent.save()


def move_file_subscription(old_event_sub, old_node, new_event_sub, new_node):
    if old_event_sub == new_event_sub:
        return []
    old_sub = NotificationSubscription.load(to_subscription_key(old_node, old_event_sub))
    if not old_sub:
        return []
    old_sub.update_fields(_id=to_subscription_key(new_node._id, new_event_sub), event_name=new_event_sub,
                          owner=new_node)
    # Remove users that don't have permission on the new node. Return user ids to send e-mail.
    removed_users = {}
    for notification_type in constants.NOTIFICATION_TYPES:
        if notification_type == 'none':
            continue
        removed_users[notification_type] = []
        for user in getattr(old_sub, notification_type, []):
            if not new_node.has_permission(user, 'read'):
                removed_users[notification_type].append(user)
                old_sub.remove_user_from_subscription(user)
    old_sub.save()
    return removed_users


def get_configured_projects(user):
    """ Filter all user subscriptions for ones that are on parent projects and return the project ids
    :param user: modular odm User object
    :return: list of project ids for projects with no parent
    """
    configured_project_ids = set()
    user_subscriptions = get_all_user_subscriptions(user)

    for subscription in user_subscriptions:
        # If the user has opted out of emails skip
        node = subscription.owner

        if not isinstance(node, Node) or (user in subscription.none and not node.parent_id):
            continue

        while node.parent_id and not node.is_deleted:
            node = Node.load(node.parent_id)

        if not node.is_deleted:
            configured_project_ids.add(node._id)

    return list(configured_project_ids)


def check_project_subscriptions_are_all_none(user, node):
    node_subscriptions = get_all_node_subscriptions(user, node)
    for s in node_subscriptions:
        if user not in s.none:
            return False
    return True


def get_all_user_subscriptions(user):
    """ Get all Subscription objects that the user is subscribed to"""
    for notification_type in constants.NOTIFICATION_TYPES:
        for subscription in getattr(user, notification_type, []):
            yield subscription


def get_all_node_subscriptions(user, node, user_subscriptions=None):
    """ Get all Subscription objects for a node that the user is subscribed to

    :param user: modular odm User object
    :param node: modular odm Node object
    :param user_subscriptions: all Subscription objects that the user is subscribed to
    :return: list of Subscription objects for a node that the user is subscribed to
    """
    if not user_subscriptions:
        user_subscriptions = get_all_user_subscriptions(user)
    for subscription in user_subscriptions:
        if subscription.owner == node:
            yield subscription


def format_data(user, node_ids):
    """ Format subscriptions data for project settings page
    :param user: modular odm User object
    :param node_ids: list of parent project ids
    :return: treebeard-formatted data
    """
    items = []

    for node_id in node_ids:
        node = Node.load(node_id)
        assert node, '{} is not a valid Node.'.format(node_id)

        can_read = node.has_permission(user, 'read')
        can_read_children = node.can_read_children(user)

        if not can_read and not can_read_children:
            continue

        children = []
        # List project/node if user has at least 'read' permissions (contributor or admin viewer) or if
        # user is contributor on a component of the project/node

        if can_read:
            node_sub_available = list(constants.NODE_SUBSCRIPTIONS_AVAILABLE.keys())
            for subscription in get_all_node_subscriptions(user, node):
                try:
                    index = node_sub_available.index(getattr(subscription, 'event_name'))
                    children.append(serialize_event(user, subscription=subscription,
                                                    node=node, event_description=node_sub_available.pop(index)))
                except ValueError:
                    pass  # Currently doesn't handle non-specified subscriptions as in <file>_file_updated
            for node_sub in node_sub_available:
                    children.append(serialize_event(user, node=node, event_description=node_sub))
            children.sort(key=lambda s: s['event']['title'])

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
            'kind': 'folder' if not node.node__parent or not node.parent_node.has_permission(user, 'read') else 'node'
        }

        items.append(item)

    return items


def format_user_subscriptions(user):
    """ Format user-level subscriptions (e.g. comment replies across the OSF) for user settings page"""
    return [
        serialize_event(user, subscription) for subscription in get_all_user_subscriptions(user)
        if getattr(subscription, 'event_name') in constants.USER_SUBSCRIPTIONS_AVAILABLE
    ]


def format_file_subscription(user, node_id, path, provider):
    """Formats a single file event"""
    node = Node.load(node_id)
    addon = node.get_addon(provider)
    file_guid, created = addon.find_or_create_file_guid(path if path.startswith('/') else '/' + path)
    for subscription in get_all_node_subscriptions(user, node):
        if file_guid.guid_url.strip('/') in getattr(subscription, 'event_name'):
            return serialize_event(user, subscription, node)
    return serialize_event(user, node=node, event_description='file_updated')


def serialize_event(user, subscription=None, node=None, event_description=None):
    """
    :param user: modular odm User object
    :param subscription: modular odm Subscription object, use if parsing particular subscription
    :param node: modular odm Node object, use if node is known
    :param event_description: use if specific subscription is known
    :return: treebeard-formatted subscription event
    """
    all_subs = constants.NODE_SUBSCRIPTIONS_AVAILABLE.copy()
    all_subs.update(constants.USER_SUBSCRIPTIONS_AVAILABLE)
    if not event_description:
        event_description = getattr(subscription, 'event_name')
    # Looks at only the types available. Deals with prepending file names.
        for sub_type in all_subs:
            if sub_type in event_description:
                event_type = sub_type
    else:
        event_type = event_description
    if node and node.node__parent:
        notification_type = 'adopt_parent'
    else:
        notification_type = 'null'
    if subscription:
        for n_type in constants.NOTIFICATION_TYPES:
            if user in getattr(subscription, n_type):
                notification_type = n_type
    return {
        'event': {
            'title': event_description,
            'description': all_subs[event_type],
            'notificationType': notification_type,
            'parent_notification_type': get_parent_notification_type(node, event_type, user)
        },
        'kind': 'event',
        'children': []
    }


def get_parent_notification_type(node, event, user):
    """
    Given an event on a node (e.g. comment on node 'xyz'), find the user's notification
    type on the parent project for the same event.
    :param obj node: event owner (Node or User object)
    :param str event: notification event (e.g. 'comment_replies')
    :param obj user: modular odm User object
    :return: str notification type (e.g. 'email_transactional')
    """
    if node and isinstance(node, Node) and node.node__parent and node.parent_node.has_permission(user, 'read'):
        for parent in node.node__parent:
            key = to_subscription_key(parent._id, event)
            try:
                subscription = model.NotificationSubscription.find_one(Q('_id', 'eq', key))
            except NoResultsFound:
                return get_parent_notification_type(parent, event, user)

            for notification_type in constants.NOTIFICATION_TYPES:
                if user in getattr(subscription, notification_type):
                    return notification_type
            else:
                return get_parent_notification_type(parent, event, user)
    else:
        return None


def format_user_and_project_subscriptions(user):
    """ Format subscriptions data for user settings page. """
    return [
        {
            'node': {
                'id': user._id,
                'title': 'User Notifications',
            },
            'kind': 'heading',
            'children': format_user_subscriptions(user)
        },
        {
            'node': {
                'id': '',
                'title': 'Project Notifications',
            },
            'kind': 'heading',
            'children': format_data(user, get_configured_projects(user))
        }]
