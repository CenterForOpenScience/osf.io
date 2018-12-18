# -*- coding: utf-8 -*-
import re

from django.core.validators import URLValidator, validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.deconstruct import deconstructible
from django.utils.six import string_types

from website.notifications.constants import NOTIFICATION_TYPES

from osf.utils.sanitize import strip_html
from osf.exceptions import ValidationError, ValidationValueError, reraise_django_validation_errors, BlacklistedEmailError


def validate_history_item(items):
    for value in items or []:
        string_required(value.get('institution'))
        startMonth = value.get('startMonth')
        startYear = value.get('startYear')
        endMonth = value.get('endMonth')
        endYear = value.get('endYear')

        validate_year(startYear)
        validate_year(endYear)

        if startYear and endYear:
            if endYear < startYear:
                raise ValidationValueError('End date must be later than start date.')
            elif endYear == startYear:
                if endMonth and startMonth and endMonth < startMonth:
                    raise ValidationValueError('End date must be later than start date.')


def validate_year(item):
    if item:
        try:
            int(item)
        except ValueError:
            raise ValidationValueError('Please enter a valid year.')
        else:
            if isinstance(item, string_types) and len(item) != 4:
                raise ValidationValueError('Please enter a valid year.')


def string_required(value):
    if value is None or value.strip() == '':
        raise ValidationValueError('Value must not be empty.')
    return True


def validate_subscription_type(value):
    if value not in NOTIFICATION_TYPES:
        raise ValidationValueError


def validate_title(value):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 512 characters.
    """
    if value is None or not value.strip():
        raise ValidationValueError('Title cannot be blank.')

    value = strip_html(value)

    if value is None or not value.strip():
        raise ValidationValueError('Invalid title.')

    if len(value) > 512:
        raise ValidationValueError('Title cannot exceed 512 characters.')

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
    from osf.models import OSFUser
    for soc_key in value.keys():
        if soc_key not in OSFUser.SOCIAL_FIELDS:
            raise ValidationError('{} is not a valid key for social.'.format(soc_key))

def validate_email(value):
    from osf.models import BlacklistedEmailDomain
    with reraise_django_validation_errors():
        django_validate_email(value)
    domain = value.split('@')[1].lower()
    if BlacklistedEmailDomain.objects.filter(domain=domain).exists():
        raise BlacklistedEmailError('Invalid Email')


def validate_subject_highlighted_count(provider, is_highlighted_addition):
    if is_highlighted_addition and provider.subjects.filter(highlighted=True).count() >= 10:
        raise DjangoValidationError('Too many highlighted subjects for PreprintProvider {}'.format(provider._id))

def validate_subject_hierarchy_length(parent):
    from osf.models import Subject
    parent = Subject.objects.get(id=parent)
    if parent and len(parent.hierarchy) >= 3:
        raise DjangoValidationError('Invalid hierarchy')

def validate_subject_provider_mapping(provider, mapping):
    if not mapping and provider._id != 'osf':
        raise DjangoValidationError('Invalid PreprintProvider / Subject alias mapping.')

def validate_subject_hierarchy(subject_hierarchy):
    from osf.models import Subject
    validated_hierarchy, raw_hierarchy = [], set(subject_hierarchy)
    for subject_id in subject_hierarchy:
        subject = Subject.load(subject_id)
        if not subject:
            raise ValidationValueError('Subject with id <{}> could not be found.'.format(subject_id))

        if subject.parent:
            continue

        raw_hierarchy.remove(subject_id)
        validated_hierarchy.append(subject._id)

        while raw_hierarchy:
            if not set(subject.children.values_list('_id', flat=True)) & raw_hierarchy:
                raise ValidationValueError('Invalid subject hierarchy: {}'.format(subject_hierarchy))
            else:
                for child in subject.children.filter(_id__in=raw_hierarchy):
                    subject = child
                    validated_hierarchy.append(child._id)
                    raw_hierarchy.remove(child._id)
                    break
        if set(validated_hierarchy) == set(subject_hierarchy):
            return
        else:
            raise ValidationValueError('Invalid subject hierarchy: {}'.format(subject_hierarchy))
    raise ValidationValueError('Unable to find root subject in {}'.format(subject_hierarchy))


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
