from django.contrib.contenttypes.models import ContentType
from rest_framework import status as http_status

from flask import request

from framework import sentry
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from osf.models import AbstractNode, Registration
NOTIFICATION_TYPES = {}
USER_SUBSCRIPTIONS_AVAILABLE = {}
NODE_SUBSCRIPTIONS_AVAILABLE = {}
from website.project.decorators import must_be_valid_project
import collections

from django.apps import apps
from django.db.models import Q

from osf.models import NotificationSubscription
from osf.utils.permissions import READ


class NotificationsDict(dict):
    def __init__(self):
        super().__init__()
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


def find_subscription_type(subscription):
    """Find subscription type string within specific subscription.
     Essentially removes extraneous parts of the string to get the type.
    """
    subs_available = list(USER_SUBSCRIPTIONS_AVAILABLE.keys())
    subs_available.extend(list(NODE_SUBSCRIPTIONS_AVAILABLE.keys()))
    for available in subs_available:
        if available in subscription:
            return available


def to_subscription_key(uid, event):
    """Build the Subscription primary key for the given guid and event"""
    return f'{uid}_{event}'


def from_subscription_key(key):
    parsed_key = key.split('_', 1)
    return {
        'uid': parsed_key[0],
        'event': parsed_key[1]
    }


def users_to_remove(source_event, source_node, new_node):
    """Find users that do not have permissions on new_node.
    :param source_event: such as _file_updated
    :param source_node: Node instance where a subscription currently resides
    :param new_node: Node instance where a sub or new sub will be.
    :return: Dict of notification type lists with user_ids
    """
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    removed_users = {key: [] for key in NOTIFICATION_TYPES}
    if source_node == new_node:
        return removed_users
    old_sub = NotificationSubscription.objects.get(
        subscribed_object=source_node,
        notification_type__name=source_event
    )
    for notification_type in NOTIFICATION_TYPES:
        users = []
        if hasattr(old_sub, notification_type):
            users += list(getattr(old_sub, notification_type).values_list('guids___id', flat=True))
    return removed_users


def move_subscription(remove_users, source_event, source_node, new_event, new_node):
    """Moves subscription from old_node to new_node
    :param remove_users: dictionary of lists of users to remove from the subscription
    :param source_event: A specific guid event <guid>_file_updated
    :param source_node: Instance of Node
    :param new_event: A specific guid event
    :param new_node: Instance of Node
    :return: Returns a NOTIFICATION_TYPES list of removed users without permissions
    """
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    OSFUser = apps.get_model('osf.OSFUser')
    if source_node == new_node:
        return
    old_sub = NotificationSubscription.load(to_subscription_key(source_node._id, source_event))
    if not old_sub:
        return
    elif old_sub:
        old_sub._id = to_subscription_key(new_node._id, new_event)
        old_sub.event_name = new_event
        old_sub.owner = new_node
    new_sub = old_sub
    new_sub.save()
    # Remove users that don't have permission on the new node.
    for notification_type in NOTIFICATION_TYPES:
        if new_sub:
            for user_id in remove_users[notification_type]:
                related_manager = getattr(new_sub, notification_type, None)
                subscriptions = related_manager.all() if related_manager else []
                if user_id in subscriptions:
                    user = OSFUser.load(user_id)
                    new_sub.remove_user_from_subscription(user)


def get_configured_projects(user):
    """Filter all user subscriptions for ones that are on parent projects
     and return the node objects.
    :param user: OSFUser object
    :return: list of node objects for projects with no parent
    """
    configured_projects = set()
    user_subscriptions = get_all_user_subscriptions(user, extra=(
        ~Q(node__type='osf.collection') &
        Q(node__is_deleted=False)
    ))

    for subscription in user_subscriptions:
        # If the user has opted out of emails skip
        node = subscription.owner

        if (
            (subscription.none.filter(id=user.id).exists() and not node.parent_id) or
            node._id not in user.notifications_configured
        ):
            continue

        root = node.root

        if not root.is_deleted:
            configured_projects.add(root)

    return sorted(configured_projects, key=lambda n: n.title.lower())


