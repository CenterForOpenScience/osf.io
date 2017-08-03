import httplib as http
from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException


def dict_error_formatting(errors, index=None):
    """
    Formats all dictionary error messages for both single and bulk requests
    """

    formatted_error_list = []

    # Error objects may have the following members. Title and id removed to avoid clash with "title" and "id" field errors.
    top_level_error_keys = ['links', 'status', 'code', 'detail', 'source', 'meta']

    # Resource objects must contain at least 'id' and 'type'
    resource_object_identifiers = ['type', 'id']

    if index is None:
        index = ''
    else:
        index = str(index) + '/'

    for error_key, error_description in errors.iteritems():
        if isinstance(error_description, basestring):
            error_description = [error_description]

        if error_key in top_level_error_keys:
            formatted_error_list.extend({error_key: description} for description in error_description)
        elif error_key in resource_object_identifiers:
            formatted_error_list.extend([{'source': {'pointer': '/data/{}'.format(index) + error_key}, 'detail': reason} for reason in error_description])
        elif error_key == 'non_field_errors':
            formatted_error_list.extend([{'detail': description for description in error_description}])
        else:
            formatted_error_list.extend([{'source': {'pointer': '/data/{}attributes/'.format(index) + error_key}, 'detail': reason} for reason in error_description])

    return formatted_error_list


def json_api_exception_handler(exc, context):
    """
    Custom exception handler that returns errors object as an array
    """

    # We're deliberately not stripping html from exception detail.
    # This creates potential vulnerabilities to script injection attacks
    # when returning raw user input into error messages.
    #
    # Fortunately, Django's templating language strips markup bu default,
    # but if our frontend changes we may lose that protection.
    # TODO: write tests to ensure our html frontend strips html

    # Import inside method to avoid errors when the OSF is loaded without Django
    from rest_framework.views import exception_handler

    response = exception_handler(exc, context)

    errors = []

    if response:
        message = response.data

        if isinstance(exc, TwoFactorRequiredError):
            response['X-OSF-OTP'] = 'required; app'

        if isinstance(exc, JSONAPIException):
            errors.extend([{
                'source': exc.source or {},
                'detail': exc.detail,
                'meta': exc.meta or {},
                'code': exc.code or {},
            }])
        elif isinstance(message, dict):
            errors.extend(dict_error_formatting(message, None))
        else:
            if isinstance(message, basestring):
                message = [message]
            for index, error in enumerate(message):
                if isinstance(error, dict):
                    errors.extend(dict_error_formatting(error, index))
                else:
                    errors.append({'detail': error})

        response.data = {'errors': errors}

    return response


class EndpointNotImplementedError(APIException):
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    default_detail = _('This endpoint is not yet implemented.')


class ServiceUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _('Service is unavailable at this time.')


class JSONAPIException(APIException):
    """Inherits from the base DRF API exception and adds extra metadata to support JSONAPI error objects

    :param str detail: a human-readable explanation specific to this occurrence of the problem
    :param dict source: A dictionary containing references to the source of the error.
        See http://jsonapi.org/format/#error-objects.
        Example: ``source={'pointer': '/data/attributes/title'}``
    :param dict meta: A meta object containing non-standard meta info about the error.
    """
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail=None, source=None, meta=None, code=None):
        super(JSONAPIException, self).__init__(detail=detail)
        self.source = source
        self.meta = meta
        self.code = code


# Custom Exceptions the Django Rest Framework does not support
class Gone(JSONAPIException):
    status_code = status.HTTP_410_GONE
    default_detail = ('The requested resource is no longer available.')


def UserGone(user):
    return Gone(detail='The requested user is no longer available.',
            meta={'full_name': user.fullname, 'family_name': user.family_name, 'given_name': user.given_name,
                    'middle_names': user.middle_names, 'profile_image': user.profile_image_url()})

