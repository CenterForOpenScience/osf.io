# -*- coding: utf-8 -*-

import uuid

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from website import security
from website.project import new_node
from website.models import User, Node


def get_or_create_user(fullname, address, is_spam):
    """Get or create user by email address.

    :param str fullname: User full name
    :param str address: User email address
    :param bool is_spam: User flagged as potential spam
    :return: Tuple of (user, created)
    """
    try:
        user = User.find_one(Q('username', 'iexact', address))
        return user, False
    except ModularOdmException:
        password = str(uuid.uuid4())
        user = User.create_confirmed(address, password, fullname)
        user.verification_key = security.random_string(20)
        if is_spam:
            user.system_tags.append('is_spam')
        user.save()
        return user, True


def get_or_create_node(title, user):
    """Get or create node by title and creating user.

    :param str title: Node title
    :param User user: User creating node
    :return: Tuple of (node, created)
    """
    try:
        node = Node.find_one(
            Q('title', 'iexact', title)
            & Q('contributors', 'eq', user._id)
        )
        return node, False
    except ModularOdmException:
        node = new_node('project', title, user)
        return node, True
