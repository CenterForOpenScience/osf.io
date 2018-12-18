import collections

from django.apps import apps
from django.db.models import Q

from framework.postcommit_tasks.handlers import run_postcommit
from website.notifications import constants
from website.notifications.exceptions import InvalidSubscriptionError
from website.project import signals

from framework.celery_tasks import app


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


def find_subscription_type(subscription):
    """Find subscription type string within specific subscription.
     Essentially removes extraneous parts of the string to get the type.
    """
    subs_available = list(constants.USER_SUBSCRIPTIONS_AVAILABLE.keys())
    subs_available.extend(list(constants.NODE_SUBSCRIPTIONS_AVAILABLE.keys()))
    for available in subs_available:
        if available in subscription:
            return available


def to_subscription_key(uid, event):
    """Build the Subscription primary key for the given guid and event"""
    return u'{}_{}'.format(uid, event)


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
    # Preprints don't have subscriptions at this time
    if isinstance(node, Preprint):
            return

    if user._id not in node.admin_contributor_ids:
        node_subscriptions = get_all_node_subscriptions(user, node)
        for subscription in node_subscriptions:
            subscription.remove_user_from_subscription(user)


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
    NotificationSubscription.objects.filter(node=node).delete()
    parent = node.parent_node

    if parent and parent.child_node_subscriptions:
        for user_id in parent.child_node_subscriptions:
            if node._id in parent.child_node_subscriptions[user_id]:
                parent.child_node_subscriptions[user_id].remove(node._id)
        parent.save()


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
        if node.has_permission(user, 'read'):
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
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    removed_users = {key: [] for key in constants.NOTIFICATION_TYPES}
    if source_node == new_node:
        return removed_users
    old_sub = NotificationSubscription.load(to_subscription_key(source_node._id, source_event))
    old_node_sub = NotificationSubscription.load(to_subscription_key(source_node._id,
                                                                     '_'.join(source_event.split('_')[-2:])))
    if not old_sub and not old_node_sub:
        return removed_users
    for notification_type in constants.NOTIFICATION_TYPES:
        users = []
        if hasattr(old_sub, notification_type):
            users += list(getattr(old_sub, notification_type).values_list('guids___id', flat=True))
        if hasattr(old_node_sub, notification_type):
            users += list(getattr(old_node_sub, notification_type).values_list('guids___id', flat=True))
        subbed, removed_users[notification_type] = separate_users(new_node, users)
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
    user_subscriptions = get_all_user_subscriptions(user, extra=(
        ~Q(node__type='osf.collection') &
        ~Q(node__type='osf.quickfilesnode') &
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
    node_subscriptions = get_all_node_subscriptions(user, node)
    for s in node_subscriptions:
        if not s.none.filter(id=user.id).exists():
            return False
    return True


def get_all_user_subscriptions(user, extra=None):
    """ Get all Subscription objects that the user is subscribed to"""
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    queryset = NotificationSubscription.objects.filter(
        Q(none=user.pk) |
        Q(email_digest=user.pk) |
        Q(email_transactional=user.pk)
    ).distinct()
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
    return user_subscriptions.filter(user__isnull=True, node=node)


def format_data(user, nodes):
    """ Format subscriptions data for project settings page
    :param user: OSFUser object
    :param nodes: list of parent project node objects
    :return: treebeard-formatted data
    """
    items = []

    user_subscriptions = get_all_user_subscriptions(user)
    for node in nodes:
        assert node, '{} is not a valid Node.'.format(node._id)

        can_read = node.has_permission(user, 'read')
        can_read_children = node.has_permission_on_children(user, 'read')

        if not can_read and not can_read_children:
            continue

        children = node.get_nodes(**{'is_deleted': False, 'is_node_link': False})
        children_tree = []
        # List project/node if user has at least 'read' permissions (contributor or admin viewer) or if
        # user is contributor on a component of the project/node

        if can_read:
            node_sub_available = list(constants.NODE_SUBSCRIPTIONS_AVAILABLE.keys())
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
            'kind': 'folder' if not node.parent_node or not node.parent_node.has_permission(user, 'read') else 'node',
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
    user_subs_available = list(constants.USER_SUBSCRIPTIONS_AVAILABLE.keys())
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


all_subs = constants.NODE_SUBSCRIPTIONS_AVAILABLE.copy()
all_subs.update(constants.USER_SUBSCRIPTIONS_AVAILABLE)

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
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')

    if node and isinstance(node, AbstractNode) and node.parent_node and node.parent_node.has_permission(user, 'read'):
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


def check_if_all_global_subscriptions_are_none(user):
    all_global_subscriptions_none = False
    user_sunscriptions = get_all_user_subscriptions(user)
    for user_subscription in user_sunscriptions:
        if user_subscription.event_name.startswith('global_'):
            all_global_subscriptions_none = True
            global_notification_type = get_global_notification_type(user_subscription, user)
            if global_notification_type != 'none':
                return False

    return all_global_subscriptions_none


def subscribe_user_to_global_notifications(user):
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    notification_type = 'email_transactional'
    user_events = constants.USER_SUBSCRIPTIONS_AVAILABLE
    for user_event in user_events:
        user_event_id = to_subscription_key(user._id, user_event)

        # get_or_create saves on creation
        subscription, created = NotificationSubscription.objects.get_or_create(_id=user_event_id, user=user, event_name=user_event)
        subscription.add_user_to_subscription(user, notification_type)
        subscription.save()


def subscribe_user_to_notifications(node, user):
    """ Update the notification settings for the creator or contributors
    :param user: User to subscribe to notifications
    """
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    Preprint = apps.get_model('osf.Preprint')
    if isinstance(node, Preprint):
        raise InvalidSubscriptionError('Preprints are invalid targets for subscriptions at this time.')

    if node.is_collection:
        raise InvalidSubscriptionError('Collections are invalid targets for subscriptions')

    if node.is_deleted:
        raise InvalidSubscriptionError('Deleted Nodes are invalid targets for subscriptions')

    events = constants.NODE_SUBSCRIPTIONS_AVAILABLE
    notification_type = 'email_transactional'
    target_id = node._id

    if user.is_registered:
        for event in events:
            event_id = to_subscription_key(target_id, event)
            global_event_id = to_subscription_key(user._id, 'global_' + event)
            global_subscription = NotificationSubscription.load(global_event_id)

            subscription = NotificationSubscription.load(event_id)

            # If no subscription for component and creator is the user, do not create subscription
            # If no subscription exists for the component, this means that it should adopt its
            # parent's settings
            if not(node and node.parent_node and not subscription and node.creator == user):
                if not subscription:
                    subscription = NotificationSubscription(_id=event_id, owner=node, event_name=event)
                    # Need to save here in order to access m2m fields
                    subscription.save()
                if global_subscription:
                    global_notification_type = get_global_notification_type(global_subscription, user)
                    subscription.add_user_to_subscription(user, global_notification_type)
                else:
                    subscription.add_user_to_subscription(user, notification_type)
                subscription.save()


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
