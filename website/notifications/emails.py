from babel import dates, core, Locale

from osf.models import AbstractNode, OSFUser, NotificationDigest, NotificationSubscription

from website import mails
from website.notifications import constants
from website.notifications import utils
from website.util import web_url_for


def notify(event, user, node, timestamp, **context):
    """Retrieve appropriate ***subscription*** and passe user list

    :param event: event that triggered the notification
    :param user: user who triggered notification
    :param node: instance of Node
    :param timestamp: time event happened
    :param context: optional variables specific to templates
        target_user: used with comment_replies
    :return: List of user ids notifications were sent to
    """
    sent_users = []
    # The user who the current comment is a reply to
    target_user = context.get('target_user', None)
    exclude = context.get('exclude', [])
    # do not notify user who initiated the emails
    exclude.append(user._id)

    event_type = utils.find_subscription_type(event)
    if target_user and event_type in constants.USER_SUBSCRIPTIONS_AVAILABLE:
        # global user
        subscriptions = get_user_subscriptions(target_user, event_type)
    else:
        # local project user
        subscriptions = compile_subscriptions(node, event_type, event)

    for notification_type in subscriptions:
        if notification_type == 'none' or not subscriptions[notification_type]:
            continue
        # Remove excluded ids from each notification type
        subscriptions[notification_type] = [guid for guid in subscriptions[notification_type] if guid not in exclude]

        # If target, they get a reply email and are removed from the general email
        if target_user and target_user._id in subscriptions[notification_type]:
            subscriptions[notification_type].remove(target_user._id)
            store_emails([target_user._id], notification_type, 'comment_replies', user, node, timestamp, **context)
            sent_users.append(target_user._id)

        if subscriptions[notification_type]:
            store_emails(subscriptions[notification_type], notification_type, event_type, user, node, timestamp, **context)
            sent_users.extend(subscriptions[notification_type])
    return sent_users

def notify_mentions(event, user, node, timestamp, **context):
    recipient_ids = context.get('new_mentions', [])
    recipients = OSFUser.objects.filter(guids___id__in=recipient_ids)
    sent_users = notify_global_event(event, user, node, timestamp, recipients, context=context)
    return sent_users

def notify_global_event(event, sender_user, node, timestamp, recipients, template=None, context=None):
    event_type = utils.find_subscription_type(event)
    sent_users = []

    for recipient in recipients:
        subscriptions = get_user_subscriptions(recipient, event_type)
        context['is_creator'] = recipient == node.creator
        for notification_type in subscriptions:
            if (notification_type != 'none' and subscriptions[notification_type] and recipient._id in subscriptions[notification_type]):
                store_emails([recipient._id], notification_type, event, sender_user, node, timestamp, template=template, **context)
                sent_users.append(recipient._id)

    return sent_users


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
    if notification_type == 'none':
        return

    # If `template` is not specified, default to using a template with name `event`
    template = '{template}.html.mako'.format(template=template or event)

    # user whose action triggered email sending
    context['user'] = user
    node_lineage_ids = get_node_lineage(node) if node else []

    for recipient_id in recipient_ids:
        if recipient_id == user._id:
            continue
        recipient = OSFUser.load(recipient_id)
        if recipient.is_disabled:
            continue
        context['localized_timestamp'] = localize_timestamp(timestamp, recipient)
        context['recipient'] = recipient
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
        subscription = NotificationSubscription.load(utils.to_subscription_key(node._id, event))
        for notification_type in node_subscriptions:
            users = getattr(subscription, notification_type, [])
            if users:
                for user in users.exclude(date_disabled__isnull=False):
                    if node.has_permission(user, 'read'):
                        node_subscriptions[notification_type].append(user._id)
    return node_subscriptions


def get_user_subscriptions(user, event):
    if user.is_disabled:
        return {}
    user_subscription = NotificationSubscription.load(utils.to_subscription_key(user._id, event))
    if user_subscription:
        return {key: list(getattr(user_subscription, key).all().values_list('guids___id', flat=True)) for key in constants.NOTIFICATION_TYPES}
    else:
        return {key: [] for key in constants.NOTIFICATION_TYPES}


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
    except IOError:  # An IOError will be raised if locale's casing is incorrect, e.g. de_de vs. de_DE
        # Attempt to fix the locale, e.g. de_de -> de_DE
        try:
            user_locale = Locale(fix_locale(user.locale))
            user_locale.date_formats
        except (core.UnknownLocaleError, IOError):
            user_locale = Locale('en')

    formatted_date = dates.format_date(timestamp, format='full', locale=user_locale)
    formatted_time = dates.format_time(timestamp, format='short', tzinfo=user_timezone, locale=user_locale)

    return u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
