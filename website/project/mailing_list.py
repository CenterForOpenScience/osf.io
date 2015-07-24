# -*- coding: utf-8 -*-

import requests
import json

from framework import sentry
from framework.tasks import app
from framework.tasks.handlers import queued_task
from framework.auth.signals import user_confirmed
from framework.exceptions import HTTPError

from website import settings
from website.util import waterbutler_url_for

from website.settings.local import MAILGUN_API_KEY, MAILGUN_DOMAIN, OWN_URL

###############################################################################
# Base Functions
###############################################################################

def address(node_id):
    return node_id + '@' + MAILGUN_DOMAIN

def project_url(node_id):
    return OWN_URL + node_id

def list_sender(node_id, node_title):
    return {
        'name': '{} Mailing List'.format(node_title),
        'email': address(node_id),
        'subscribed': False
    }

def get_list(node_id):
    info = requests.get(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', MAILGUN_API_KEY),
    )
    if info.status_code != 200 and info.status_code != 404:
        raise HTTPError(400)
    info = json.loads(info.text)

    members = requests.get(
        'https://api.mailgun.net/v3/lists/{}/members'.format(address(node_id)),
        auth=('api', MAILGUN_API_KEY),
    )
    if members.status_code != 200 and members.status_code != 404:
        raise HTTPError(400)
    members = json.loads(members.text)

    return info, members

def create_list(node_id, node_title, subscriptions):
    res = requests.post(
        'https://api.mailgun.net/v3/lists',
        auth=('api', MAILGUN_API_KEY),
        data={
            'address': address(node_id),
            'name': '{} Mailing List'.format(node_title),
            'access_level': 'members'
        }
    )
    if res.status_code != 200:
        raise HTTPError(400)
    for _id in subscriptions.keys():
        add_member(node_id, subscriptions[_id], _id)
    send_message(node_id, node_title, {
        'subject': 'Mailing List Created for {}'.format(node_title),
        'text': 'A mailing list has been created/enabled for the project {}.'.format(node_title)
    })

def delete_list(node_id):
    res = requests.delete(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', MAILGUN_API_KEY)
    )
    if res.status_code != 200:
        raise HTTPError(400)

def update_title(node_id, node_title):
    res = requests.put(
        'https://api.mailgun.net/v3/lists/{}'.format(address(node_id)),
        auth=('api', MAILGUN_API_KEY),
        data={
            'name': '{} Mailing List'.format(node_title)
        }
    )
    if res.status_code != 200:
        raise HTTPError(400)

def add_member(node_id, user, user_id):
    res = requests.post(
        'https://api.mailgun.net/v3/lists/{}/members'.format(address(node_id)),
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': user['subscribed'],
            'address': user['email'],
            'name': user['name'],
            'vars': json.dumps({'project_url': project_url(node_id), 'id': user_id})
        }
    )
    if res.status_code != 200:
        raise HTTPError(400)

def remove_member(node_id, email):
    res = requests.delete(
        'https://api.mailgun.net/v3/lists/{0}/members/{1}'.format(address(node_id), email),
        auth=('api', MAILGUN_API_KEY)
    )
    if res.status_code != 200:
        raise HTTPError(400)

def update_member(node_id, user, old_email):
    res = requests.put(
        'https://api.mailgun.net/v3/lists/{0}/members/{1}'.format(address(node_id), old_email),
        auth=('api', MAILGUN_API_KEY),
        data={
            'subscribed': user['subscribed'],
            'address': user['email'],
            'name': user['name'],
        }
    )
    if res.status_code != 200:
        raise HTTPError(400)

###############################################################################
# Celery Tasks
###############################################################################

@queued_task
@app.task(bind=True, default_retry_delay=120)
def update_list(self, node_id, node_title, node_has_list, subscriptions):
    # Need to put the sender in the list of members as '' to avoid potential conflicts
    subscriptions[''] = list_sender(node_id, node_title)

    try:
        info, members = get_list(node_id)

        if node_has_list:

            if 'list' in info.keys():
                info = info['list']
                members = members['items']
                list_members = {}
                for member in members:
                    list_members[member['vars']['id']] = {
                        'subscribed': member['subscribed'],
                        'email': member['address'],
                        'name': member['name']
                    }
                if info['name'] != ' Mailing List'.format(node_title):
                    update_title(node_id, node_title)

                ids_to_add = set(subscriptions.keys()).difference(set(list_members.keys()))
                for contrib_id in ids_to_add:
                    add_member(node_id, subscriptions[contrib_id], contrib_id)

                ids_to_remove = set(list_members.keys()).difference(set(subscriptions.keys()))
                for member_id in ids_to_remove:
                    remove_member(node_id, list_members[member_id]['address'])
                    del list_members[member_id]

                for member_id in list_members.keys():
                    if list_members[member_id] != subscriptions[member_id]:
                        update_member(node_id, subscriptions[member_id], list_members[member_id]['email'])

            else:
                create_list(node_id, node_title, subscriptions)
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
            'https://api.mailgun.net/v3/{}/messages'.format(MAILGUN_DOMAIN),
            auth=('api', MAILGUN_API_KEY),
            data={'from': '{0} Mailing List <{1}>'.format(node_title,address(node_id)),
                  'to': address(node_id),
                  'subject': message['subject'],
                  'html': '<html>{}</html>'.format(message['text'])})
        if res.status_code != 200:
            raise HTTPError(400)

    except (HTTPError, requests.ConnectionError):
        self.retry()

