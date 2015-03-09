# -*- coding: utf-8 -*-

import json
import httplib
import logging

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.exceptions import HTTPError
from framework.transactions.context import TokuTransaction
from framework.transactions.handlers import no_auto_transaction

from website import settings
from website.models import Node
from website.util import web_url_for
from website.mails import send_mail
from website.mails import CONFERENCE_SUBMITTED, CONFERENCE_INACTIVE, CONFERENCE_FAILED

from website.conferences import utils
from website.conferences.message import ConferenceMessage, ConferenceError
from website.conferences.model import Conference


logger = logging.getLogger(__name__)


@no_auto_transaction
def meeting_hook():
    """View function for email conference submission.
    """
    message = ConferenceMessage()

    try:
        message.verify()
    except ConferenceError as error:
        logger.error(error)
        raise HTTPError(httplib.NOT_ACCEPTABLE)

    try:
        conference = Conference.get_by_endpoint(message.conference_name, active=False)
    except ConferenceError as error:
        logger.error(error)
        raise HTTPError(httplib.NOT_ACCEPTABLE)

    if not conference.active:
        send_mail(
            message.sender_email,
            CONFERENCE_INACTIVE,
            fullname=message.sender_display,
            presentations_url=web_url_for('conference_view', _absolute=True),
        )
        raise HTTPError(httplib.NOT_ACCEPTABLE)

    add_poster_by_email(conference=conference, message=message)


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

    with TokuTransaction():
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
                _absolute=True,
            )
        else:
            set_password_url = None

        node, node_created = utils.get_or_create_node(message.subject, user)
        if node_created:
            created.append(node)

        utils.provision_node(conference, message, node, user)
        utils.record_message(message, created)

    utils.upload_attachments(user, node, message.attachments)

    download_url = node.web_url_for(
        'addon_view_or_download_file',
        path=message.attachments[0].filename,
        provider='osfstorage',
        action='download',
        _absolute=True,
    )

    # Send confirmation email
    send_mail(
        message.sender_email,
        CONFERENCE_SUBMITTED,
        conf_full_name=conference.name,
        conf_view_url=web_url_for(
            'conference_results',
            meeting=message.conference_name,
            _absolute=True,
        ),
        fullname=message.sender_display,
        user_created=user_created,
        set_password_url=set_password_url,
        profile_url=user.absolute_url,
        node_url=node.absolute_url,
        file_url=download_url,
        presentation_type=message.conference_category.lower(),
        is_spam=message.is_spam,
    )


def _render_conference_node(node, idx):
    storage_settings = node.get_addon('osfstorage')
    records = storage_settings.file_tree.children if storage_settings.file_tree else []
    try:
        record = next(
            each for each in records
            if not each.is_deleted,
        )
        download_count = record.get_download_count()

        download_url = node.web_url_for(
            'addon_view_or_download_file',
            path=record.path,
            provider='osfstorage',
            action='download',
            _absolute=True,
        )
    except StopIteration:
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
        Q('tags', 'iexact', meeting) &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )

    ret = [
        _render_conference_node(each, idx)
        for idx, each in enumerate(nodes)
    ]
    return ret


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
            Q('tags', 'iexact', conf.endpoint)
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
