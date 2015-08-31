# -*- coding: utf-8 -*-
from modularodm import Q

from datetime import datetime, timedelta
from website.models import Node

def _week_check(email):
    sent_emails = email.find_others_to()
    for email_ in sent_emails:
        if email_.sent_at > (datetime.utcnow() - timedelta(weeks=1)):
            return False
    return True

def no_addon(email):
    if _week_check(email):
        if len(email.to_.get_addons()) is 0:
            return True
    return False

def no_login(email):
    if _week_check(email):
        return True
    return False

def new_public(email):
    if _week_check(email):
        node = Node.find_one(Q('_id', 'eq', email.data['nid']))
        if node.is_public:
            return True
    return False

def welcome_osf4m(email):
    if _week_check(email):
        return True
    return False

EMAIL_TYPES = {
    'no_addon': {
        'template': 'no_addon',
        'callback': no_addon,
        'subject': 'Link an add-on to your OSF project',
    },
    'no_login': {
        'template': 'no_login',
        'callback': no_login,
        'subject': 'What you’re missing on the OSF',
    },
    'new_public': {
        'template': 'new_public',
        'callback': new_public,
        'subject': 'Now, public. Next, impact.',
    },
    'welcome_osf4m': {
        'template': 'welcome_osf4m',
        'callback': welcome_osf4m,
        'subject': 'The benefits of sharing your presentation',
    }
}
