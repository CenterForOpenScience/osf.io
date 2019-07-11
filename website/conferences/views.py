# -*- coding: utf-8 -*-

from rest_framework import status as http_status
import logging

from django.db import transaction, connection
from django.contrib.contenttypes.models import ContentType

from framework.auth import get_or_create_user
from framework.exceptions import HTTPError
from framework.flask import redirect
from framework.transactions.handlers import no_auto_transaction
from osf import features
from osf.models import AbstractNode, Node, Conference, OSFUser
from website import settings
from website.conferences import utils, signals
from website.conferences.message import ConferenceMessage, ConferenceError
from website.ember_osf_web.decorators import ember_flag_is_active
from website.mails import CONFERENCE_SUBMITTED, CONFERENCE_INACTIVE, CONFERENCE_FAILED
from website.mails import send_mail
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
        raise HTTPError(http_status.HTTP_406_NOT_ACCEPTABLE)

    try:
        conference = Conference.get_by_endpoint(message.conference_name, active=False)
    except ConferenceError as error:
        logger.error(error)
        raise HTTPError(http_status.HTTP_406_NOT_ACCEPTABLE)

    if not conference.active:
        send_mail(
            message.sender_email,
            CONFERENCE_INACTIVE,
            fullname=message.sender_display,
            presentations_url=web_url_for('conference_view', _absolute=True),
            can_change_preferences=False,
            logo=settings.OSF_MEETINGS_LOGO,
        )
        raise HTTPError(http_status.HTTP_406_NOT_ACCEPTABLE)

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
            can_change_preferences=False,
            logo=settings.OSF_MEETINGS_LOGO
        )

    with transaction.atomic():
        user, user_created = get_or_create_user(
            message.sender_display,
            message.sender_email,
            is_spam=message.is_spam,
        )
        if user_created:
            if utils.is_valid_email(user.fullname):
                user.fullname = user._id  # Users cannot use an email as their full name

            user.save()  # need to save in order to access m2m fields (e.g. tags)
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

        # Always create a new meeting node
        node = Node.objects.create(
            title=message.subject,
            creator=user
        )
        node.add_system_tag('osf4m')
        node.save()

        utils.provision_node(conference, message, node, user)
        created_user = user if user_created else None
        utils.record_message(message, node, created_user)
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
        can_change_preferences=False,
        logo=settings.OSF_MEETINGS_LOGO
    )
    if user_created:
        signals.osf4m_user_created.send(user, conference=conference, node=node)

def conference_data(meeting):
    try:
        conf = Conference.objects.get(endpoint__iexact=meeting)
    except Conference.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    return conference_submissions_sql(conf)

