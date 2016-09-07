from osf_models.exceptions import ValidationError, ValidationValueError

from osf_models.utils.base import strip_html

from website.notifications.constants import NOTIFICATION_TYPES


def validate_subscription_type(value):
    if value not in NOTIFICATION_TYPES:
        raise ValidationValueError

def validate_title(value):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 200 characters.
    """
    if value is None or not value.strip():
        raise ValidationError('Title cannot be blank.')

    value = strip_html(value)

    if value is None or not value.strip():
        raise ValidationError('Invalid title.')

    if len(value) > 200:
        raise ValidationError('Title cannot exceed 200 characters.')

    return True

def validate_page_name(value):
    value = (value or '').strip()

    if not value:
        raise ValidationError('Page name cannot be blank.')
    if value.find('/') != -1:
        raise ValidationError('Page name cannot contain forward slashes.')
    return True
