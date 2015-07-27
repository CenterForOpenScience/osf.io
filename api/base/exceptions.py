
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

    # Return 401 instead of 403 during unauthorized requests without having user log in with Basic Auth
    if response is not None and response.data['errors'][0]['detail'] == "Authentication credentials were not provided.":
        response.status_code = 401

    return response
