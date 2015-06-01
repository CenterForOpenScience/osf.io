from framework.auth import Auth

from website.archiver import (
    StatResult, AggregateStatResult,
    ARCHIVE_COPY_FAIL,
    ARCHIVE_SIZE_EXCEEDED,
    ARCHIVE_METADATA_FAIL,
)

from website import mails
from website import settings

def send_archiver_success_mail(dst):
    user = dst.creator
    mails.send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_SUCCESS,
        user=user,
        src=dst,
        mimetype='html',
    )

def send_archiver_size_exceeded_mails(src, user, stat_result):
    mails.send_mail(
        to_addr=settings.SUPPORT_EMAIL,
        mail=mails.ARCHIVE_SIZE_EXCEEDED_DESK,
        user=user,
        src=src,
        stat_result=stat_result
    )
    mails.send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_SIZE_EXCEEDED_USER,
        user=user,
        src=src,
        stat_result=stat_result,
        mimetype='html',
    )

def send_archiver_copy_error_mails(src, user, results):
    mails.send_mail(
        to_addr=settings.SUPPORT_EMAIL,
        mail=mails.ARCHIVE_COPY_ERROR_DESK,
        user=user,
        src=src,
        results=results,
    )
    mails.send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_COPY_ERROR_USER,
        user=user,
        src=src,
        results=results,
        mimetype='html',
    )

def handle_archive_fail(reason, src, dst, user, result):
    delete_registration_tree(dst)
    if reason in [ARCHIVE_COPY_FAIL, ARCHIVE_METADATA_FAIL]:
        send_archiver_copy_error_mails(src, user, result)
    elif reason == ARCHIVE_SIZE_EXCEEDED:
        send_archiver_size_exceeded_mails(src, user, result)

def archive_provider_for(node, user):
    """A generic function to get the archive provider for some node, user pair.

    :param node: target node
    :param user: target user (currently unused, but left in for future-proofing
    the code for use with archive providers other than OSF Storage)
    """
    return node.get_addon(settings.ARCHIVE_PROVIDER)

def has_archive_provider(node, user):
    """A generic function for checking whether or not some node, user pair has
    an attached provider for archiving

    :param node: target node
    :param user: target user (currently unused, but left in for future-proofing
    the code for use with archive providers other than OSF Storage)
    """
    return node.has_addon(settings.ARCHIVE_PROVIDER)

def link_archive_provider(node, user):
    """A generic function for linking some node, user pair with the configured
    archive provider

    :param node: target node
    :param user: target user (currently unused, but left in for future-proofing
    the code for use with archive providers other than OSF Storage)
    """
    addon = node.get_or_add_addon(settings.ARCHIVE_PROVIDER, auth=Auth(user))
    addon.on_add()
    node.save()

def update_status(node, addon, status, meta={}):
    up = {
        'status': status,
    }
    up.update(meta)
    node.archived_providers.update({
        addon: up
    })
    node.save()

def delete_registration_tree(node):
    node.is_deleted = True
    if not getattr(node.embargo, 'for_existing_registration', False):
        node.registered_from = None
    node.save()
    for child in node.nodes:
        delete_registration_tree(child)

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
        result = StatResult(
            target_name=fileobj_metadata['name'],
            target_id=fileobj_metadata['path'].lstrip('/'),
            disk_usage=disk_usage or 0,
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
