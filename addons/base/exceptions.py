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


class NotApplicableError(AddonError):
    """This exception is used by non-storage and/or non-oauth add-ons when they don't need or have certain features."""

    pass
