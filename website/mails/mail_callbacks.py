# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from website import settings
from modularodm import Q
from modularodm.exceptions import NoResultsFound, MultipleResultsFound

def no_addon(email):
    if len(email.user.get_addons()) is 0 and email.user.is_registered:
        return True

def no_login(email):
    if not email.user.is_registered or email.user.date_last_login > datetime.utcnow() - settings.NO_LOGIN_WAIT_TIME:
        return False
    return True

def new_public_project(email):
    from website.models import Node
    node = Node.find_one(Q('_id', 'eq', email.data['nid']))
    public = email.find_same_sent()
    if node.is_public and not len(public):
        return True
    return False

def welcome_osf4m(email):
    from website.addons.osfstorage.model import OsfStorageFileNode
    if email.user.date_last_login > datetime.utcnow() - timedelta(days=12):
        return False
    try:
        upload = OsfStorageFileNode.find_one(Q('_id', 'eq', email.data['fid']))
        all_files = list(OsfStorageFileNode.find(Q('node_settings', 'eq', upload.node_settings)))
        email.data['downloads'] = 0
        for file_ in all_files:
            email.data['downloads'] += file_.get_download_count()
    except (NoResultsFound, MultipleResultsFound):
        email.data['downloads'] = 0
        pass
    email.save()
    return True
