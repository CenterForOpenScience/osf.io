from modularodm.exceptions import ValidationValueError
from website.addons.base.exceptions import AddonError

class WikiError(AddonError):
    """Base exception class for Wiki-related error."""
    pass

class NameEmptyError(WikiError, ValidationValueError):
    """Raised if user tries to provide an empty name value."""
    pass

class NameInvalidError(WikiError, ValidationValueError):
    """Raised if user tries to provide a string containing an invalid character."""
    pass

class NameMaximumLengthError(WikiError, ValidationValueError):
    """Raised if user tries to provide a name which exceeds the maximum accepted length."""
    pass

class PageCannotRenameError(WikiError):
    """Raised if user tried to rename special wiki pages, e.g. home."""
    pass

class PageConflictError(WikiError):
    """Raised if user tries to use an existing wiki page name."""
    pass

class PageNotFoundError(WikiError):
    """Raised if user tries to access a wiki page that does not exist."""
    pass

class InvalidVersionError(WikiError):
    """Raised if user tries to access a wiki page version that does not exist."""
    pass