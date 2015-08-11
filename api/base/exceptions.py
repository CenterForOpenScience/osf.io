from rest_framework.exceptions import APIException
from rest_framework import status

#Custom Exceptions the Django Rest Framework does not support

class Gone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = ('The requested resource is no longer available.')
