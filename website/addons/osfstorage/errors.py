# -*- coding: utf-8 -*-

class OsfStorageError(Exception):
    pass

class PathLockedError(OsfStorageError):
    pass

class SignatureConsumedError(OsfStorageError):
    pass

class NoVersionsError(OsfStorageError):
    pass

class PendingSignatureMismatchError(OsfStorageError):
    pass

class VersionNotPendingError(OsfStorageError):
    pass

class DeleteError(OsfStorageError):
    pass

class UndeleteError(OsfStorageError):
    pass

class InvalidVersionError(OsfStorageError):
    pass

