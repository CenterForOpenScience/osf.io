from rest_framework.exceptions import APIException
from rest_framework import status

def jsonapi_exception_handler(exc, context):
    """
    Custom exception handler that returns errors object as an array with a 'detail' member
    """
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    if response is not None:
        if 'detail' in response.data:
            response.data = {'errors': [response.data]}
        else:
            response.data = {'errors': [{'detail': response.data}]}

    return response


# Custom Exceptions the Django Rest Framework does not support
class Gone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = ('The requested resource is no longer available.')
