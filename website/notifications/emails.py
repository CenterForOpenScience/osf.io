from babel import dates, core, Locale
from mako.lookup import Template

from website import mails
from website import models as website_models
from website.notifications import constants
from website.notifications import utils
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.util import web_url_for


def email_transactional(recipient_ids, uid, event, user, node, timestamp, **context):
    """
    :param recipient_ids: mod-odm User object ids
    :param uid: id of the event owner (Node or User)
    :param event: name of notification event (e.g. 'comments')
    :param context: context variables for email template
        See notify for specifics
    :return:
    """
    template = event + '.html.mako'
    context['title'] = node.title
    context['user'] = user
    subject = Template(constants.EMAIL_SUBJECT_MAP[event]).render(**context)

    for user_id in recipient_ids:
        recipient = website_models.User.load(user_id)
        email = recipient.username
        context['localized_timestamp'] = localize_timestamp(timestamp, recipient)
        message = mails.render_message(template, **context)

        if user._id != recipient._id:
            mails.send_mail(
                to_addr=email,
                mail=mails.TRANSACTIONAL,
                mimetype='html',
                name=recipient.fullname,
                node_id=node._id,
                node_title=node.title,
                subject=subject,
                message=message,
                url=get_settings_url(uid, recipient)
            )


def email_digest(recipient_ids, uid, event, user, node, timestamp, **context):
    """ Render the email message from context vars and store in the
        NotificationDigest objects created for each subscribed user.
    """
    template = event + '.html.mako'
    context['user'] = user
    node_lineage_ids = get_node_lineage(node) if node else []

    for user_id in recipient_ids:
        recipient = website_models.User.load(user_id)
        context['localized_timestamp'] = localize_timestamp(timestamp, recipient)
        message = mails.render_message(template, **context)

        if user._id != recipient._id:
            digest = NotificationDigest(
                timestamp=timestamp,
                event=event,
                user_id=recipient._id,
                message=message,
                node_lineage=node_lineage_ids
            )
            digest.save()


EMAIL_FUNCTION_MAP = {
    'email_transactional': email_transactional,
    'email_digest': email_digest,
}


def notify(uid, event, user, node, timestamp, **context):
    """
    :param uid: node's id
    :param event: type of notification
    :param user: user "sending" notification
    :param node: the node
    :param timestamp: time
    :param context: optional variables specific to templates
        target_user: used with comment_replies
    :return:
    """
    subscriptions = {}
    for notification_type in constants.NOTIFICATION_TYPES:
        subscriptions[notification_type] = []
    subscription = NotificationSubscription.load(utils.to_subscription_key(uid, event))
    if 'file_updated' in event:
        for notification_type in constants.NOTIFICATION_TYPES:
            subscriptions[notification_type] = getattr(subscription, notification_type, [])
        event = "_".join(event.split("_")[-2:])  # tests indicate that this should work with no underscores
        subscription = NotificationSubscription.load(utils.to_subscription_key(uid, event))
    none_set = set(subscriptions['none'])
    for notification_type in constants.NOTIFICATION_TYPES:
        if notification_type != 'none':
            subscriptions[notification_type].extend(getattr(subscription, notification_type, []))
            subscriptions[notification_type].extend(check_parent(node, event, notification_type))
            subscribed_users = list(set(subscriptions[notification_type]).difference(none_set))
            send(subscribed_users, notification_type, uid, event, user, node, timestamp, **context)


def check_parent(node, event, notification_type):
    """ Check subscription object for the event on the parent project
        and send transactional email to indirect subscribers.
    """
    if node and node.parent_id:
        parent = website_models.Node.load(node.parent_id)
        subscription = NotificationSubscription.load(utils.to_subscription_key(parent._id, event))

        if not subscription:
            return check_parent(parent, event, notification_type)

        subscribed_users = getattr(subscription, notification_type, [])

        return subscribed_users.extend(check_parent(parent, event, notification_type))

    return []


def send(recipient_ids, notification_type, uid, event, user, node, timestamp, **context):
    """Dispatch to the handler for the provided notification_type"""

    # Remove file path if it exists
    event_type = "_".join(event.split("_")[-2:])  # tests indicate that this should work with no underscores

    if notification_type == 'none':
        return

    try:
        EMAIL_FUNCTION_MAP[notification_type](
            recipient_ids=recipient_ids,
            uid=uid,
            event=event_type,
            user=user,
            node=node,
            timestamp=timestamp,
            **context
        )
    except KeyError:
        raise ValueError('Unrecognized notification_type')


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