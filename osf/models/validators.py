# -*- coding: utf-8 -*-
import re

from django.core.validators import URLValidator, validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.deconstruct import deconstructible

from website.notifications.constants import NOTIFICATION_TYPES
from website.util.sanitize import strip_html
from website import settings

from osf.exceptions import ValidationError, ValidationValueError, reraise_django_validation_errors


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
        reduced_comment = self.mention_re.sub(self.link_repl, value)
        if len(reduced_comment) > self.max_length + 2:
            raise ValidationValueError(
                'Ensure this field has no more than {} characters.'.format(self.max_length))

        return True


sanitize_pattern = re.compile(r'<\/?[^>]+>')
def validate_no_html(value):
    if value != sanitize_pattern.sub('', value):
        raise ValidationError('Unsanitary string')
    return True


def validate_doi(value):
    # DOI must start with 10 and have a slash in it - avoided getting too complicated
    if not re.match('10\\.\\S*\\/', value):
        raise ValidationValueError('"{}" is not a valid DOI'.format(value))
    return True


def validate_location(value):
    if value is None:
        return  # Allow for None locations but not broken dicts
    from addons.osfstorage import settings

    for key in ('service', settings.WATERBUTLER_RESOURCE, 'object'):
        if key not in value:
            raise ValidationValueError('Location {} missing key "{}"'.format(value, key))
    return True
