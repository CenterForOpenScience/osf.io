"""
Custom exceptions for add-ons.
"""

class AddonError(Exception):
    pass

class InvalidFolderError(AddonError):
    pass

class InvalidAuthError(AddonError):
    pass

class HookError(AddonError):
    pass

class QueryError(AddonError):
    pass

class DoesNotExist(AddonError):
    pass
