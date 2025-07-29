from django.apps import apps

from babel import dates, core, Locale
from django.contrib.contenttypes.models import ContentType

from osf.models import AbstractNode, NotificationSubscription, NotificationType
from osf.models.notifications import NotificationDigest
from osf.utils.permissions import READ
from website import mails
from website.notifications import constants
from website.notifications import utils
from website.util import web_url_for


def notify(event, user, node, timestamp, **context):
    """Retrieve appropriate ***subscription*** and passe user list
website/notifications/u
    :param event: event that triggered the notification
    :param user: user who triggered notification
    :param node: instance of Node
    :param timestamp: time event happened
    :param context: optional variables specific to templates
        target_user: used with comment_replies
    :return: List of user ids notifications were sent to
    """
    if event.endswith('_file_updated'):
        NotificationType.objects.get(
            name=NotificationType.Type.NODE_FILE_ADDED
        ).emit(
            user=user,
            subscribed_object=node,
            event_context=context,
            is_digest=True,
        )

def store_emails(recipient_ids, notification_type, event, user, node, timestamp, abstract_provider=None, template=None, **context):
    """Store notification emails

    Emails are sent via celery beat as digests
    :param recipient_ids: List of user ids to send mail to.
    :param notification_type: from constants.Notification_types
    :param event: event that triggered notification
    :param user: user who triggered the notification
    :param node: instance of Node
    :param timestamp: time event happened
    :param context:
    :return: --
    """
    OSFUser = apps.get_model('osf', 'OSFUser')

    if notification_type == 'none':
        return

    # If `template` is not specified, default to using a template with name `event`
    template = f'{template or event}.html.mako'

    # user whose action triggered email sending
    context['user_fullname'] = user.fullname
    node_lineage_ids = get_node_lineage(node) if node else []

    for recipient_id in recipient_ids:
        if recipient_id == user._id:
            continue
        recipient = OSFUser.load(recipient_id)
        if recipient.is_disabled:
            continue
        context['localized_timestamp'] = localize_timestamp(timestamp, recipient)
        context['recipient_fullname'] = recipient.fullname
        message = mails.render_message(template, **context)
        digest = NotificationDigest(
            timestamp=timestamp,
            send_type=notification_type,
            event=event,
            user=recipient,
            message=message,
            node_lineage=node_lineage_ids,
            provider=abstract_provider
        )
        digest.save()


def compile_subscriptions(node, event_type, event=None, level=0):
    """Recurse through node and parents for subscriptions.

    :param node: current node
    :param event_type: Generally node_subscriptions_available
    :param event: Particular event such a file_updated that has specific file subs
    :param level: How deep the recursion is
    :return: a dict of notification types with lists of users.
    """
    subscriptions = check_node(node, event_type)
    if event:
        subscriptions = check_node(node, event)  # Gets particular event subscriptions
        parent_subscriptions = compile_subscriptions(node, event_type, level=level + 1)  # get node and parent subs
    elif getattr(node, 'parent_id', False):
        parent_subscriptions = \
            compile_subscriptions(AbstractNode.load(node.parent_id), event_type, level=level + 1)
    else:
        parent_subscriptions = check_node(None, event_type)
    for notification_type in parent_subscriptions:
        p_sub_n = parent_subscriptions[notification_type]
        p_sub_n.extend(subscriptions[notification_type])
        for nt in subscriptions:
            if notification_type != nt:
                p_sub_n = list(set(p_sub_n).difference(set(subscriptions[nt])))
        if level == 0:
            p_sub_n, removed = utils.separate_users(node, p_sub_n)
        parent_subscriptions[notification_type] = p_sub_n
    return parent_subscriptions


def check_node(node, event):
    """Return subscription for a particular node and event."""
    node_subscriptions = {key: [] for key in constants.NOTIFICATION_TYPES}
    if node:
        subscription = NotificationSubscription.objects.filter(
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node),
            notification_type__name=event
        )
        for notification_type in node_subscriptions:
            users = getattr(subscription, notification_type, [])
            if users:
                for user in users.exclude(date_disabled__isnull=False):
                    if node.has_permission(user, READ):
                        node_subscriptions[notification_type].append(user._id)
    return node_subscriptions


def get_user_subscriptions(user, event):
    if user.is_disabled:
        return {}
    user_subscription, _ = NotificationSubscription.objects.get_or_create(
        user=user,
        notification_type__name=event
    )
    return user_subscription


def get_node_lineage(node):
    """ Get a list of node ids in order from the node to top most project
        e.g. [parent._id, node._id]
    """
    from osf.models import Preprint
    lineage = [node._id]
    if isinstance(node, Preprint):
        return lineage

    while node.parent_id:
        node = node.parent_node
        lineage = [node._id] + lineage

    return lineage


def get_settings_url(uid, user):
    if uid == user._id:
        return web_url_for('user_notifications', _absolute=True)

    node = AbstractNode.load(uid)
    assert node, 'get_settings_url recieved an invalid Node id'
    return node.web_url_for('node_setting', _guid=True, _absolute=True)

def fix_locale(locale):
    """Atempt to fix a locale to have the correct casing, e.g. de_de -> de_DE

    This is NOT guaranteed to return a valid locale identifier.
    """
    try:
        language, territory = locale.split('_', 1)
    except ValueError:
        return locale
    else:
        return '_'.join([language, territory.upper()])

def localize_timestamp(timestamp, user):
    try:
        user_timezone = dates.get_timezone(user.timezone)
    except LookupError:
        user_timezone = dates.get_timezone('Etc/UTC')

    try:
        user_locale = Locale(user.locale)
    except core.UnknownLocaleError:
        user_locale = Locale('en')

    # Do our best to find a valid locale
    try:
        user_locale.date_formats
    except OSError:  # An IOError will be raised if locale's casing is incorrect, e.g. de_de vs. de_DE
        # Attempt to fix the locale, e.g. de_de -> de_DE
        try:
            user_locale = Locale(fix_locale(user.locale))
            user_locale.date_formats
        except (core.UnknownLocaleError, OSError):
            user_locale = Locale('en')

    formatted_date = dates.format_date(timestamp, format='full', locale=user_locale)
    formatted_time = dates.format_time(timestamp, format='short', tzinfo=user_timezone, locale=user_locale)

    return f'{formatted_time} on {formatted_date}'
