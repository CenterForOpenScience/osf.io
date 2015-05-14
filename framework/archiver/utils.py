from framework.auth import Auth

from framework.archiver import ARCHIVER_FAILURE
from framework.archiver.settings import (
    ARCHIVE_PROVIDER,
)

def archive_provider_for(node, user):
    return node.get_addon(ARCHIVE_PROVIDER)

def has_archive_provider(node, user):
    return node.has_addon(ARCHIVE_PROVIDER)

def link_archive_provider(node, user):
    addon = node.get_or_add_addon(ARCHIVE_PROVIDER, auth=Auth(user))
    addon.on_add()
    node.save()

def catch_archive_addon_error(node, addon_short_name, errors=[]):
    node.archived_providers[addon_short_name].update({
        'status': ARCHIVER_FAILURE,
        'errors': errors,
    })
    node.save()
