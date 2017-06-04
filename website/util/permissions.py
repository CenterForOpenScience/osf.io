# -*- coding: utf-8 -*-

# Permissions
READ = 'read'
WRITE = 'write'
ADMIN = 'admin'
# NOTE: Ordered from most-restrictive to most permissive
PERMISSIONS = [READ, WRITE, ADMIN]
CREATOR_PERMISSIONS = [READ, WRITE, ADMIN]
DEFAULT_CONTRIBUTOR_PERMISSIONS = [READ, WRITE]


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
