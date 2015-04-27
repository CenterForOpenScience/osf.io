from celery import Task
from urllib2 import urlopen

from framework.tasks import app as celery_app

from website.util import waterbutler_url_for

from website.addons.base import StorageAddonBase

class StatResult(object):

    num_files = 1

    def __init__(self, target_id, target_name, problems=[], disk_usage=0, owner=None):
        self.target_id = target_id
        self.target_name = target_name
        self.disk_usage = disk_usage
        self.owner = owner
        self.problems = []

class AggregateStatResult(object):

    def __init__(self, target_id, target_name, targets=[]):
        self.target_id = target_id
        self.target_name = target_name
        self.targets = {
            "{0}:{1}".format(item.target_name, item.target_id): item
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


class ArchiverError(Exception):
    pass

class Archiver(Task):

    def _archive(self, src, dst, user, *args, **kwargs):
        result = self._stat(src, user)
        if result.problems:
            raise ArchiverError
        else:
            pass

    def run(self, src, dst, user=None, *args, **kwargs):
        src.archiving = True
        self._archive(src, dst, user)

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

    def _stat_file(self, node_addon, file_metadata, user=None):
        """
        Map Waterbulter file metadata to a StatResult object

        TODO: identify problems
        """
        disk_usage = file_metadata.get('size')
        import ipdb; ipdb.set_trace()
        if file_metadata['kind'] == 'file' and not disk_usage:
            disk_usage = self._get_file_size(node_addon, file_metadata, user),
        return StatResult(
            target_id=file_metadata['path'].lstrip('/'),
            target_name=file_metadata['name'],
            disk_usage=disk_usage,
            problems=[],
        )

    def _get_file_size(self, node_addon, file_metadata, user=None):
        download_url = waterbutler_url_for(
            'download',
            provider=node_addon.config.short_name,
            path=file_metadata.get('path'),
            node=node_addon.owner,
            user=user
        )
        import ipdb; ipdb.set_trace()
        dl = urlopen(download_url).read()
        return len(dl)

    def _stat(self, node_addon, user):
        """
        Get the addon's file tree and aggregate the StatResults into an AggregateStatResult
        """
        file_tree = node_addon._get_file_tree(user=user)
        import ipdb; ipdb.set_trace()
        return AggregateStatResult(
            node_addon._id,
            node_addon.config.short_name,
            targets=[self._stat_file(node_addon, addon_file, user=user) for addon_file in self._iflatten_file_tree(file_tree)]
        )

class NodeArchiver(Archiver):
    def _stat_addons(self, node, user):
        return [AddonArchiver()._stat(node_addon, user)
                for node_addon in node.get_addons()
                if isinstance(node_addon, StorageAddonBase)]

    def _stat(self, node, user):
        addon_results = self._stat_addons(node, user)
        return AggregateStatResult(node.title, node._id, addon_results)
