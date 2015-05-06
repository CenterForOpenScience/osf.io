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
