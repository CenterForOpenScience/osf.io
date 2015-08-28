from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField, Link
from website.models import User
from rest_framework.fields import empty, SkipField, get_attribute, CharField, MaxLengthValidator, MinLengthValidator, URLValidator, URLField


class SocialCharField(ser.CharField):

    def __init__(self, social_default, **kwargs):
        self.allow_blank = kwargs.pop('allow_blank', False)
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        super(CharField, self).__init__(**kwargs)
        if self.max_length is not None:
            message = self.error_messages['max_length'].format(max_length=self.max_length)
            self.validators.append(MaxLengthValidator(self.max_length, message=message))
        if self.min_length is not None:
            message = self.error_messages['min_length'].format(min_length=self.min_length)
            self.validators.append(MinLengthValidator(self.min_length, message=message))
        self.social_default = social_default

    def get_attribute(self, instance):
        """
        Given the *outgoing* object instance, return the primitive value
        that should be used for this field.
        """
        try:
            return get_attribute(instance, self.source_attrs)
        except (KeyError, AttributeError) as exc:
            if not self.required and self.default and self.social_default is empty:
                raise SkipField()
            if self.social_default == '':
                return self.social_default
            msg = (
                'Got {exc_type} when attempting to get a value for field '
                '`{field}` on serializer `{serializer}`.\nThe serializer '
                'field might be named incorrectly and not match '
                'any attribute or key on the `{instance}` instance.\n'
                'Original exception text was: {exc}.'.format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc
                )
            )
            raise type(exc)(msg)


class SocialUrlField(ser.URLField):

    def __init__(self, social_default, **kwargs):
        super(URLField, self).__init__(**kwargs)
        validator = URLValidator(message=self.error_messages['invalid'])
        self.validators.append(validator)
        self.social_default = social_default

    def get_attribute(self, instance):
        """
        Given the *outgoing* object instance, return the primitive value
        that should be used for this field.
        """
        try:
            return get_attribute(instance, self.source_attrs)
        except (KeyError, AttributeError) as exc:
            if not self.required and self.default and self.social_default is empty:
                raise SkipField()
            if self.social_default == '':
                return self.social_default
            msg = (
                'Got {exc_type} when attempting to get a value for field '
                '`{field}` on serializer `{serializer}`.\nThe serializer '
                'field might be named incorrectly and not match '
                'any attribute or key on the `{instance}` instance.\n'
                'Original exception text was: {exc}.'.format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc
                )
            )
            raise type(exc)(msg)


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'fullname',
        'given_name',
        'middle_names',
        'family_name',
        'id'
    ])
    id = ser.CharField(read_only=True, source='_id')
    fullname = ser.CharField(required=True, help_text='Display name used in the general user interface')
    given_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    middle_names = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    suffix = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)
    gravatar_url = ser.URLField(required=False, read_only=True,
                                help_text='URL for the icon used to identify the user. Relies on http://gravatar.com ')

    # Social Fields are broken out to get around DRF complex object bug and to make API updating more user friendly.
    gitHub = SocialCharField(required=False, social_default='', source='social.github',
                             allow_blank=True, help_text='GitHub Handle')
    scholar = SocialCharField(required=False, social_default='', source='social.scholar',
                              allow_blank=True, help_text='Google Scholar Account')
    personal_website = SocialUrlField(required=False, social_default='', source='social.personal',
                                      allow_blank=True, help_text='Personal Website')
    twitter = SocialCharField(required=False, social_default='', source='social.twitter',
                              allow_blank=True, help_text='Twitter Handle')
    linkedIn = SocialCharField(required=False, social_default='', source='social.linkedIn',
                               allow_blank=True, help_text='LinkedIn Account')
    impactStory = SocialCharField(required=False, social_default='', source='social.impactStory',
                                  allow_blank=True, help_text='ImpactStory Account')
    orcid = SocialCharField(required=False, social_default='', source='social.orcid',
                            allow_blank=True, help_text='ORCID')
    researcherId = SocialCharField(required=False, social_default='', source='social.researcherId',
                                   allow_blank=True, help_text='ResearcherId Account')

    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'user_id': '<pk>'})
        }
    })

    class Meta:
        type_ = 'users'

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        assert isinstance(instance, User), 'instance must be a User'
        for attr, value in validated_data.items():
            # If the field is the social dictionary, then update the original social values with the new ones, and save.
            # If its any other field, just update with the value.
            if attr == 'social':
                social_fields = instance.social
                social_fields.update(value)
                setattr(instance, attr, social_fields)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')
