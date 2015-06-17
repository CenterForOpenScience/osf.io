# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from modularodm import Q

from website import mails
from website import settings
from website.project.model import Node

from website.util.permissions import ADMIN

# Alias the project serializer
from website.project.views.node import _view_project
serialize_node = _view_project

def get_embargo_urls(node, user):
    approval_token, disapproval_token = None, None
    if node.has_permission(user, ADMIN):
        approval_token = node.embargo.approval_state[user._id]['approval_token']
        disapproval_token = node.embargo.approval_state[user._id]['disapproval_token']

    return {
        'view': node.web_url_for('view_project', _absolute=True),
        'approve': node.web_url_for(
            'node_registration_embargo_approve',
            token=approval_token,
            _absolute=True
        ) if approval_token else None,
        'disapprove': node.web_url_for(
            'node_registration_embargo_disapprove',
            token=disapproval_token,
            _absolute=True
        ) if disapproval_token else None,
    }

def send_embargo_email(node, user, urls=None):
    """ Sends pending embargo announcement email to contributors. Project
    admins will also receive approval/disapproval information.
    :param node: Node being embargoed
    :param user: User to be emailed
    """
    urls = urls or get_embargo_urls(node, user)

    embargo_end_date = node.embargo.end_date
    registration_link = urls['view']
    initiators_fullname = node.embargo.initiated_by.fullname
    if node.has_permission(user, ADMIN):
        approval_link = urls['approve']
        disapproval_link = urls['disapprove']
        approval_time_span = settings.EMBARGO_PENDING_TIME.days * 24

        mails.send_mail(
            user.username,
            mails.PENDING_EMBARGO_ADMIN,
            'plain',
            user=user,
            initiated_by=initiators_fullname,
            approval_link=approval_link,
            disapproval_link=disapproval_link,
            registration_link=registration_link,
            embargo_end_date=embargo_end_date,
            approval_time_span=approval_time_span
        )
    else:
        mails.send_mail(
            user.username,
            mails.PENDING_EMBARGO_NON_ADMIN,
            user=user,
            initiated_by=initiators_fullname,
            registration_link=registration_link,
            embargo_end_date=embargo_end_date,
        )

def recent_public_registrations(n=10):
    recent_query = (
        Q('category', 'eq', 'project') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )
    registrations = Node.find(
        recent_query &
        Q('is_registration', 'eq', True)
    ).sort(
        '-registered_date'
    )
    for reg in registrations:
        if not n:
            break
        if reg.is_retracted or reg.pending_embargo:
            continue
        n = n - 1
        yield reg
