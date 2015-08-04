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
    return node_id + '@' + settings.MAILGUN_DOMAIN


def node_url(node_id):
    return settings.DOMAIN + node_id


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
        raise HTTPError(400)
    info = json.loads(info.text)

    members = requests.get(
        'https://api.mailgun.net/v3/lists/{}/members'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
    )
    if members.status_code != 200 and members.status_code != 404:
        raise HTTPError(400)
    members = json.loads(members.text)

    return info, members


def create_list(node_id, node_title, emails, subscriptions):
    """ Creates a new mailing list on Mailgun with all emails and subscriptions
    :param node_id: The id of the node in question
    :param node_title: The title of the node in question
    :param emails: List of emails on the mailing list
    :param subscriptions: List of subscribed emails on the mailing list
    """
    res = requests.post(
        'https://api.mailgun.net/v3/lists',
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'address': address(node_id),
            'name': '{} Mailing List'.format(node_title),
            'access_level': 'members'
        }
    )
    if res.status_code != 200:
        raise HTTPError(400)

    for email in emails:
        add_member(node_id, email, subscriptions[email])

    # send_message(node_id, node_title, {
    #     'subject': 'Mailing List Created for {}'.format(node_title),
    #     'text': 'A mailing list has been created/enabled for the project {}.'.format(node_title)
    # })


def delete_list(node_id):
    """ Deletes a mailing list from Mailgun
    :param node_id: The id of the node in question
    """
    res = requests.delete(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY)
    )
    if res.status_code != 200:
        raise HTTPError(400)


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
        raise HTTPError(400)


def add_member(node_id, email, subscription):
    """ Adds a member to a mailing list on Mailgun
    :param node_id: The id of the node in question
    :param email: The email of the member being added
    :param subscription: The initial subscription status
    """
    res = requests.post(
        'https://api.mailgun.net/v3/lists/{}/members'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'subscribed': subscription,
            'address': email,
            'vars': json.dumps({'project_url': node_url(node_id)})
        }
    )
    if res.status_code != 200:
        raise HTTPError(400)


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
        raise HTTPError(400)


def update_member(node_id, email, subscription):
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
        raise HTTPError(400)


###############################################################################
# Celery Tasks
###############################################################################


@queued_task
@app.task
def update_list(node_id, node_title, list_enabled, emails, subscriptions):
    """ Updates Mailgun to match the current status of a node's discussions
    :param node_id: The id of the node whose mailing list is being updated
    :param node_title: The title of the node in question
    :param list_enabled: The status of the node's email discussions (is_enabled)
    :param emails: List of emails on the node's mailing list
    :param subscriptions: List of emails subscribed to the node's mailing list
    """
    # Need to put the sender in the list of members to avoid potential conflicts
    emails.add(address(node_id))
    # Convert subscriptions to a dictionary for ease of use in functions
    subscriptions = {email: email in subscriptions for email in emails}

    info, members = get_list(node_id)

    if list_enabled:

        if 'list' in info.keys():
            info = info['list']
            members = members['items']

            if info['name'] != '{} Mailing List'.format(node_title):
                update_title(node_id, node_title)

            list_emails = set([member['address'] for member in members])
            list_subscriptions = {member['address']: member['subscribed'] for member in members}

            emails_to_add = emails.difference(list_emails)
            for email in emails_to_add:
                add_member(node_id, email, subscriptions[email])

            emails_to_remove = list_emails.difference(emails)
            for email in emails_to_remove:
                remove_member(node_id, email)

            for email in emails.intersection(list_emails):
                if subscriptions[email] != list_subscriptions[email]:
                    update_member(node_id, email, subscriptions[email])

        else:
            create_list(node_id, node_title, emails, subscriptions)
            return

    else:

        if 'list' in info.keys():
            delete_list(node_id)


@queued_task
@app.task
def send_message(node_id, node_title, message):
    """ Sends a message from the node through the given mailing list
    :param node_id:
    :param node_title:
    :param message:
    :return:
    """
    res = requests.post(
        'https://api.mailgun.net/v3/{}/messages'.format(settings.MAILGUN_DOMAIN),
        auth=('api', settings.MAILGUN_API_KEY),
        data={'from': '{0} Mailing List <{1}>'.format(node_title, address(node_id)),
              'to': address(node_id),
              'subject': message['subject'],
              'html': '<html>{}</html>'.format(message['text'])})
    if res.status_code != 200:
        raise HTTPError(400)