class Conflict(JSONAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = ('Resource identifier does not match server endpoint.')


class JSONAPIParameterException(JSONAPIException):
    def __init__(self, detail=None, parameter=None):
        source = {
            'parameter': parameter
        }
        super(JSONAPIParameterException, self).__init__(detail=detail, source=source)


class JSONAPIAttributeException(JSONAPIException):
    def __init__(self, detail=None, attribute=None):
        source = {
            'pointer': '/data/attributes/{}'.format(attribute)
        }
        super(JSONAPIAttributeException, self).__init__(detail=detail, source=source)


class InvalidQueryStringError(JSONAPIParameterException):
    """Raised when client passes an invalid value to a query string parameter."""
    default_detail = 'Query string contains an invalid value.'
    status_code = http.BAD_REQUEST


class InvalidFilterOperator(JSONAPIParameterException):
    """Raised when client passes an invalid operator to a query param filter."""
    status_code = http.BAD_REQUEST

    def __init__(self, detail=None, value=None, valid_operators=('eq', 'lt', 'lte', 'gt', 'gte', 'contains', 'icontains')):
        if value and not detail:
            valid_operators = ', '.join(valid_operators)
            detail = "Value '{0}' is not a supported filter operator; use one of {1}.".format(
                value,
                valid_operators
            )
        super(InvalidFilterOperator, self).__init__(detail=detail, parameter='filter')


class InvalidFilterValue(JSONAPIParameterException):
    """Raised when client passes an invalid value to a query param filter."""
    status_code = http.BAD_REQUEST

    def __init__(self, detail=None, value=None, field_type=None):
        if not detail:
            detail = "Value '{0}' is not valid".format(value)
            if field_type:
                detail += ' for a filter on type {0}'.format(
                    field_type
                )
            detail += '.'
        super(InvalidFilterValue, self).__init__(detail=detail, parameter='filter')


class InvalidFilterError(JSONAPIParameterException):
    """Raised when client passes an malformed filter in the query string."""
    default_detail = _('Query string contains a malformed filter.')
    status_code = http.BAD_REQUEST

    def __init__(self, detail=None):
        super(InvalidFilterError, self).__init__(detail=detail, parameter='filter')


class InvalidFilterComparisonType(JSONAPIParameterException):
    """Raised when client tries to filter on a field that is not a date or number type"""
    default_detail = _('Comparison operators are only supported for dates and numbers.')
    status_code = http.BAD_REQUEST


class InvalidFilterMatchType(JSONAPIParameterException):
    """Raised when client tries to do a match filter on a field that is not a string or a list"""
    default_detail = _('Match operators are only supported for strings and lists.')
    status_code = http.BAD_REQUEST


class InvalidFilterFieldError(JSONAPIParameterException):
    """Raised when client tries to filter on a field that is not supported"""
    default_detail = _('Query contained one or more filters for invalid fields.')
    status_code = http.BAD_REQUEST

    def __init__(self, detail=None, parameter=None, value=None):
        if value and not detail:
            detail = "Value '{}' is not a filterable field.".format(value)
        super(InvalidFilterFieldError, self).__init__(detail=detail, parameter=parameter)


class CASJSONWebEncryptionError(JSONAPIException):
    """ Raised when client tries to make a request to CAS endpoint without proper JWE/JWT encryption.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = 40101
    default_detail = _('API CAS endpoint fails to verify the JWE/JWT encryption of the request.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(CASJSONWebEncryptionError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class InvalidPasswordError(JSONAPIException):
    """ Raised when CAS provides an invalid password for username/password login.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = 40102
    default_detail = _('Invalid password.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(InvalidPasswordError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class InvalidVerificationKeyError(JSONAPIException):
    """ Raised when CAS provides an invalid verification key for username/verification_key login.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = 40103
    default_detail = _('Invalid verification key.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(InvalidVerificationKeyError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class InvalidExternalIdentityError(JSONAPIException):
    """ Raised when CAS provides an invalid external identity for login through external identity provider.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = 40104
    default_detail = _('Invalid External Identity.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(InvalidExternalIdentityError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class TwoFactorRequiredError(JSONAPIException):
    """ Raised when two factor is required for API authentication or any type CAS login.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = 40105
    default_detail = _('Must specify two-factor authentication OTP code.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(TwoFactorRequiredError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class TwoFactorFailedError(JSONAPIException):
    """ Raised when two factor fails for any CAS login.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = 40106
    default_detail = _('Two factor authentication failed for login.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(TwoFactorFailedError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class InvalidInstitutionLoginError(JSONAPIException):
    """ Raised when CAS provides an invalid institution or user for institution login.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = 40107
    default_detail = _('Institution Login Failed')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(InvalidInstitutionLoginError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class MalformedRequestError(JSONAPIException):
    """ Raised when the API server fails parse the successfully decrypted request body.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40001
    default_detail = _('Fail to parse the CAS request body.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(MalformedRequestError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class OauthScopeError(JSONAPIException):
    """ Raised when CAS provides an invalid or inactive scope.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40002
    default_detail = _('The scope requested is not found or inactive.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(OauthScopeError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class OauthPersonalAccessTokenError(JSONAPIException):
    """ Raised when CAS provides an invalid personal access token
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40003
    default_detail = _('The personal access token requested is not found or invalid.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(OauthPersonalAccessTokenError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class EmailAlreadyRegisteredError(JSONAPIException):
    """ Raised when CAS tries to create an account with an email that has already been registered.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40004
    default_detail = _('This email has already been registered with OSF.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(EmailAlreadyRegisteredError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class EmailAlreadyConfirmedError(JSONAPIException):
    """ Raise when CAS tries to confirm an email that has already been confirmed.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40005
    default_detail = _('This email has already been confirmed.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(EmailAlreadyConfirmedError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class InvalidOrBlacklistedEmailError(JSONAPIException):
    """ Raised when CAS tries to create and account with an email that is invalid or has been blacklisted.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40006
    default_detail = _('This email is invalid or blacklisted')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(InvalidOrBlacklistedEmailError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class PasswordSameAsEmailError(JSONAPIException):
    """ Raised when CAS tries to set a password which is the same as one of the user's email address.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40007
    default_detail = _('Password cannot be the same as your email address.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(PasswordSameAsEmailError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class AccountNotEligibleError(JSONAPIException):
    """ Raise when an account is not eligible for the requested action.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40008
    default_detail = _('The OSF account associated with this email is not eligible for the requested action.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(AccountNotEligibleError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class AccountNotFoundError(JSONAPIException):
    """ Raised when the account associated with an email, a GUID or an external identity is not found.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40009
    default_detail = _('Account not found.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(AccountNotFoundError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class UnconfirmedAccountError(JSONAPIException):
    """ Raised when the account is created but not confirmed.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40010
    default_detail = _('Please confirm your account before using the API.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(UnconfirmedAccountError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class UnclaimedAccountError(JSONAPIException):
    """ Raised when the account is created but not claimed.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40011
    default_detail = _('Please claim your account before using the API.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(UnclaimedAccountError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class DeactivatedAccountError(JSONAPIException):
    """ Raised when the account is disabled.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40012
    default_detail = _('Making API requests with credentials associated with a deactivated account is not allowed.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(DeactivatedAccountError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class MergedAccountError(JSONAPIException):
    """ Raised when the account has already been merged by another one.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40013
    default_detail = _('Making API requests with credentials associated with a merged account is not allowed.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(MergedAccountError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class InvalidAccountError(JSONAPIException):
    """ Raised when the account is in an invalid status that is unexpected.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40014
    default_detail = _('Making API requests with credentials associated with an invalid account is not allowed.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(InvalidAccountError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class ExternalIdentityAlreadyClaimedError(JSONAPIException):
    """ Raised when CAS tries to register an external identity that has already been claimed.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40015
    default_detail = _('The external identity has already been claimed by another user.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(ExternalIdentityAlreadyClaimedError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class InvalidVerificationCodeError(JSONAPIException):
    """ Raised when CAS provides an invalid verification code for account management.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40016
    default_detail = _('The verification code is invalid.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(InvalidVerificationCodeError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class ExpiredVerificationCodeError(JSONAPIException):
    """ Raised when CAS provides an expired verification code for account management.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40017
    default_detail = _('The verification code has expired.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(ExpiredVerificationCodeError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class EmailThrottleActiveError(JSONAPIException):
    """ Raised when a user tries to resend confirmation email or request password reset too frequently
    """
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = 40018
    default_detail = _('You have recently make the same request. Please wait a few minutes before trying again.')

    def __init__(self, detail=None, source=None, meta=None, code=error_code):
        super(EmailThrottleActiveError, self).__init__(detail=detail, source=source, meta=meta, code=code)


class CASRequestFailedError(JSONAPIException):
    """ Raised when an unexpected error occurs when API processing the CAS request.
    """
    code = 50001
    default_detail = _('Request failed! A server error has occurred.')


class InvalidModelValueError(JSONAPIException):
    status_code = 400
    default_detail = _('Invalid value in POST/PUT/PATCH request.')


class TargetNotSupportedError(Exception):
    """Raised if a TargetField is used for a resource that isn't supported."""
    pass


class RelationshipPostMakesNoChanges(Exception):
    """Raised when a post is on a relationship that already exists, so view can return a 204"""
    pass


class NonDescendantNodeError(APIException):
    """Raised when a client attempts to associate a non-descendant node with a view only link"""
    status_code = 400
    default_detail = _('The node {0} cannot be affiliated with this View Only Link because the node you\'re trying to affiliate is not descended from the node that the View Only Link is attached to.')

    def __init__(self, node_id, detail=None):
        if not detail:
            detail = self.default_detail.format(node_id)
        super(NonDescendantNodeError, self).__init__(detail=detail)
