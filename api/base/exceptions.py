from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import APIException
from rest_framework import status


class Accepted(APIException):
    status_code = status.HTTP_202_ACCEPTED
    default_detail = _('Accepted')
