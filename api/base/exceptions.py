
from rest_framework import status
from rest_framework.exceptions import APIException, ParseError


def json_api_exception_handler(exc, context):
    """ Custom exception handler that returns errors object as an array """

    # Import inside method to avoid errors when the OSF is loaded without Django
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    # Error objects may have the following members. Title removed to avoid clash with node "title" errors.
    top_level_error_keys = ['id', 'links', 'status', 'code', 'detail', 'source', 'meta']
    errors = []

    if response:
        message = response.data

        if isinstance(message, dict):
            for error_key, error_description in message.iteritems():
                if error_key in top_level_error_keys:
                    errors.append({error_key: error_description})
                else:
                    if isinstance(error_description, basestring):
                        error_description = [error_description]
                    errors.extend([{'source': {'pointer': '/data/attributes/' + error_key}, 'detail': reason}
                                   for reason in error_description])
        else:
            if isinstance(message, basestring):
                message = [message]
            errors.extend([{'detail': error} for error in message])

        response.data = {'errors': errors}

    return response


# Custom Exceptions the Django Rest Framework does not support
class Gone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = ('The requested resource is no longer available.')


class InvalidFilterError(ParseError):
    """Raised when client passes an invalid filter in the querystring."""
    default_detail = 'Querystring contains an invalid filter.'
