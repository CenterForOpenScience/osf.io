# -*- coding: utf-8 -*-
import re
import waffle
import jsonschema

from django.core.validators import URLValidator, validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.deconstruct import deconstructible
from past.builtins import basestring
from rest_framework import exceptions

from website.notifications.constants import NOTIFICATION_TYPES

from osf.utils.registrations import FILE_VIEW_URL_REGEX
from osf.utils.sanitize import strip_html
from osf.exceptions import ValidationError, ValidationValueError, reraise_django_validation_errors, BlacklistedEmailError

from website.language import SWITCH_VALIDATOR_ERROR

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
            if isinstance(item, basestring) and len(item) != 4:
                raise ValidationValueError('Please enter a valid year.')


def string_required(value):
    if value is None or value.strip() == '':
        raise ValidationValueError('Value must not be empty.')
    return True


def validate_subscription_type(value):
    if value not in NOTIFICATION_TYPES:
        raise ValidationValueError


def validate_title(value, allow_blank=False):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 512 characters.
    """

    if not allow_blank:
        if value is None or not value.strip():
            raise ValidationValueError('Title cannot be blank.')

    value = strip_html(value)

    if not allow_blank:
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

def validate_subjects(subject_list):
    """
    Asserts all subjects in subject_list are valid subjects
    :param subject_list list[Subject._id] List of flattened subject ids
    :return Subject queryset
    """
    from osf.models import Subject
    subjects = Subject.objects.filter(_id__in=subject_list)
    if subjects.count() != len(subject_list):
        raise ValidationValueError('Subject not found.')
    return subjects

def expand_subject_hierarchy(subject_list):
    """
    Takes flattened subject list which may or may not include all parts
    of the subject hierarchy and supplements with all the parents

    :param subject_list list[Subject._id] List of flattened subjects
    :return list of flattened subjects, supplemented with parents
    """
    subjects = validate_subjects(subject_list)
    expanded_subjects = []
    for subj in subjects:
        expanded_subjects.append(subj)
        while subj.parent:
            if subj.parent not in expanded_subjects:
                expanded_subjects.append(subj.parent)
            subj = subj.parent
    return expanded_subjects

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


class RegistrationResponsesValidator:
    NON_EMPTY_STRING = {
        'type': 'string',
        'minLength': 1,
    }

    FILE_REFERENCE = {
        'type': 'object',
        'additionalProperties': False,
        'required': ['file_id', 'file_name', 'file_urls', 'file_hashes'],
        'properties': {
            'file_name': NON_EMPTY_STRING,
            'file_id': NON_EMPTY_STRING,
            'file_urls': {
                'type': 'object',
                'minProperties': 1,  # at least one identifying URL
                'additionalProperties': False,
                'required': ['html'],  # html/view URL is required by archiver and for converting to legacy "nested" format
                'properties': {
                    'html': {
                        'type': 'string',
                        'regex': FILE_VIEW_URL_REGEX,  # loosen this constraint to `format: iri` when we can drop the legacy format
                    },
                    'download': {
                        'type': 'string',
                        'format': 'iri',
                    },
                },
            },
            'file_hashes': {
                'type': 'object',
                'minProperties': 1,  # at least one hash
                'additionalProperties': False,
                'properties': {
                    'sha256': NON_EMPTY_STRING,
                },
            },
        },
    }

    def __init__(self, schema_blocks, required_fields):
        """For validating `registration_responses` on Registrations and DraftRegistrations

        :params schema_blocks iterable of SchemaBlock instances
        :params required_fields boolean - do we want to enforce that required fields are present
        """
        self.schema_blocks = schema_blocks
        self.required_fields = required_fields
        self.json_schema = self._build_json_schema()

    def validate(self, registration_responses):
        """Validate the given registration_responses

        :returns True (if valid)
        :raises ValidationError (if invalid)
        """
        try:
            jsonschema.validate(registration_responses, self.json_schema)
        except jsonschema.ValidationError as e:
            properties = self.json_schema.get('properties', {})
            relative_path = getattr(e, 'relative_path', None)
            question_id = relative_path[0] if relative_path else ''
            if properties.get(question_id, None):
                question_title = properties.get(question_id).get('description') or question_id
                if e.relative_schema_path[0] == 'required':
                    raise ValidationError(
                        'For your registration the \'{}\' field is required'.format(question_title)
                    )
                elif 'enum' in properties.get(question_id):
                    raise ValidationError(
                        'For your registration, your response to the \'{}\' field is invalid, your response must be one of the provided options.'.format(
                            question_title,
                        ),
                    )
                else:
                    raise ValidationError(
                        'For your registration, your response to the \'{}\' field is invalid. {}'.format(question_title, e.message),
                    )
            raise ValidationError(e.message)
        except jsonschema.SchemaError as e:
            raise ValidationError(e.message)
        return True

    def _build_json_schema(self):
        """Builds jsonschema for validating flattened registration_responses field
        """
        # schema blocks corresponding to registration_responses
        questions = [
            block for block in self.schema_blocks
            if block.registration_response_key is not None
        ]

        properties = {
            question.registration_response_key: self._build_question_schema(question)
            for question in questions
        }

        json_schema = {
            'type': 'object',
            'additionalProperties': False,
            'properties': properties
        }

        if self.required_fields:
            json_schema['required'] = [
                question.registration_response_key
                for question in questions
                if question.required
            ]

        return json_schema

    def _get_multiple_choice_options(self, question):
        """
        Returns a dictionary with an 'enum' key, and a value as
        an array with the possible multiple choice answers for a given question.
        Schema blocks are linked by schema_block_group_keys, so fetches multiple choice options
        with the same schema_block_group_key as the given question
        :question SchemaBlock with an registration_response_key
        """
        options = [
            block.display_text
            for block in self.schema_blocks
            if block.block_type == 'select-input-option'
            and block.schema_block_group_key == question.schema_block_group_key
        ]

        # required is True if we want to both enforce required_fields
        # and the question in particular is required.
        required = self.required_fields and question.required
        if not required and '' not in options:
            options.append('')

        return options

    def _build_question_schema(self, question):
        """
        Returns json for validating an individual question
        :params question SchemaBlock
        """
        question_text = next(
            (
                block.display_text
                for block in self.schema_blocks
                if block.block_type == 'question-label'
                and block.schema_block_group_key == question.schema_block_group_key
            ),
            question.registration_response_key,  # default
        )

        if question.block_type == 'single-select-input':
            return {
                'type': 'string',
                'enum': self._get_multiple_choice_options(question),
                'description': question_text,
            }
        elif question.block_type == 'multi-select-input':
            return {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'enum': self._get_multiple_choice_options(question),
                },
                'description': question_text,
            }
        elif question.block_type == 'file-input':
            return {
                'type': 'array',
                'items': self.FILE_REFERENCE,
                'description': question_text,
            }
        elif question.block_type in ('short-text-input', 'long-text-input', 'contributors-input'):
            if self.required_fields and question.required:
                return {
                    'type': 'string',
                    'minLength': 1,
                    'description': question_text,
                }
            else:
                return {
                    'type': 'string',
                    'description': question_text,
                }

        raise ValueError('Unexpected `block_type`: {}'.format(question.block_type))


class SwitchValidator(object):
    def __init__(self, switch_name: str, message: str = SWITCH_VALIDATOR_ERROR, should_be: bool = True):
        """
        This throws a validation error if a switched off field is prematurely used. This the on/off state of the field
        is determined by the validators `should_be` value, if the switch's active value is `not` what it `should_be` a
        validation error is thrown.

        Remember turning a switch off (to active to False) can mean turning a feature on and vice versa, so use the
        `should_be` value appropriately.

        :param switch_name: String The switch's name
        :param message: String The error message to be displayed if validation fails
        :param should_be: Boolean The value that must match the switch value to avoid a validation error
        """
        self.switch_name = switch_name
        self.should_be = should_be
        self.message = message

    def __call__(self, value):
        if waffle.switch_is_active(self.switch_name) != self.should_be:
            raise exceptions.ValidationError(detail=self.message)

        return value
