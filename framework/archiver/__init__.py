import json

ARCHIVER_FAILURE = 'FAILURE'
ARCHIVER_SUCCESS = 'SUCCESS'
ARCHIVER_PENDING = 'ARCHIVING'o
ARCHIVER_CHECKING = 'CHECKING'

class StatResult(object):
    """
    Helper class to collect metadata about a single file
    """
    num_files = 1

    def __init__(self, target_id, target_name, disk_usage=0, meta=None):
        self.target_id = target_id
        self.target_name = target_name
        self.disk_usage = float(disk_usage)
        self.meta = meta

    def __str__(self):
        return json.dumps(self._to_dict())

    def _to_dict(self):
        return {
            'target_id': self.target_id,
            'target_name': self.target_name,
            'disk_usage': self.disk_usage,
            'meta': self.meta,
        }


class AggregateStatResult(object):
    """
    Helper class to collect metadata about aribitrary depth file/addon/node file trees
    """
    def __init__(self, target_id, target_name, targets=[], meta=None):
        self.target_id = target_id
        self.target_name = target_name
        self.targets = {
            "{0}".format(item.target_id): item
            for item in targets
            if item
        }
        self.meta = meta

    def __str__(self):
        return json.dumps(self._to_dict())

    def _to_dict(self):
        return {
            'target_id': self.target_id,
            'target_name': self.target_name,
            'targets': [
                target.__str__()
                for target in self.targets
            ],
            'num_files': self.num_files,
            'disk_usage': self.disk_usage,
            'meta': self.meta,
        }

    @property
    def num_files(self):
        return reduce(lambda accum, target: accum + target.num_files, self.targets.values(), 0)

    @property
    def disk_usage(self):
        return reduce(lambda accum, target: accum + (target.disk_usage or 0), self.targets.values(), 0)
