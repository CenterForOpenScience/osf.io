# -*- coding: utf-8 -*-

import uuid

import requests
from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.auth import Auth
from framework.auth.core import get_user

from website import util
from website import security
from website import settings
from website.project import new_node
from website.models import User, Node, MailRecord


def record_message(message, created):
    record = MailRecord(
        data=message.raw,
        records=created,
    )
    record.save()


def get_or_create_user(fullname, address, is_spam):
    """Get or create user by email address.

    :param str fullname: User full name
    :param str address: User email address
    :param bool is_spam: User flagged as potential spam
    :return: Tuple of (user, created)
    """
    user = get_user(email=address)
    if user:
        return user, False
    else:
        password = str(uuid.uuid4())
        user = User.create_confirmed(address, password, fullname)
        user.verification_key = security.random_string(20)
        if is_spam:
            user.system_tags.append('is_spam')
        # user.save()
        # signals.user_confirmed.send(user)
        return user, True


def get_or_create_node(title, user):
    """Get or create node by title and creating user.

    :param str title: Node title
    :param User user: User creating node
    :return: Tuple of (node, created)
    """
    try:
        node = Node.find_one(
            Q('title', 'iexact', title)
            & Q('contributors', 'eq', user._id)
        )
        return node, False
    except ModularOdmException:
        node = new_node('project', title, user)
        return node, True


def provision_node(conference, message, node, user):
    """
    :param Conference conference:
    :param ConferenceMessage message:
    :param Node node:
    :param User user:
    """
    auth = Auth(user=user)

    node.update_node_wiki('home', message.text, auth)
    node.add_contributors(prepare_contributors(conference.admins), log=False)

    if not message.is_spam and conference.public_projects:
        node.set_privacy('public', meeting_creation=True, auth=auth)

    node.add_tag(message.conference_name, auth=auth)
    node.add_tag(message.conference_category, auth=auth)
    node.system_tags.extend(['emailed', message.conference_name, message.conference_category])
    if message.is_spam:
        node.system_tags.append('spam')

    node.save()


def prepare_contributors(admins):
    return [
        {
            'user': admin,
            'permissions': ['read', 'write', 'admin'],
            'visible': False,
        }
        for admin in admins
    ]


def upload_attachment(user, node, attachment):
    attachment.seek(0)
    name = '/' + (attachment.filename or settings.MISSING_FILE_NAME)
    content = attachment.read()
    upload_url = util.waterbutler_url_for('upload', 'osfstorage', name, node, user=user)

    requests.put(
        upload_url,
        data=content,
    )


def upload_attachments(user, node, attachments):
    for attachment in attachments:
        upload_attachment(user, node, attachment)