def conference_submissions_sql(conf):
    """
    Serializes all meeting submissions to a conference (returns array of dictionaries)

    :param obj conf: Conference object.

    """
    submission1_name = conf.field_names['submission1']
    submission2_name = conf.field_names['submission2']
    conference_url = web_url_for('conference_results', meeting=conf.endpoint)
    abstract_node_content_type_id = ContentType.objects.get_for_model(AbstractNode).id
    osf_user_content_type_id = ContentType.objects.get_for_model(OSFUser).id

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT  json_build_object(
                    'id', ROW_NUMBER() OVER (ORDER BY 1),
                    'title', osf_abstractnode.title,
                    'nodeUrl', '/' || GUID._id || '/',
                    'author', CASE WHEN AUTHOR.family_name != '' THEN AUTHOR.family_name ELSE AUTHOR.fullname END,
                    'authorUrl', '/' || AUTHOR_GUID._id || '/',
                    'category', CASE WHEN %s = ANY(TAGS_LIST.tag_list) THEN %s ELSE %s END,
                    'download', COALESCE(DOWNLOAD_COUNT, 0),
                    'downloadUrl', COALESCE('/project/' || GUID._id || '/files/osfstorage/' || FILE._id || '/?action=download', ''),
                    'dateCreated', osf_abstractnode.created,
                    'confName', %s,
                    'confUrl', %s,
                    'tags', array_to_string(TAGS_LIST.tag_list, ' ')
                )
            FROM osf_abstractnode
              INNER JOIN osf_conference_submissions ON (osf_conference_submissions.abstractnode_id = osf_abstractnode.id)
              LEFT JOIN LATERAL(
                SELECT array_agg(osf_tag.name) AS tag_list
                  FROM osf_tag
                  INNER JOIN osf_abstractnode_tags ON (osf_tag.id = osf_abstractnode_tags.tag_id)
                  WHERE (osf_tag.system = FALSE AND osf_abstractnode_tags.abstractnode_id = osf_abstractnode.id)
                ) AS TAGS_LIST ON TRUE -- Concatenates tag names with space in between
              LEFT JOIN LATERAL (
                        SELECT osf_osfuser.*
                        FROM osf_osfuser
                          INNER JOIN osf_contributor ON (osf_contributor.user_id = osf_osfuser.id)
                        WHERE (osf_contributor.node_id = osf_abstractnode.id AND osf_contributor.visible = TRUE)
                        ORDER BY osf_contributor._order ASC
                        LIMIT 1
                        ) AUTHOR ON TRUE  -- Returns first visible contributor
              LEFT JOIN LATERAL (
                SELECT osf_guid._id
                FROM osf_guid
                WHERE (osf_guid.object_id = osf_abstractnode.id AND osf_guid.content_type_id = %s) -- Content type for AbstractNode
                ORDER BY osf_guid.created DESC
                LIMIT 1   -- Returns node guid
              ) GUID ON TRUE
              LEFT JOIN LATERAL (
                SELECT osf_guid._id
                FROM osf_guid
                WHERE (osf_guid.object_id = AUTHOR.id AND osf_guid.content_type_id = %s)  -- Content type for OSFUser
                LIMIT 1
              ) AUTHOR_GUID ON TRUE   -- Returns author_guid
              LEFT JOIN LATERAL (
                SELECT osf_basefilenode.*
                FROM osf_basefilenode
                WHERE (osf_basefilenode.type = 'osf.osfstoragefile'
                       AND osf_basefilenode.provider = 'osfstorage'
                       AND osf_basefilenode.target_content_type_id = %s -- Content type for AbstractNode
                       AND osf_basefilenode.target_object_id = osf_abstractnode.id)
                ORDER BY osf_basefilenode.id ASC
                LIMIT 1 -- Joins file
              ) FILE ON TRUE
              LEFT JOIN LATERAL (
                SELECT P.total AS DOWNLOAD_COUNT
                FROM osf_pagecounter AS P
                WHERE P._id = 'download:' || GUID._id || ':' || FILE._id
                LIMIT 1
              ) DOWNLOAD_COUNT ON TRUE
            -- Get all the nodes for a specific meeting
            WHERE (osf_conference_submissions.conference_id = %s
                   AND osf_abstractnode.is_deleted = FALSE
                   AND osf_abstractnode.is_public = TRUE
                   AND AUTHOR_GUID IS NOT NULL)
            ORDER BY osf_abstractnode.created DESC;

            """, [
                submission1_name,
                submission1_name,
                submission2_name,
                conf.name,
                conference_url,
                abstract_node_content_type_id,
                osf_user_content_type_id,
                abstract_node_content_type_id,
                conf.id,
            ]
        )
        rows = cursor.fetchall()
        return [row[0] for row in rows]

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
        'num_submissions': conf.valid_submissions.count(),
        'poster': conf.poster,
        'public_projects': conf.public_projects,
        'start_date': conf.start_date,
        'talk': conf.talk,
    }

@ember_flag_is_active(features.EMBER_MEETING_DETAIL)
def conference_results(meeting):
    """Return the data for the grid view for a conference.

    :param str meeting: Endpoint name for a conference.
    """
    try:
        conf = Conference.objects.get(endpoint__iexact=meeting)
    except Conference.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    data = conference_data(meeting)

    return {
        'data': data,
        'label': meeting,
        'meeting': serialize_conference(conf),
        # Needed in order to use base.mako namespace
        'settings': settings,
    }


def redirect_to_conference_results(meeting):
    return redirect('/meetings/{}'.format(meeting))


def conference_submissions(**kwargs):
    """
    This view previously cached submissions count on num_submissions field.
    """
    return {'success': True}

@ember_flag_is_active(features.EMBER_MEETINGS)
def conference_view(**kwargs):
    meetings = []
    for conf in Conference.objects.all():
        if conf.valid_submissions < settings.CONFERENCE_MIN_COUNT:
            continue
        if (hasattr(conf, 'is_meeting') and (conf.is_meeting is False)):
            continue
        meetings.append({
            'name': conf.name,
            'location': conf.location,
            'end_date': conf.end_date.strftime('%b %d, %Y') if conf.end_date else None,
            'start_date': conf.start_date.strftime('%b %d, %Y') if conf.start_date else None,
            'url': web_url_for('conference_results', meeting=conf.endpoint),
            'count': conf.valid_submissions.count(),
        })

    meetings.sort(key=lambda meeting: meeting['count'], reverse=True)
    return {'meetings': meetings}
