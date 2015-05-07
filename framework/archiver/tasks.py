from urllib2 import urlopen
from celery import chain, group

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

from website.util import waterbutler_url_for
from website.addons.base import StorageAddonBase
from website.project.model import Node

from website import settings

import logging  # noqa
from celery.utils.log import get_task_logger

from celery.contrib import rdb

raven_client = None
raven_handler = None
if settings.SENTRY_DSN:
    raven_client = Client(settings.SENTRY_DSN)
    raven_handler = SentryHandler(raven_client)
    setup_logging(raven_handler)


def set_app_context(func):
    def wrapper(*args, **kwargs):
        from website.app import init_addons, do_set_backends
        init_addons(settings)
        do_set_backends(settings)
        return func(*args, **kwargs)
    return wrapper

logger = get_task_logger(__name__)

def _add_archiver_log(self, message):
    logger.info(message)

def _add_archiver_error_log(self, error):
    pass

def check_stat_result(src_addon, stat_result):
    pass

def get_file_size(src_addon, file_metadata, user):
    """
    Download a file and get its size
    """
    rdb.set_trace()
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
def stat_addon(Model, src_addon_pk, user_pk):
    src_addon = Model.load(src_addon_pk)
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
@set_app_context
def stat_node(src_pk, user_pk):
    src = Node.load(src_pk)
    user = User.load(user_pk)
    subtasks = []
    # Get addons
    for addon in src.get_addons():
        if not isinstance(addon, StorageAddonBase):
            continue
        subtasks.append(
            stat_addon(
                type(addon),
                addon._id,
                user._id
            )
        )
    # TODO other subtasks?
    return group(iter(subtasks)).apply_async()

@celery_app.task
def archive_addon(Model, src_addon_pk, dst_addon_pk, user):
    src_addon = Model.load(src_addon_pk)
    dst_addon = Model.load(dst_addon_pk)
    root = dst_addon.root_node
    parent = root.append_folder("Archive of {addon}".format(addon=src_addon.config.full_name))
    src_addon._copy_files(dst_addon=dst_addon, dst_folder=parent)
    return dst_addon

@celery_app.task
def archive_node(group_result, src_pk, dst_pk, user_pk):
    stat_result = group_result.results[0].result
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    user = User.load(user_pk)
    subtasks = []
    for result in stat_result.targets.values():
        provider = result.target_name
        if provider:
            src_addon = src.get_addon(provider)
            dst_addon = dst.get_or_add_addon(provider)
            subtasks.append(archive_addon.s(type(src_addon), src_addon._id, dst_addon._id, user._id, result))
    return group(iter(subtasks))

@celery_app.task
def archive(src_pk, dst_pk, user_pk):
    return chain(stat_node.s(src_pk, user_pk), archive_node.s(src_pk, dst_pk, user_pk)).apply_async()

