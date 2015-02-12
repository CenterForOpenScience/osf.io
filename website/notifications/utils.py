import collections
from framework.auth.signals import contributor_removed
from website import settings
from website.models import Node
from website.notifications.model import Subscription
from modularodm import Q
from modularodm.exceptions import NoResultsFound


class NotificationsDict(dict):
    def __init__(self):
        super(dict, self).__init__()
        self.update(messages=[], children=collections.defaultdict(NotificationsDict))

    def add_message(self, keys, messages):
        d_to_use = self
        for key in keys:
            d_to_use = d_to_use['children'][key]
        if not isinstance(messages, list):
            messages = [messages]
        d_to_use['messages'].extend(messages)
        return True

@contributor_removed.connect
def remove_contributor_from_subscriptions(contributor, node):
    user_subscriptions = get_all_user_subscriptions(contributor)
    node_subscriptions = []
    for user_subscription in user_subscriptions:
        if user_subscription.object_id == node._id:
            node_subscriptions.append(user_subscription)

    for subscription in node_subscriptions:
        for n in settings.NOTIFICATION_TYPES:
            if contributor in getattr(subscription, n):
                getattr(subscription, n).remove(contributor)
                subscription.save()


def get_configured_projects(user):
    configured_project_ids = []
    user_subscriptions = get_all_user_subscriptions(user)
    for subscription in user_subscriptions:
        try:
            node = Node.load(subscription.object_id)
        except NoResultsFound:
            # handle case where object_id for the subscription is NOT a project, but a user
            pass

        if node and node.project_or_component == 'project' and not node.is_deleted and subscription.object_id not in configured_project_ids:
                configured_project_ids.append(subscription.object_id)

    return configured_project_ids


def get_all_user_subscriptions(user):
    user_subscriptions = []
    for notification_type in settings.NOTIFICATION_TYPES:
        if getattr(user, notification_type, []):
            for subscription in getattr(user, notification_type, []):
                if subscription:
                    user_subscriptions.append(subscription)

    return user_subscriptions


def format_data(user, node_ids, data, subscriptions_available=settings.SUBSCRIPTIONS_AVAILABLE):

    for idx, node_id in enumerate(node_ids):
        node = Node.load(node_id)
        index = len(data)
        data.append({'node_id': node_id,
                     'title': node.title,
                     'kind': 'folder' if not node.node__parent else 'node',
                     'nodeUrl': node.url,
                     'children': []
                    })

        user_subscriptions = get_all_user_subscriptions(user)
        node_subscriptions = []
        for user_subscription in user_subscriptions:
            if user_subscription.object_id == node_id:
                node_subscriptions.append(user_subscription) #xyz_comments

        for s in subscriptions_available:
            event = {
                'title': s,
                'description': subscriptions_available[s],
                'kind': 'event',
                'notificationType': 'none' if not node.node__parent else 'adopt_parent',
                'children': []
            }
            for subscription in node_subscriptions:
                if subscription.event_name == s:
                    for notification_type in settings.NOTIFICATION_TYPES:
                        if user in getattr(subscription, notification_type):
                            event['notificationType'] = notification_type

            if event['notificationType'] == 'adopt_parent':
                event['parent_notification_type'] = get_parent_notification_type(node_id, s, user)
            else:
                event['parent_notification_type'] = None #only get nt if node = adopt_parent for display purposes

            data[index]['children'].append(event)

        if node.nodes:
            authorized_nodes = [n for n in node.nodes if user in n.contributors and not n.is_deleted]
            format_data(user, [n._id for n in authorized_nodes], data[index]['children'])

    return data


def get_parent_notification_type(uid, event, user):
    node = Node.load(uid)
    if node and node.node__parent:
        for p in node.node__parent:
            key = str(p._id + '_' + event)
            try:
                subscription = Subscription.find_one(Q('_id', 'eq', key))
            except NoResultsFound:
                return

            for notification_type in settings.NOTIFICATION_TYPES:
                if user in getattr(subscription, notification_type):
                    return notification_type


def format_user_and_project_subscriptions(user):
    return [
        {
            'title': 'User Notifications',
            'node_id': user._id,
            'kind': 'heading',
            'children': format_user_subscriptions(user, [])
        },
        {
            'title': 'Project Notifications',
            'node_id': '',
            'kind': 'heading',
            'children': format_data(user, get_configured_projects(user), [])
        }]


def format_user_subscriptions(user, data):
    user_subscriptions = [s for s in Subscription.find(Q('object_id', 'eq', user._id))]
    for s in settings.USER_SUBSCRIPTIONS_AVAILABLE:
        event = {
                'title': s,
                'description': settings.USER_SUBSCRIPTIONS_AVAILABLE[s],
                'kind': 'event',
                'notificationType': 'none',
                'children': []
                }
        for subscription in user_subscriptions:
            if subscription.event_name == s:
                for notification_type in settings.NOTIFICATION_TYPES:
                    if user in getattr(subscription, notification_type):
                        event['notificationType'] = notification_type

        data.append(event)

    return data