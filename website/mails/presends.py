# -*- coding: utf-8 -*-
from datetime import datetime
from modularodm import Q

from website import settings

def no_addon(email):
    return len(email.user.get_addons()) == 0

def no_login(email):
    from website.models import QueuedMail
    from website.mails import NO_LOGIN_TYPE
    sent = QueuedMail.find(Q('user', 'eq', email.user) & Q('email_type', 'eq', NO_LOGIN_TYPE) & Q('_id', 'ne', email._id))
    if sent.count():
        return False
    return email.user.date_last_login < datetime.utcnow() - settings.NO_LOGIN_WAIT_TIME

def new_public_project(email):
    """ Will check to make sure the project that triggered this presend is still public
    before sending the email. It also checks to make sure this is the first (and only)
    new public project email to be sent

    :param email: QueuedMail object, with 'nid' in its data field
    :return: boolean based on whether the email should be sent
    """

    # In line import to prevent circular importing
    from website.models import Node

    node = Node.load(email.data['nid'])

    if not node:
        return False
    public = email.find_sent_of_same_type_and_user()
    return node.is_public and not len(public)

def welcome_osf4m(email):
    """ presend has two functions. First is to make sure that the user has not
    converted to a regular OSF user by logging in. Second is to populate the
    data field with downloads by finding the file/project (node_settings) and
    counting downloads of all files within that project

    :param email: QueuedMail object with data field including fid
    :return: boolean based on whether the email should be sent
    """
    # In line import to prevent circular importing
    from website.files.models import OsfStorageFileNode
    if email.user.date_last_login:
        if email.user.date_last_login > datetime.utcnow() - settings.WELCOME_OSF4M_WAIT_TIME_GRACE:
            return False
    upload = OsfStorageFileNode.load(email.data['fid'])
    if upload:
        email.data['downloads'] = upload.get_download_count()
    else:
        email.data['downloads'] = 0
    email.save()
    return True
