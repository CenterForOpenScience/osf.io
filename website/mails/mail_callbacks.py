# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from modularodm import Q

def no_addon(email):
    if len(email.user.get_addons()) is 0:
        return True

def no_login(email):
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
    upload = OsfStorageFileNode.find_one(Q('_id', 'eq', email.data['fid']))
    all_files = list(OsfStorageFileNode.find(Q('node_settings', 'eq', upload.node_settings)))
    email.data['downloads'] = 0
    for file_ in all_files:
        email.data['downloads'] += file_.get_download_count()
    email.save()
    return True
