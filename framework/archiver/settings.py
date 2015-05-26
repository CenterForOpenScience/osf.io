from datetime import timedelta

ARCHIVE_PROVIDER = 'osfstorage'

MAX_ARCHIVE_SIZE = 1024 ** 3  # == math.pow(1024, 3) == 1 GB
MAX_FILE_SIZE = MAX_ARCHIVE_SIZE  # TODO limit file size?

ARCHIVE_TIMEOUT_TIMEDELTA = timedelta(1)  # 24 hours
