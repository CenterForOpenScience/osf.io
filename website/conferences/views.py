# -*- coding: utf-8 -*-

import httplib
import logging
from flask import request

from django.db import transaction
from django_bulk_update.helper import bulk_update
from django.core.paginator import Paginator, EmptyPage

from addons.osfstorage.models import OsfStorageFile
from framework.auth import get_or_create_user
from framework.exceptions import HTTPError
from framework.flask import redirect
from framework import sentry
from framework.transactions.handlers import no_auto_transaction
from osf.models import AbstractNode, Node, Conference, Tag
from website import settings
from website.conferences import utils, signals
from website.conferences.message import ConferenceMessage, ConferenceError
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

        node, node_created = Node.objects.get_or_create(
            title__iexact=message.subject,
            is_deleted=False,
            _contributors__guids___id=user._id,
            defaults={
                'title': message.subject,
                'creator': user
            }
        )
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
    tags = list(node.tags.filter(system=False).values_list('name', flat=True))

    return {
        'id': idx,
        'title': node.title,
        'nodeUrl': node.url,
        'author': author.family_name if author.family_name else author.fullname,
        'authorUrl': author.url,
        'category': conf.field_names['submission1'] if conf.field_names['submission1'] in tags else conf.field_names['submission2'],
        'download': download_count,
        'downloadUrl': download_url,
        'dateCreated': node.created.isoformat(),
        'confName': conf.name,
        'confUrl': web_url_for('conference_results', meeting=conf.endpoint),
        'tags': ' '.join(tags)
    }


def conference_data(meeting, meetings_page=1):
    try:
        conf = Conference.objects.get(endpoint__iexact=meeting)
    except Conference.DoesNotExist:
        raise HTTPError(httplib.NOT_FOUND)

    nodes = AbstractNode.objects.filter(tags__id__in=Tag.objects.filter(name__iexact=meeting, system=False).values_list('id', flat=True), is_public=True, is_deleted=False)
    paginator = Paginator(nodes, 50)
    try:
        selected_nodes = paginator.page(meetings_page)
    except EmptyPage:
        selected_nodes = paginator.page(paginator.num_pages)
    ret = []
    for idx, each in enumerate(selected_nodes.object_list):
        # To handle OSF-8864 where projects with no users caused meetings to be unable to resolve
        try:
            ret.append(_render_conference_node(each, idx, conf))
        except IndexError:
            sentry.log_exception()
    return ret, selected_nodes


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

def get_meetings_page():
    """
    Returns requested page number, fetched from query param.
    If none, returns 1 by default.
    """
    if request.args.get('page', None):
        try:
            return int(request.args.get('page'))
        except ValueError:
            return 1
    return 1

def create_pagination_array(current_page, total_pages):
    """
    Returns an array of page numbers for pagination in UI. Creates similar UI
    to ember addon https://github.com/mharris717/ember-cli-pagination

    For example: [1, 2, '...', 23, 24, 25, 26], where current page is 25.
    Or, [1, 2, '...', 6, 7, 8, 9, 10, '...', 25, 26], where current page is 8.
    : param integer current_page: current page of results being displayed
    : param integer total_pages: total number of pages available
    """
    if total_pages <= 4:
        return range(1, total_pages + 1)

    # Pagination available will always include the first two and last two pages
    start = [1, 2]
    end = [total_pages - 1, total_pages]

    # Middle range of pagination available will take the form:
    # [current - 2, current - 1, current, current + 1, current + 2]
    middle = []
    for page_num in range(current_page - 2, current_page + 3):
        if page_num > 2 and page_num < total_pages - 1:
            middle.append(page_num)

    # If there is a gap between the start range and the middle range, add a '...'
    if not middle or middle[0] != 3:
        middle.insert(0, '...')

    # If gap between middle and end ranges, add a '...'
    if not middle or (middle[-1] != '...' and middle[-1] != (total_pages - 2)):
        middle.append('...')

    # Now flatten the start, middle, and end lists into one! This is your pagination.
    return [item for sublist in [start, middle, end] for item in sublist]

def conference_results(meeting, **kwargs):
    """Return the data for the grid view for a conference.

    :param str meeting: Endpoint name for a conference.
    """
    try:
        conf = Conference.objects.get(endpoint__iexact=meeting)
    except Conference.DoesNotExist:
        raise HTTPError(httplib.NOT_FOUND)

    data, current_page = conference_data(meeting, meetings_page=get_meetings_page())

    return {
        'data': data,
        'label': meeting,
        'meeting': serialize_conference(conf),
        # Needed in order to use base.mako namespace
        'settings': settings,
        'pagination': create_pagination_array(current_page.number, current_page.paginator.num_pages),
        'page': current_page
    }

def conference_submissions(**kwargs):
    """Return data for all OSF4M submissions.

    The total number of submissions for each meeting is calculated and cached
    in the Conference.num_submissions field.
    """
    conferences = Conference.objects.filter(is_meeting=True)
    #  TODO: Revisit this loop, there has to be a way to optimize it
    for conf in conferences:
        # For efficiency, we filter by tag first, then node
        # instead of doing a single Node query
        tags = Tag.objects.filter(system=False, name__iexact=conf.endpoint).values_list('pk', flat=True)
        nodes = AbstractNode.objects.filter(tags__in=tags, is_public=True, is_deleted=False)
        # Cache the number of submissions
        conf.num_submissions = nodes.count()
    bulk_update(conferences, update_fields=['num_submissions'])
    return {'success': True}

def conference_view(**kwargs):
    meetings = []
    for conf in Conference.objects.all():
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
