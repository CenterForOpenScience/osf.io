from framework.exceptions import FrameworkError

class AuthError(FrameworkError):
    """Base class for auth-related errors."""
    pass


class ChangePasswordError(AuthError):
    """Raised if a change password is called with invalid data.
    """
    def __init__(self, message):
        self.messages = message if isinstance(message, (list, tuple)) else [message]
        super(ChangePasswordError, self).__init__(message)


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


class LoginDisabledError(AuthError):
    """Raised if the ``User.is_disabled`` is True for the user logging in."""
    pass


class PasswordIncorrectError(AuthError):
    """Raised if login is called with an incorrect password attempt.
    """
    pass


class TwoFactorValidationError(AuthError):
    """Raised in case an incorrect two-factor code is provided by the user."""
    pass
