from website.addons.base.exceptions import AddonError

class OSFFilesError(AddonError):
    """Base exception class for OSFFiles-related error."""
    pass

class FileNotFoundError(OSFFilesError):
    """Raised if user requests a file that does not exist."""
    pass

class VersionNotFoundError(OSFFilesError, ValueError):
    """Raised if user tries to access a file version that does not exist."""
    pass

class InvalidVersionError(OSFFilesError, TypeError):
    """Raised if user tries to access an invalid version value, e.g. a string
    instead of an integer.
    """
    pass

class FileNotModified(OSFFilesError):
    def __init__(self, message=None):
        message = (
            message or
            u'File identical to current version'
        )
        super(FileNotModified, self).__init__(message)
