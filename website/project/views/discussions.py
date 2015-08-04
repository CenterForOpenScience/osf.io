# -*- coding: utf-8 -*-

import re

from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.auth.decorators import collect_auth
from framework.auth.core import User

from website import mails
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
    must_be_contributor
)
from website.util.permissions import ADMIN
from website.models import Node


###############################################################################
# Internal Calls
###############################################################################


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def enable_discussions(node, **kwargs):
    node.discussions.enable(save=True)


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def disable_discussions(node, **kwargs):
    node.discussions.disable(save=True)


@must_be_valid_project
@collect_auth
@must_be_contributor
@must_not_be_registration
def set_subscription(node, auth, **kwargs):
    subscription = request.json.get('discussionsSub')
    subscribed = True if subscription == 'subscribed' else False
    if subscribed:
        node.discussions.subscribe_member(auth.user._id, save=True)
    else:
        node.discussions.unsubscribe_member(auth.user._id, save=True)


###############################################################################
# MailGun Calls
###############################################################################


def route_message(**kwargs):
    message = request.form
    target_address = message['To']
    node_id = re.search(r'[a-z0-9]*@', target_address).group(0)[:-1]
    sender_email = message['From']
    # allow for both "{email}" syntax and "{name} <{email}>" syntax
    if ' ' in sender_email:
        sender_email = re.search(r'<\S*>$', sender_email).group(0)[1:-1]

    sender = User.find_by_email(sender_email)
    if sender:
        sender = sender[0]
    else:
        mails.send_mail(to_addr=sender_email,
                        mail=mails.DISCUSSIONS_EMAIL_REJECTED,
                        user=None,
                        target_address=target_address,
                        node_type='',
                        node_url='',
                        reason='no_user')
        return

    try:
        node = Node.find_one(Q('_id', 'eq', node_id))
    except NoResultsFound:
        mails.send_mail(to_addr=sender_email,
                        mail=mails.DISCUSSIONS_EMAIL_REJECTED,
                        user=sender,
                        target_address=target_address,
                        node_type='',
                        node_url='',
                        reason='project_dne')
        return

    if node.is_deleted:
        mails.send_mail(to_addr=sender_email,
                        mail=mails.DISCUSSIONS_EMAIL_REJECTED,
                        user=sender,
                        target_address=target_address,
                        node_type=node.project_or_component,
                        node_url=node.absolute_url,
                        reason='project_deleted')
        return

    if sender not in node.contributors:
        if node.is_public:
            mails.send_mail(to_addr=sender_email,
                            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
                            user=sender,
                            target_address=target_address,
                            node_type=node.project_or_component,
                            node_url=node.absolute_url,
                            reason='no_access')
        else:
            mails.send_mail(to_addr=sender_email,
                            mail=mails.DISCUSSIONS_EMAIL_REJECTED,
                            user=sender,
                            target_address=target_address,
                            node_type='',
                            node_url='',
                            reason='project_dne')
        return

    if not node.discussions.is_enabled:
        mails.send_mail(to_addr=sender_email,
                        mail=mails.DISCUSSIONS_EMAIL_REJECTED,
                        user=sender,
                        target_address=target_address,
                        node_type=node.project_or_component,
                        node_url=node.absolute_url,
                        is_admin='admin' in node.get_permissions(sender),
                        reason='discussions_disabled')
        return
