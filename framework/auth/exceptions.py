from framework.exceptions import FrameworkError

class AuthError(FrameworkError):
    """Base class for auth-related errors."""
    pass


class DuplicateEmailError(AuthError):
    """Raised if a user tries to register an email that is already in the
    database.
    """
    pass


class LoginNotAllowedError(AuthError):
    """Raised if user login is called for a user that is not registered or
    is not claimed, etc.
    """
    pass

class PasswordIncorrectError(AuthError):
    """Raised if login is called with an incorrect password attempt.
    """
    pass

class TwoFactorValidationError(AuthError):
    """Raised in case an incorrect two-factor code is provided by the user."""
    pass
