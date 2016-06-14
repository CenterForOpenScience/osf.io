import httplib as http
from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed


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
            errors.extend([{'source': exc.source or {}, 'detail': exc.detail, 'meta': exc.meta or {}}])
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

    def __init__(self, detail=None, source=None, meta=None):
        super(JSONAPIException, self).__init__(detail=detail)
        self.source = source
        self.meta = meta


# Custom Exceptions the Django Rest Framework does not support
class Gone(JSONAPIException):
    status_code = status.HTTP_410_GONE
    default_detail = ('The requested resource is no longer available.')


class Conflict(APIException):
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


class UnconfirmedAccountError(APIException):
    status_code = 400
    default_detail = _('Please confirm your account before using the API.')


class DeactivatedAccountError(APIException):
    status_code = 400
    default_detail = _('Making API requests with credentials associated with a deactivated account is not allowed.')


class TwoFactorRequiredError(AuthenticationFailed):
    default_detail = _('Must specify two-factor authentication OTP code.')
    pass


class InvalidModelValueError(JSONAPIException):
    status_code = 400
    default_detail = _('Invalid value in POST/PUT/PATCH request.')


class TargetNotSupportedError(Exception):
    """Raised if a TargetField is used for a resource that isn't supported."""
    pass

class RelationshipPostMakesNoChanges(Exception):
    """Raised when a post is on a relationship that already exists, so view can return a 204"""
    pass
