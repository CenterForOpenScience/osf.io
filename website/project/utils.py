# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from website.project.views import node

from website import mails
from website import settings

# Alias the project serializer
serialize_node = node._view_project

def send_embargo_email(node, user):
    """ Sends pending embargo announcement email to contributors. Project
    admins will also receive approval/disapproval information.
    :param node: Node being embargoed
    :param user: User to be emailed
    """

    embargo_end_date = node.embargo.end_date
    registration_link = node.web_url_for('view_project', _absolute=True)
    initiators_fullname = node.embargo.initiated_by.fullname

    if node.has_permission(user, 'admin'):
        approval_token = node.embargo.approval_state[user._id]['approval_token']
        disapproval_token = node.embargo.approval_state[user._id]['disapproval_token']
        approval_link = node.web_url_for(
            'node_registration_embargo_approve',
            token=approval_token,
            _absolute=True)
        disapproval_link = node.web_url_for(
            'node_registration_embargo_disapprove',
            token=disapproval_token,
            _absolute=True)
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
