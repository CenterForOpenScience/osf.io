# -*- coding: utf-8 -*-

import os
import re
import hmac
import json
import uuid
import hashlib
import logging
import urlparse
import httplib as http
from nameparser import HumanName

from framework import Q
from framework.forms.utils import sanitize
from framework.exceptions import HTTPError
from framework.flask import request
from framework.auth.decorators import Auth

from website import settings, security
from website.util import web_url_for
from website.models import User, Node, MailRecord
from website.project import new_node
from website.project.views.file import prepare_file
from website.util.sanitize import deep_clean
from website.mails import send_mail, CONFERENCE_SUBMITTED, CONFERENCE_FAILED

logger = logging.getLogger(__name__)


def request_to_data():
    return {
        'headers': dict(request.headers),
        'form': request.form.to_dict(),
        'args': request.args.to_dict(),
    }


# TODO: Move me to database
MEETING_DATA = {
    'spsp2014': {
        'name': 'SPSP 2014',
        'info_url': 'http://cos.io/spsp/',
        'active': False,
    },
    'asb2014': {
        'name': 'ASB 2014',
        'info_url': 'http://www.sebiologists.org/meetings/talks_posters.html',
        'active': True,
    },
    'aps2014': {
        'name': 'APS 2014',
        'info_url': 'http://centerforopenscience.org/aps/',
        'active': True,
    },
    'annopeer2014': {
        'name': '#annopeer',
        'info_url': '',
        'active': True,
    },
}


def get_or_create_user(fullname, address, is_spam):
    """Get or create user by email address.

    """
    user = User.find(Q('username', 'iexact', address))
    user = user[0] if user.count() else None
    user_created = False
    if user is None:
        password = str(uuid.uuid4())
        user = User.create_confirmed(address, password, fullname)
        user.verification_key = security.random_string(20)
        # Flag as potential spam account if Mailgun detected spam
        if is_spam:
            user.system_tags.append('is_spam')
        user.save()
        user_created = True

    return user, user_created


def add_poster_by_email(conf_id, recipient, address, fullname, subject,
                        message, attachments, tags=None, system_tags=None,
                        is_spam=False):

    # Fail if no attachments
    if not attachments:
        send_mail(
            address,
            CONFERENCE_FAILED,
            fullname=fullname
        )
        return

    # Use address as name if name missing
    fullname = fullname or address.split('@')[0]

    created = []

    user, user_created = get_or_create_user(fullname, address, is_spam)

    if user_created:
        created.append(user)
        set_password_url = web_url_for(
            'reset_password',
            verification_key=user.verification_key,
        )
    else:
        set_password_url = None

    auth = Auth(user=user)

    # Find or create node
    node = Node.find(Q('title', 'iexact', subject))
    node = node[0] if node.count() else None
    if node is None or not node.is_contributor(user):
        node = new_node('project', subject, user)
        created.append(node)

    # Make public if confident that this is not spam
    if not is_spam:
        node.set_privacy('public', auth=auth)
    else:
        logger.warn(
            'Possible spam detected in email modification of '
            'user {0} / node {1}'.format(
                user._id, node._id,
            )
        )

    # Add body
    node.update_node_wiki(
        page='home',
        content=sanitize(message),
        auth=auth,
    )

    # Add tags
    presentation_type = 'talk' if 'talk' in recipient else 'poster'

    tags = tags or []
    tags.append(presentation_type)
    for tag in tags:
        node.add_tag(tag, auth=auth)

    # Add system tags
    system_tags = system_tags or []
    system_tags.append(presentation_type)
    system_tags.append('emailed')
    if is_spam:
        system_tags.append('spam')
    for tag in system_tags:
        if tag not in node.system_tags:
            node.system_tags.append(tag)

    # Add files
    files = []
    for attachment in attachments:
        name, content, content_type, size = prepare_file(attachment)
        file_object = node.add_file(
            auth=auth,
            file_name=name,
            content=content,
            size=size,
            content_type=content_type,
        )
        files.append(file_object)

    # Save changes
    node.save()

    # Add mail record
    mail_record = MailRecord(
        data=request_to_data(),
        records=created,
    )
    mail_record.save()

    # Send confirmation email
    send_mail(
        address,
        CONFERENCE_SUBMITTED,
        conf_full_name=MEETING_DATA[conf_id]['name'],
        conf_view_url=urlparse.urljoin(
            settings.DOMAIN, os.path.join('view', conf_id)
        ),
        fullname=fullname,
        user_created=user_created,
        set_password_url=set_password_url,
        profile_url=user.absolute_url,
        node_url=urlparse.urljoin(settings.DOMAIN, node.url),
        file_url=urlparse.urljoin(settings.DOMAIN, files[0].download_url(node)),
        presentation_type=presentation_type,
        is_spam=is_spam,
    )


def get_mailgun_subject(form):
    subject = form['subject']
    subject = re.sub(r'^re:', '', subject, flags=re.I)
    subject = re.sub(r'^fwd:', '', subject, flags=re.I)
    subject = subject.strip()
    return subject


