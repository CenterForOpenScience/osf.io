# -*- coding: utf-8 -*-
from modularodm import Q

from datetime import datetime, timedelta

def _week_check(email):
    sent_emails = email.find_others_to()
    for email_ in sent_emails:
        if email_.sent_at > (datetime.utcnow() - timedelta(weeks=1)):
            return False
    return True

def no_addon(email):
    if _week_check(email):
        if len(email.user.get_addons()) is 0:
            return True
    return False

def no_login(email):
    if _week_check(email):
        return True
    return False

def new_public_project(email):
    if _week_check(email):
        from website.models import Node
        node = Node.find_one(Q('_id', 'eq', email.data['nid']))
        if node.is_public:
            return True
    return False

def welcome_osf4m(email):
    if _week_check(email):
        return True
    return False
