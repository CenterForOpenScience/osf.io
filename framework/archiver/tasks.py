from urllib2 import urlopen
from celery import group
import requests
import json
from time import sleep

from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

from framework.tasks import app as celery_app
from framework.archiver.exceptions import (
    AddonFileSizeExceeded,
    AddonArchiveSizeExceeded,
)
from framework.auth.core import User

from framework.archiver import StatResult
from framework.archiver import AggregateStatResult

from website.addons.base import StorageAddonBase
from website.project.model import Node

from website import settings

import logging  # noqa
from celery.utils.log import get_task_logger

from framework.archiver.settings import ARCHIVE_PROVIDER
from framework.archiver.utils import archive_provider_for

raven_client = None
raven_handler = None
if settings.SENTRY_DSN:
    raven_client = Client(settings.SENTRY_DSN)
    raven_handler = SentryHandler(raven_client)
    setup_logging(raven_handler)


def set_app_context():
    from website.app import init_addons, do_set_backends
    init_addons(settings)
    do_set_backends(settings)


logger = get_task_logger(__name__)

def check_stat_result(src_addon, stat_result):
    pass

def get_file_size(src_addon, file_metadata, user):
    """
    Download a file and get its size
    """
    # TODO
    return 0
    '''
    download_url = waterbutler_url_for(
        'download',
        provider=src_addon.config.short_name,
        path=file_metadata.get('path'),
        node=src_addon.owner,
        user=user,
        view_only=False
    )
    dl = urlopen(download_url)
    size = 0
    while True:
        chunk = dl.read(512)
        if not chunk:
            break
        size += len(chunk)
    return size
    '''

def check_file(src_addon, file_stat_result):
    if file_stat_result.disk_usage > src_addon.MAX_FILE_SIZE:
        # TODO better problem reporting?
        return [
            "File object '{filename}' (id: {fid}) exceeds the maximum file size ({max}MB) for the {addon}".format(
                filename=file_stat_result.target_name,
                fid=file_stat_result.target_id,
                max=src_addon.MAX_FILE_SIZE,
                addon=src_addon.config.full_name,
            )
        ]

def stat_file_tree(src_addon, fileobj_metadata, user):
    is_file = fileobj_metadata['kind'] == 'file'
    disk_usage = fileobj_metadata.get('size')
    if is_file:
        if not disk_usage:
            disk_usage = get_file_size(src_addon, fileobj_metadata, user)
        result = StatResult(
            target_name=fileobj_metadata['name'],
            target_id=fileobj_metadata['path'].lstrip('/'),
            disk_usage=disk_usage,
            meta=fileobj_metadata,
        )
        result.problems = (check_file(src_addon, result) or [])
        return result
    else:
        return AggregateStatResult(
            target_id=fileobj_metadata['path'].lstrip('/'),
            target_name=fileobj_metadata['name'],
            targets=[stat_file_tree(src_addon, child, user) for child in fileobj_metadata.get('children', [])],
            meta=fileobj_metadata
        )

@celery_app.task
def stat_addon(addon_short_name, src_node_pk, user_pk, *args, **kwargs):
    set_app_context()
    src = Node.load(src_node_pk)
    src_addon = src.get_addon(addon_short_name)
    user = User.load(user_pk)
    file_tree = src_addon._get_file_tree(user=user)
    result = AggregateStatResult(
        src_addon._id,
        src_addon.config.short_name,
        targets=[stat_file_tree(src_addon, file_tree, user)],
    )
    try:
        check_stat_result(src_addon, result)
        return result
    except AddonArchiveSizeExceeded as e:
        result.problems.append("The archive size for this {addon} exceeds the maximum size of {max}MB".format(
            addon=src_addon.config.full_name,
            max=src_addon.MAX_ARCHIVE_SIZE,
        ))
        raise e

@celery_app.task
def stat_node(src_pk, user_pk, *args, **kwargs):
    set_app_context()
    src = Node.load(src_pk)
    user = User.load(user_pk)
    tasks = group(
        stat_addon.si(
            addon.config.short_name,
            src._id,
            user._id,
        )
        for addon in src.get_addons()
        if isinstance(addon, StorageAddonBase)
    )
    return tasks.apply_async()

@celery_app.task
def make_copy_request(url, data):
    return requests.post(url, data=json.dumps(data))

@celery_app.task(bind=True)
def archive_addon(self, addon_short_name, src_pk, dst_pk, user_pk, *args, **kwargs):
    self.update_state(state="Archiving {0}".format(addon_short_name))
    set_app_context()
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    user = User.load(user_pk)
    src_provider = src.get_addon(addon_short_name)
    dst_provider = archive_provider_for(dst, user)
    if not dst_provider.root_node:
        dst_provider.on_add()
    parent_name = "Archive of {addon}".format(addon=src_provider.config.full_name)
    if hasattr(src_provider, 'folder'):
        parent_name = parent_name + " (folder)".format(folder=src_provider.folder)
    provider = src_provider.config.short_name
    cookie = user.get_or_create_cookie()
    data = dict(
        source=dict(
            cookie=cookie,
            nid=src._id,
            provider=provider,
            path='/',
        ),
        destination=dict(
            cookie=cookie,
            nid=dst._id,
            provider=ARCHIVE_PROVIDER,
            path="/",
        ),
        rename=parent_name
    )
    copy_url = settings.WATERBUTLER_URL + '/ops/copy'
    return make_copy_request.si(copy_url, data)

@celery_app.task
def archive_node(group_result, src_pk, dst_pk, user_pk, *args, **kwargs):
    set_app_context()
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    user = User.load(user_pk)
    stat_result = AggregateStatResult(
        src._id,
        src.title,
        targets=[result.result for result in group_result.results]
    )
    tasks = group(
        archive_addon.si(
            result.target_name,
            src._id,
            dst._id,
            user._id,
            result,
        )
        for result in stat_result.targets.values()
    )
    return tasks.apply_async()

@celery_app.task
def finish(result, dst_pk, user_pk, *args, **kwargs):
    dst = Node.load(dst_pk)
    dst.archiving = False
    dst.save()

@celery_app.task(bind=True, name='archiver.archive')
def archive(self, src_pk, dst_pk, user_pk, *args, **kwargs):
    self.update_state(state='ARCHIVING', meta={})
    dst = Node.load(dst_pk)
    dst.archiving = True
    dst.archive_task_id = self.request.id
    dst.save()
    (stat_node.si(src_pk, user_pk) | archive_node.s(src_pk, dst_pk, user_pk) | finish.s(dst_pk, user_pk)).apply_async()
