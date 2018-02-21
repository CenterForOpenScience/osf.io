# -*- coding: utf-8 -*-

from enum import unique

from osf.utils.workflows import ChoiceEnum


# Permissions
READ = 'read'
WRITE = 'write'
ADMIN = 'admin'
# NOTE: Ordered from most-restrictive to most permissive
PERMISSIONS = [READ, WRITE, ADMIN]
CREATOR_PERMISSIONS = [READ, WRITE, ADMIN]
DEFAULT_CONTRIBUTOR_PERMISSIONS = [READ, WRITE]


@unique
class PermissionChoices(ChoiceEnum):
    READ = READ
    WRITE = WRITE
    ADMIN = ADMIN


def expand_permissions(permission):
    if not permission:
        return []
    index = PERMISSIONS.index(permission) + 1
    return PERMISSIONS[:index]


def reduce_permissions(permissions):
    for permission in PERMISSIONS[::-1]:
        if permission in permissions:
            return permission
    raise ValueError('Permissions not in permissions list')


def check_private_key_for_anonymized_link(private_key):
    from osf.models import PrivateLink
    try:
        link = PrivateLink.objects.get(key=private_key)
    except PrivateLink.DoesNotExist:
        return False
    return link.anonymous
