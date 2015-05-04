import abc
from urllib2 import urlopen
from celery import chain, group

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

import logging  # noqa
from celery.utils.log import get_task_logger

from celery.contrib import rdb

class ArchiverLogger(object):

    logger = get_task_logger(__name__)

    def __init__(self, log_to_sentry=True, *args, **kwargs):
        self.log_to_sentry = log_to_sentry

    def _log(self, kind, msg):
        getattr(self.logger, kind)(msg)
        if self.log_to_sentry:
            self._log_to_sentry(kind, msg)

    def _log_to_sentry(self, kind, msg):
        # TODO
        pass

    def info(self, msg):
        self._log('info', msg)

    def error(self, msg):
        self._log('error', msg)

class ArchiverTaskBase(celery_app.Task):
    #  http://jsatt.com/blog/class-based-celery-tasks/

    ### Celery attributes ###
    abstract = True
    max_retries = 3
    #########################

    __meta__ = abc.ABCMeta

    logger = ArchiverLogger()

    def bind(self, app):
        return super(ArchiverTaskBase, self).bind(celery_app)

    def _add_archiver_log(self, message):
        self.logger.info(message)

    def _add_archiver_error_log(self, error):
        pass

    @abc.abstractmethod
    def run(self, *args, **kwargs):
        pass

class ArchiveTask(ArchiverTaskBase):

    def run(self, src_pk, dst_pk, user_pk, *args, **kwargs):
        stat_node_task = StatNodeTask()
        archive_node_task = ArchiveNodeTask()
        self._add_archiver_log('Running ArchiveTask')
        return chain(stat_node_task.s(src_pk, user_pk), archive_node_task.s(src_pk, dst_pk, user_pk)).apply_async()

class StatNodeTask(ArchiverTaskBase):

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
            user=user
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

    def _stat(self, node_addon, user):
        """
        Get the addon's file tree and aggregate the StatResults into an AggregateStatResult
        """
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

    def run(self, Model, node_addon_pk, user_pk):
        node_addon = Model.load(node_addon_pk)
        user = User.load(user_pk)
        result = self._stat(node_addon, user)
        self._add_archiver_log("Running StatAddonTask")
        return result

class ArchiveNodeTask(ArchiverTaskBase):

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

    def run(self, group_result, src_pk, dst_pk, user_pk, *args, **kwargs):
        rdb.set_trace()
        stat_result = group_result.results[0].result
        src = Node.load(src_pk)
        dst = Node.load(dst_pk)
        user = User.load(user_pk)
        archive_node_tasks = self._archive(src, dst, user, stat_result)
        self._add_archiver_log("Running ArchiveNodeTask")
        return archive_node_tasks.apply_async()

class ArchiveAddonTask(ArchiveTask):

    def _copy_file_tree(self, root, children):
        for child in children:
            if isinstance(child, AggregateStatResult):
                child_node = root.append_folder(child.target_name)
                self._copy_file_tree(child_node, child.targets)

    def _archive(self, src_addon, dst_addon, user, stat_result):
        root = dst_addon.root_node
        parent = root.append_folder("Archive of {addon}".format(addon=src_addon.config.full_name))
        self._copy_file_tree(
            parent,
            stat_result.targets.values()
        )
        return dst_addon

    def run(self, Model, src_addon_pk, dst_addon_pk, user_pk, result):
        rdb.set_trace()
        src_addon = Model.load(src_addon_pk)
        dst_addon = Model.load(dst_addon_pk)
        user = User.load(user_pk)
        self._add_archiver_log("Running ArchiveAddonTask")
        return self._archive(src_addon, dst_addon, user, result)
