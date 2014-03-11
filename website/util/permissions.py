from website import settings

def expand_permissions(permission):
    if permission is None:
        return []
    index = settings.PERMISSIONS.index(permission) + 1
    return settings.PERMISSIONS[:index]


def reduce_permissions(permissions):
    for permission in settings.PERMISSIONS[::-1]:
        if permission in permissions:
            return permission
    raise ValueError('Permissions not in permissions list')
