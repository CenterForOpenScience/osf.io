# -*- coding: utf-8 -*-

import httplib
import logging

from django.db import transaction
from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.auth import get_or_create_user
from framework.exceptions import HTTPError
from framework.flask import redirect
from framework.transactions.handlers import no_auto_transaction
from website import settings
from website.conferences import utils, signals
from website.conferences.message import ConferenceMessage, ConferenceError
from website.conferences.model import Conference
from website.files.models import OsfStorageFile
from website.mails import CONFERENCE_SUBMITTED, CONFERENCE_INACTIVE, CONFERENCE_FAILED
from website.mails import send_mail
from website.models import Node, Tag
from website.util import web_url_for

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

    nodes_created = []
    users_created = []

    with transaction.atomic():
        user, user_created = get_or_create_user(
            message.sender_display,
            message.sender_email,
            is_spam=message.is_spam,
        )
        if user_created:
            user.save()  # need to save in order to access m2m fields (e.g. tags)
            users_created.append(user)
            user.add_system_tag('osf4m')
            user.update_date_last_login()
            user.save()

            # must save the user first before accessing user._id
            set_password_url = web_url_for(
                'reset_password_get',
                uid=user._id,
                token=user.verification_key_v2['token'],
                _absolute=True,
            )
        else:
            set_password_url = None

        node, node_created = utils.get_or_create_node(message.subject, user)
        if node_created:
            nodes_created.append(node)
            node.add_system_tag('osf4m')
            node.save()

        utils.provision_node(conference, message, node, user)
        utils.record_message(message, nodes_created, users_created)
    # Prevent circular import error
    from framework.auth import signals as auth_signals
    if user_created:
        auth_signals.user_confirmed.send(user)

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
    if node_created and user_created:
        signals.osf4m_user_created.send(user, conference=conference, node=node)


def _render_conference_node(node, idx, conf):
    record = OsfStorageFile.objects.filter(node=node).first()

    if not record:
        download_url = ''
        download_count = 0
    else:
        download_count = record.get_download_count()
        download_url = node.web_url_for(
            'addon_view_or_download_file',
            path=record.path.strip('/'),
            provider='osfstorage',
            action='download',
            _absolute=True,
        )

    author = node.visible_contributors[0]
    tags = [n.lower() for n in node.tags.filter(system=False).values_list('name', flat=True)]

    return {
        'id': idx,
        'title': node.title,
        'nodeUrl': node.url,
        'author': author.family_name if author.family_name else author.fullname,
        'authorUrl': node.creator.url,
        'category': conf.field_names['submission1'] if conf.field_names['submission1'] in node.system_tags else conf.field_names['submission2'],
        'download': download_count,
        'downloadUrl': download_url,
        'dateCreated': node.date_created.isoformat(),
        'confName': conf.name,
        'confUrl': web_url_for('conference_results', meeting=conf.endpoint),
        'tags': ' '.join(tags)
    }


def conference_data(meeting):
    try:
        conf = Conference.find_one(Q('endpoint', 'iexact', meeting))
    except ModularOdmException:
        raise HTTPError(httplib.NOT_FOUND)

    nodes = Node.objects.filter(tags__id__in=Tag.objects.filter(name__iexact=meeting, system=False).values_list('id', flat=True), is_public=True, is_deleted=False)

    ret = [
        _render_conference_node(each, idx, conf)
        for idx, each in enumerate(nodes)
    ]
    return ret


def redirect_to_meetings(**kwargs):
    return redirect('/meetings/')


def serialize_conference(conf):
    return {
        'active': conf.active,
        'admins': list(conf.admins.all().values_list('guids___id', flat=True)),
        'end_date': conf.end_date,
        'endpoint': conf.endpoint,
        'field_names': conf.field_names,
        'info_url': conf.info_url,
        'is_meeting': conf.is_meeting,
        'location': conf.location,
        'logo_url': conf.logo_url,
        'name': conf.name,
        'num_submissions': conf.num_submissions,
        'poster': conf.poster,
        'public_projects': conf.public_projects,
        'start_date': conf.start_date,
        'talk': conf.talk,
    }


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
        'data': data,
        'label': meeting,
        'meeting': serialize_conference(conf),
        # Needed in order to use base.mako namespace
        'settings': settings,
    }

def conference_submissions(**kwargs):
    """Return data for all OSF4M submissions.

    The total number of submissions for each meeting is calculated and cached
    in the Conference.num_submissions field.
    """
    submissions = []
    #  TODO: Revisit this loop, there has to be a way to optimize it
    for conf in Conference.find():
        if (hasattr(conf, 'is_meeting') and (conf.is_meeting is False)):
            continue
        # For efficiency, we filter by tag first, then node
        # instead of doing a single Node query
        projects = set()

        tags = Tag.find(Q('system', 'eq', False) & Q('name', 'iexact', conf.endpoint.lower())).values_list('pk', flat=True)
        nodes = Node.find(
            Q('tags', 'in', tags) &
            Q('is_public', 'eq', True) &
            Q('is_deleted', 'ne', True)
        )
        projects.update(list(nodes))

        for idx, node in enumerate(projects):
            submissions.append(_render_conference_node(node, idx, conf))
        num_submissions = len(projects)
        # Cache the number of submissions
        conf.num_submissions = num_submissions
        conf.save()
        if num_submissions < settings.CONFERENCE_MIN_COUNT:
            continue
    submissions.sort(key=lambda submission: submission['dateCreated'], reverse=True)
    return {'submissions': submissions}

def conference_view(**kwargs):
    meetings = []
    for conf in Conference.find():
        if conf.num_submissions < settings.CONFERENCE_MIN_COUNT:
            continue
        if (hasattr(conf, 'is_meeting') and (conf.is_meeting is False)):
            continue
        meetings.append({
            'name': conf.name,
            'location': conf.location,
            'end_date': conf.end_date.strftime('%b %d, %Y') if conf.end_date else None,
            'start_date': conf.start_date.strftime('%b %d, %Y') if conf.start_date else None,
            'url': web_url_for('conference_results', meeting=conf.endpoint),
            'count': conf.num_submissions,
        })

    meetings.sort(key=lambda meeting: meeting['count'], reverse=True)
    return {'meetings': meetings}
