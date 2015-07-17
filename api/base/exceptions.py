from rest_framework.exceptions import APIException


class Gone(APIException):
    status_code = 410
    default_detail = 'Gone: The requested resource is no longer available.'
