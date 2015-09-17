class FileException(Exception):
    pass


class SubclassNotFound(FileException):
    pass


class VersionNotFoundError(FileException):
    pass
