"""Functions that listen for event signals and queue up emails.
All triggered emails live here.
"""
from datetime import datetime

from modularodm import Q

from website import mails, settings
from framework.auth import signals as auth_signals
from website.project import signals as project_signals
from website.conferences import signals as conference_signals


@auth_signals.unconfirmed_user_created.connect
def queue_no_addon_email(user):
    """Queue an email for user who has not connected an addon after
    `settings.NO_ADDON_WAIT_TIME` months of signing up for the OSF.
    """
    mails.queue_mail(
        to_addr=user.username,
        mail=mails.NO_ADDON,
        send_at=datetime.utcnow() + settings.NO_ADDON_WAIT_TIME,
        user=user,
        fullname=user.fullname
    )

@project_signals.privacy_set_public.connect
def queue_first_public_project_email(user, node, meeting_creation):
    """Queue and email after user has made their first
    non-OSF4M project public.
    """
    if not meeting_creation:
        sent_mail = mails.QueuedMail.find(Q('user', 'eq', user) & Q('sent_at', 'ne', None) &
                                          Q('email_type', 'eq', mails.NEW_PUBLIC_PROJECT_TYPE))
        if not sent_mail.count():
            mails.queue_mail(
                to_addr=user.username,
                mail=mails.NEW_PUBLIC_PROJECT,
                send_at=datetime.utcnow() + settings.NEW_PUBLIC_PROJECT_WAIT_TIME,
                user=user,
                nid=node._id,
                fullname=user.fullname,
                project_title=node.title
            )

@conference_signals.osf4m_user_created.connect
def queue_osf4m_welcome_email(user, conference, node):
    """Queue an email once a new user is created for OSF for Meetings"""
    root = (node.get_addon('osfstorage')).get_root()
    root_children = [child for child in root.children if child.is_file]
    mails.queue_mail(
        to_addr=user.username,
        mail=mails.WELCOME_OSF4M,
        send_at=datetime.utcnow() + settings.WELCOME_OSF4M_WAIT_TIME,
        user=user,
        conference=conference.name,
        fullname=user.fullname,
        fid=root_children[0]._id if len(root_children) else None
    )
