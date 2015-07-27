
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
