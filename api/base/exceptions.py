
from rest_framework import status
from rest_framework.exceptions import APIException


def json_api_exception_handler(exc, context):
    """
    Custom exception handler that returns errors object as an array
    """
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    # Title removed to avoid clash with node "title" errors
    acceptable_members = ['id', 'links', 'status', 'code', 'detail', 'source', 'meta']
    errors = []

    if response is not None:
        message = response.data
        if isinstance(message, dict):
            for key, value in message.iteritems():
                if key in acceptable_members:
                    errors.append({key: value})
                else:
                    errors.append({'detail': {key: value}})
        elif isinstance(message, list):
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
