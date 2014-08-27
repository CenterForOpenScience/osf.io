
from framework.auth.exceptions import AuthError


class TwoFactorValidationError(AuthError):
    """Raised in case an incorrect two-factor code is provided by the user."""
    pass
