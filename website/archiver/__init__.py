ARCHIVER_INITIATED = 'INITIATED'
ARCHIVER_FAILURE = 'FAILURE'
ARCHIVER_SUCCESS = 'SUCCESS'
ARCHIVER_SENT = 'SENT'

ARCHIVER_PENDING = 'ARCHIVING'
ARCHIVER_CHECKING = 'CHECKING'
ARCHIVER_SENDING = 'SENDING'

ARCHIVER_NETWORK_ERROR = 'NETWORK_ERROR'
ARCHIVER_SIZE_EXCEEDED = 'SIZE_EXCEEDED'
ARCHIVER_UNCAUGHT_ERROR = 'UNCAUGHT_ERROR'

ARCHIVER_FAILURE_STATUSES = {
    ARCHIVER_FAILURE,
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_SIZE_EXCEEDED,
    ARCHIVER_UNCAUGHT_ERROR,
}

class StatResult(object):
    """
    Helper class to collect metadata about a single file
    """
    num_files = 1

    def __init__(self, target_id, target_name, disk_usage=0):
        self.target_id = target_id
        self.target_name = target_name
        self.disk_usage = float(disk_usage)

    def __str__(self):
        return str(dict(self))

    def _to_dict(self):
        return {
            'target_id': self.target_id,
            'target_name': self.target_name,
            'disk_usage': self.disk_usage,
        }


class AggregateStatResult(object):
    """
    Helper class to collect metadata about aribitrary depth file/addon/node file trees
    """
    def __init__(self, target_id, target_name, targets=None):
        self.target_id = target_id
        self.target_name = target_name
        self.targets = [target for target in targets if target]

    def __str__(self):
        return str(self._to_dict())

    def _to_dict(self):
        return {
            'target_id': self.target_id,
            'target_name': self.target_name,
            'targets': [
                target._to_dict()
                for target in self.targets
            ],
            'num_files': self.num_files,
            'disk_usage': self.disk_usage,
        }

    @property
    def num_files(self):
        return sum([value.num_files for value in self.targets])

    @property
    def disk_usage(self):
        return sum([value.disk_usage for value in self.targets])
