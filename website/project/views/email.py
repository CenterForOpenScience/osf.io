# -*- coding: utf-8 -*-

import re
import hmac
import uuid
import hashlib
import logging
import urlparse
import httplib as http
from mako.template import Template

from framework import Q
from framework.exceptions import HTTPError
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

You recently tried to create a project on the Open Science Framework via email, but your message did not contain any file attachments. Please try again, making sure to attach the files you'd like to upload to your message.

From the Open Science Framework Robot
''')

CREATED_PROJECT_SUBJECT = 'Project created on Open Science Framework'
MESSAGE_TEMPLATE = Template('''
Hello ${fullname},

Congratulations! You have successfully added your SPSP 2014 poster to the Open Science Framework. If the conference is still going, come by SPSP booth 14 to claim your free Center for Open Science T-shirt (while supplies last)!

% if user_created:
Your account on the Open Science Framework has been created via email. To claim your account, please create a password by clicking here: [ ${set_password_url} ].

% endif
Your SPSP 2014 poster has been added to the Open Science Framework (OSF). To view the persistent link to your poster, click here: [ ${file_url} ].

To view your project page link, where you can add more details about your research, click here: [ ${node_url} ].

Get more from the OSF by enhancing your page with the following:

* Collaborators/contributors to the poster.
* Related details through the wiki.
* Charts, graphs, and data that didn't make it onto the poster.
* Links to related publications or reference lists.
* Connect your GitHub account via add-on integration to share your code.

Visit the Center for Open Science team at SPSP booth 14 to learn more about using the Open Science Framework, our current job opportunities [ http://centerforopenscience.org/jobs/ ], and ways to get involved in replication projects [ http://centerforopenscience.org/spsp/ ]!

Follow COS at @OSFramework on Twitter [ https://twitter.com/OSFramework ]
Like us on Facebook [ https://www.facebook.com/OpenScienceFramework ]

From the Open Science Framework Robot
''')

def add_poster_by_email(address, fullname, subject, attachments, tags=None,
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

    # Find or create user
    user = User.find(Q('username', 'iexact', address))
    user = user[0] if user else None
    user_created = False
    set_password_url = None
    if user is None:
        password = str(uuid.uuid4())
        user = register(address, password, fullname)
        user.verification_key = helper.random_string(20)
        set_password_url = urlparse.urljoin(
            settings.DOMAIN, 'resetpassword/{0}/'.format(
                user.verification_key
            )
        )
        user.save()
        user_created = True

    auth = Auth(user=user)

    # Find or create node
    node = Node.find(Q('title', 'iexact', subject))
    node = node[0] if node else None
    if node is None or not node.is_contributor(user):
        node = new_node('project', subject, user)

    # Make public if confident that this is not spam
    if not is_spam:
        node.set_permissions('public', auth=auth)
    else:
        logger.warn(
            'Possible spam detected in email modification of user {} / node {}'.format(
                user._id, node._id,
            )
        )

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
        node_url=urlparse.urljoin(settings.DOMAIN, node.url),
        file_url=urlparse.urljoin(settings.DOMAIN, files[0].download_url(node)),
    )

    # Send confirmation email
    send_email(
        from_addr=settings.FROM_EMAIL,
        to_addr=address,
        subject=CREATED_PROJECT_SUBJECT,
        message=message,
        mimetype='plain',
    )

def get_mailgun_from():
    sender = request.form['from']
    sender = re.sub(r'<.*?>', '', sender).strip()
    return sender

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
    dkim_header = request.form['X-Mailgun-Dkim-Check-Result']
    spf_header = request.form['X-Mailgun-Spf']

    return (
        dkim_header not in DKIM_PASS_VALUES or
        spf_header not in SPF_PASS_VALUES
    )

def spsp_poster_hook():

    # Fail if not from Mailgun
    check_mailgun_headers()

    # Add poster
    add_poster_by_email(
        address=request.form['sender'],
        fullname=get_mailgun_from(),
        subject=request.form['subject'],
        attachments=get_mailgun_attachments(),
        tags=['spsp2014', 'poster'],
        is_spam=check_mailgun_spam(),
    )
