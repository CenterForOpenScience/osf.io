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


def project_url(node_id):
    return settings.DOMAIN + node_id


def get_list(node_id):
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

    # Add the list sender, so that the OSF can send messages through the list
    add_member(node_id, address(node_id), False)

    for email in emails:
        add_member(node_id, email, subscriptions[email])

    send_message(node_id, node_title, {
        'subject': 'Mailing List Created for {}'.format(node_title),
        'text': 'A mailing list has been created/enabled for the project {}.'.format(node_title)
    })


def delete_list(node_id):
    res = requests.delete(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY)
    )
    if res.status_code != 200:
        raise HTTPError(400)


def update_title(node_id, node_title):
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
    res = requests.post(
        'https://api.mailgun.net/v3/lists/{}/members'.format(address(node_id)),
        auth=('api', settings.MAILGUN_API_KEY),
        data={
            'subscribed': subscription,
            'address': email,
            'vars': json.dumps({'project_url': project_url(node_id)})
        }
    )
    if res.status_code != 200:
        raise HTTPError(400)


def remove_member(node_id, email):
    res = requests.delete(
        'https://api.mailgun.net/v3/lists/{0}/members/{1}'.format(address(node_id), email),
        auth=('api', settings.MAILGUN_API_KEY)
    )
    if res.status_code != 200:
        raise HTTPError(400)


def update_member(node_id, email, subscription):
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
@app.task(bind=True, default_retry_delay=120)
def update_list(self, node_id, node_title, list_enabled, emails, subscriptions):
    # Need to put the sender in the list of members to avoid potential conflicts
    emails.append(address(node_id))
    # Convert subscriptions to a dictionary for ease of use in functions
    subscriptions = {email: email in subscriptions for email in emails}

    try:
        info, members = get_list(node_id)

        if list_enabled:

            if 'list' in info.keys():
                info = info['list']
                members = members['items']

                if info['name'] != '{} Mailing List'.format(node_title):
                    update_title(node_id, node_title)

                emails = set(emails)
                list_emails = set([member['address'] for member in members])

                emails_to_add = emails.difference(list_emails)
                for email in emails_to_add:
                    add_member(node_id, email, subscriptions[email])

                emails_to_remove = list_emails.difference(emails)
                for email in emails_to_remove:
                    remove_member(node_id, email)

                list_subscriptions = {member['address']: member['subscribed'] for member in members}

                for email in emails:
                    if subscriptions[email] != list_subscriptions[email]:
                        update_member(node_id, email, subscriptions[email])

            else:
                create_list(node_id, node_title, emails, subscriptions)
                return

        else:

            if 'list' in info.keys():
                delete_list(node_id)

    except (HTTPError, requests.ConnectionError):
        self.retry()


@queued_task
@app.task(bind=True, default_retry_delay=120)
def send_message(self, node_id, node_title, message):
    try:
        res = requests.post(
            'https://api.mailgun.net/v3/{}/messages'.format(settings.MAILGUN_DOMAIN),
            auth=('api', settings.MAILGUN_API_KEY),
            data={'from': '{0} Mailing List <{1}>'.format(node_title, address(node_id)),
                  'to': address(node_id),
                  'subject': message['subject'],
                  'html': '<html>{}</html>'.format(message['text'])})
        if res.status_code != 200:
            raise HTTPError(400)

    except (HTTPError, requests.ConnectionError):
        self.retry()
