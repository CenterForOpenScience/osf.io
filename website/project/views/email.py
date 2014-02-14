# -*- coding: utf-8 -*-

import uuid
import logging
import urlparse
from mako.template import Template

from framework import Q
from framework.flask import request
from framework.auth import helper
from framework.auth import register
from framework.auth.decorators import Auth
from framework.email.tasks import send_email

from website import settings
from website.models import User, Node
from website.project import new_node
from website.project.views.file import prepare_file

logger = logging.getLogger(__name__)


SET_PASSWORD_SUBJECT = 'Set your Open Science Framework password'
SET_PASSWORD_TEMPLATE = Template('''
Hello ${fullname},

Your account on the Open Science Framework has been created via email. To
create a password for your account, click here: <a href="${url}">${url}</a>.

From the Open Science Robot.
''')

CREATED_PROJECT_SUBJECT = 'Project created on Open Science Framework'
MESSAGE_TEMPLATE = Template('''
Hello ${fullname},

Your SPSP poster has been added to the Open Science Framework. To view your
poster, click here: <a href="${url}">${url}</a>.

From the Open Science Robot.
''')

def send_password_set_email(user):

    user.verification_key = helper.random_string(20)
    user.save()

    url = urlparse.urljoin(settings.DOMAIN, 'resetpassword')
    message = SET_PASSWORD_TEMPLATE.render(
        fullname=user.fullname,
        url=url,
    )

    send_email(
        from_addr=settings.FROM_EMAIL,
        to_addr=user.username,
        subject=SET_PASSWORD_SUBJECT,
        message=message,
        mimetype='plain',
    )

def add_poster_by_email(address, fullname, subject, message, attachments, tags=None):

    # Find or create user
    user = User.find(Q('username', 'iexact', address))
    user = user[0] if user else None
    if user is None:
        password = str(uuid.uuid4())
        user = register(address, password, fullname)
        send_password_set_email(user)

    auth = Auth(user=user)

    # Find or create node
    node = Node.find(Q('title', 'iexact', subject))
    node = node[0] if node else None
    if node is None or not node.is_contributor(user):
        node = new_node('project', subject, user, message)

    # Make public
    node.set_permissions('public', auth=auth)

    # Add tags
    for tag in (tags or []):
        node.add_tag(tag, auth=auth)

    # Add files
    for attachment in attachments:
        name, content, content_type, size = prepare_file(attachment)
        node.add_file(
            auth=auth,
            file_name=name,
            content=content,
            size=size,
            content_type=content_type,
        )

    # Render message
    message = MESSAGE_TEMPLATE.render(
        fullname=fullname,
        url=node.url,
    )

    # Send confirmation email
    send_email(
        from_addr=settings.FROM_EMAIL,
        to_addr=address,
        subject=CREATED_PROJECT_SUBJECT,
        message=message,
        mimetype='plain',
    )

def get_mailgun_attachments():
    return [
        request.files['attachment-{0}'.format(idx + 1)]
        for idx in range(int(request.form['attachment-count']))
    ]

def spsp_poster_hook():
    add_poster_by_email(
        address=request.form['sender'],
        fullname=request.form['from'],
        subject=request.form['subject'],
        message=request.form['stripped-text'],
        attachments=get_mailgun_attachments(),
        tags=['spsp2014', 'poster'],
    )
