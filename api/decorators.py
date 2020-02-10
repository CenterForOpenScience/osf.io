import functools

from rest_framework.exceptions import ValidationError as RestValidationError
from django.core.exceptions import ValidationError


def rethrow_validation_error_for_serializer(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            raise RestValidationError(detail=e.message)

    return wrapped
