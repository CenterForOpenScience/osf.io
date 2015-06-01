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

        digest = NotificationDigest(
            timestamp=timestamp,
            event=event,
            user_id=user_id,
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
    event_type = "_".join(event.split("_")[-2:])  # tests indicate that this should work with no underscores
    subscriptions = compile_subscriptions(node, event_type, event)
    sent_users = []
    target_user = context.get('target_user', None)
    for notification_type in subscriptions:
        if notification_type != 'none' and subscriptions[notification_type]:
            if user._id in subscriptions[notification_type]:
                subscriptions[notification_type].pop(subscriptions[notification_type].index(user._id))
            if target_user and target_user._id in subscriptions[notification_type]:
                subscriptions[notification_type].pop(subscriptions[notification_type].index(target_user._id))
                send([target_user._id], notification_type, uid, 'comment_replies', user, node, timestamp, **context)
                sent_users.append(target_user._id)
            if subscriptions[notification_type]:
                send(subscriptions[notification_type], notification_type, uid, event_type, user, node,
                     timestamp, **context)
                sent_users.extend(subscriptions[notification_type])
    return sent_users


def remove_users_from_subscription(recipients, event, user, node, timestamp, **context):
    """
    Notify recipients that a subscription of theirs has been cancelled due to an action
    by the user. Creates a temporary subscription and assigns user list
    :param recipients: dict of users in notification types
    :param event: base type of subscription
    :param user: The one who changed things
    :param node: Original node
    :param timestamp: time sent
    :param context: Extra space
    :return:
    """
    event_id = utils.to_subscription_key(node._id, event)
    subscription = NotificationSubscription(_id=event_id, owner=node, event_name=event)
    for notification_type in recipients:
        recipient_list = recipients[notification_type]
        if len(recipient_list) == 0:
            continue
        for recipient in recipient_list:
            subscription.add_user_to_subscription(recipient, notification_type)
    subscription.save()
    notify(node._id, event, user, node, timestamp, **context)


def compile_subscriptions(node, event_type, event=None):
    """
    Recurse through node and parents for subscriptions.
    :param node: current node
    :param event_type: Generally node_subscriptions_available
    :param event: Particular event such a file_updated that has specific file subs
    :return: a dict of notification types with lists of users.
    """
    subscriptions = check_node(node, event_type)
    if event:
        subscriptions = check_node(node, event)  # Gets particular event subscriptions
        parent_subscriptions = compile_subscriptions(node, event_type)  # get node and parent subs
    elif node.parent_id:
        parent_subscriptions = compile_subscriptions(website_models.Node.load(node.parent_id), event_type)
    else:
        parent_subscriptions = check_node(None, event_type)
    for notification_type in parent_subscriptions:
        parent_subscriptions[notification_type].extend(subscriptions[notification_type])
        for nt in subscriptions:
            if notification_type != nt:
                parent_subscriptions[notification_type] = \
                    list(set(parent_subscriptions[notification_type]).difference(set(subscriptions[nt])))
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


def send(recipient_ids, notification_type, uid, event, user, node, timestamp, **context):
    """Dispatch to the handler for the provided notification_type"""
    if notification_type == 'none':
        return

    try:
        EMAIL_FUNCTION_MAP[notification_type](
            recipient_ids=recipient_ids,
            uid=uid,
            event=event,
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