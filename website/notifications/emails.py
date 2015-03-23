from babel import dates, core, Locale
from mako.lookup import Template

from website import mails
from website import models as website_models
from website.notifications import constants
from website.notifications import utils
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.util import web_url_for

LOCALTIME_FORMAT = '%H:%M on %A, %B %d %Z'
EMAIL_SUBJECT_MAP = {
    'comments': '${commenter.fullname} commented on "${title}".',
    'comment_replies': '${commenter.fullname} replied to your comment on "${title}".'
}


def email_transactional(subscribed_user_ids, uid, event, **context):
    """
    :param subscribed_user_ids: mod-odm User object ids
    :param uid: id of the event owner (Node or User)
    :param event: name of notification event (e.g. 'comments')
    :param context: context variables for email template
    :return:
    """
    template = event + '.html.mako'
    subject = Template(EMAIL_SUBJECT_MAP[event]).render(**context)

    for user_id in subscribed_user_ids:
        user = website_models.User.load(user_id)
        email = user.username
        context['localized_timestamp'] = localize_timestamp(context.get('timestamp'), user)
        message = mails.render_message(template, **context)

        if context.get('commenter')._id != user._id:
            mails.send_mail(
                to_addr=email,
                mail=mails.TRANSACTIONAL,
                mimetype='html',
                name=user.fullname,
                node_id=context.get('node_id'),
                node_title=context.get('title'),
                subject=subject,
                message=message,
                url=get_settings_url(uid, user)
            )


def email_digest(subscribed_user_ids, uid, event, **context):
    """ Render the email message from context vars and store in the
        NotificationDigest objects created for each subscribed user.
    """
    template = event + '.html.mako'

    node = website_models.Node.load(uid)
    node_lineage_ids = get_node_lineage(node) if node else []

    for user_id in subscribed_user_ids:
        user = website_models.User.load(user_id)
        context['localized_timestamp'] = localize_timestamp(context.get('timestamp'), user)
        message = mails.render_message(template, **context)

        if context.get('commenter')._id != user._id:
            digest = NotificationDigest(
                timestamp=context.get('timestamp'),
                event=event,
                user_id=user._id,
                message=message,
                node_lineage=node_lineage_ids
            )
            digest.save()


EMAIL_FUNCTION_MAP = {
    'email_transactional': email_transactional,
    'email_digest': email_digest,
}


def notify(uid, event, **context):
    node_subscribers = []
    subscription = NotificationSubscription.load(utils.to_subscription_key(uid, event))

    if subscription:
        for notification_type in constants.NOTIFICATION_TYPES:
            subscribed_users = getattr(subscription, notification_type, [])

            node_subscribers.extend(subscribed_users)

            if subscribed_users and notification_type != 'none':
                for user in subscribed_users:
                    event = 'comment_replies' if context.get('target_user') == user else event
                    send([user._id], notification_type, uid, event, **context)

    return check_parent(uid, event, node_subscribers, **context)


def check_parent(uid, event, node_subscribers, **context):
    """ Check subscription object for the event on the parent project
        and send transactional email to indirect subscribers.
    """
    node = website_models.Node.load(uid)
    target_user = context.get('target_user', None)

    if node and node.parent_id:
        key = utils.to_subscription_key(node.parent_id, event)
        subscription = NotificationSubscription.load(key)

        if not subscription:
            return check_parent(node.parent_id, event, node_subscribers, **context)

        for notification_type in constants.NOTIFICATION_TYPES:
            subscribed_users = getattr(subscription, notification_type, [])

            for u in subscribed_users:
                if u not in node_subscribers and node.has_permission(u, 'read'):
                    if notification_type != 'none':
                        event = 'comment_replies' if target_user == u else event
                        send([u._id], notification_type, uid, event, **context)
                    node_subscribers.append(u)

        return check_parent(node.parent_id, event, node_subscribers, **context)

    return node_subscribers


def send(subscribed_user_ids, notification_type, uid, event, **context):
    """Dispatch to the handler for the provided notification_type"""

    if notification_type == 'none':
        return

    try:
        EMAIL_FUNCTION_MAP[notification_type](
            subscribed_user_ids=subscribed_user_ids,
            uid=uid,
            event=event,
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