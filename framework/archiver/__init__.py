from website.project import signals as project_signals

class StatResult(object):

    def __init__(self, target, problems=[], num_files=0, disk_usage=0, owners=[]):
        self.target = target
        self.num_files = num_files
        self.disk_usage = disk_usage
        self.owners = owners
        self.problems = []

class AggregateStatResult(object):

    def __init__(self, targets=[]):
        self.targets = {
            item.target: item
            for item in targets
        }

    @property
    def problems(self):
        return reduce(lambda accum, target: (accum or []) + target.problems, self.targets.values())

    @property
    def num_files(self):
        return reduce(lambda accum, target: (accum or 0) + target.num_files, self.targets.values())

    @property
    def disk_usage(self):
        return reduce(lambda accum, target: (accum or 0) + target.disk_usage, self.targets.values())

class NodeArchiveError(Exception):
    pass

class NodeArchiver(object):

    def __init__(self):
        pass

    def stat_addons(self, node):
        return AggregateStatResult([node_addon.stat() for node_addon in node.get_addons()])

    def stat_node(self, node):
        addon_result = self.stat_addons(node)

        return addon_result

    def _archive(self, src, dst):
        # TODO
        pass

    @project_signals.after_create_registration.connect
    def archive(self, src, dst, user):
        src.archiving = True
        result = self.stat_node(src)
        if result.problems:
            raise NodeArchiveError
        else:
            self._archive(src, dst)
