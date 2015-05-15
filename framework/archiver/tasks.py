from celery import group, chain
import requests
import json

from framework.tasks import app as celery_app
from framework.auth.core import User
from framework.archiver import mails
from framework.archiver import (
    StatResult,
    AggregateStatResult,
)
from framework.archiver.exceptions import ArchiverSizeExceeded

from website.addons.base import StorageAddonBase
from website.project.model import Node
from website.project import signals as project_signals
from website.mails import send_mail

from website import settings

from framework.archiver import (
    ARCHIVER_PENDING,
    ARCHIVER_CHECKING,
    ARCHIVER_SUCCESS,
)
from framework.archiver.settings import (
    ARCHIVE_PROVIDER,
    MAX_ARCHIVE_SIZE,
)
from framework.archiver.utils import catch_archive_addon_error

def stat_file_tree(addon_short_name, fileobj_metadata, user):
    """Traverse the addon's file tree and collect metadata in AggregateStatResult

    :param src_addon: AddonNodeSettings instance of addon being examined
    :param fileobj_metadata: file or folder metadata of current point of reference
    in file tree
    :param user: archive initatior
    :return: top-most recursive call returns AggregateStatResult containing addon file tree metadata
    """
    is_file = fileobj_metadata['kind'] == 'file'
    disk_usage = fileobj_metadata.get('size')
    if is_file:
        if not disk_usage and not addon_short_name.config.short_name == 'osfstorage':
            disk_usage = 0  # float('inf')  # trigger failure
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
            targets=[stat_file_tree(addon_short_name, child, user) for child in fileobj_metadata.get('children', [])],
            meta=fileobj_metadata,
        )

@celery_app.task
def stat_addon(addon_short_name, src_pk, dst_pk, user_pk):
    """Collect metadata about the file tree of a given addon

    :param addon_short_name: AddonConfig.short_name of the addon to be examined
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: AggregateStatResult containing file tree metadata
    """
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    dst.archived_providers[addon_short_name] = {
        'status': ARCHIVER_CHECKING,
    }
    dst.save()
    src_addon = src.get_addon(addon_short_name)
    user = User.load(user_pk)
    file_tree = src_addon._get_file_tree(user=user)
    result = AggregateStatResult(
        src_addon._id,
        src_addon.config.short_name,
        targets=[stat_file_tree(addon_short_name, file_tree, user)],
    )
    return result

@celery_app.task
def stat_node(src_pk, dst_pk, user_pk):
    """Create a celery.group group of #stat_addon subtasks

    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: celery.result.GroupResult containing the collected return
    values of a #stat_addon
    """
    src = Node.load(src_pk)
    return group(
        stat_addon.si(
            addon.config.short_name,
            src_pk,
            dst_pk,
            user_pk,
        )
        for addon in src.get_addons()
        if isinstance(addon, StorageAddonBase)
    ).apply_async()

@celery_app.task
def make_copy_request(dst_pk, url, data):
    """Make the copy request to the WaterBulter API and handle
    successful and fauled responses

    :param dst_pk: primary key of registration node
    :param url: URL to send request to
    :parama data: <dict> of setting to send in POST to WaterBulter API
    :return: None
    """
    dst = Node.load(dst_pk)
    provider = data['source']['provider']
    res = requests.post(url, data=json.dumps(data))
    if res.status_code not in (200, 201, 202):
        catch_archive_addon_error(dst, provider, errors=[res.json()])
    elif res.status_code in (200, 201):
        dst.archived_providers[provider]['status'] = ARCHIVER_SUCCESS
    dst.save()
    project_signals.archive_callback.send(dst)


@celery_app.task
def archive_addon(addon_short_name, src_pk, dst_pk, user_pk, stat_result):
    """Archive the contents of an addon by making a copy request to the
    WaterBulter API

    :param addon_short_name: AddonConfig.short_name of the addon to be archived
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    dst.archived_providers[addon_short_name] = {
        'status': ARCHIVER_PENDING,
        'stat_result': str(stat_result),
    }
    dst.save()
    user = User.load(user_pk)
    src_provider = src.get_addon(addon_short_name)
    parent_name = "Archive of {addon}".format(addon=src_provider.config.full_name)
    if hasattr(src_provider, 'folder'):
        parent_name = parent_name + " ({folder})".format(folder=src_provider.folder)
    provider = src_provider.config.short_name
    cookie = user.get_or_create_cookie()
    data = dict(
        source=dict(
            cookie=cookie,
            nid=src_pk,
            provider=provider,
            path='/',
        ),
        destination=dict(
            cookie=cookie,
            nid=dst_pk,
            provider=ARCHIVE_PROVIDER,
            path='/',
        ),
        rename=parent_name
    )
    copy_url = settings.WATERBUTLER_URL + '/ops/copy'
    make_copy_request.si(dst_pk, copy_url, data).apply_async()


@celery_app.task
def archive_node(group_result, src_pk, dst_pk, user_pk):
    """First use the result of #stat_node to check disk usage of the
    initated registration, then either fail the registration or
    create a celery.group group of subtasks to archive addons

    :param group_result: a celery.result.GroupResulf containing the collected
    results from the #stat_addon subtasks spawned in #stat_node
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    user = User.load(user_pk)
    stat_result = AggregateStatResult(
        src_pk,
        src.title,
        targets=[result.result for result in group_result.results]
    )
    if stat_result.disk_usage > MAX_ARCHIVE_SIZE:
        raise ArchiverSizeExceeded(
            src,
            dst,
            user,
            stat_result
        )
    group(
        archive_addon.si(
            result.target_name,
            src_pk,
            dst_pk,
            user_pk,
            result,
        )
        for result in stat_result.targets.values()
    ).apply_async()

@celery_app.task(bind=True, name='archiver.archive')
def archive(self, src_pk, dst_pk, user_pk):
    """Create a celery.chain task chain for first examining the file trees
    of a Node and its associated addons, then archiving that Node.

    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    dst = Node.load(dst_pk)
    dst.archiving = True
    dst.archive_task_id = self.request.id
    dst.save()
    chain(stat_node.si(src_pk, dst_pk, user_pk), archive_node.s(src_pk, dst_pk, user_pk)).apply_async()


@celery_app.task
def send_success_message(dst_pk):
    """Send success email when archive completes

    :param dst_pk: primary key of registration Node
    :return: None
    """
    dst = Node.load(dst_pk)
    user = dst.creator

    send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_SIZE_EXCEEDED_USER,
        user=user,
        src=dst,
    )
