from furl import furl
import json
import re
import requests

from flask import request

from framework.auth.core import get_user
from framework.auth.signals import user_confirmed
from framework.celery_tasks import app
from framework.celery_tasks.handlers import queued_task
from framework.exceptions import HTTPError

from website import settings
from website.notifications.utils import to_subscription_key

from website.mailing_list.model import MailingListEventLog
from website.project.signals import contributor_added, contributor_removed, node_deleted

ANGLE_BRACKETS_REGEX = re.compile(r'<(.*?)>')

MAILGUN_BASE_LISTS_URL = '{}/lists'.format(settings.MAILGUN_API_URL)

###############################################################################
# Decorator
###############################################################################

def require_mailgun(func):
    """ Execute MailGun API calls iff API key is set """
    def wrapper(*args, **kwargs):
        if settings.MAILGUN_API_KEY:
            return func(*args, **kwargs)
        return None
    return wrapper

###############################################################################
# List Management Functions
###############################################################################

@require_mailgun
def get_info(node_id):
    """ Returns information about the mailing list from Mailgun
    :param str node_id: ID of the node in question
    :returns dict info: mailing list info
    """
    resp = requests.get(
        '{}/{}'.format(MAILGUN_BASE_LISTS_URL, address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
    )
    if resp.status_code == 200:
        return json.loads(resp.text)
    elif resp.status_code == 404:
        return None
    raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

@require_mailgun
def get_members(node_id):
    """ Returns member list for mailing list from Mailgun
    :param str node_id: ID of the node in question
    :returns dict members: list of members
    """
    resp = requests.get(
        '{}/{}/members'.format(MAILGUN_BASE_LISTS_URL, address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
    )
    if resp.status_code == 200:
        return json.loads(resp.text)
    raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

@require_mailgun
def get_list(node_id):
    """ Returns information about the mailing list from Mailgun
    :param str node_id: ID of the node in question
    :returns: info, members: Two dictionaries about list and members
    """
    info = get_info(node_id)

    if not info:
        return None, None

    members = get_members(node_id)

    return info, members

@require_mailgun
def create_list(node_id):
    """ Creates a new mailing list on Mailgun with all emails and subscriptions
    :param str node_id: ID of the node in question
    """
    from website.models import Node  # avoid circular import
    node = Node.load(node_id)
    resp = requests.post(
        MAILGUN_BASE_LISTS_URL,
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'address': address(node_id),
            'name': list_title(node),
            'access_level': 'members'
        }
    )
    if resp.status_code != 200:
        raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

    members_list = []
    members_list = jsonify_users_list(node.contributors, unsubs=get_unsubscribes(node))
    members_list.append({'address': 'mailing_list_robot@osf.io', 'subscribed': True})  # Routing robot

    update_multiple_users_in_list(node_id, members_list)

@require_mailgun
def delete_list(node_id):
    """ Deletes list on MailGun
    :param str node_id: ID of the node in question
    """
    resp = requests.delete(
        '{}/{}'.format(MAILGUN_BASE_LISTS_URL, address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY)
    )
    if resp.status_code not in [200, 404]:
        raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

@require_mailgun
def update_title(node_id):
    """ Updates the title of a mailing list to match the list's project
    :param str node_id: ID of the node in question
    """
    from website.models import Node  # avoid circular import
    node = Node.load(node_id)

    resp = requests.put(
        '{}/{}'.format(MAILGUN_BASE_LISTS_URL, address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'name': list_title(node)
        }
    )
    if resp.status_code != 200:
        raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

@require_mailgun
def update_single_user_in_list(node_id, user_id, email=None, enabled=True, old_email=None):
    """ Adds/updates single member of a mailing list on Mailgun
    Called to add, subscribe, or unsubscribe a user.

    :param str node: ID of node in question
    :param str user: ID of user to update
    :param str email: email address to add. If None, `user.username` assumed.
    :param bool enabled: Enable or disable user?
    :param str old_email: Previous email of this user in list, included when user changes primary email.
    """
    from website.models import Node, User  # avoid circular import
    node = Node.load(node_id)
    user = User.load(user_id)
    email = email or user.username

    if old_email:
        resp = requests.put(
            '{}/{}/members/{}'.format(MAILGUN_BASE_LISTS_URL, address(node_id), old_email),
            auth=('api', settings.MAILGUN_API_KEY),
            data={
                'subscribed': 'no',
                'vars': json.dumps({'_id': user_id, 'primary': False})
            }
        )
        if resp.status_code not in [200, 404]:
            raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

    resp = requests.post(
        '{}/{}/members'.format(MAILGUN_BASE_LISTS_URL, address(node._id)),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'address': email,
            'subscribed': enabled and email == user.username and user not in get_unsubscribes(node),
            'vars': json.dumps({'_id': user._id, 'primary': email == user.username or bool(old_email)}),
            'upsert': True
        }
    )
    if resp.status_code != 200:
        raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