def check_project_subscriptions_are_all_none(user, node):
    node_subscriptions = NotificationSubscription.objects.filter(
        user=user,
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node).id,
    )
    for s in node_subscriptions:
        if not s.message_frequecy == 'none':
            return False
    return True


def get_all_user_subscriptions(user, extra=None):
    """ Get all Subscription objects that the user is subscribed to"""
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    queryset = NotificationSubscription.objects.filter(
        user=user,
    )
    return queryset.filter(extra) if extra else queryset


def get_all_node_subscriptions(user, node, user_subscriptions=None):
    """ Get all Subscription objects for a node that the user is subscribed to
    :param user: OSFUser object
    :param node: Node object
    :param user_subscriptions: all Subscription objects that the user is subscribed to
    :return: list of Subscription objects for a node that the user is subscribed to
    """
    if not user_subscriptions:
        user_subscriptions = get_all_user_subscriptions(user)
    return user_subscriptions.filter(
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node).id,
    )


def format_data(user, nodes):
    """ Format subscriptions data for project settings page
    :param user: OSFUser object
    :param nodes: list of parent project node objects
    :return: treebeard-formatted data
    """
    items = []

    user_subscriptions = get_all_user_subscriptions(user)
    for node in nodes:
        assert node, f'{node._id} is not a valid Node.'

        can_read = node.has_permission(user, READ)
        can_read_children = node.has_permission_on_children(user, READ)

        if not can_read and not can_read_children:
            continue

        children = node.get_nodes(**{'is_deleted': False, 'is_node_link': False})
        children_tree = []
        # List project/node if user has at least READ permissions (contributor or admin viewer) or if
        # user is contributor on a component of the project/node

        if can_read:
            node_sub_available = list(NODE_SUBSCRIPTIONS_AVAILABLE.keys())
            subscriptions = get_all_node_subscriptions(user, node, user_subscriptions=user_subscriptions).filter(event_name__in=node_sub_available)

            for subscription in subscriptions:
                index = node_sub_available.index(getattr(subscription, 'event_name'))
                children_tree.append(serialize_event(user, subscription=subscription,
                                                node=node, event_description=node_sub_available.pop(index)))
            for node_sub in node_sub_available:
                children_tree.append(serialize_event(user, node=node, event_description=node_sub))
            children_tree.sort(key=lambda s: s['event']['title'])

        children_tree.extend(format_data(user, children))

        item = {
            'node': {
                'id': node._id,
                'url': node.url if can_read else '',
                'title': node.title if can_read else 'Private Project',
            },
            'children': children_tree,
            'kind': 'folder' if not node.parent_node or not node.parent_node.has_permission(user, READ) else 'node',
            'nodeType': node.project_or_component,
            'category': node.category,
            'permissions': {
                'view': can_read,
            },
        }

        items.append(item)

    return items


def format_user_subscriptions(user):
    """ Format user-level subscriptions (e.g. comment replies across the OSF) for user settings page"""
    user_subs_available = list(USER_SUBSCRIPTIONS_AVAILABLE.keys())
    subscriptions = [
        serialize_event(
            user, subscription,
            event_description=user_subs_available.pop(user_subs_available.index(getattr(subscription, 'event_name')))
        )
        for subscription in get_all_user_subscriptions(user)
        if subscription is not None and getattr(subscription, 'event_name') in user_subs_available
    ]
    subscriptions.extend([serialize_event(user, event_description=sub) for sub in user_subs_available])
    return subscriptions


def format_file_subscription(user, node_id, path, provider):
    """Format a single file event"""
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)
    wb_path = path.lstrip('/')
    for subscription in get_all_node_subscriptions(user, node):
        if wb_path in getattr(subscription, 'event_name'):
            return serialize_event(user, subscription, node)
    return serialize_event(user, node=node, event_description='file_updated')

