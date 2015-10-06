import httplib as http

from rest_framework import status
from rest_framework.exceptions import APIException, ParseError

def json_api_exception_handler(exc, context):
    """ Custom exception handler that returns errors object as an array """

    # Import inside method to avoid errors when the OSF is loaded without Django
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    # Error objects may have the following members. Title and id removed to avoid clash with "title" and "id" field errors.
    top_level_error_keys = ['links', 'status', 'code', 'detail', 'source', 'meta']
    resource_object_identifiers = ['type', 'id']
    errors = []

    if response:
        message = response.data

        if isinstance(exc, JSONAPIException):
            errors.extend([
                {
                    'source': exc.source,
                    'detail': exc.detail,
                }
            ])
        elif isinstance(message, dict):
            for error_key, error_description in message.iteritems():
                if error_key in top_level_error_keys:
                    errors.append({error_key: error_description})
                elif error_key in resource_object_identifiers:
                    if isinstance(error_description, basestring):
                        error_description = [error_description]
                    errors.extend([{'source': {'pointer': '/data/' + error_key}, 'detail': reason} for reason in error_description])
                elif error_key == 'attributes':
                    if isinstance(error_description, list):
                        errors.extend([{'source': {'pointer': '/data/' + error_key}, 'detail': reason} for reason in error_description])
                else:
                    if isinstance(error_description, basestring):
                        error_description = [error_description]
                    errors.extend([{'source': {'pointer': '/data/attributes/' + error_key}, 'detail': reason} for reason in error_description])

        else:
            if isinstance(message, basestring):
                message = [message]
            errors.extend([{'detail': error} for error in message])

        response.data = {'errors': errors}

    return response


class ServiceUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service is unavailable at this time.'


class JSONAPIException(APIException):
    """Inherits from the base DRF API exception and adds extra metadata to support JSONAPI error objects

    :param str detail: a human-readable explanation specific to this occurrence of the problem
    :param dict source: A dictionary containing references to the source of the error.
        See http://jsonapi.org/format/#error-objects.
        Example: ``source={'pointer': '/data/attributes/title'}``
    """
    status_code = status.HTTP_400_BAD_REQUEST
    def __init__(self, detail=None, source=None):
        super(JSONAPIException, self).__init__(detail=detail)
        self.source = source

# Custom Exceptions the Django Rest Framework does not support
class Gone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = ('The requested resource is no longer available.')


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = ('Resource identifier does not match server endpoint.')


class InvalidQueryStringError(JSONAPIException):
    """Raised when client passes an invalid value to a query string parameter."""
    default_detail = 'Query string contains an invalid value.'
    status_code = http.BAD_REQUEST

    def __init__(self, detail=None, parameter=None):
        super(InvalidQueryStringError, self).__init__(detail=detail, source={
            'parameter': parameter
        })


class InvalidFilterError(ParseError):
    """Raised when client passes an invalid filter in the query string."""
    default_detail = 'Query string contains an invalid filter.'


class UnconfirmedAccountError(APIException):
    status_code = 400
    default_detail = 'Please confirm your account before using the API.'


class DeactivatedAccountError(APIException):
    status_code = 400
    default_detail = 'Making API requests with credentials associated with a deactivated account is not allowed.'


class InvalidModelValueError(JSONAPIException):
    status_code = 400
    default_detail = 'Invalid value in POST/PUT/PATCH request.'
