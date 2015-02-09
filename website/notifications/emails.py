import datetime
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from model import Subscription
from model import DigestNotification
from website import mails
from website.models import Node
from mako.lookup import Template


def notify(uid, event, **context):
    key = str(uid + '_' + event)

    direct_subscribers = []

    for notification_type in notifications.keys():

        try:
            subscription = Subscription.find_one(Q('_id', 'eq', key))
        except NoResultsFound:
            subscription = None
        subscribed_users = []
        try:
            subscribed_users = getattr(subscription, notification_type)
        # TODO: handle this error
        except AttributeError:
            pass

        for u in subscribed_users:
            direct_subscribers.append(u)

        if notification_type != 'none':
            send(subscribed_users, notification_type, uid, event, **context)

    check_parent(uid, event, direct_subscribers, **context)


def check_parent(uid, event, direct_subscribers, **context):
    parent = Node.load(uid).node__parent
    if parent:
        for idx, p in parent:
            key = str(p[idx]._id + '_' + event)
            try:
                subscription = Subscription.find_one(Q('_id', 'eq', key))
            except NoResultsFound:
                return

            for notification_type in notifications.keys():
                subscribed_users = []
                try:
                    subscribed_users = getattr(subscription, notification_type)
                except AttributeError:
                    pass

                for u in subscribed_users:
                    if u not in direct_subscribers:
                        send([u], notification_type, uid, event, **context)

    return {}


def send(subscribed_users, notification_type, uid, event, **context):
    notifications.get(notification_type)(subscribed_users, uid, event, **context)


def email_transactional(subscribed_users, uid, event, **context):
    """
    :param subscribed_users:mod-odm User objects
    :param context: context variables for email template
    :return:
    """
    template = event + '.txt.mako'
    subject = Template(email_templates[event]['subject']).render(**context)
    message = mails.render_message(template, **context)

    for user in subscribed_users:
        email = user.username
        if context.get('commenter') != user.fullname:
            mails.send_mail(
                to_addr=email,
                mail=mails.TRANSACTIONAL,
                name=user.fullname,
                subject=subject,
                message=message)


def email_digest(subscribed_users, uid, event, **context):
    template = event + '.txt.mako'
    message = mails.render_message(template, **context)

    try:
        node = Node.find_one(Q('_id', 'eq', uid))
        nodes = get_node_lineage(node, [])
        nodes.reverse()
    except NoResultsFound:
        nodes = []

    for user in subscribed_users:
        if context.get('commenter') != user.fullname:
            digest = DigestNotification(timestamp=datetime.datetime.utcnow(),
                                        event=event,
                                        user_id=user._id,
                                        message=message,
                                        node_lineage=nodes if nodes else [])
            digest.save()


def get_node_lineage(node, node_lineage):
    if node is not None:
        node_lineage.append(node._id)
    if node.node__parent != []:
        for n in node.node__parent:
            get_node_lineage(n, node_lineage)

    return node_lineage

notifications = {
    'email_transactional': email_transactional,
    'email_digest': email_digest,
    'none': 'none'
}

email_templates = {
    'comments': {
        'subject': '${commenter} commented on "${title}".'
    },
    # 'comment_replies': {
    #     'subject': '${commenter} replied to your comment on "${title}".',
    #     'message': '${commenter} replied to your comment "${parent_comment}" on your project "${title}": "${content}".' +
    #     '\n\n\tTo view this on the Open Science Framework, please visit: ${url}.'
    # }
}


