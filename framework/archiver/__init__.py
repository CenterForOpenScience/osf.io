from celery import Task
from urllib2 import urlopen

from framework.tasks import app as celery_app
from framework.archiver.exceptions import (
    ArchiverError,
    AddonFileSizeExceeded,
    AddonArchiveSizeExceeded,
)

from website.util import waterbutler_url_for
from website.addons.base import StorageAddonBase
from website.addons.osfstorage.model import OsfStorageFileNode

class StatResult(object):

    num_files = 1

    def __init__(self, target_id, target_name, problems=[], disk_usage=0, owner=None, meta=None):
        self.target_id = target_id
        self.target_name = target_name
        self.disk_usage = disk_usage
        self.owner = owner
        self.problems = []

class AggregateStatResult(object):

    def __init__(self, target_id, target_name, targets=[], meta=None):
        self.target_id = target_id
        self.target_name = target_name
        self.targets = {
            "{0}".format(item.target_id): item
            for item in targets
            if item
        }

    @property
    def problems(self):
        return reduce(lambda accum, target: accum + target.problems, self.targets.values(), [])

    @property
    def num_files(self):
        return reduce(lambda accum, target: accum + target.num_files, self.targets.values(), 0)

    @property
    def disk_usage(self):
        return reduce(lambda accum, target: accum + (target.disk_usage or 0), self.targets.values(), 0)

    @property
    def owners(self):
        return {target.owner for target in self.targets.values() if target.owner}

class Archiver(Task):
    abstract = True

    STORAGE = 'osfstorage'
    STORAGE_FOLDER_CLASS = OsfStorageFileNode

    def _add_archive_log(log):
        pass

    def _add_archive_error_log(error):
        pass

    def _archive(self, dst_addon, user, stat_result=None):
        pass

    def run(self, src, dst, user=None, *args, **kwargs):
        src.archiving = True
        try:
            result = self._stat(src, user)
            self._archive(src, dst, user, result)
        except ArchiverError as e:
            self._add_archive_error_log(e)

class AddonArchiver(Archiver):

    def _iflatten_file_tree(self, dod):
        """
        Iteratively flatten a file tree
        """
        ret = []
        stack = [dod]
        while stack:
            cur = stack.pop()
            ret.append(cur)
            stack = stack + cur.get('children', [])
        return ret

    def _copy_file_tree(self, root, children):
        for child in children:
            if isinstance(child, AggregateStatResult):
                child_node = root.append_folder(child.target_name)
                self._copy_file_tree(child_node, child.targets)

    def _archive(self, src_addon, dst_addon, user=None, stat_result=None):
        root = dst_addon.root_node
        parent = root.append_folder("Archive of {addon}".format(addon=src_addon.config.full_name))
        self._copy_file_tree(
            parent,
            stat_result.targets.values()
        )
        return dst_addon

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

class NodeArchiver(Archiver):

    def _stat_addons(self, node, user):
        return [AddonArchiver()._stat(node_addon, user)
                for node_addon in node.get_addons()
                if isinstance(node_addon, StorageAddonBase)]

    def _stat(self, node, user):
        addon_results = self._stat_addons(node, user)
        return AggregateStatResult(node.title, node._id, addon_results)

    def _archive(self, src, dst, user, stat_result):
        for result in stat_result.targets.values():
            provider = result.target_name
            if provider:
                src_addon = src.get_addon(provider)
                dst_addon = dst.get_or_add_addon(provider)
                AddonArchiver()._archive(src_addon, dst_addon, user, result)
        import ipdb; ipdb.set_trace()
        return dst
