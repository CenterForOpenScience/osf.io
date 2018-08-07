# -*- coding: utf-8 -*-
import requests

from framework.auth import Auth

from website import settings
from osf.models import MailRecord
from api.base.utils import waterbutler_api_url_for


def record_message(message, node_created, user_created):
    record = MailRecord.objects.create(
        data=message.raw,
    )
    if user_created:
        record.users_created.add(user_created)
    record.nodes_created.add(node_created)
    record.save()


def provision_node(conference, message, node, user):
    """
    :param Conference conference:
    :param ConferenceMessage message:
    :param Node node:
    :param User user:
    """
    auth = Auth(user=user)

    node.update_node_wiki('home', message.text, auth)
    if conference.admins.exists():
        node.add_contributors(prepare_contributors(conference.admins.all()), log=False)

    if not message.is_spam and conference.public_projects:
        node.set_privacy('public', meeting_creation=True, auth=auth)

    node.add_tag(message.conference_name, auth=auth)
    node.add_tag(message.conference_category, auth=auth)
    for systag in ['emailed', message.conference_name, message.conference_category]:
        node.add_system_tag(systag, save=False)
    if message.is_spam:
        node.add_system_tag('spam', save=False)

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
    name = (attachment.filename or settings.MISSING_FILE_NAME)
    content = attachment.read()
    upload_url = waterbutler_api_url_for(node._id, 'osfstorage', name=name, base_url=node.osfstorage_region.waterbutler_url, cookie=user.get_or_create_cookie(), _internal=True)

    requests.put(
        upload_url,
        data=content,
    )


def upload_attachments(user, node, attachments):
    for attachment in attachments:
        upload_attachment(user, node, attachment)