def get_mailgun_from():
    """Get name and email address of sender. Note: this uses the `from` field
    instead of the `sender` field, meaning that envelope headers are ignored.

    """
    name = re.sub(r'<.*?>', '', request.form['from']).strip()
    name = name.replace('"', '')
    name = str(HumanName(name))
    match = re.search(r'<(.*?)>', request.form['from'])
    address = match.groups()[0] if match else ''
    return name, address


def get_mailgun_attachments():
    attachment_count = request.form.get('attachment-count', 0)
    attachment_count = int(attachment_count)
    return [
        request.files['attachment-{0}'.format(idx + 1)]
        for idx in range(attachment_count)
    ]


def check_mailgun_headers():
    """Verify that request comes from Mailgun. Based on sample code from
    http://documentation.mailgun.com/user_manual.html#webhooks

    """
    # TODO: Cap request payload at 25MB
    signature = hmac.new(
        key=settings.MAILGUN_API_KEY,
        msg='{}{}'.format(
            request.form['timestamp'],
            request.form['token'],
        ),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if signature != request.form['signature']:
        logger.warn('Invalid headers on incoming mail')
        raise HTTPError(http.NOT_ACCEPTABLE)


SSCORE_MAX_VALUE = 5
DKIM_PASS_VALUES = ['Pass']
SPF_PASS_VALUES = ['Pass', 'Neutral']


def check_mailgun_spam():
    """Check DKIM and SPF verification to determine whether incoming message
    is spam. Returns `True` if either criterion indicates spam, else False.
    See http://documentation.mailgun.com/user_manual.html#spam-filter for
    details.

    :return: Is message spam

    """
    try:
        sscore_header = float(request.form.get('X-Mailgun-Sscore'))
    except (TypeError, ValueError):
        return True
    dkim_header = request.form.get('X-Mailgun-Dkim-Check-Result')
    spf_header = request.form.get('X-Mailgun-Spf')

    return (
        (sscore_header and sscore_header > SSCORE_MAX_VALUE) or
        (dkim_header and dkim_header not in DKIM_PASS_VALUES) or
        (spf_header and spf_header not in SPF_PASS_VALUES)
    )


def parse_mailgun_receiver(form):
    """Check Mailgun recipient and extract test status, meeting name, and
    content category. Crash if test status does not match development mode in
    settings.

    :returns: Tuple of (meeting, category)

    """
    match = re.search(
        r'''^
            (?P<test>test-)?
            (?P<meeting>\w*?)
            -
            (?P<category>poster|talk)
            @osf\.io
            $''',
        form['recipient'],
        flags=re.IGNORECASE | re.VERBOSE,
    )

    if not match:
        raise HTTPError(http.NOT_ACCEPTABLE)

    data = match.groupdict()

    if bool(settings.DEV_MODE) != bool(data):
        raise HTTPError(http.NOT_ACCEPTABLE)

    return data['meeting'], data['category']


def meeting_hook():

    # Fail if not from Mailgun
    check_mailgun_headers()

    form = deep_clean(request.form.to_dict())
    meeting, category = parse_mailgun_receiver(form)

    # Fail if not found or inactive
    # Note: Throw 406 to disable Mailgun retries
    try:
        if not MEETING_DATA[meeting]['active']:
            raise HTTPError(http.NOT_ACCEPTABLE)
    except KeyError:
        raise HTTPError(http.NOT_ACCEPTABLE)

    name, address = get_mailgun_from()

    # Add poster
    add_poster_by_email(
        conf_id=meeting,
        recipient=form['recipient'],
        address=address,
        fullname=name,
        subject=get_mailgun_subject(form),
        message=form['stripped-text'],
        attachments=get_mailgun_attachments(),
        tags=[meeting],
        system_tags=[meeting],
        is_spam=check_mailgun_spam(),
    )


def _render_conference_node(node, idx):

    # Hack: Avoid circular import
    from website.addons.osffiles.model import NodeFile

    if node.files_current:
        file_id = node.files_current.values()[0]
        file_obj = NodeFile.load(file_id)
        download_url = file_obj.download_url(node)
        download_count = file_obj.download_count(node)
    else:
        download_url = ''
        download_count = 0

    return {
        'id': idx,
        'title': node.title,
        'nodeUrl': node.url,
        'author': node.creator.family_name if node.creator else '',
        'authorUrl': node.creator.url if node.creator else '',
        'category': 'talk' if 'talk' in node.system_tags else 'poster',
        'download': download_count,
        'downloadUrl': download_url,
    }


def conference_results(meeting):

    if meeting not in MEETING_DATA:
        raise HTTPError(http.NOT_FOUND)

    nodes = Node.find(
        Q('tags', 'eq', meeting) &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )

    data = [
        _render_conference_node(each, idx)
        for idx, each in enumerate(nodes)
    ]

    return {
        'data': json.dumps(data),
        'meeting': MEETING_DATA[meeting],
    }
