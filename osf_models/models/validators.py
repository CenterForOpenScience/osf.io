from django.core.exceptions import ValidationError

from website.util import sanitize


def validate_title(value):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 200 characters.
    """
    if value is None or not value.strip():
        raise ValidationError('Title cannot be blank.')

    value = sanitize.strip_html(value)

    if value is None or not value.strip():
        raise ValidationError('Invalid title.')

    if len(value) > 200:
        raise ValidationError('Title cannot exceed 200 characters.')

    return True
