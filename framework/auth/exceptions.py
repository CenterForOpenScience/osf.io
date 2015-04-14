from framework.exceptions import FrameworkError
from website import language


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


class EmailConfirmTokenError(FrameworkError):
    """Base class for errors arising from the use of an email confirm token."""
    pass


class InvalidTokenError(EmailConfirmTokenError):
    """Raised if an email confirmation token is not found."""
    message_short = "Invalid Token"
    message_long = language.INVALID_EMAIL_CONFIRM_TOKEN


class ExpiredTokenError(EmailConfirmTokenError):
    """Raised if an email confirmation token is expired."""
    message_short = "Expired Token"
    message_long = language.EXPIRED_EMAIL_CONFIRM_TOKEN


class RetractionTokenError(FrameworkError):
    """Base class for errors arising from the user of a retraction token."""


class InvalidRetractionApprovalToken(RetractionTokenError):
    """Raised if a retraction approval token is not found."""
    message_short = "Invalid Token"
    message_long = "This retraction approval link is invalid."


class InvalidRetractionDisapprovalToken(RetractionTokenError):
    """Raised if a retraction disapproval token is not found."""
    message_short = "Invalid Token"
    message_long = "This retraction disapproval link is invalid."
