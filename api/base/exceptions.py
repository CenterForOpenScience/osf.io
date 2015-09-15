
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
            for key, value in message.iteritems():
                if key in top_level_error_keys:
                    errors.append({key: value})
                else:
                    if isinstance(value, list):
                        for reason in value:
                            errors.append({'detail': reason, 'meta': {'field': key}})
                    else:
                        errors.append({'detail': value, 'meta': {'field': key}})
        elif isinstance(message, (list, tuple)):
            for error in message:
                errors.append({'detail': error})
        else:
            errors.append({'detail': message})

        response.data = {'errors': errors}

    return response


# Custom Exceptions the Django Rest Framework does not support
class Gone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = ('The requested resource is no longer available.')


class InvalidFilterError(ParseError):
    """Raised when client passes an invalid filter in the querystring."""
    default_detail = 'Querystring contains an invalid filter.'
