# -*- coding: utf-8 -*-

import re
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


CREATE_FAILED_SUBJECT = 'Open Science Framework Error: No files attached'
CREATE_FAILED_TEMPLATE = Template('''
Hello ${fullname},

You recently tried to create a project on the Open Science Framework via email, but your
message did not contain any file attachments. Please try again, making sure to attach the files
you'd like to upload to your message.

From the Open Science Framework Robot
''')

CREATED_PROJECT_SUBJECT = 'Project created on Open Science Framework'
MESSAGE_TEMPLATE = Template('''
Hello ${fullname},

Congratulations! You have successfully added your SPSP 2014 poster to the Open Science Framework.
Come by SPSP booth 14 to claim your free COS T-shirt!

% if user_created:
    Your account on the Open Science Framework has been created via email. To
    claim your account, please create a password by clicking here: [ ${set_password_url} ].
% endif

Your SPSP 2014 poster has been added to the Open Science Framework (OSF). To view the persistent link to your
poster, click here: <a href="${file_url}">${file_url}</a>. To view your project page link, where you can
add more details about your research, click here: [ ${node_url} ].

Get more from the OSF by enhancing your page with the following:

* Collaborators/contributors to the poster.
* Related details through the wiki.
* Charts, graphs, and data that didn't make it onto the poster.
* Links to related publications or reference lists.
* Connect your GitHub account via add-on integration to share your code.

Visit the Center for Open Science team at SPSP booth 14 to learn more about using the Open Science Framework,
our current job opportunities [ http://centerforopenscience.org/jobs/ ], and ways to get involved in
(and rewarded for!) replication projects [ http://centerforopenscience.org/spsp/ ]!

Follow COS at @OSFramework on Twitter [ https://twitter.com/OSFramework ] or
Like us on Facebook [ https://www.facebook.com/OpenScienceFramework ].

From the Open Science Framework Robot
''')

def add_poster_by_email(address, fullname, subject, message, attachments, tags=None):

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

    # Find or create user
    user = User.find(Q('username', 'iexact', address))
    user = user[0] if user else None
    user_created = False
    set_password_url = None
    if user is None:
        password = str(uuid.uuid4())
        user = register(address, password, fullname)
        set_password_url = urlparse.urljoin(settings.DOMAIN, 'resetpassword')
        user.verification_key = helper.random_string(20)
        user.save()
        user_created = True

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

    # Render message
    message = MESSAGE_TEMPLATE.render(
        fullname=fullname,
        user_created=user_created,
        set_password_url=set_password_url,
        node_url=node.url,
        file_url=files[0].url,
    )

    # Send confirmation email
    send_email(
        from_addr=settings.FROM_EMAIL,
        to_addr=address,
        subject=CREATED_PROJECT_SUBJECT,
        message=message,
        mimetype='plain',
    )

def get_mailgun_sender():
    sender = request.form['sender']
    sender = re.sub(r'<.*?>', '', sender).strip()
    return sender

def get_mailgun_attachments():
    return [
        request.files['attachment-{0}'.format(idx + 1)]
        for idx in range(int(request.form['attachment-count']))
    ]

def spsp_poster_hook():
    add_poster_by_email(
        address=get_mailgun_sender(),
        fullname=request.form['from'],
        subject=request.form['subject'],
        message=request.form['stripped-text'],
        attachments=get_mailgun_attachments(),
        tags=['spsp2014', 'poster'],
    )
