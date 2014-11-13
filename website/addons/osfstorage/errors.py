#!/usr/bin/env python
# encoding: utf-8

class OsfStorageError(Exception):
    pass

class PathLockedError(OsfStorageError):
    pass

class SignatureConsumedError(OsfStorageError):
    pass

class VersionNotFoundError(OsfStorageError):
    pass

class SignatureMismatchError(OsfStorageError):
    pass

class VersionStatusError(OsfStorageError):
    pass

class DeleteError(OsfStorageError):
    pass

class UndeleteError(OsfStorageError):
    pass

class InvalidVersionError(OsfStorageError):
    pass

class MissingFieldError(OsfStorageError):
    pass
