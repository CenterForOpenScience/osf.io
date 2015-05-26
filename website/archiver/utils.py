from framework.auth import Auth

from website.archiver import (
    StatResult, AggregateStatResult,
    ARCHIVER_FAILURE,
)
from website.archiver.settings import (
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

def delete_registration_tree(node):
    node.is_deleted = True
    node.save()
    for child in node.nodes:
        delete_registration_tree(child)

def update_status(node, addon, status, meta={}):
    tmp = node.archived_providers.get(addon) or {}
    tmp['status'] = status
    tmp.update(meta)
    node.archived_providers[addon] = tmp
    node.save()

def aggregate_file_tree_metadata(addon_short_name, fileobj_metadata, user):
    """Recursively traverse the addon's file tree and collect metadata in AggregateStatResult

    :param src_addon: AddonNodeSettings instance of addon being examined
    :param fileobj_metadata: file or folder metadata of current point of reference
    in file tree
    :param user: archive initatior
    :return: top-most recursive call returns AggregateStatResult containing addon file tree metadata
    """
    disk_usage = fileobj_metadata.get('size')
    if fileobj_metadata['kind'] == 'file':
        # Files are never actually copied on osfstorage, so file size is irrelivant
        if not disk_usage and not addon_short_name == 'osfstorage':
            disk_usage = float('inf')  # trigger failure
        result = StatResult(
            target_name=fileobj_metadata['name'],
            target_id=fileobj_metadata['path'].lstrip('/'),
            disk_usage=disk_usage,
            meta=fileobj_metadata,
        )
        return result
    else:
        return AggregateStatResult(
            target_id=fileobj_metadata['path'].lstrip('/'),
            target_name=fileobj_metadata['name'],
            targets=[aggregate_file_tree_metadata(addon_short_name, child, user) for child in fileobj_metadata.get('children', [])],
            meta=fileobj_metadata,
        )
