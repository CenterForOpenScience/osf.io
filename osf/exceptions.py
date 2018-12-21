import contextlib

from django.core.exceptions import ValidationError as DjangoValidationError

# Remants from MODM days
# TODO: Remove usages of aliased Exceptions
ValidationError = DjangoValidationError
ValidationValueError = DjangoValidationError
ValidationTypeError = DjangoValidationError


class TokenError(Exception):
    pass


class TokenHandlerNotFound(TokenError):
    def __init__(self, action, *args, **kwargs):
        super(TokenHandlerNotFound, self).__init__(*args, **kwargs)

        self.action = action


class UnsupportedSanctionHandlerKind(Exception):
    pass


class OSFError(Exception):
    """Base class for exceptions raised by the Osf application"""
    pass


class NodeError(OSFError):
    """Raised when an action cannot be performed on a Node model"""
    pass


class NodeStateError(NodeError):
    """Raised when the Node's state is not suitable for the requested action

    Example: Node.remove_node() is called, but the node has non-deleted children
    """
    pass

class UserStateError(OSFError):
    """Raised when the user's state is not suitable for the requested action

    Example: user.gdpr_delete() is called, but the user has resources that cannot be deleted.
    """
    pass


class SanctionTokenError(TokenError):
    """Base class for errors arising from the user of a sanction token."""
    pass


class MaxRetriesError(OSFError):
    """Raised when an operation has been attempted a pre-determined number of times"""
    pass


class InvalidSanctionRejectionToken(TokenError):
    """Raised if a Sanction subclass disapproval token submitted is invalid
     or associated with another admin authorizer
    """
    message_short = 'Invalid Token'
    message_long = 'This disapproval link is invalid. Are you logged into the correct account?'


class InvalidSanctionApprovalToken(TokenError):
    """Raised if a Sanction subclass approval token submitted is invalid
     or associated with another admin authorizer
    """
    message_short = 'Invalid Token'
    message_long = 'This approval link is invalid. Are you logged into the correct account?'


class InvalidTagError(OSFError):
    """Raised when attempting to perform an invalid operation on a tag"""
    pass


class TagNotFoundError(OSFError):
    """Raised when attempting to perform an operation on an absent tag"""
    pass


class UserNotAffiliatedError(OSFError):
    """Raised if a user attempts to add an institution that is not currently
    one of its affiliations.
    """
    message_short = 'User not affiliated'
    message_long = 'This user is not affiliated with this institution.'


@contextlib.contextmanager
def reraise_django_validation_errors():
    """Context manager to reraise DjangoValidationErrors as `osf.exceptions.ValidationErrors` (for
    MODM compat).
    """
    try:
        yield
    except DjangoValidationError as err:
        raise ValidationError(*err.args)


class NaiveDatetimeException(Exception):
    pass


class InvalidTriggerError(Exception):
    def __init__(self, trigger, state, valid_triggers):
        self.trigger = trigger
        self.state = state
        self.valid_triggers = valid_triggers
        self.message = 'Cannot trigger "{}" from state "{}". Valid triggers: {}'.format(trigger, state, valid_triggers)
        super(Exception, self).__init__(self.message)


class InvalidTransitionError(Exception):
    def __init__(self, machine, transition):
        self.message = 'Machine "{}" received invalid transitions: "{}" expected but not defined'.format(machine, transition)


class PreprintError(OSFError):
    """Raised when an action cannot be performed on a Preprint model"""
    pass


class PreprintStateError(PreprintError):
    """Raised when the Preprint's state is not suitable for the requested action"""
    pass


class PreprintProviderError(PreprintError):
    """Raised when there is an error with the preprint provider"""
    pass


class BlacklistedEmailError(OSFError):
    """Raised if a user tries to register an email that is included
    in the blacklisted domains list
    """
    pass