'''
class ArchiveTask(ArchiverTaskBase):

    @set_app_context
    def run(self, src_pk, dst_pk, user_pk, *args, **kwargs):
        stat_node_task = StatNodeTask()
        archive_node_task = ArchiveNodeTask()
        self._add_archiver_log('Running ArchiveTask')
        return (stat_node_task.s(src_pk, user_pk) | archive_node_task.s(src_pk, dst_pk, user_pk)).apply_async()

class StatNodeTask(ArchiverTaskBase):

    @set_app_context
    def _stat(self, src, user):
        stat_addon_task = StatAddonTask()
        return group(
            stat_addon_task.s(type(node_addon), node_addon._id, user._id)
            for node_addon in src.get_addons()
            if isinstance(node_addon, StorageAddonBase)
        )

    def run(self, src_pk, user_pk, *args, **kwargs):
        self._add_archiver_log("Running StatNodeTask")
        src = Node.load(src_pk)
        user = User.load(user_pk)
        stat_node_tasks = self._stat(src, user)
        return stat_node_tasks.apply_async()

class StatAddonTask(ArchiverTaskBase):

    def _get_file_size(self, node_addon, file_metadata, user=None):
        """
        Download a file and get its size
        """
        download_url = waterbutler_url_for(
            'download',
            provider=node_addon.config.short_name,
            path=file_metadata.get('path'),
            node=node_addon.owner,
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
    def _check_file(self, node_addon, file_stat_result):
        if file_stat_result.disk_usage > node_addon.MAX_FILE_SIZE:
            # TODO better problem reporting?
            return [
                "File object '{filename}' (id: {fid}) exceeds the maximum file size ({max}MB) for the {addon}".format(
                    filename=file_stat_result.target_name,
                    fid=file_stat_result.target_id,
                    max=node_addon.MAX_FILE_SIZE,
                    addon=node_addon.config.full_name,
                )
            ]

    def _stat_file_tree(self, node_addon, fileobj_metadata, user=None):
        """
        Recursive mapping from Waterbulter file object metadata to a StatResult object

        """
        is_file = fileobj_metadata['kind'] == 'file'
        disk_usage = fileobj_metadata.get('size')
        if is_file:
            if not disk_usage:
                disk_usage = self._get_file_size(node_addon, fileobj_metadata, user)
            result = StatResult(
                target_name=fileobj_metadata['name'],
                target_id=fileobj_metadata['path'].lstrip('/'),
                disk_usage=disk_usage,
                meta=fileobj_metadata,
            )
            result.problems = (self._check_file(node_addon, result) or [])
            return result
        else:
            return AggregateStatResult(
                target_id=fileobj_metadata['path'].lstrip('/'),
                target_name=fileobj_metadata['name'],
                targets=[self._stat_file_tree(node_addon, child, user) for child in fileobj_metadata.get('children', [])],
                meta=fileobj_metadata
            )

    def _check_for_problems(self, node_addon, addon_stat_result):
        if addon_stat_result.disk_usage > node_addon.MAX_ARCHIVE_SIZE:
            raise AddonArchiveSizeExceeded(node_addon.config.short_name, addon_stat_result)
        if addon_stat_result.problems:  # TODO other problems?
            raise AddonFileSizeExceeded(node_addon.config.short_name, addon_stat_result)
        return False

    @set_app_context
    def _stat(self, node_addon, user):
        """
        Get the addon's file tree and aggregate the StatResults into an AggregateStatResult
        """
        rdb.set_trace()
        file_tree = node_addon._get_file_tree(user=user)
        result = AggregateStatResult(
            node_addon._id,
            node_addon.config.short_name,
            targets=[self._stat_file_tree(node_addon, file_tree, user=user)],
        )
        try:
            self._check_for_problems(node_addon, result)
            return result
        except AddonArchiveSizeExceeded as e:
            result.problems.append("The archive size for this {addon} exceeds the maximum size of {max}MB".format(
                addon=node_addon.config.full_name,
                max=node_addon.MAX_ARCHIVE_SIZE,
            ))
            raise e

    @set_app_context
    def run(self, Model, node_addon_pk, user_pk):
        node_addon = Model.load(node_addon_pk)
        user = User.load(user_pk)
        result = self._stat(node_addon, user)
        self._add_archiver_log("Running StatAddonTask")
        return result

class ArchiveNodeTask(ArchiverTaskBase):

    @set_app_context
    def _archive(self, src, dst, user, stat_result):
        tasks = []
        archive_addon_task = ArchiveAddonTask()
        for result in stat_result.targets.values():
            provider = result.target_name
            if provider:
                src_addon = src.get_addon(provider)
                dst_addon = dst.get_or_add_addon(provider)
                tasks.append(archive_addon_task.s(type(src_addon), src_addon._id, dst_addon._id, user._id, result))
        return group(iter(tasks))

    @set_app_context
    def run(self, group_result, src_pk, dst_pk, user_pk, *args, **kwargs):
        stat_result = group_result.results[0].result
        src = Node.load(src_pk)
        dst = Node.load(dst_pk)
        user = User.load(user_pk)
        archive_node_tasks = self._archive(src, dst, user, stat_result)
        self._add_archiver_log("Running ArchiveNodeTask")
        return archive_node_tasks.apply_async()

class ArchiveAddonTask(ArchiveTask):

    @set_app_context
    def _archive(self, src_addon, dst_addon, user, stat_result):
        root = dst_addon.root_node
        parent = root.append_folder("Archive of {addon}".format(addon=src_addon.config.full_name))
        src_addon._copy_files(dst_addon=dst_addon, dst_folder=parent)
        return dst_addon

    def run(self, Model, src_addon_pk, dst_addon_pk, user_pk, result):
        src_addon = Model.load(src_addon_pk)
        dst_addon = Model.load(dst_addon_pk)
        user = User.load(user_pk)
        self._add_archiver_log("Running ArchiveAddonTask")
        return self._archive(src_addon, dst_addon, user, result)
'''
