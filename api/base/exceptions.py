from rest_framework.exceptions import APIException

#Custom Exceptions the Django Rest Framework does not support

class Gone(APIException):
    status_code = 410
    default_detail = 'Gone: The requested resource is no longer available.'
