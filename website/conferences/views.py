# -*- coding: utf-8 -*-

import json
import httplib
import logging

import requests
from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.auth import Auth
from framework.flask import request
from framework.exceptions import HTTPError

from website import settings
from website.util import web_url_for
from website.models import Node
from website.mails import send_mail, CONFERENCE_SUBMITTED, CONFERENCE_FAILED

from website.conferences import utils
from website.conferences.message import ConferenceMessage
from website.conferences.model import Conference, MailRecord

logger = logging.getLogger(__name__)


def request_to_data():
    return {
        'headers': dict(request.headers),
        'form': request.form.to_dict(),
        'args': request.args.to_dict(),
    }


def prepare_contributors(conference):
    return [
        {
            'user': contributor,
            'permissions': ['read', 'write', 'admin'],
            'visible': False,
        }
        for contributor in conference.admins
    ]


def upload_attachment(user, node, attachment):
    from website.addons.osfstorage import utils as storage_utils
    attachment.seek(0)
    name = attachment.filename or settings.MISSING_FILE_NAME
    content_type = attachment.content_type
    content = attachment.read()
    size = content.tell()
    upload_url = storage_utils.get_upload_url(node, user, size, content_type, name)
    requests.put(
        upload_url,
        data=content,
        headers={'Content-Type': attachment.content_type},
    )


def upload_attachments(user, node, attachments):
    for attachment in attachments:
        upload_attachment(user, node, attachment)


def meeting_hook():

    message = ConferenceMessage()

    try:
        conference = Conference.find_one(Q('endpoint', 'iexact', message.conference_name))
    except ModularOdmException:
        raise HTTPError(httplib.NOT_FOUND)

    if not conference.active:
        logger.error('Conference {0} is not active'.format(conference.endpoint))
        raise HTTPError(httplib.NOT_ACCEPTABLE)

    # Add poster
    add_poster_by_email(conference=conference, message=message)


def provision_node(conference, message, node, user):
    """
    :param Conference conference:
    :param ConferenceMessage message:
    :param Node node:
    :param User user:
    """
    auth = Auth(user=user)

    node.update_node_wiki('home', message, auth)
    node.add_contributors(prepare_contributors(conference.admins), log=False)

    if not message.is_spam and conference.public_projects:
        node.set_privacy('public', auth=auth)

    node.add_tag(message.conference_category, auth=auth)
    node.system_tags.extend(['emailed', message.conference_category])
    if message.is_spam:
        node.system_tags.append('spam')

    upload_attachments(user, node, message.attachments)

    node.save()


def add_poster_by_email(conference, message):
    """
    :param Conference conference:
    :param ConferenceMessage message:
    """
    # Fail if no attachments
    if not message.attachments:
        return send_mail(
            message.sender_email,
            CONFERENCE_FAILED,
            fullname=message.sender_display,
        )

    created = []

    user, user_created = utils.get_or_create_user(
        message.sender_display,
        message.sender_email,
        message.is_spam,
    )
    if user_created:
        created.append(user)

    if user_created:
        created.append(user)
        set_password_url = web_url_for(
            'reset_password',
            verification_key=user.verification_key,
        )
    else:
        set_password_url = None

    node, node_created = utils.get_or_create_node(message.subject, user)
    if node_created:
        created.append(node)

    provision_node(conference, message, node, user)

    download_url = node.web_url_for(
        'osf_storage_view_file',
        path=message.attachments[0].filename,
        action='download',
        _absolute=True,
    )

    # Add mail record
    mail_record = MailRecord(
        data=request_to_data(),
        records=created,
    )
    mail_record.save()

    # Send confirmation email
    send_mail(
        message.address,
        CONFERENCE_SUBMITTED,
        conf_full_name=conference.name,
        conf_view_url=web_url_for(
            'conference_results',
            meeting=message.conference_name,
        ),
        fullname=message.sender_display,
        user_created=user_created,
        set_password_url=set_password_url,
        profile_url=user.absolute_url,
        node_url=node.absolute_url,
        file_url=download_url,
        presentation_type=message.conference_category,
        is_spam=message.is_spam,
    )


def _render_conference_node(node, idx):
    storage_settings = node.get_addon('osfstorage')
    if storage_settings.file_tree and storage_settings.file_tree.children:
        record = storage_settings.file_tree.children[0]
        download_count = record.get_download_count()
        download_url = node.web_url_for(
            'osf_storage_view_file',
            path=record.path,
            action='download',
        )
    else:
        download_url = ''
        download_count = 0

    author = node.visible_contributors[0]

    return {
        'id': idx,
        'title': node.title,
        'nodeUrl': node.url,
        'author': author.family_name,
        'authorUrl': node.creator.url,
        'category': 'talk' if 'talk' in node.system_tags else 'poster',
        'download': download_count,
        'downloadUrl': download_url,
    }


def conference_data(meeting):
    try:
        Conference.find_one(Q('endpoint', 'iexact', meeting))
    except ModularOdmException:
        raise HTTPError(httplib.NOT_FOUND)

    nodes = Node.find(
        Q('tags', 'eq', meeting) &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )

    data = [
        _render_conference_node(each, idx)
        for idx, each in enumerate(nodes)
    ]
    return data


def conference_results(meeting):
    """Return the data for the grid view for a conference.

    :param str meeting: Endpoint name for a conference.
    """
    try:
        conf = Conference.find_one(Q('endpoint', 'iexact', meeting))
    except ModularOdmException:
        raise HTTPError(httplib.NOT_FOUND)

    data = conference_data(meeting)

    return {
        'data': json.dumps(data),
        'label': meeting,
        'meeting': conf.to_storage(),
    }


def conference_view(**kwargs):

    meetings = []
    for conf in Conference.find():
        query = (
            Q('tags', 'eq', conf.endpoint)
            & Q('is_public', 'eq', True)
            & Q('is_deleted', 'eq', False)
        )
        projects = Node.find(query)
        submissions = projects.count()
        if submissions < settings.CONFERNCE_MIN_COUNT:
            continue
        meetings.append({
            'name': conf.name,
            'active': conf.active,
            'url': web_url_for('conference_results', meeting=conf.endpoint),
            'submissions': submissions,
        })
    meetings.sort(key=lambda meeting: meeting['submissions'], reverse=True)

    return {'meetings': meetings}
