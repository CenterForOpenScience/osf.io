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


class DraftRegistrationStateError(OSFError):
    """Raised when an action cannot be performed on a Draft Registration model"""
    pass


class PreprintProviderError(PreprintError):
    """Raised when there is an error with the preprint provider"""
    pass


class BlockedEmailError(OSFError):
    """Raised if a user tries to register an email that is included
    in the blocked domains list
    """
    pass

class SchemaBlockConversionError(OSFError):
    """Raised if unexpected data breaks the conversion between the legacy
    nested registration schema/metadata format and the new, flattened,
    'schema block' format.
    """
    pass


class SchemaResponseError(OSFError):
    """Superclass for errors ariseing from unexpected SchemaResponse behavior."""
    pass


class SchemaResponseStateError(SchemaResponseError):
    """Raised when attempting to perform an operation against a
    SchemaResponse with an invalid state.
    """
    pass


class PreviousSchemaResponseError(SchemaResponseError):
    """Raised when attempting to create a new SchemaResponse for a parent that
    already has a SchemaResponse in an unsupported state
    """
    pass


class RegistrationBulkCreationContributorError(OSFError):
    """Raised if contributor preparation has failed"""

    def __init__(self, error=None):
        self.error = error if error else 'Contributor preparation error'


class RegistrationBulkCreationRowError(OSFError):
    """Raised if a draft registration failed creation during bulk upload"""

    def __init__(self, upload_id, row_id, title, external_id, draft_id=None, error=None, approval_failure=False):

        # `draft_id` is provided when the draft is created but not related to the row object
        self.draft_id = draft_id
        # `approval_failure` determines whether the error happens during the approval process
        self.approval_failure = approval_failure
        # The error information for logging, sentry and email
        self.error = error if error else 'Draft registration creation error'
        # The short error message to be added to the error list that will be returned to the initiator via email
        self.short_message = 'Title: {}, External ID: {}, Error: {}'.format(title, external_id, self.error)
        # The long error message for logging and sentry
        self.long_message = 'Draft registration creation failed: [upload_id="{}", row_id="{}", title="{}", ' \
                            'external_id="{}", error="{}"]'.format(upload_id, row_id, title, external_id, self.error)


class SchemaResponseUpdateError(SchemaResponseError):
    """Raised when assigning an invalid value (or key) to a SchemaResponseBlock."""

    def __init__(self, response, invalid_responses=None, unsupported_keys=None):
        self.invalid_responses = invalid_responses
        self.unsupported_keys = unsupported_keys

        invalid_response_message = ''
        unsupported_keys_message = ''
        if invalid_responses:
            invalid_response_message = (
                f'\nThe following responses had invalid values: {invalid_responses}'
            )
        if unsupported_keys:
            unsupported_keys_message = (
                f'\nReceived the following resposnes had invalid keys: {unsupported_keys}'
            )
        error_message = (
            f'Error update SchemaResponse with id [{response._id}]:'
            f'{invalid_response_message}{unsupported_keys_message}'
        )

        super().__init__(error_message)