@require_mailgun
def remove_user_from_list(node_id, user_id):
    """ Removes single member of a mailing list on Mailgun
    Called when a contributor is removed from a Node.

    :param str node_id: ID of node in question
    :param str user_id: ID of user to remove
    """
    from website.models import User  # avoid circular import
    user = User.load(user_id)

    for email in user.emails:
        resp = requests.delete(
            '{}/{}/members/{}'.format(MAILGUN_BASE_LISTS_URL, address(node_id), email),
            auth=('api', settings.MAILGUN_API_KEY)
        )
        if resp.status_code not in [200, 404]:
            raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

@require_mailgun
def update_multiple_users_in_list(node_id, members):
    """ Adds/updates members of a mailing list on Mailgun

    :param str node_id: The id of the node in question
    :param list members: List of json-formatted user dicts to add/enable/update
    """
    resp = requests.post(
        '{}/{}/members.json'.format(MAILGUN_BASE_LISTS_URL, address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'upsert': True,
            'members': json.dumps(members)
        }
    )
    if resp.status_code != 200:
        raise HTTPError(resp.status_code, data={'message_long': resp.message or resp.json or ''})

@require_mailgun
def full_update(node_id):
    """ Matches remote list with internal representation
    :param str node_id: The node to update the mailing list for
    """
    from website.models import Node  # avoid circular import
    node = Node.load(node_id)

    info, members = get_list(node_id)

    if node.is_deleted:
        delete_list(node_id)
    elif node.mailing_enabled:
        if 'list' in info.keys():
            info = info['list']
            remote_subscribes = [member['address'] for member in members['items'] if member['subscribed']].sort()
            local_subscribes = [user.username for user in get_recipients(node)].sort()

            if info['name'] != list_title(node):
                # Update title if necessary
                update_title(node_id, node.title)

            if remote_subscribes != local_subscribes:
                # Push local changes
                members_list = jsonify_users_list(node.contributors, unsubs=get_unsubscribes(node))
                update_multiple_users_in_list(node_id, members_list)

            # Delete any noncontribs
            from website.models import User  # avoid circular import
            member_ids = set([member['vars']['_id'] for member in members['items'] if member.get('vars', {}).get('_id', False)])
            for u_id in member_ids:
                if u_id not in node.contributors:
                    user = User.load(u_id)
                    if user:
                        remove_user_from_list(node_id, u_id)

        else:
            create_list(node_id)
    else:
        if 'list' in info.keys():
            delete_list(node_id)


###############################################################################
# Celery Queued tasks
###############################################################################

@queued_task
@app.task
def celery_create_list(*args, **kwargs):
    create_list(*args, **kwargs)

@queued_task
@app.task
def celery_delete_list(*args, **kwargs):
    delete_list(*args, **kwargs)

@queued_task
@app.task
def celery_update_title(*args, **kwargs):
    update_title(*args, **kwargs)

@queued_task
@app.task
def celery_update_single_user_in_list(*args, **kwargs):
    update_single_user_in_list(*args, **kwargs)

@queued_task
@app.task
def celery_remove_user_from_list(*args, **kwargs):
    remove_user_from_list(*args, **kwargs)

@queued_task
@app.task
def celery_update_multiple_users_in_list(*args, **kwargs):
    update_multiple_users_in_list(*args, **kwargs)

