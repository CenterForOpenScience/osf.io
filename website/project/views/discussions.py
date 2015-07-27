# -*- coding: utf-8 -*-

import re

from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.auth.decorators import must_be_logged_in, collect_auth

from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
)
from website.util.permissions import ADMIN, READ, WRITE
from website.models import Node


###############################################################################
# Internal Calls
###############################################################################


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def enable(node, **kwargs):
    node.discussions.enable()


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def disable(node, **kwargs):
    node.discussions.disable()


@must_be_valid_project
@collect_auth
@must_not_be_registration
def subscribe(node, auth, **kwargs):
    node.discussions.subscribe_member(auth.user.email)


@must_be_valid_project
@collect_auth
@must_not_be_registration
def unsubscribe(node, auth, **kwargs):
    node.discussions.unsubscribe_member(auth.user.email)


###############################################################################
# MailGun Calls
###############################################################################


def route_message(**kwargs):
    message = request.form
    attachments = request.files.values()
    node_id = re.search(r'[a-z0-9]*@', message['To']).group(0)[:-1]
    sender_email = message['From']
    # allow for both "{email}" syntax and "{name} <{email}>" syntax
    if ' ' in sender_email:
        sender_email = re.search(r'<\S*>$', sender_email).group(0)[1:-1]
    parsed_message = {
        'From': sender_email,
        'subject': message['subject'],
        'text': message['stripped-text'],
        'attachments': attachments
    }
    node = Node.find_one(Q('_id','eq',node_id))


# def unsubscribe_by_mail(**kwargs):
#     info = request.form
#     node_id = re.search(r'[a-z0-9]*@', info['mailing-list']).group(0)[:-1]
#     email = info['recipient']
#     # allow for both "{email}" syntax and "{name} <{email}>" syntax
#     if ' ' in email:
#         email = re.search(r'<\S*>$', email).group(0)[1:-1]
#     node = Node.find_one(Q('_id','eq',node_id))
#     node.unsubscribe_by_mail(email)
