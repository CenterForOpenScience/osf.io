import collections

from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from framework.postcommit_tasks.handlers import run_postcommit
from osf.models import NotificationSubscription, NotificationType
from osf.utils.permissions import READ
from website.notifications import constants
from website.notifications.exceptions import InvalidSubscriptionError
from website.project import signals

from framework.celery_tasks import app


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
    subs_available = constants.USER_SUBSCRIPTIONS_AVAILABLE
    subs_available.extend(list({
        'file_updated': 'Files updated'
    }.keys()))
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


@signals.contributor_removed.connect
def remove_contributor_from_subscriptions(node, user):
    """ Remove contributor from node subscriptions unless the user is an
        admin on any of node's parent projects.
    """
    Preprint = apps.get_model('osf.Preprint')
    DraftRegistration = apps.get_model('osf.DraftRegistration')
    # Preprints don't have subscriptions at this time
    if isinstance(node, Preprint):
        return
    if isinstance(node, DraftRegistration):
        return

    # If user still has permissions through being a contributor or group member, or has
    # admin perms on a parent, don't remove their subscription
    if not (node.is_contributor_or_group_member(user)) and user._id not in node.admin_contributor_or_group_member_ids:
        node_subscriptions = NotificationSubscription.objects.filter(
            user=user,
            user__isnull=True,
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node)
        )

        for subscription in node_subscriptions:
            subscription.remove_user_from_subscription()


@signals.node_deleted.connect
def remove_subscription(node):
    remove_subscription_task(node._id)

@signals.node_deleted.connect
def remove_supplemental_node(node):
    remove_supplemental_node_from_preprints(node._id)

@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def remove_subscription_task(node_id):
    AbstractNode = apps.get_model('osf.AbstractNode')
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    node = AbstractNode.load(node_id)
    NotificationSubscription.objects.filter(
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node),
    ).delete()


@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def remove_supplemental_node_from_preprints(node_id):
    AbstractNode = apps.get_model('osf.AbstractNode')

    node = AbstractNode.load(node_id)
    for preprint in node.preprints.all():
        if preprint.node is not None:
            preprint.node = None
            preprint.save()


def separate_users(node, user_ids):
    """Separates users into ones with permissions and ones without given a list.
    :param node: Node to separate based on permissions
    :param user_ids: List of ids, will also take and return User instances
    :return: list of subbed, list of removed user ids
    """
    OSFUser = apps.get_model('osf.OSFUser')
    removed = []
    subbed = []
    for user_id in user_ids:
        try:
            user = OSFUser.load(user_id)
        except TypeError:
            user = user_id
        if node.has_permission(user, READ):
            subbed.append(user_id)
        else:
            removed.append(user_id)
    return subbed, removed


def users_to_remove(source_event, source_node, new_node):
    """Find users that do not have permissions on new_node.
    :param source_event: such as _file_updated
    :param source_node: Node instance where a subscription currently resides
    :param new_node: Node instance where a sub or new sub will be.
    :return: Dict of notification type lists with user_ids
    """
    removed_users = {key: [] for key in constants.NOTIFICATION_TYPES}
    if source_node == new_node:
        return removed_users
    sub = NotificationSubscription.objects.get(
        object_id=source_node.id,
        content_type=ContentType.objects.get_for_model(source_node),
        notification_type__name=source_event
    )
    for notification_type in constants.NOTIFICATION_TYPES:
        users = []
        if hasattr(sub, notification_type):
            users += list(getattr(sub, notification_type).values_list('guids___id', flat=True))
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
    for notification_type in constants.NOTIFICATION_TYPES:
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
    user_subscriptions = NotificationSubscription.objects.filter(
        user=user
    )

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
        user__isnull=True,
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node)
    )

    for s in node_subscriptions:
        if not s.none.filter(id=user.id).exists():
            return False
    return True

def format_data(user, nodes):
    """ Format subscriptions data for project settings page
    :param user: OSFUser object
    :param nodes: list of parent project node objects
    :return: treebeard-formatted data
    """
    items = []

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
            subscriptions = NotificationSubscription.objects.filter(
                user=user,
                notification_type__name='file_updated',
                user__isnull=True,
                object_id=node.id,
                content_type=ContentType.objects.get_for_model(node)
            )

            for subscription in subscriptions:
                children_tree.append(
                    serialize_event(user, subscription=subscription, node=node)
                )
            for node_sub in subscriptions:
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
    user_subs_available = constants.USER_SUBSCRIPTIONS_AVAILABLE
    subscriptions = [
        serialize_event(
            user, subscription,
            event_description=user_subs_available.pop(user_subs_available.index(getattr(subscription, 'event_name')))
        )
        for subscription in NotificationSubscription.objects.get(user=user)
        if subscription is not None and getattr(subscription, 'event_name') in user_subs_available
    ]
    subscriptions.extend([serialize_event(user, event_description=sub) for sub in user_subs_available])
    return subscriptions


def format_file_subscription(user, node_id, path, provider):
    """Format a single file event"""
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)
    wb_path = path.lstrip('/')
    subscriptions = NotificationSubscription.objects.filter(
        user=user,
        user__isnull=True,
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node)
    )

    for subscription in subscriptions:
        if wb_path in getattr(subscription, 'event_name'):
            return serialize_event(user, subscription, node)
    return serialize_event(user, node=node, event_description='file_updated')


all_subs = ['file_updated']
all_subs += constants.USER_SUBSCRIPTIONS_AVAILABLE

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
        for sub_type in all_subs:
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
        for n_type in constants.NOTIFICATION_TYPES:
            if getattr(subscription, n_type).filter(id=user.id).exists():
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
    :param obj user: OSFUser object
    :return: str notification type (e.g. 'email_transactional')
    """
    AbstractNode = apps.get_model('osf.AbstractNode')

    if node and isinstance(node, AbstractNode) and node.parent_node and node.parent_node.has_permission(user, READ):
        parent = node.parent_node
        key = to_subscription_key(parent._id, event)
        try:
            subscription = NotificationSubscription.objects.get(_id=key)
        except NotificationSubscription.DoesNotExist:
            return get_parent_notification_type(parent, event, user)

        for notification_type in constants.NOTIFICATION_TYPES:
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
    for notification_type in constants.NOTIFICATION_TYPES:
        # TODO Optimize me
        if getattr(global_subscription, notification_type).filter(id=user.id).exists():
            return notification_type


def subscribe_user_to_notifications(node, user):
    """ Update the notification settings for the creator or contributors
    :param user: User to subscribe to notifications
    """

    if getattr(node, 'is_registration', False):
        raise InvalidSubscriptionError('Registrations are invalid targets for subscriptions')

    if user.is_registered:
        NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type__name=NotificationType.Type.USER_FILE_UPDATED,
        )
        NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type__name=NotificationType.Type.FILE_UPDATED,
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node)
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
