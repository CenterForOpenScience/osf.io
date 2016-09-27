# -*- coding: utf-8 -*-
import re
from django.core.validators import URLValidator, validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from osf_models.exceptions import ValidationError, ValidationValueError, reraise_django_validation_errors

from osf_models.utils.base import strip_html
from django.utils.deconstruct import deconstructible

from website.notifications.constants import NOTIFICATION_TYPES
from website import settings

def string_required(value):
    if value is None or value.strip() == '':
        raise ValidationValueError('Value must not be empty.')
    return True


def validate_subscription_type(value):
    if value not in NOTIFICATION_TYPES:
        raise ValidationValueError

def validate_title(value):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 200 characters.
    """
    if value is None or not value.strip():
        raise ValidationValueError('Title cannot be blank.')

    value = strip_html(value)

    if value is None or not value.strip():
        raise ValidationValueError('Invalid title.')

    if len(value) > 200:
        raise ValidationValueError('Title cannot exceed 200 characters.')

    return True

def validate_page_name(value):
    value = (value or '').strip()

    if not value:
        raise ValidationError('Page name cannot be blank.')
    if value.find('/') != -1:
        raise ValidationError('Page name cannot contain forward slashes.')
    return True

validate_url = URLValidator()

def validate_profile_websites(profile_websites):
    for value in profile_websites or []:
        try:
            validate_url(value)
        except DjangoValidationError:
            # Reraise with a better message
            raise ValidationError('Invalid personal URL.')

def validate_social(value):
    validate_profile_websites(value.get('profileWebsites'))

def validate_email(value):
    with reraise_django_validation_errors():
        django_validate_email(value)
    if value.split('@')[1].lower() in settings.BLACKLISTED_DOMAINS:
        raise ValidationError('Invalid Email')

@deconstructible
class CommentMaxLength(object):
    mention_re = re.compile(r'\[([@|\+].*?)\]\(htt[ps]{1,2}:\/\/[a-z\d:.]+?\/[a-z\d]{5}\/\)')
    max_length = None

    def __init__(self, max_length=500):
        self.max_length = max_length

    @staticmethod
    def link_repl(matchobj):
        return matchobj.group(1)

    def __call__(self, value):
        reduced_comment = self.mention_re.sub(self.link_repl(value))
        if len(reduced_comment) > self.max_length + 2:
            raise ValidationValueError(
                'Ensure this field has no more than {} characters.'.format(self.max_length))

        return True
