# -*- coding: utf-8 -*-

import requests
import json

from framework.tasks import app
from framework.tasks.handlers import queued_task
from framework.exceptions import HTTPError

from website import settings

###############################################################################
# Base Functions
###############################################################################


def address(node_id):
    return node_id + '@' + settings.SHORT_DOMAIN


def require_project_mailing(func):
    """ Execute function only if enable_project_mailing setting is true """
    def wrapper(*args, **kwargs):
        if settings.ENABLE_PROJECT_MAILING:
            return func(*args, **kwargs)
        return None
    return wrapper


@require_project_mailing
def get_list(node_id):
    """ Returns information about the mailing list from Mailgun
    :param node_id: The id of the node in question
    :returns: info, members: Two dictionaries about list and members
    """
    info = requests.get(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
    )
    if info.status_code != 200 and info.status_code != 404:
        raise HTTPError(info.status_code)
    info = json.loads(info.text)

    members = requests.get(
        'https://api.mailgun.net/v3/lists/{}/members'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
    )
    if members.status_code != 200 and members.status_code != 404:
        raise HTTPError(members.status_code)
    members = json.loads(members.text)

    return info, members


@require_project_mailing
def create_list(node_id, title, url, contributors, unsubs):
    """ Creates a new mailing list on Mailgun with all emails and subscriptions
    :param node_id: The id of the node in question
    :param title: The node's title
    :param url: The url to access the node
    :param contributors: The emails of the node's contributors
    :param unsubs: The emails of the node's unsubbed users
    """
    res = requests.post(
        'https://api.mailgun.net/v3/lists',
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'address': address(node_id),
            'name': '{} Mailing List'.format(title),
            'access_level': 'members'
        }
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)

    members_list = []
    for member in contributors:
        members_list.append({
            'address': member,
            'subscribed': member not in unsubs,
            'vars': {'project_url': url}
        })

    update_members(node_id, members_list)


@require_project_mailing
def delete_list(node_id):
    """ Deletes a mailing list on Mailgun
    :param node_id: The id of the node in question
    """
    res = requests.delete(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY)
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)


@require_project_mailing
def update_title(node_id, node_title):
    """ Updates the title of a mailing list to match the list's project
    :param node_id: The id of the node in question
    :param node_title: The new title
    """
    res = requests.put(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'name': '{} Mailing List'.format(node_title)
        }
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)


@require_project_mailing
def update_members(node_id, members):
    """ Adds/updates members of a mailing list on Mailgun
    :param node_id: The id of the node in question
    :param members: A list of member dictionaries
    """
    res = requests.post(
        'https://api.mailgun.net/v3/lists/{}/members.json'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'upsert': True,
            'members': json.dumps(members)
        }
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)


@require_project_mailing
def remove_member(node_id, email):
    """ Removes a member from a mailing list on Mailgun
    :param node_id: The id of the node in question
    :param email: The email of the member to be removed
    """
    res = requests.delete(
        'https://api.mailgun.net/v3/lists/{0}/members/{1}'.format(address(node_id), email),
        auth=('api', settings.MAILGUN_API_KEY)
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)


@require_project_mailing
def match_members(node_id, url, contributors, unsubs):
    """ Matches the members of the list on Mailgun with the local one
    :param node_id: The id of the node in question
    :param url: The url to access the node
    :param contributors: The emails of the node's contributors
    :param unsubs: The emails of the node's unsubscribed users
    """
    res = requests.get(
        'https://api.mailgun.net/v3/lists/{}/members'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)

    mailgun_members = json.loads(res.text)['items']
    members = {user: user not in unsubs for user in contributors}

    removed_members = []
    for member in mailgun_members:
        if member['address'] not in members:
            removed_members.append(member['address'])

    members_list = []
    for member in members:
        members_list.append({
            'address': member,
            'subscribed': members[member],
            'vars': {'project_url': url}
        })

    for member in removed_members:
        members_list.append({
            'address': member,
            'subscribed': False,
        })

    update_members(node_id, members_list)

    for member in removed_members:
        remove_member(node_id, member)


@require_project_mailing
def update_email(node_id, old_email, new_email):
    """ Updates the email of a mailing list's member on Mailgun
    :param node_id: The id of the node in question
    :param old_email: The email address being replaced
    :param new_email: The new email address
    """
    res = requests.put(
        'https://api.mailgun.net/v3/lists/{0}/members/{1}'.format(address(node_id), old_email),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'address': new_email,
        }
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)


@require_project_mailing
def update_subscription(node_id, email, subscription):
    """ Updates the subscription status of a member on Mailgun
    :param node_id: The id of the node in question
    :param email: The email of the member that needs to be updated
    :param subscription: The new subscription status
    """
    res = requests.put(
        'https://api.mailgun.net/v3/lists/{0}/members/{1}'.format(address(node_id), email),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'subscribed': subscription,
        }
    )
    if res.status_code != 200:
        raise HTTPError(res.status_code)


###############################################################################
# Celery Tasks
###############################################################################

# Celery versions of all functions that might need to be called with Celery.
# These functions are only necessary while there is no way to either use Celery
# or not on the same function. Note that this functionality changing will break
# many of the tests due to mocking, so change with caution.


@require_project_mailing
@queued_task
@app.task
def celery_create_list(*args, **kwargs):
    create_list(*args, **kwargs)


@require_project_mailing
@queued_task
@app.task
def celery_delete_list(*args, **kwargs):
    delete_list(*args, **kwargs)


@require_project_mailing
@queued_task
@app.task
def celery_match_members(*args, **kwargs):
    match_members(*args, **kwargs)


@require_project_mailing
@queued_task
@app.task
def celery_update_title(*args, **kwargs):
    update_title(*args, **kwargs)


@require_project_mailing
@queued_task
@app.task
def celery_update_email(*args, **kwargs):
    update_email(*args, **kwargs)


# TODO: Remove probably
# @queued_task
# @app.task
# def send_message(node_id, user_fullname, message):
#     """ Sends a message from the node through the given mailing list
#     :param node_id: The id of the node in question
#     :param user_fullname: The user sending the message
#     :param message: Dictionary with subject and text of the email to be sent
#     """
#     res = requests.post(
#         'https://api.mailgun.net/v3/{}/messages'.format(settings.SHORT_DOMAIN),
#         auth=('api', settings.MAILGUN_API_KEY),
#         data={'from': '{0} <{1}>'.format(user_fullname, address(node_id)),
#               'to': address(node_id),
#               'subject': message['subject'],
#               'html': '<html>{}</html>'.format(message['text'])})
#     if res.status_code != 200:
#         raise HTTPError(res.status_code)


###############################################################################
# Full Update
###############################################################################


@require_project_mailing
def full_update(node):
    """ Fully updates the mailing list of a node to match its current status
    :param node: The node whose mailing list is being updated
    :return bool: Whether or not the update succeeded
    """
    info, members = get_list(node._id)

    if node.mailing_enabled:

        if 'list' in info.keys():
            info = info['list']
            members = {member['address']: member['subscribed'] for member in members['items']}

            emails, unsubs = node.mailing_params['contributors'], node.mailing_unsubs

            subscriptions = {email: email not in unsubs for email in emails}

            if info['name'] != '{} Mailing List'.format(node.title):
                update_title(node._id, node.title)

            if members != subscriptions:
                match_members(**node.mailing_params)

        else:
            create_list(title=node.title, **node.mailing_params)

    else:

        if 'list' in info.keys():
            delete_list(node._id)
