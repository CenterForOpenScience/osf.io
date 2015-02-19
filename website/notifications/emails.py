import datetime
import urlparse
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from model import Subscription, DigestNotification
from framework.tasks import app
from framework.tasks.handlers import queued_task
from website import mails, settings
from website.util import web_url_for
from website.models import Node, User
from mako.lookup import Template
from website.notifications import utils


def notify(uid, event, **context):
    key = utils.to_subscription_key(uid, event)

    node_subscribers = []

    for notification_type in notifications.keys():

        try:
            subscription = Subscription.find_one(Q('_id', 'eq', key))
        except NoResultsFound:
            break

        try:
            subscribed_users = getattr(subscription, notification_type)
        except AttributeError:
            subscribed_users = []

        for u in subscribed_users:
            node_subscribers.append(u)

        if subscribed_users and notification_type != 'none':
            send([u._id for u in subscribed_users], notification_type, uid, event, **context)

    check_parent(uid, event, node_subscribers, **context)


def check_parent(uid, event, node_subscribers, **context):
    node = Node.load(uid)
    if node and node.node__parent:
        for p in node.node__parent:
            key = utils.to_subscription_key(p._id, event)
            try:
                subscription = Subscription.find_one(Q('_id', 'eq', key))
            except NoResultsFound:
                return check_parent(p._id, event, node_subscribers, **context)

            parent_subscribers = []
            for notification_type in notifications.keys():
                try:
                    subscribed_users = getattr(subscription, notification_type)
                except AttributeError:
                    subscribed_users = []

                for u in subscribed_users:
                    if u not in node_subscribers:
                        parent_subscribers.append(u)
                        send([u._id], notification_type, uid, event, **context)

            return check_parent(p._id, event, parent_subscribers, **context)


def send(subscribed_user_ids, notification_type, uid, event, **context):
    notifications.get(notification_type)(subscribed_user_ids, uid, event, **context)

@queued_task
@app.task
def email_transactional(subscribed_user_ids, uid, event, **context):
    """
    :param subscribed_user_ids: mod-odm User objects
    :param context: context variables for email template
    :return:
    """
    template = event + '.html.mako'
    subject = Template(email_templates[event]['subject']).render(**context)
    message = mails.render_message(template, **context)

    for user_id in subscribed_user_ids:
        user = User.load(user_id)
        email = user.username
        if context.get('commenter') != user.fullname:
            mails.send_mail(
                to_addr=email,
                mail=mails.TRANSACTIONAL,
                mimetype='html',
                name=user.fullname,
                node_title=context.get('title'),
                subject=subject,
                message=message,
                url=get_settings_url(uid, user)
            )


def get_settings_url(uid, user):
    if uid == user._id:
        return urlparse.urljoin(settings.DOMAIN, web_url_for('user_notifications'))
    else:
        return Node.load(uid).absolute_url + 'settings/'


def email_digest(subscribed_user_ids, uid, event, **context):
    template = event + '.html.mako'
    message = mails.render_message(template, **context)

    try:
        node = Node.find_one(Q('_id', 'eq', uid))
        nodes = get_node_lineage(node, [])
        nodes.reverse()
    except NoResultsFound:
        nodes = []

    for user_id in subscribed_user_ids:
        user = User.load(user_id)
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
    'comment_replies': {
        'subject': '${commenter} replied to your comment on "${title}".'
    }
}
