from babel import dates, core, Locale
from datetime import timedelta

from website import mails
from website import models as website_models
from website.notifications import constants, tasks
from website.notifications import utils
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.util import web_url_for


def notify(event, user, node, timestamp, **context):
    """
    Retrieves appropriate ***subscription*** and passes user list to store_emails
    :param event: event that triggered the notification
    :param user: user who triggered notification
    :param node: instance of Node
    :param timestamp: time event happened
    :param context: optional variables specific to templates
        target_user: used with comment_replies
    :return: List of user ids notifications were sent to
    """
    event_type = "_".join(event.split("_")[-2:])  # tests indicate that this should work with no underscores
    subscriptions = compile_subscriptions(node, event_type, event)
    sent_users = []
    target_user = context.get('target_user', None)
    if target_user:
        target_user_id = target_user._id
    for notification_type in subscriptions:
        if notification_type != 'none' and subscriptions[notification_type]:
            if user in subscriptions[notification_type]:
                subscriptions[notification_type].pop(subscriptions[notification_type].index(user))
            if target_user and target_user_id in subscriptions[notification_type]:
                subscriptions[notification_type].pop(subscriptions[notification_type].index(target_user_id))
                if target_user_id != user._id:
                    store_emails([target_user_id], notification_type, 'comment_replies', user, node,
                                 timestamp, **context)
                    sent_users.append(target_user_id)
            if subscriptions[notification_type]:
                store_emails(subscriptions[notification_type], notification_type, event_type, user, node,
                             timestamp, **context)
                sent_users.extend(subscriptions[notification_type])
    return sent_users


def store_emails(recipient_ids, notification_type, event, user, node, timestamp, **context):
    """
    Stores notification emails and calls function to check for previous celery tasks
     of user and notification.
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

    delta = 0
    if notification_type == 'email_transactional':
        delay = 60  # TODO: Look into making this adjustable, learn how fast users generally check Email
        n_seconds = timestamp.minute * 60 + timestamp.second + timestamp.microsecond * 1e-6
        delta = (n_seconds // delay) * delay + delay - n_seconds
    elif notification_type == 'email_digest':
        delay = 86400
        n_seconds = timestamp.hour * 3600 + timestamp.minute * 60 + timestamp.second + timestamp.microsecond * 1e-6
        delta = (n_seconds // delay) * delay + delay - n_seconds
    time_to_send = timestamp + timedelta(seconds=delta)

    template = event + '.html.mako'
    context['user'] = user
    node_lineage_ids = get_node_lineage(node) if node else []

    for user_id in recipient_ids:
        recipient = website_models.User.load(user_id)
        context['localized_timestamp'] = localize_timestamp(timestamp, recipient)
        message = mails.render_message(template, **context)

        digest = NotificationDigest(
            timestamp=timestamp,
            send_type=notification_type,
            event=event,
            user_id=user_id,
            message=message,
            node_lineage=node_lineage_ids
        )
        digest.save()

        tasks.check_and_send_later(user_id, timestamp, time_to_send, notification_type)


def compile_subscriptions(node, event_type, event=None, level=0):
    """
    Recurse through node and parents for subscriptions.
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
    elif node.parent_id:
        parent_subscriptions = \
            compile_subscriptions(website_models.Node.load(node.parent_id), event_type, level=level + 1)
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
            for user in users:
                if node.has_permission(user, 'read'):
                    node_subscriptions[notification_type].append(user._id)
    return node_subscriptions


def get_node_lineage(node):
    """ Get a list of node ids in order from the node to top most project
        e.g. [parent._id, node._id]
    """
    lineage = [node._id]

    while node.parent_id:
        node = website_models.Node.load(node.parent_id)
        lineage = [node._id] + lineage

    return lineage


def get_settings_url(uid, user):
    if uid == user._id:
        return web_url_for('user_notifications', _absolute=True)

    node = website_models.Node.load(uid)
    assert node, 'get_settings_url recieved an invalid Node id'
    return node.web_url_for('node_setting', _guid=True, _absolute=True)


def localize_timestamp(timestamp, user):
    try:
        user_timezone = dates.get_timezone(user.timezone)
    except LookupError:
        user_timezone = dates.get_timezone('Etc/UTC')

    try:
        user_locale = Locale(user.locale)
    except core.UnknownLocaleError:
        user_locale = 'en'

    formatted_date = dates.format_date(timestamp, format='full', locale=user_locale)
    formatted_time = dates.format_time(timestamp, format='short', tzinfo=user_timezone, locale=user_locale)

    return u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
