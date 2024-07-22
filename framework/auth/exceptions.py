import markupsafe

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
        super().__init__(message)


class DuplicateEmailError(AuthError):
    """Raised if a user tries to register an email that is already in the
    database.
    """
    pass


class EmailConfirmTokenError(FrameworkError):
    """Base class for errors arising from the use of an email confirm token."""
    pass


class InvalidTokenError(EmailConfirmTokenError):
    """Raised if an email confirmation token is not found."""
    message_short = 'Invalid Token'
    message_long = language.INVALID_EMAIL_CONFIRM_TOKEN


class ExpiredTokenError(EmailConfirmTokenError):
    """Raised if an email confirmation token is expired."""
    message_short = 'Expired Token'
    message_long = language.EXPIRED_EMAIL_CONFIRM_TOKEN


class MergeConfirmedRequiredError(EmailConfirmTokenError):
    """Raised if a merge is possible, but requires user confirmation"""

    def __init__(self, message, user, user_to_merge, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.user_to_merge = user_to_merge
        self.user = user

    message_short = language.MERGE_CONFIRMATION_REQUIRED_SHORT

    @property
    def message_long(self):
        src_user = markupsafe.escape(self.user.username)
        dest_user = markupsafe.escape(self.user_to_merge.username)
        return language.MERGE_CONFIRMATION_REQUIRED_LONG.format(
            src_user=src_user,
            dest_user=dest_user,
        )


class MergeConflictError(EmailConfirmTokenError):
    """Raised if a merge is not possible due to a conflict"""
    message_short = language.CANNOT_MERGE_ACCOUNTS_SHORT
    message_long = language.CANNOT_MERGE_ACCOUNTS_LONG
