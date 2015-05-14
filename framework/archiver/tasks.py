from celery import group, chain
import requests
import json

from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

from framework.tasks import app as celery_app
from framework.auth.core import User

from framework.archiver import (
    StatResult,
    AggregateStatResult,
)
from framework.archiver.exceptions import ArchiverSizeExceeded

from website.addons.base import StorageAddonBase
from website.project.model import Node
from website.project import signals as project_signals

from website import settings

import logging  # noqa
from celery.utils.log import get_task_logger

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

raven_client = None
raven_handler = None
if settings.SENTRY_DSN:
    raven_client = Client(settings.SENTRY_DSN)
    raven_handler = SentryHandler(raven_client)
    setup_logging(raven_handler)

logger = get_task_logger(__name__)

def stat_file_tree(src_addon, fileobj_metadata, user, cookie=None):
    is_file = fileobj_metadata['kind'] == 'file'
    disk_usage = fileobj_metadata.get('size')
    if is_file:
        if not disk_usage and not src_addon.config.short_name == 'osfstorage':
            disk_usage = 0  # float('inf')  # trigger failure
        result = StatResult(
            target_name=fileobj_metadata['name'],
            target_id=fileobj_metadata['path'].lstrip('/'),
            disk_usage=disk_usage,
            meta=fileobj_metadata,
        )
        return result
    else:
        cookie = user.get_or_create_cookie()
        return AggregateStatResult(
            target_id=fileobj_metadata['path'].lstrip('/'),
            target_name=fileobj_metadata['name'],
            targets=[stat_file_tree(src_addon, child, user, cookie=cookie) for child in fileobj_metadata.get('children', [])],
            meta=fileobj_metadata,
        )

@celery_app.task
def stat_addon(addon_short_name, src_pk, dst_pk, user_pk, *args, **kwargs):
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
        targets=[stat_file_tree(src_addon, file_tree, user)],
    )
    return result

@celery_app.task
def stat_node(src_pk, dst_pk, user_pk, *args, **kwargs):
    src = Node.load(src_pk)
    tasks = group(
        stat_addon.si(
            addon.config.short_name,
            src_pk,
            dst_pk,
            user_pk,
        )
        for addon in src.get_addons()
        if isinstance(addon, StorageAddonBase)
    )
    return tasks.apply_async()

@celery_app.task
def make_copy_request(dst_pk, url, data):
    dst = Node.load(dst_pk)
    provider = data['source']['provider']
    res = requests.post(url, data=json.dumps(data))
    if res.status_code not in (200, 201, 202):
        catch_archive_addon_error(dst, provider, errors=[res.json()])
    elif res.status_code in (200, 201):
        dst.archived_providers[provider]['status'] = ARCHIVER_SUCCESS
    dst.save()
    project_signals.archive_callback.send(dst)
    return res

@celery_app.task
def archive_addon(addon_short_name, src_pk, dst_pk, user_pk, stat_result, *args, **kwargs):
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    dst.archived_providers[addon_short_name] = {
        'status': ARCHIVER_PENDING,
        'stat_result': str(stat_result),
    }
    try:  # TODO why?
        dst.save()
    except Exception as e:
        pass
    user = User.load(user_pk)
    src_provider = src.get_addon(addon_short_name)
    parent_name = "Archive of {addon}".format(addon=src_provider.config.full_name)
    if hasattr(src_provider, 'folder'):
        parent_name = parent_name + " (folder)".format(folder=src_provider.folder)
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
            path="/",
        ),
        rename=parent_name
    )
    copy_url = settings.WATERBUTLER_URL + '/ops/copy'
    return make_copy_request.si(dst_pk, copy_url, data).apply_async()

@celery_app.task
def archive_node(group_result, src_pk, dst_pk, user_pk, *args, **kwargs):
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
    return group(
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
def archive(self, src_pk, dst_pk, user_pk, *args, **kwargs):
    dst = Node.load(dst_pk)
    dst.archiving = True
    dst.archive_task_id = self.request.id
    dst.save()
    return chain(stat_node.si(src_pk, dst_pk, user_pk), archive_node.s(src_pk, dst_pk, user_pk)).apply_async()

@celery_app.task
def send_success_message(dst_pk):
    pass
