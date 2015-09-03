# -*- coding: utf-8 -*-
from modularodm import Q

def no_addon(email):
    if len(email.user.get_addons()) is 0:
        return True

def no_login(email):
    return True

def new_public_project(email):
    from website.models import Node
    node = Node.find_one(Q('_id', 'eq', email.data['nid']))
    if node.is_public:
        return True
    return False

def welcome_osf4m(email):
    return True
