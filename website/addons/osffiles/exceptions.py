

class VersionNotFoundError(ValueError):
    """Raised if user tries to access a file version that does not exist."""
    pass

class InvalidVersionError(TypeError):
    """Raised if user tries to access an invalid version value, e.g. a string
    instead of an integer.
    """
    pass
