# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from website import settings
from modularodm import Q
from modularodm.exceptions import NoResultsFound, MultipleResultsFound

def no_addon(email):
    return len(email.user.get_addons()) == 0 and email.user.is_registered

def no_login(email):
    return email.user.is_registered or not email.user.date_last_login > datetime.utcnow() - settings.NO_LOGIN_WAIT_TIME

def new_public_project(email):
    """ Will check to make sure the project that triggered this callback is still public
    before sending the email. It also checks to make sure this is the first (and only)
    new public project email to be sent

    :param email: QueuedMail object, with 'nid' in its data field
    :return: boolean based on whether the email should be sent
    """

    # In line import to prevent circular importing
    from website.models import Node
    try:
        node = Node.find_one(Q('_id', 'eq', email.data['nid']))
    except (NoResultsFound, MultipleResultsFound):
        return False
    public = email.find_same_sent()
    if node.is_public and not len(public):
        return True
    return False

def welcome_osf4m(email):
    """ Callback has two functions. First is to make sure that the user has not
    converted to a regular OSF user by logging in. Second is to populate the
    data field with downloads by finding the file/project (node_settings) and
    counting downloads of all files within that project

    :param email: QueuedMail object with data field including fid
    :return: boolean based on whether the email should be sent
    """
    # In line import to prevent circular importing
    from website.addons.osfstorage.model import OsfStorageFileNode
    if email.user.date_last_login > datetime.utcnow() - timedelta(days=12):
        return False
    try:
        upload = OsfStorageFileNode.find_one(Q('_id', 'eq', email.data['fid']))
        all_files = list(OsfStorageFileNode.find(Q('node_settings', 'eq', upload.node_settings)))
        email.data['downloads'] = 0
        for file_ in all_files:
            email.data['downloads'] += file_.get_download_count() or 0
    except (NoResultsFound, MultipleResultsFound):
        email.data['downloads'] = 0
        pass
    email.save()
    return True