def serialize_event(user, subscription=None, node=None, event_description=None):
    """
    :param user: OSFUser object
    :param subscription: Subscription object, use if parsing particular subscription
    :param node: Node object, use if node is known
    :param event_description: use if specific subscription is known
    :return: treebeard-formatted subscription event
    """
    if not event_description:
        event_description = getattr(subscription, 'event_name')
    # Looks at only the types available. Deals with pre-pending file names.
        for sub_type in {}:
            if sub_type in event_description:
                event_type = sub_type
    else:
        event_type = event_description
    if node and node.parent_node:
        notification_type = 'adopt_parent'
    elif event_type.startswith('global_'):
        notification_type = 'email_transactional'
    else:
        notification_type = 'none'
    if subscription:
        for n_type in {}:
            if getattr(subscription, n_type).filter(id=user.id).exists():
                notification_type = n_type
    return {
        'event': {
            'title': event_description,
            'description': {}[event_type],
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
    :param obj user: OSFUser object
    :return: str notification type (e.g. 'email_transactional')
    """
    AbstractNode = apps.get_model('osf.AbstractNode')
    NotificationSubscriptionLegacy = apps.get_model('osf.NotificationSubscriptionLegacy')

    if node and isinstance(node, AbstractNode) and node.parent_node and node.parent_node.has_permission(user, READ):
        parent = node.parent_node
        key = to_subscription_key(parent._id, event)
        try:
            subscription = NotificationSubscriptionLegacy.objects.get(_id=key)
        except NotificationSubscriptionLegacy.DoesNotExist:
            return get_parent_notification_type(parent, event, user)

        for notification_type in NOTIFICATION_TYPES:
            if getattr(subscription, notification_type).filter(id=user.id).exists():
                return notification_type
        else:
            return get_parent_notification_type(parent, event, user)
    else:
        return None


def get_global_notification_type(global_subscription, user):
    """
    Given a global subscription (e.g. NotificationSubscription object with event_type
    'global_file_updated'), find the user's notification type.
    :param obj global_subscription: NotificationSubscription object
    :param obj user: OSFUser object
    :return: str notification type (e.g. 'email_transactional')
    """
    for notification_type in NOTIFICATION_TYPES:
        # TODO Optimize me
        if getattr(global_subscription, notification_type).filter(id=user.id).exists():
            return notification_type


def check_if_all_global_subscriptions_are_none(user):
    # This function predates comment mentions, which is a global_ notification that cannot be disabled
    # Therefore, an actual check would never return True.
    # If this changes, an optimized query would look something like:
    # not NotificationSubscriptionLegacy.objects.filter(Q(event_name__startswith='global_') & (Q(email_digest=user.pk)|Q(email_transactional=user.pk))).exists()
    return False


def subscribe_user_to_global_notifications(user):
    NotificationSubscriptionLegacy = apps.get_model('osf.NotificationSubscriptionLegacy')
    notification_type = 'email_transactional'
    user_events = USER_SUBSCRIPTIONS_AVAILABLE
    for user_event in user_events:
        user_event_id = to_subscription_key(user._id, user_event)

        # get_or_create saves on creation
        subscription, created = NotificationSubscriptionLegacy.objects.get_or_create(_id=user_event_id, user=user, event_name=user_event)
        subscription.add_user_to_subscription(user, notification_type)
        subscription.save()


class InvalidSubscriptionError:
    pass


def subscribe_user_to_notifications(node, user):
    """ Update the notification settings for the creator or contributors
    :param user: User to subscribe to notifications
    """
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    Preprint = apps.get_model('osf.Preprint')
    DraftRegistration = apps.get_model('osf.DraftRegistration')
    if isinstance(node, Preprint):
        raise InvalidSubscriptionError('Preprints are invalid targets for subscriptions at this time.')

    if isinstance(node, DraftRegistration):
        raise InvalidSubscriptionError('DraftRegistrations are invalid targets for subscriptions at this time.')

    if node.is_collection:
        raise InvalidSubscriptionError('Collections are invalid targets for subscriptions')

    if node.is_deleted:
        raise InvalidSubscriptionError('Deleted Nodes are invalid targets for subscriptions')

    if getattr(node, 'is_registration', False):
        raise InvalidSubscriptionError('Registrations are invalid targets for subscriptions')

    events = NODE_SUBSCRIPTIONS_AVAILABLE

    if user.is_registered:
        for event in events:
            subscription, _ = NotificationSubscription.objects.get_or_create(
                user=user,
                notification_type__name=event
            )


def format_user_and_project_subscriptions(user):
    """ Format subscriptions data for user settings page. """
    return [
        {
            'node': {
                'id': user._id,
                'title': 'Default Notification Settings',
                'help': 'These are default settings for new projects you create ' +
                        'or are added to. Modifying these settings will not ' +
                        'modify settings on existing projects.'
            },
            'kind': 'heading',
            'children': format_user_subscriptions(user)
        },
        {
            'node': {
                'id': '',
                'title': 'Project Notifications',
                'help': 'These are settings for each of your projects. Modifying ' +
                        'these settings will only modify the settings for the selected project.'
            },
            'kind': 'heading',
            'children': format_data(user, get_configured_projects(user))
        }]


@must_be_logged_in
def get_subscriptions(auth):
    return format_user_and_project_subscriptions(auth.user)


@must_be_logged_in
@must_be_valid_project
def get_node_subscriptions(auth, **kwargs):
    node = kwargs.get('node') or kwargs['project']
    return format_data(auth.user, [node])


@must_be_logged_in
def get_file_subscriptions(auth, **kwargs):
    node_id = request.args.get('node_id')
    path = request.args.get('path')
    provider = request.args.get('provider')
    return format_file_subscription(auth.user, node_id, path, provider)


@must_be_logged_in
def configure_subscription(auth):
    user = auth.user
    json_data = request.get_json()
    target_id = json_data.get('id')
    event = json_data.get('event')
    notification_type = json_data.get('notification_type')
    path = json_data.get('path')
    provider = json_data.get('provider')

    if not event or (notification_type not in NOTIFICATION_TYPES and notification_type != 'adopt_parent'):
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_long='Must provide an event and notification type for subscription.')
        )

    node = AbstractNode.load(target_id)
    if 'file_updated' in event and path is not None and provider is not None:
        wb_path = path.lstrip('/')
        event = wb_path + '_file_updated'
    event_id = to_subscription_key(target_id, event)

    if not node:
        # if target_id is not a node it currently must be the current user
        if not target_id == user._id:
            sentry.log_message(
                '{!r} attempted to subscribe to either a bad '
                'id or non-node non-self id, {}'.format(user, target_id)
            )
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)

        if notification_type == 'adopt_parent':
            sentry.log_message(
                f'{user!r} attempted to adopt_parent of a none node id, {target_id}'
            )
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        # owner = user
    else:
        if not node.has_permission(user, READ):
            sentry.log_message(f'{user!r} attempted to subscribe to private node, {target_id}')
            raise HTTPError(http_status.HTTP_403_FORBIDDEN)

        if isinstance(node, Registration):
            sentry.log_message(
                f'{user!r} attempted to subscribe to registration, {target_id}'
            )
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

        if notification_type != 'adopt_parent':
            pass
            # owner = node
        else:
            if 'file_updated' in event and len(event) > len('file_updated'):
                pass
            else:
                parent = node.parent_node
                if not parent:
                    sentry.log_message(
                        '{!r} attempted to adopt_parent of '
                        'the parentless project, {!r}'.format(user, node)
                    )
                    raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

            # If adopt_parent make sure that this subscription is None for the current User
            subscription, _ = NotificationSubscription.objects.get_or_create(
                user=user,
                subscribed_object=node,
                notification_type__name=event
            )
            if not subscription:
                return {}  # We're done here

            subscription.remove_user_from_subscription(user)
            return {}

    subscription, _ = NotificationSubscription.objects.get_or_create(
        user=user,
        notification_type__name=event
    )
    subscription.save()

    if node and node._id not in user.notifications_configured:
        user.notifications_configured[node._id] = True
        user.save()

    subscription.save()

    return {'message': f'Successfully subscribed to {notification_type} list on {event_id}'}
