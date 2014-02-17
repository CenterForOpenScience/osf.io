# -*- coding: utf-8 -*-

import re
import hmac
import json
import uuid
import hashlib
import logging
import urlparse
import httplib as http
from mako.template import Template

from framework import Q
from framework.forms.utils import sanitize
from framework.exceptions import HTTPError
from framework.flask import request
from framework.auth import helper
from framework.auth import register
from framework.auth.decorators import Auth
from framework.email.tasks import send_email

from website import settings
from website.models import User, Node, MailRecord
from website.project import new_node
from website.project.views.file import prepare_file

logger = logging.getLogger(__name__)


CREATE_FAILED_SUBJECT = 'Open Science Framework Error: No files attached'
CREATE_FAILED_TEMPLATE = Template('''
Hello, ${fullname},

You recently tried to create a project on the Open Science Framework via email, but your message did not contain any file attachments. Please try again, making sure to attach the files you'd like to upload to your message.

Sincerely yours,

The OSF Robot
''')

CREATED_PROJECT_SUBJECT = 'Project created on Open Science Framework'
MESSAGE_TEMPLATE = Template('''
Hello, ${fullname},

Congratulations! You have successfully added your SPSP 2014 ${poster_or_talk} to the Open Science Framework (OSF).

% if user_created:
Your account on the Open Science Framework has been created. To claim your account, please create a password by clicking here: [ ${set_password_url} ]. Please verify your profile information at [ ${profile_url} ].

% endif
Your SPSP 2014 poster has been added to the Open Science Framework. You now have a permanent, citable URL, that you can share and more details about your research: [ ${node_url} ].

Get more from the OSF by enhancing your page with the following:

* Collaborators/contributors to the poster
* Charts, graphs, and data that didn't make it onto the poster
* Links to related publications or reference lists
* Connecting your GitHub account via add-on integration

To learn more about the OSF, visit [ http://osf.io/getting-started ], Center for Open Science (COS) job opportunities [ http://cos.io/jobs ], and ways to get involved in replication projects [ http://cos.io/spsp/ ]!

Follow the COS at @OSFramework on Twitter [ https://twitter.com/OSFramework ]
Like us on Facebook [ https://www.facebook.com/OpenScienceFramework ]

Sincerely yours,

The OSF Robot
''')

def request_to_data():
    return {
        'headers': dict(request.headers),
        'form': request.form.to_dict(),
        'args': request.args.to_dict(),
    }

def add_poster_by_email(recipient, address, fullname, subject, message,
                        attachments, tags=None, system_tags=None,
                        is_spam=False):

    # Fail if no attachments
    if not attachments:
        message = CREATE_FAILED_TEMPLATE.render(fullname=fullname)
        send_email(
            from_addr=settings.FROM_EMAIL,
            to_addr=address,
            subject=CREATE_FAILED_SUBJECT,
            message=message,
            mimetype='plain',
        )
        return

    # Use address as name if name missing
    fullname = fullname or address.split('@')[0]

    created = []

    # Find or create user
    user = User.find(Q('username', 'iexact', address))
    user = user[0] if user.count() else None
    user_created = False
    set_password_url = None
    if user is None:
        password = str(uuid.uuid4())
        user = register(address, password, fullname, send_welcome=False)
        user.verification_key = helper.random_string(20)
        set_password_url = urlparse.urljoin(
            settings.DOMAIN, 'resetpassword/{0}/'.format(
                user.verification_key
            )
        )
        user.save()
        user_created = True
        created.append(user)

    auth = Auth(user=user)

    # Find or create node
    node = Node.find(Q('title', 'iexact', subject))
    node = node[0] if node.count() else None
    if node is None or not node.is_contributor(user):
        node = new_node('project', subject, user)
        created.append(node)

    # Make public if confident that this is not spam
    if True:#not is_spam:
        node.set_permissions('public', auth=auth)
    else:
        logger.warn(
            'Possible spam detected in email modification of user {} / node {}'.format(
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
    if 'talk' in recipient:
        poster_or_talk = 'talk'
    else:
        poster_or_talk = 'poster'

    tags = tags or []
    tags.append(poster_or_talk)
    for tag in tags:
        node.add_tag(tag, auth=auth)

    # Add system tags
    system_tags = system_tags or []
    system_tags.append(poster_or_talk)
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

    # Render message
    message = MESSAGE_TEMPLATE.render(
        fullname=fullname,
        user_created=user_created,
        set_password_url=set_password_url,
        profile_url=user.url,
        node_url=urlparse.urljoin(settings.DOMAIN, node.url),
        file_url=urlparse.urljoin(settings.DOMAIN, files[0].download_url(node)),
        poster_or_talk=poster_or_talk,
        is_spam=False,#is_spam,
    )

    # Send confirmation email
    send_email(
        from_addr=settings.FROM_EMAIL,
        to_addr=address,
        subject=CREATED_PROJECT_SUBJECT,
        message=message,
        mimetype='plain',
    )

def get_mailgun_subject():
    subject = request.form['subject']
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
        raise HTTPError(http.BAD_REQUEST)

DKIM_PASS_VALUES = ['Pass']
SPF_PASS_VALUES = ['Pass', 'Neutral']

def check_mailgun_spam():
    """Check DKIM and SPF verification to determine whether incoming message
    is spam. Returns `True` if either criterion indicates spam, else False.
    See http://documentation.mailgun.com/user_manual.html#spam-filter for
    details.

    :return: Is message spam

    """
    dkim_header = request.form.get('X-Mailgun-Dkim-Check-Result')
    spf_header = request.form.get('X-Mailgun-Spf')

    return (
        dkim_header not in DKIM_PASS_VALUES or
        spf_header not in SPF_PASS_VALUES
    )

def spsp_poster_hook():

    # Fail if not from Mailgun
    check_mailgun_headers()
    name, address = get_mailgun_from()

    # Add poster
    add_poster_by_email(
        recipient=request.form['recipient'],
        address=address,
        fullname=name,
        subject=get_mailgun_subject(),
        message=request.form['stripped-text'],
        attachments=get_mailgun_attachments(),
        tags=['spsp2014'],
        system_tags=['spsp2014'],
        is_spam=check_mailgun_spam(),
    )

def _render_spsp_node(node, idx):

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

def spsp_results():

    nodes = Node.find(
        Q('tags', 'eq', 'spsp2014') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )

    data = [
        _render_spsp_node(each, idx)
        for idx, each in enumerate(nodes)
    ]

    return {'data': json.dumps(data)}
