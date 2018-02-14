ARCHIVER_INITIATED = 'INITIATED'
ARCHIVER_FAILURE = 'FAILURE'
ARCHIVER_SUCCESS = 'SUCCESS'
ARCHIVER_SENT = 'SENT'

ARCHIVER_PENDING = 'ARCHIVING'
ARCHIVER_CHECKING = 'CHECKING'
ARCHIVER_SENDING = 'SENDING'

ARCHIVER_NETWORK_ERROR = 'NETWORK_ERROR'
ARCHIVER_SIZE_EXCEEDED = 'SIZE_EXCEEDED'
ARCHIVER_FILE_NOT_FOUND = 'FILE_NOT_FOUND'
ARCHIVER_FORCED_FAILURE = 'FORCED_FAILURE'
ARCHIVER_UNCAUGHT_ERROR = 'UNCAUGHT_ERROR'

ARCHIVER_FAILURE_STATUSES = {
    ARCHIVER_FAILURE,
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_SIZE_EXCEEDED,
    ARCHIVER_FILE_NOT_FOUND,
    ARCHIVER_FORCED_FAILURE,
    ARCHIVER_UNCAUGHT_ERROR,
}

NO_ARCHIVE_LIMIT = 'high_upload_limit'

# StatResult and AggregateStatResult are dict subclasses because they are used
# in celery tasks, and celery serializes to JSON by default

class StatResult(dict):
    """
    Helper class to collect metadata about a single file
    """
    num_files = 1

    def __init__(self, target_id, target_name, disk_usage=0):
        self.target_id = target_id
        self.target_name = target_name
        self.disk_usage = float(disk_usage)

        self.update({
            'target_id': self.target_id,
            'target_name': self.target_name,
            'disk_usage': self.disk_usage,
            'num_files': self.num_files
        })


class AggregateStatResult(dict):
    """
    Helper class to collect metadata about arbitrary depth file/addon/node file trees
    """
    def __init__(self, target_id, target_name, targets=None):
        self.target_id = target_id
        self.target_name = target_name
        targets = targets or []
        self.targets = [target for target in targets if target]

        self.update({
            'target_id': self.target_id,
            'target_name': self.target_name,
            'targets': [
                target
                for target in self.targets
            ],
            'num_files': self.num_files,
            'disk_usage': self.disk_usage,
        })

    @property
    def num_files(self):
        return sum([value['num_files'] for value in self.targets])

    @property
    def disk_usage(self):
        return sum([value['disk_usage'] for value in self.targets])