@queued_task
@app.task
def celery_full_update(*args, **kwargs):
    full_update(*args, **kwargs)


###############################################################################
# Signalled Functions
###############################################################################

@contributor_added.connect
def subscribe_contributor_to_mailing_list(node, contributor, auth=None):
    if node.mailing_enabled and contributor.is_active:
        subscription = node.get_or_create_mailing_list_subscription()
        subscription.add_user_to_subscription(contributor, 'email_transactional', save=True)
        celery_update_single_user_in_list(node._id, contributor._id)
        node.mailing_updated = True
        node.save()

@contributor_removed.connect
def unsubscribe_contributor_from_mailing_list(node, user, auth=None):
    if node.mailing_enabled:
        subscription = node.get_or_create_mailing_list_subscription()
    else:
        from website.models import NotificationSubscription  # avoid circular import
        subscription = NotificationSubscription.load(to_subscription_key(node._id, 'mailing_list_events'))
    if subscription:
        subscription.remove_user_from_subscription(user)
        node.mailing_updated = True
        node.save()
    celery_remove_user_from_list(node._id, user._id)


@user_confirmed.connect
def resubscribe_on_confirm(user):
    for node in user.contributed:
        subscribe_contributor_to_mailing_list(node, user)

@node_deleted.connect
def remove_list_for_deleted_node(node):
    node.mailing_updated = True
    node.save()
    celery_delete_list(node._id)


###############################################################################
# Mailing List Helper Functions
###############################################################################

def jsonify_users_list(users, unsubs=[]):
    """ Serializes list of users for Mailgun

    :param list users: users to serialize
    :param list unsubs: unsubscribed users
    """
    members_list = []
    for member in users:
        for email in member.emails:
            members_list.append({
                'address': email,
                'subscribed': member not in unsubs and email == member.username,
                'vars': {'_id': member._id, 'primary': email == member.username}
            })
    return members_list

def address(node_id):
    return '{}@{}'.format(node_id, furl(settings.DOMAIN).host)

def list_title(node):
    return '{} Mailing List'.format(node.title)

def find_email(long_email):
    # allow for both "{email}" syntax and "{name} <{email}>" syntax
    if '<' in long_email:
        email_match = ANGLE_BRACKETS_REGEX.search(long_email)
        if email_match:
            return email_match.groups()[0].lower().strip()
    elif '@' in long_email:
        return long_email.lower().strip()
    return None

def log_message(**kwargs):
    """ Acquires and logs messages sent through Mailgun"""
    from website.models import Node  # avoid circular imports
    message = request.form
    target = find_email(message['To'])
    node = Node.load(re.search(r'[a-z0-9]*@', target).group(0)[:-1])

    sender_email = find_email(message['From'])
    sender = get_user(email=sender_email)

    # Create a log of this mailing event
    MailingListEventLog(
        email_content=message,
        destination_node=node,
        sending_user=sender,
    ).save()

def unsubscribe_user_hook(*args, **kwargs):
    """ Hook triggered by MailGun when user unsubscribes.
    See `Unsubscribes Webhook` below https://documentation.mailgun.com/user_manual.html#tracking-unsubscribes
    for possible kwargs
    """
    message = request.form
    unsub = message.get('recipient')
    mailing_list = message.get('mailing-list')
    if not unsub or not mailing_list:
        raise Exception()
    from website.models import User, NotificationSubscription  # avoid circular imports
    user = User.find_one('username', 'eq', unsub)
    node_id = mailing_list.split('@')[0]
    subscription = NotificationSubscription.load(to_subscription_key(node_id, 'mailing_list_events'))
    subscription.add_user_to_subscription(user, 'none', save=True)

def get_recipients(node):
    if node.mailing_enabled:
        from website.models import NotificationSubscription  # avoid circular import
        subscription = NotificationSubscription.load(to_subscription_key(node._id, 'mailing_list_events'))
        return [u for u in subscription.email_transactional]
    return []

def get_unsubscribes(node):
    # Non-subscribed users not guaranteed to be in subscription.none
    # Safer to calculate it
    if node.mailing_enabled:
        recipients = get_recipients(node)
        return [u for u in node.contributors if u not in recipients]
    return []
